from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, session
from flask_login import login_user, logout_user, login_required, current_user
from . import db, limiter
from .models import User, Company, validate_ethiopian_phone
from .security import safe_redirect_target

auth = Blueprint('auth', __name__)


def _get_google_oauth():
    """Get the Google OAuth client, or None if not configured."""
    oauth = getattr(current_app, 'oauth', None)
    if oauth:
        return oauth.create_client('google')
    return None

# Endpoints allowed while must_change_password is True
_PASSWORD_CHANGE_ALLOWED = frozenset({
    'auth.change_password',
    'auth.logout',
    'auth.set_language',
    'static',
    'health',
})


@auth.before_app_request
def enforce_password_change():
    """Invited users must set their own password before using the app."""
    if not current_user.is_authenticated:
        return None
    if not getattr(current_user, 'must_change_password', False):
        return None
    endpoint = request.endpoint or ''
    if endpoint in _PASSWORD_CHANGE_ALLOWED:
        return None
    return redirect(url_for('auth.change_password'))


@auth.route('/login', methods=['GET', 'POST'])
@limiter.limit('5 per minute')
def login():
    if current_user.is_authenticated:
        if current_user.must_change_password:
            return redirect(url_for('auth.change_password'))
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        login_id = request.form.get('login_id', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        # Try to find user by phone or email
        user = None
        if login_id:
            # Check if it looks like a phone number
            cleaned = login_id.replace(' ', '')
            looks_like_phone = (
                cleaned.startswith('09') or cleaned.startswith('07') or
                cleaned.startswith('+251') or
                (cleaned.isdigit() and len(cleaned) == 9 and cleaned[0] in ('7', '9'))
            )
            if looks_like_phone:
                # Normalize phone and look up
                is_valid, normalized, _ = validate_ethiopian_phone(login_id)
                if is_valid:
                    user = User.query.filter_by(phone=normalized).first()
            if user is None:
                # Try email
                user = User.query.filter_by(email=login_id.lower()).first()

        if not user or not user.check_password(password):
            flash('Invalid credentials.', 'danger')
            return redirect(url_for('auth.login'))
        login_user(user, remember=remember)
        from datetime import datetime, timezone
        session['_login_time'] = datetime.now(timezone.utc).timestamp()
        session['_last_active'] = session['_login_time']
        session.permanent = True
        if user.must_change_password:
            flash('Please set a new password to continue. Your temporary password needs to be changed.', 'warning')
            return redirect(url_for('auth.change_password'))
        next_page = safe_redirect_target(request.args.get('next'))
        flash(f'Welcome back! Logged in as {user.phone or user.email}.', 'success')
        return redirect(next_page)
    return render_template(
        'auth/login.html',
        demo_enabled=bool(current_app.config.get('ENABLE_DEMO_MODE', False)),
        google_enabled=bool(current_app.config.get('GOOGLE_CLIENT_ID', '')),
    )


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
@limiter.limit('10 per minute')
def change_password():
    """Force or allow password change (required for invited temporary passwords)."""
    if request.method == 'POST':
        current = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        new_password2 = request.form.get('new_password2', '')

        if not current_user.check_password(current):
            flash('Current password is incorrect.', 'danger')
            return redirect(url_for('auth.change_password'))
        if new_password != new_password2:
            flash('New passwords do not match.', 'danger')
            return redirect(url_for('auth.change_password'))
        if len(new_password) < 8:
            flash('Password must be at least 8 characters.', 'danger')
            return redirect(url_for('auth.change_password'))
        if current_user.check_password(new_password):
            flash('New password must be different from the current password.', 'danger')
            return redirect(url_for('auth.change_password'))

        current_user.set_password(new_password)
        current_user.must_change_password = False
        db.session.commit()
        flash('Password updated. You can continue.', 'success')
        return redirect(url_for('main.index'))

    return render_template(
        'auth/change_password.html',
        forced=bool(current_user.must_change_password),
    )


@auth.route('/language/<lang>')
def set_language(lang):
    """Set UI language (en=English, am=Amharic, om=Afaan Oromoo)."""
    if lang not in ('en', 'am', 'om'):
        lang = 'en'
    from flask import session
    session['language'] = lang
    # referrer can be attacker-controlled; only follow safe same-host targets
    target = safe_redirect_target(request.referrer)
    return redirect(target)


@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip().lower() or None
        password = request.form.get('password', '')
        password2 = request.form.get('password2', '')
        company_name = request.form.get('company_name', '').strip() or None

        # Validate required fields
        if not phone or not password:
            flash('Phone and password are required.', 'danger')
            return redirect(url_for('auth.register'))

        # Validate phone format
        is_valid, normalized_phone, phone_error = validate_ethiopian_phone(phone)
        if not is_valid:
            flash(phone_error, 'danger')
            return redirect(url_for('auth.register'))

        # Validate password
        if password != password2:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('auth.register'))
        from payroll_engine.password_policy import check_password_strength
        is_strong, pw_error = check_password_strength(password)
        if not is_strong:
            flash(pw_error, 'danger')
            return redirect(url_for('auth.register'))

        # Check duplicate phone
        if User.query.filter_by(phone=normalized_phone).first():
            flash('Phone number already registered.', 'danger')
            return redirect(url_for('auth.register'))

        # Check duplicate email (if provided)
        if email and User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('auth.register'))

        # Create company if name provided (backward-compatible one-step flow)
        company = None
        if company_name:
            existing_company = Company.query.filter_by(name=company_name).first()
            if existing_company:
                flash('A company with that name already exists.', 'danger')
                return redirect(url_for('auth.register'))
            company = Company(name=company_name)
            db.session.add(company)
            db.session.flush()

        # Create user
        user = User(
            email=email,
            phone=normalized_phone,
            company_id=company.id if company else None,
            role='owner'
        )
        user.set_password(password)

        # Apply referral code if present
        referral_code = session.pop('referral_code', None)
        if referral_code:
            referrer = User.query.filter_by(referral_code=referral_code).first()
            if referrer:
                user.referred_by = referrer.id

        db.session.add(user)
        db.session.commit()
        flash('Account created! Please log in and set up your company.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html')


@auth.route('/google/login')
def google_login():
    """Initiate Google OAuth login."""
    google = _get_google_oauth()
    if not google:
        flash('Google sign-in is not configured.', 'danger')
        return redirect(url_for('auth.login'))
    redirect_uri = url_for('auth.google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)


@auth.route('/google/callback')
def google_callback():
    """Handle Google OAuth callback."""
    google = _get_google_oauth()
    if not google:
        flash('Google sign-in is not configured.', 'danger')
        return redirect(url_for('auth.login'))

    try:
        token = google.authorize_access_token()
    except Exception as e:
        current_app.logger.error('Google OAuth error: %s', e)
        flash('Google sign-in failed. Please try again.', 'danger')
        return redirect(url_for('auth.login'))

    resp = google.get('userinfo')
    if resp.status_code != 200:
        flash('Could not get user info from Google.', 'danger')
        return redirect(url_for('auth.login'))

    user_info = resp.json()
    email = user_info.get('email', '').lower()
    google_name = user_info.get('name', '')

    if not email:
        flash('Google account has no email. Please use phone login.', 'danger')
        return redirect(url_for('auth.login'))

    # Find existing user by email
    user = User.query.filter_by(email=email).first()

    if user:
        # Existing user — log them in
        login_user(user)
        from datetime import datetime, timezone
        session['_login_time'] = datetime.now(timezone.utc).timestamp()
        session['_last_active'] = session['_login_time']
        session.permanent = True
        flash('Welcome back!', 'success')
        next_page = safe_redirect_target(request.args.get('next'))
        return redirect(next_page)

    # New user — store Google info in session and redirect to complete registration
    session['google_email'] = email
    session['google_name'] = google_name
    return redirect(url_for('auth.google_register'))


@auth.route('/google/register', methods=['GET', 'POST'])
def google_register():
    """Complete registration for Google OAuth users."""
    email = session.get('google_email')
    google_name = session.get('google_name')

    if not email:
        flash('Session expired. Please try Google sign-in again.', 'danger')
        return redirect(url_for('auth.login'))

    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        company_name = request.form.get('company_name', '').strip()

        if not phone or not company_name:
            flash('Phone and company name are required.', 'danger')
            return redirect(url_for('auth.google_register'))

        is_valid, normalized_phone, phone_error = validate_ethiopian_phone(phone)
        if not is_valid:
            flash(phone_error, 'danger')
            return redirect(url_for('auth.google_register'))

        if User.query.filter_by(phone=normalized_phone).first():
            flash('Phone number already registered.', 'danger')
            return redirect(url_for('auth.google_register'))

        existing_company = Company.query.filter_by(name=company_name).first()
        if existing_company:
            flash('A company with that name already exists.', 'danger')
            return redirect(url_for('auth.google_register'))

        company = Company(name=company_name)
        db.session.add(company)
        db.session.commit()

        user = User(
            email=email,
            phone=normalized_phone,
            company_id=company.id,
            role='owner',
        )
        user.set_password(User._generate_temp_password())
        db.session.add(user)
        db.session.commit()

        # Clear session
        session.pop('google_email', None)
        session.pop('google_name', None)

        login_user(user)
        from datetime import datetime, timezone
        session['_login_time'] = datetime.now(timezone.utc).timestamp()
        session['_last_active'] = session['_login_time']
        session.permanent = True
        flash('Account created with Google!', 'success')
        return redirect(url_for('main.index'))

    return render_template(
        'auth/google_register.html',
        email=email,
        google_name=google_name,
    )


# --- Password Reset ---

@auth.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit('5 per minute')
def forgot_password():
    """Request a password reset token. Accepts phone or email."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        login_id = request.form.get('login_id', '').strip()
        if not login_id:
            flash('Please enter your phone number or email.', 'danger')
            return redirect(url_for('auth.forgot_password'))

        # Find user by phone or email
        user = None
        cleaned = login_id.replace(' ', '')
        looks_like_phone = (
            cleaned.startswith('09') or cleaned.startswith('07') or
            cleaned.startswith('+251') or
            (cleaned.isdigit() and len(cleaned) == 9 and cleaned[0] in ('7', '9'))
        )
        if looks_like_phone:
            is_valid, normalized, _ = validate_ethiopian_phone(login_id)
            if is_valid:
                user = User.query.filter_by(phone=normalized).first()
        if user is None:
            user = User.query.filter_by(email=login_id.lower()).first()

        # Always show the same message (don't reveal whether account exists)
        if user:
            token = user.generate_reset_token()
            db.session.commit()
            # TODO: Send token via SMS/email. For now, show it on screen.
            flash(
                f'Password reset token generated. '
                f'In production this would be sent to your phone/email. '
                f'For now, here it is: {token}',
                'info',
            )
            return redirect(url_for('auth.reset_password', token=token))

        flash('If an account with that phone/email exists, a reset link has been sent.', 'info')
        return redirect(url_for('auth.login'))

    return render_template('auth/forgot_password.html')


@auth.route('/reset-password/<token>', methods=['GET', 'POST'])
@limiter.limit('5 per minute')
def reset_password(token):
    """Reset password using a valid token."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    # Find user by token hash
    import hashlib
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    user = User.query.filter_by(
        reset_token_hash=token_hash
    ).first()

    if not user or not user.verify_reset_token(token):
        flash('Invalid or expired reset token.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        password2 = request.form.get('password2', '')

        if password != password2:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('auth.reset_password', token=token))

        from payroll_engine.password_policy import check_password_strength
        is_strong, pw_error = check_password_strength(password)
        if not is_strong:
            flash(pw_error, 'danger')
            return redirect(url_for('auth.reset_password', token=token))

        user.set_password(password)
        user.clear_reset_token()
        user.must_change_password = False
        db.session.commit()
        flash('Password reset successfully. Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', token=token)


# --- MFA / TOTP Setup ---

@auth.route('/mfa/setup', methods=['GET', 'POST'])
@login_required
def mfa_setup():
    """Set up TOTP-based MFA."""
    if current_user.mfa_enabled:
        flash('MFA is already enabled.', 'info')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        if not code:
            flash('Please enter the 6-digit code from your authenticator app.', 'danger')
            return redirect(url_for('auth.mfa_setup'))

        # During setup, verify directly against the secret (not via verify_totp which bypasses when mfa_enabled=False)
        import pyotp
        totp = pyotp.TOTP(current_user.totp_secret)
        if totp.verify(code, valid_window=1):
            current_user.enable_mfa()
            db.session.commit()
            flash('MFA enabled successfully!', 'success')
            return redirect(url_for('main.index'))
        else:
            flash('Invalid code. Please try again.', 'danger')
            return redirect(url_for('auth.mfa_setup'))

    # Generate secret if not already set
    if not current_user.totp_secret:
        current_user.generate_totp_secret()
        db.session.commit()

    uri = current_user.get_totp_uri()
    return render_template('auth/mfa_setup.html', uri=uri, secret=current_user.totp_secret)


@auth.route('/mfa/verify', methods=['GET', 'POST'])
@login_required
def mfa_verify():
    """Verify TOTP code before sensitive action (e.g., payroll approval)."""
    next_url = request.args.get('next', '') or request.form.get('next', '')

    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        if current_user.verify_totp(code):
            # Mark MFA as verified for this session
            from flask import session
            session['mfa_verified'] = True
            if next_url:
                from payroll_engine.security import safe_redirect_target
                return redirect(safe_redirect_target(next_url))
            return redirect(url_for('main.index'))
        else:
            flash('Invalid code. Please try again.', 'danger')

    return render_template('auth/mfa_verify.html', next_url=next_url)


@auth.route('/mfa/disable', methods=['POST'])
@login_required
def mfa_disable():
    """Disable MFA (requires current TOTP code)."""
    code = request.form.get('code', '').strip()
    if not current_user.verify_totp(code):
        flash('Invalid code. MFA was not disabled.', 'danger')
        return redirect(url_for('main.index'))
    current_user.disable_mfa()
    db.session.commit()
    flash('MFA disabled.', 'info')
    return redirect(url_for('main.index'))

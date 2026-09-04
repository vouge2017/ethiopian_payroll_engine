import hashlib
from datetime import UTC, datetime, timedelta

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from . import db, limiter
from .models import Company, User, validate_ethiopian_phone
from .security import safe_redirect_target

auth = Blueprint('auth', __name__)


def _get_google_oauth():
    """Get the Google OAuth client, or None if not configured."""
    oauth = getattr(current_app, 'oauth', None)
    if oauth:
        return oauth.create_client('google')
    return None


# Endpoints allowed while must_change_password is True
_PASSWORD_CHANGE_ALLOWED = frozenset(
    {
        'auth.change_password',
        'auth.logout',
        'auth.set_language',
        'static',
        'health',
    }
)


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

        # Normalize identifier for lockout tracking
        # Must match the format used in DB lookup to prevent bypass via format variation
        identifier = login_id.lower().strip() if login_id else ''
        if identifier:
            cleaned = identifier.replace(' ', '')
            looks_like_phone = (
                cleaned.startswith('09')
                or cleaned.startswith('07')
                or cleaned.startswith('+251')
                or (cleaned.isdigit() and len(cleaned) == 9 and cleaned[0] in ('7', '9'))
            )
            if looks_like_phone:
                from payroll_engine.models import validate_ethiopian_phone

                is_valid, normalized, _ = validate_ethiopian_phone(identifier)
                if is_valid:
                    identifier = normalized

        # Check brute-force lockout BEFORE processing
        from payroll_engine.models import LoginAttempt

        is_locked, remaining = LoginAttempt.is_locked_out(identifier)
        if is_locked:
            minutes = max(1, remaining // 60)
            flash(
                f'Account temporarily locked due to too many failed attempts. Try again in {minutes} minute(s).',
                'danger',
            )
            return redirect(url_for('auth.login'))

        # Try to find user by phone or email
        user = None
        if login_id:
            # Check if it looks like a phone number
            cleaned = login_id.replace(' ', '')
            looks_like_phone = (
                cleaned.startswith('09')
                or cleaned.startswith('07')
                or cleaned.startswith('+251')
                or (cleaned.isdigit() and len(cleaned) == 9 and cleaned[0] in ('7', '9'))
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
            # Record failed attempt and check lockout
            is_locked, remaining = LoginAttempt.record_failure(identifier, request.remote_addr)

            # Audit: failed login attempt (tenant-scoped table requires a
            # company; skip for unknown identifiers — logged instead).
            if user:
                from payroll_engine.shared import create_audit_log

                create_audit_log(
                    company_id=user.company_id,
                    user_id=user.id,
                    action='login_failed',
                    details={'attempted_id': login_id[:120], 'locked': is_locked},
                )
                db.session.commit()
            else:
                current_app.logger.warning(
                    'Login failed for unknown identifier (%s)', identifier
                )

            if is_locked:
                minutes = max(1, remaining // 60)
                flash(f'Too many failed attempts. Account locked for {minutes} minute(s).', 'danger')
            else:
                flash('Invalid credentials.', 'danger')
            return redirect(url_for('auth.login'))

        # Successful login — clear lockout counter
        LoginAttempt.record_success(identifier)
        login_user(user, remember=remember)
        from datetime import datetime

        session['_login_time'] = datetime.now(UTC).timestamp()
        session['_last_active'] = session['_login_time']
        session.permanent = True
        # Audit: successful login (skip for platform-operator accounts with no tenant)
        if user.company_id:
            from payroll_engine.shared import create_audit_log

            create_audit_log(
                company_id=user.company_id,
                user_id=user.id,
                action='login_success',
                details={'method': 'phone' if looks_like_phone else 'email'},
            )
            db.session.commit()
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
    # Audit: logout
    from payroll_engine.shared import create_audit_log

    create_audit_log(company_id=current_user.company_id, user_id=current_user.id, action='logout')
    db.session.commit()
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
@limiter.limit('10 per minute')
def change_password():
    """Force or allow password change. User is already authenticated, so
    we don't re-verify identity — only the new password is required."""
    if request.method == 'POST':
        new_password = request.form.get('new_password', '')
        new_password2 = request.form.get('new_password2', '')

        if not new_password:
            flash('Please enter a new password.', 'danger')
            return redirect(url_for('auth.change_password'))
        if new_password != new_password2:
            flash('New passwords do not match.', 'danger')
            return redirect(url_for('auth.change_password'))

        from payroll_engine.password_policy import check_password_strength

        is_strong, pw_error = check_password_strength(new_password)
        if not is_strong:
            flash(pw_error, 'danger')
            return redirect(url_for('auth.change_password'))

        if current_user.check_password(new_password):
            flash('New password must be different from the current password.', 'danger')
            return redirect(url_for('auth.change_password'))

        try:
            current_user.set_password(new_password)
            current_user.must_change_password = False
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception('Failed to change password: %s', e)
            flash('Password change failed. Please try again.', 'danger')
            return redirect(url_for('auth.change_password'))

        flash('Password updated successfully.', 'success')
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
@limiter.limit('3 per minute')
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    phone = ''
    email = None
    password = ''
    password2 = ''
    company_name = None

    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip().lower() or None
        password = request.form.get('password', '')
        password2 = request.form.get('password2', '')
        company_name = request.form.get('company_name', '').strip() or None

        # Validate required fields
        if not phone or not password:
            flash('Phone and password are required.', 'danger')
            return render_template(
                'auth/register.html',
                form_data={
                    'first_name': request.form.get('first_name', ''),
                    'middle_name': request.form.get('middle_name', ''),
                    'last_name': request.form.get('last_name', ''),
                    'phone': phone,
                    'email': request.form.get('email', ''),
                    'company_name': company_name or '',
                },
            ), 400

        # Validate phone format
        is_valid, normalized_phone, phone_error = validate_ethiopian_phone(phone)
        if not is_valid:
            flash(phone_error, 'danger')
            return render_template(
                'auth/register.html',
                form_data={
                    'first_name': request.form.get('first_name', ''),
                    'middle_name': request.form.get('middle_name', ''),
                    'last_name': request.form.get('last_name', ''),
                    'phone': phone,
                    'email': request.form.get('email', ''),
                    'company_name': company_name or '',
                },
            ), 400

        # Validate password
        if password != password2:
            flash('Passwords do not match.', 'danger')
            return render_template(
                'auth/register.html',
                form_data={
                    'first_name': request.form.get('first_name', ''),
                    'middle_name': request.form.get('middle_name', ''),
                    'last_name': request.form.get('last_name', ''),
                    'phone': normalized_phone or phone,
                    'email': request.form.get('email', ''),
                    'company_name': company_name or '',
                },
            ), 400
        from payroll_engine.password_policy import check_password_strength

        is_strong, pw_error = check_password_strength(password)
        if not is_strong:
            flash(pw_error, 'danger')
            return render_template(
                'auth/register.html',
                form_data={
                    'first_name': request.form.get('first_name', ''),
                    'middle_name': request.form.get('middle_name', ''),
                    'last_name': request.form.get('last_name', ''),
                    'phone': normalized_phone or phone,
                    'email': request.form.get('email', ''),
                    'company_name': company_name or '',
                },
            ), 400

        # Check duplicate phone
        if User.query.filter_by(phone=normalized_phone).first():
            flash('Phone number already registered.', 'danger')
            return render_template(
                'auth/register.html',
                form_data={
                    'first_name': request.form.get('first_name', ''),
                    'middle_name': request.form.get('middle_name', ''),
                    'last_name': request.form.get('last_name', ''),
                    'phone': normalized_phone,
                    'email': request.form.get('email', ''),
                    'company_name': company_name or '',
                },
            ), 400

        # Check duplicate email (if provided)
        if email and User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template(
                'auth/register.html',
                form_data={
                    'first_name': request.form.get('first_name', ''),
                    'middle_name': request.form.get('middle_name', ''),
                    'last_name': request.form.get('last_name', ''),
                    'phone': normalized_phone,
                    'email': request.form.get('email', ''),
                    'company_name': company_name or '',
                },
            ), 400

        # Create company if name provided (backward-compatible one-step flow)
        company = None
        if company_name:
            existing_company = Company.query.filter_by(name=company_name).first()
            if existing_company:
                flash('A company with that name already exists.', 'danger')
                return render_template(
                    'auth/register.html',
                    form_data={
                        'first_name': request.form.get('first_name', ''),
                        'middle_name': request.form.get('middle_name', ''),
                        'last_name': request.form.get('last_name', ''),
                        'phone': normalized_phone,
                        'email': request.form.get('email', ''),
                        'company_name': company_name or '',
                    },
                ), 400
            company = Company(name=company_name)
            # 30-day trial for new signups (see payroll_engine/billing.py).
            from payroll_engine.billing import TRIAL_DAYS

            company.trial_ends_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=TRIAL_DAYS)
            db.session.add(company)
            db.session.flush()

        # Create user
        user = User(email=email, phone=normalized_phone, company_id=company.id if company else None, role='owner')
        user.set_password(password)

        # Apply referral code if present
        referral_code = session.pop('referral_code', None)
        if referral_code:
            referrer = User.query.filter_by(referral_code=referral_code).first()
            if referrer:
                user.referred_by = referrer.id

        try:
            db.session.add(user)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception('Failed to create user: %s', e)
            current_app.logger.error(
                'Register failed: phone=%s email=%s company_name=%s role=%s company_id=%s',
                normalized_phone, email, company_name, user.role,
                user.company_id,
            )
            err_msg = str(e).lower()
            if 'unique' in err_msg or 'duplicate' in err_msg:
                if 'phone' in err_msg:
                    flash('This phone number is already registered. Try logging in instead.', 'danger')
                elif 'email' in err_msg:
                    flash('This email is already registered. Try logging in instead.', 'danger')
                else:
                    flash('This account already exists. Try logging in instead.', 'danger')
            elif 'null' in err_msg or 'not-null' in err_msg:
                current_app.logger.error('NOT NULL violation during register: %s', e)
                flash('Account creation failed. Please contact support. (ref: notnull)', 'danger')
            else:
                err_type = type(e).__name__
                flash(f'Account creation failed ({err_type}). Please try again or contact support.', 'danger')
            return render_template(
                'auth/register.html',
                form_data={
                    'first_name': request.form.get('first_name', ''),
                    'middle_name': request.form.get('middle_name', ''),
                    'last_name': request.form.get('last_name', ''),
                    'phone': normalized_phone,
                    'email': request.form.get('email', ''),
                    'company_name': company_name or '',
                },
            ), 400
        flash('Account created! Please log in and set up your company.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form_data=None)


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
        google.authorize_access_token()
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
        from datetime import datetime

        session['_login_time'] = datetime.now(UTC).timestamp()
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
            must_change_password=True,  # Force password change on first login
        )
        user.set_password(User._generate_temp_password())
        db.session.add(user)
        db.session.commit()

        # Clear session
        session.pop('google_email', None)
        session.pop('google_name', None)

        login_user(user)
        from datetime import datetime

        session['_login_time'] = datetime.now(UTC).timestamp()
        session['_last_active'] = session['_login_time']
        session.permanent = True
        flash('Account created with Google! Please set your password.', 'success')
        return redirect(url_for('auth.change_password'))

    return render_template(
        'auth/google_register.html',
        email=email,
        google_name=google_name,
    )


# --- Password Reset (3-step flow: forgot → verify → new) ---


@auth.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit('3 per minute')
def forgot_password():
    """Step 1 of password recovery: collect phone/email, store in session."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        login_id = request.form.get('login_id', '').strip()
        if not login_id:
            flash('Please enter your phone number or email.', 'danger')
            return redirect(url_for('auth.forgot_password'))

        # Determine if phone or email
        cleaned = login_id.replace(' ', '')
        identity_type = None
        identity_value = None

        looks_like_phone = (
            cleaned.startswith('09')
            or cleaned.startswith('07')
            or cleaned.startswith('+251')
            or (cleaned.isdigit() and len(cleaned) == 9 and cleaned[0] in ('7', '9'))
        )
        if looks_like_phone:
            is_valid, normalized, _ = validate_ethiopian_phone(login_id)
            if is_valid:
                identity_type = 'phone'
                identity_value = normalized
        if identity_type is None and '@' in login_id:
            identity_type = 'email'
            identity_value = login_id.lower()

        if identity_type is None:
            flash('Please enter a valid Ethiopian phone or email address.', 'danger')
            return redirect(url_for('auth.forgot_password'))

        # Find user
        if identity_type == 'phone':
            user = User.query.filter_by(phone=identity_value).first()
        else:
            user = User.query.filter_by(email=identity_value).first()

        # Always show the same message (no account enumeration)
        if user:
            token = user.generate_reset_token()
            db.session.commit()
            current_app.logger.debug(f'Password reset token for {login_id}: {token}')

        # Preserve identity in session — the KEY improvement
        # No re-typing phone/email after this step!
        session['reset_identity'] = {
            'type': identity_type,
            'value': identity_value,
            'code_attempts': 0,
        }
        session.permanent = True
        flash('If an account exists for that phone/email, a reset code has been sent.', 'info')
        return redirect(url_for('auth.reset_password_verify'))

    return render_template('auth/forgot_password.html')


@auth.route('/reset-password/verify', methods=['GET', 'POST'])
@limiter.limit('5 per minute')
def reset_password_verify():
    """Step 2 of password recovery: enter the 6-digit code.
    Identity is preserved in session — no re-typing needed."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    identity = session.get('reset_identity')
    if not identity:
        flash('Please start the password reset from the beginning.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        token = request.form.get('token', '').strip()
        if not token:
            flash('Please enter the 6-digit code we sent.', 'danger')
            return redirect(url_for('auth.reset_password_verify'))

        # Brute-force protection
        if identity.get('code_attempts', 0) >= 5:
            session.pop('reset_identity', None)
            flash('Too many attempts. Please start over.', 'danger')
            return redirect(url_for('auth.forgot_password'))

        token_hash = hashlib.sha256(token.encode()).hexdigest()
        if identity['type'] == 'phone':
            user = User.query.filter_by(phone=identity['value']).first()
        else:
            user = User.query.filter_by(email=identity['value']).first()

        if not user or not user.verify_reset_token(token):
            identity['code_attempts'] = identity.get('code_attempts', 0) + 1
            session['reset_identity'] = identity
            flash('Invalid or expired code. Please try again.', 'danger')
            return redirect(url_for('auth.reset_password_verify'))

        # Code accepted — mark verified, proceed to password step
        session['reset_identity']['verified'] = True
        flash('Code verified. Now set your new password.', 'success')
        return redirect(url_for('auth.reset_password_new'))

    return render_template(
        'auth/reset_password_verify.html',
        identity_type=identity['type'],
        masked_value=_mask_identity(identity['type'], identity['value']),
    )


@auth.route('/reset-password/new', methods=['GET', 'POST'])
@limiter.limit('5 per minute')
def reset_password_new():
    """Step 3 of password recovery: set the new password.
    Identity is already in session — only password fields are shown."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    identity = session.get('reset_identity')
    if not identity or not identity.get('verified'):
        flash('Please verify your identity first.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        password2 = request.form.get('password2', '')

        if not password:
            flash('Please enter a new password.', 'danger')
            return redirect(url_for('auth.reset_password_new'))

        if password != password2:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('auth.reset_password_new'))

        from payroll_engine.password_policy import check_password_strength

        is_strong, pw_error = check_password_strength(password)
        if not is_strong:
            flash(pw_error, 'danger')
            return redirect(url_for('auth.reset_password_new'))

        # Look up user by the preserved identity
        if identity['type'] == 'phone':
            user = User.query.filter_by(phone=identity['value']).first()
        else:
            user = User.query.filter_by(email=identity['value']).first()

        if not user:
            session.pop('reset_identity', None)
            flash('Account not found. Please start over.', 'danger')
            return redirect(url_for('auth.forgot_password'))

        try:
            user.set_password(password)
            user.clear_reset_token()
            user.must_change_password = False
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception('Failed to reset password: %s', e)
            flash('Password reset failed. Please try again.', 'danger')
            return redirect(url_for('auth.reset_password_new'))

        # Auto-login the user with the new password
        login_user(user)
        from datetime import datetime

        session['_login_time'] = datetime.now(UTC).timestamp()
        session['_last_active'] = session['_login_time']
        session.permanent = True
        session.pop('reset_identity', None)

        flash('Password updated! You are now signed in.', 'success')
        return redirect(url_for('main.index'))

    return render_template(
        'auth/reset_password_new.html',
        identity_type=identity['type'],
        masked_value=_mask_identity(identity['type'], identity['value']),
    )


def _mask_identity(identity_type: str, value: str) -> str:
    """Mask an identity value for display (e.g., +251 91***567)."""
    if identity_type == 'phone':
        if len(value) >= 9:
            return '+251 ' + value[:2] + '***' + value[-3:]
        return '+251 ' + value
    # email
    if '@' in value:
        local, domain = value.split('@', 1)
        if len(local) <= 2:
            masked_local = local[0] + '***'
        else:
            masked_local = local[:2] + '***' + local[-1:]
        return f'{masked_local}@{domain}'
    return value


# Backward-compat: old /reset-password URL redirects to the new flow
@auth.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """Legacy single-step reset — redirects users to the new 3-step flow."""
    return redirect(url_for('auth.forgot_password'))


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
            flash('Invalid authentication code. Please check your authenticator app and try again.', 'danger')

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

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from . import db, limiter
from .models import User, Company, validate_ethiopian_phone
from .security import safe_redirect_target

auth = Blueprint('auth', __name__)

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
            if cleaned.startswith('09') or cleaned.startswith('07') or cleaned.startswith('+251'):
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
        if user.must_change_password:
            flash('You must set a new password before continuing.', 'warning')
            return redirect(url_for('auth.change_password'))
        next_page = safe_redirect_target(request.args.get('next'))
        flash('Welcome back!', 'success')
        return redirect(next_page)
    return render_template(
        'auth/login.html',
        demo_enabled=bool(current_app.config.get('ENABLE_DEMO_MODE', False)),
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
        company_name = request.form.get('company_name', '').strip()

        # Validate required fields
        if not phone or not password or not company_name:
            flash('Phone, password, and company name are required.', 'danger')
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
        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'danger')
            return redirect(url_for('auth.register'))

        # Check duplicate phone
        if User.query.filter_by(phone=normalized_phone).first():
            flash('Phone number already registered.', 'danger')
            return redirect(url_for('auth.register'))

        # Check duplicate email (if provided)
        if email and User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('auth.register'))

        # Check duplicate company name
        existing_company = Company.query.filter_by(name=company_name).first()
        if existing_company:
            flash(
                'A company with that name already exists. '
                'Contact your admin for an invite, or use a different name.',
                'danger'
            )
            return redirect(url_for('auth.register'))

        # Create company and user
        company = Company(name=company_name)
        db.session.add(company)
        db.session.commit()
        user = User(
            email=email,
            phone=normalized_phone,
            company_id=company.id,
            role='owner'
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Account created. Please log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html')

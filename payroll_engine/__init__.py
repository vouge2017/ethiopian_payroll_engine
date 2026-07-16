import logging
import os
import uuid
from datetime import date, datetime, timedelta

logger = logging.getLogger('payroll_engine')

from flask import Flask, current_app, g, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per hour"],
    storage_uri=os.environ.get('RATELIMIT_STORAGE_URI', 'memory://'),
)

@login_manager.user_loader
def load_user(user_id):
    from .models import User
    return User.query.get(int(user_id))

CELERY_BROKER_DEFAULT = "redis:" + chr(47) + chr(47) + "localhost:6379/0"

def _json_serializer(obj):
    """Custom JSON serializer that handles Decimal for db.JSON columns."""
    import json as _json
    from decimal import Decimal as _Dec
    if isinstance(obj, _Dec):
        return float(obj)
    raise TypeError(f'Object of type {type(obj).__name__} is not JSON serializable')


class RequestIdFilter(logging.Filter):
    def filter(self, record):
        try:
            record.request_id = getattr(g, 'request_id', '-')
            record.method = request.method
            record.path = request.path
        except RuntimeError:
            record.request_id = '-'
            record.method = '-'
            record.path = '-'
        return True


def _configure_logging(app):
    log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO'), logging.INFO)
    handler = logging.StreamHandler()
    handler.setLevel(log_level)
    handler.setFormatter(logging.Formatter(
        '[%(asctime)s] %(levelname)s req=%(request_id)s %(method)s %(path)s %(message)s'
    ))
    handler.addFilter(RequestIdFilter())
    app.logger.addHandler(handler)
    app.logger.setLevel(log_level)
    app.logger.propagate = False


def create_app():
    app = Flask(__name__)

    env = os.environ.get('FLASK_ENV', 'development')

    if env == 'production':
        secret = os.environ.get('SECRET_KEY', '')
        db_url = os.environ.get('DATABASE_URL', '')
        enc_key = os.environ.get('DB_ENCRYPTION_KEY', '')
        errors = []
        if not secret or secret in ('dev-change-in-production', 'your-secret-key-here'):
            errors.append('SECRET_KEY must be a real value in production')
        if not db_url or 'sqlite' in db_url:
            errors.append('DATABASE_URL must be a PostgreSQL connection string in production')
        if not enc_key or enc_key == 'dev-encryption-key-not-for-production-use-only-32b':
            errors.append('DB_ENCRYPTION_KEY must be a real value in production')
        if errors:
            raise RuntimeError('Insecure production configuration: ' + '; '.join(errors))
        from config import ProductionConfig
        app.config.from_object(ProductionConfig())
    else:
        from config import _env_bool
        app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-change-in-production')
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
        app.config['CELERY_BROKER_URL'] = os.environ.get('CELERY_BROKER_URL', CELERY_BROKER_DEFAULT)
        app.config['ENABLE_DEMO_MODE'] = _env_bool(
            'ENABLE_DEMO_MODE',
            default=(env == 'development'),
        )

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', '/tmp/uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    app.config['LOG_LEVEL'] = os.environ.get('LOG_LEVEL', 'INFO').upper()

    _configure_logging(app)
    engine_options = {
        'json_serializer': lambda obj, **kwargs: __import__('json').dumps(obj, default=_json_serializer, **kwargs),
    }
    # Connection pooling (only for non-SQLite — SQLite in-memory doesn't support these)
    db_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if not db_url.startswith('sqlite'):
        engine_options.update({
            'pool_size': int(os.environ.get('SQLALCHEMY_POOL_SIZE', '5')),
            'max_overflow': int(os.environ.get('SQLALCHEMY_MAX_OVERFLOW', '10')),
            'pool_timeout': int(os.environ.get('SQLALCHEMY_POOL_TIMEOUT', '30')),
            'pool_recycle': int(os.environ.get('SQLALCHEMY_POOL_RECYCLE', '300')),
        })
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = engine_options
    csrf.init_app(app)
    limiter.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Google OAuth
    app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID', '')
    app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET', '')
    app.config['GOOGLE_DISCOVERY_URL'] = 'https://accounts.google.com/.well-known/openid-configuration'
    from authlib.integrations.flask_client import OAuth
    oauth = OAuth(app)
    if app.config['GOOGLE_CLIENT_ID']:
        oauth.register(
            name='google',
            client_id=app.config['GOOGLE_CLIENT_ID'],
            client_secret=app.config['GOOGLE_CLIENT_SECRET'],
            server_metadata_url=app.config['GOOGLE_DISCOVERY_URL'],
            client_kwargs={'scope': 'openid email profile'},
        )
    app.oauth = oauth
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    if not app.debug:
        app.config['SESSION_COOKIE_SECURE'] = True

    # Session timeout: idle timeout (configurable, default30 min)
    # Absolute max is8 hours — forces re-login even if active
    idle_minutes = int(os.environ.get('SESSION_IDLE_TIMEOUT_MINUTES', '30'))
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=idle_minutes)
    app.config['SESSION_TIMEOUT_MINUTES'] = idle_minutes
    app.config['SESSION_ABSOLUTE_TIMEOUT_HOURS'] = int(os.environ.get('SESSION_ABSOLUTE_TIMEOUT_HOURS', '8'))
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    db.init_app(app)
    migrate.init_app(app, db)

    # Register tenant-scoped models for structural isolation enforcement
    from .models import Employee, PayrollRun, AuditLog, OvertimeEntry, EmployeeDeduction, UserCompany, TenantQuery
    TenantQuery.register_model(Employee)
    TenantQuery.register_model(PayrollRun)
    TenantQuery.register_model(AuditLog)
    TenantQuery.register_model(OvertimeEntry)
    TenantQuery.register_model(EmployeeDeduction)
    TenantQuery.register_model(UserCompany)

    @app.before_request
    def set_request_id():
        g.request_id = request.headers.get('X-Request-Id', uuid.uuid4().hex[:12])

    @app.before_request
    def check_session_timeout():
        """Enforce idle and absolute session timeout.

        - Idle timeout: session expires after N minutes of inactivity.
        - Absolute timeout: session expires after N hours regardless of activity.
        - Skipped for static files and auth routes (login, register, etc.).
        """
        from flask import session as flask_session
        from flask_login import current_user

        # Skip for unauthenticated, static, and auth routes
        if not current_user.is_authenticated:
            return
        endpoint = request.endpoint or ''
        if endpoint.startswith('static') or endpoint.startswith('auth.'):
            return

        now = datetime.utcnow().timestamp()

        # Absolute timeout check
        login_time = flask_session.get('_login_time')
        if login_time:
            abs_hours = app.config['SESSION_ABSOLUTE_TIMEOUT_HOURS']
            if now - login_time > abs_hours * 3600:
                flask_session.clear()
                from flask_login import logout_user
                logout_user()
                flash('Session expired. Please log in again.', 'warning')
                return redirect(url_for('auth.login'))

        # Idle timeout check
        last_active = flask_session.get('_last_active', now)
        idle_limit = app.config['PERMANENT_SESSION_LIFETIME'].total_seconds()
        if now - last_active > idle_limit:
            flask_session.clear()
            from flask_login import logout_user
            logout_user()
            flash('Session expired due to inactivity. Please log in again.', 'warning')
            return redirect(url_for('auth.login'))

        # Update last activity timestamp
        flask_session['_last_active'] = now

    # Daily retention purge — runs once per app instance per day
    _last_retention_purge = [None]  # mutable container for closure

    @app.before_request
    def daily_retention_purge():
        """Purge expired PDF payslips once per day."""
        from flask_login import current_user
        if not current_user.is_authenticated:
            return
        today = date.today().isoformat()
        if _last_retention_purge[0] == today:
            return
        _last_retention_purge[0] = today
        try:
            from .retention import purge_expired_payslip_pdfs
            purge_expired_payslip_pdfs(app)
        except Exception:
            logger.exception('Retention purge failed')

    @app.after_request
    def add_security_headers(response):
        response.headers.set('X-Content-Type-Options', 'nosniff')
        response.headers.set('X-Frame-Options', 'DENY')
        response.headers.set('X-XSS-Protection', '0')
        if not app.debug:
            response.headers.set('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
        return response

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    # HTTPS enforcement via Flask-Talisman
    if not app.debug and not app.config.get('TESTING', False) and os.environ.get('FLASK_ENV') != 'testing':
        from flask_talisman import Talisman
        Talisman(
            app,
            force_https=True,
            strict_transport_security=True,
            strict_transport_security_max_age=31536000,
            strict_transport_security_include_subdomains=True,
            content_security_policy={
                'default-src': "'self'",
                'script-src': [
                    "'self'",
                    "'unsafe-inline'",
                    "https://cdn.jsdelivr.net",
                ],
                'style-src': [
                    "'self'",
                    "'unsafe-inline'",
                    "https://cdn.jsdelivr.net",
                ],
                'font-src': [
                    "'self'",
                    "https://cdn.jsdelivr.net",
                ],
                'img-src': "'self' data:",
            },
            content_security_policy_nonce_in=['script-src'],
        )
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)
    from .employees_bp import employees_bp
    app.register_blueprint(employees_bp)
    from .payroll_bp import payroll_bp
    app.register_blueprint(payroll_bp)
    from .reports_bp import reports_bp
    app.register_blueprint(reports_bp)
    from .settings_bp import settings_bp
    app.register_blueprint(settings_bp)
    from .portal_bp import portal_bp
    app.register_blueprint(portal_bp)
    from .api import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api/v1')
    @app.route('/healthz')
    def healthz():
        return {'status': 'healthy', 'service': 'ethiopian-payroll-engine'}, 200

    @app.route('/readyz')
    def readyz():
        from sqlalchemy import text
        status = {'self': 'up'}
        # Check DB connectivity
        try:
            db.session.execute(text('SELECT 1'))
            status['database'] = 'up'
        except Exception as e:
            status['database'] = 'down'
            current_app.logger.error('readyz DB check failed: %s', e)
            return {'status': 'not_ready', 'checks': status}, 503
        # Check migration status
        try:
            from flask_migrate import current as migration_current
            with app.app_context():
                heads = migration_current()
                status['migrations'] = 'current' if heads else 'unknown'
        except Exception as e:
            status['migrations'] = f'error: {e}'
            current_app.logger.warning('readyz migration check failed: %s', e)
        return {'status': 'ready', 'checks': status}, 200

    # Make Ethiopian calendar available in all templates
    from payroll_engine.ethiopian_calendar import format_dual_date, format_ethiopian_date
    from payroll_engine.i18n import get_string
    from datetime import date

    @app.context_processor
    def inject_ethiopian_calendar():
        # Get language from session or default to English
        from flask import session
        lang = session.get('language', 'en')

        def _safe_dual_date(d):
            """Handle both date objects and ISO date strings."""
            if not d:
                return ''
            if isinstance(d, str):
                from datetime import datetime as dt
                try:
                    d = dt.strptime(d[:10], '%Y-%m-%d').date()
                except (ValueError, IndexError):
                    return d
            return format_dual_date(d)

        def _safe_eth_date(d):
            """Handle both date objects and ISO date strings."""
            if not d:
                return ''
            if isinstance(d, str):
                from datetime import datetime as dt
                try:
                    d = dt.strptime(d[:10], '%Y-%m-%d').date()
                except (ValueError, IndexError):
                    return d
            return format_ethiopian_date(d)

        return {
            'eth_date': _safe_dual_date,
            'eth_only': _safe_eth_date,
            'today_eth': format_dual_date(date.today()),
            '_': lambda key: get_string(key, lang),
            'current_language': lang,
        }

    @app.context_processor
    def inject_deadline_alerts():
        """Inject deadline notification banner data for authenticated users."""
        from flask import session as flask_session
        from flask_login import current_user
        try:
            if not current_user.is_authenticated or not current_user.company_id:
                return {'deadline_alerts': []}
            company_id = flask_session.get('active_company_id', current_user.company_id)
            from payroll_engine.compliance import get_upcoming_deadlines
            from payroll_engine.models import PayrollRun
            latest_run = PayrollRun.query.filter_by(company_id=company_id).order_by(PayrollRun.created_at.desc()).first()
            payroll_date = latest_run.run_date.isoformat() if latest_run else date.today().isoformat()
            deadlines = get_upcoming_deadlines(payroll_date)
            alerts = []
            for key, label in [('erca', 'ERCA Filing'), ('pension', 'Pension'), ('pssa', 'PSSA')]:
                days = deadlines.get(f'{key}_days_left', 999)
                if days <= 3:
                    severity = 'danger' if days < 0 else 'warning'
                    msg = f'{label}: {abs(days)} days overdue' if days < 0 else f'{label}: {days} days remaining'
                    alerts.append({'message': msg, 'severity': severity})
            return {'deadline_alerts': alerts}
        except Exception:
            return {'deadline_alerts': []}

    # Sentry error monitoring (if DSN is set)
    sentry_dsn = os.environ.get('SENTRY_DSN', '')
    if sentry_dsn:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[FlaskIntegration(), SqlalchemyIntegration()],
            traces_sample_rate=float(os.environ.get('SENTRY_TRACES_SAMPLE_RATE', '0.1')),
            environment=env,
            release=os.environ.get('SENTRY_RELEASE', 'ethiopayroll@unknown'),
        )
        logger.info('Sentry error monitoring enabled')

    return app

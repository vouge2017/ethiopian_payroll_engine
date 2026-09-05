import logging
import os
import uuid
from datetime import UTC, date, datetime, timedelta

logger = logging.getLogger('payroll_engine')

from flask import Flask, current_app, flash, g, redirect, request, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=['200 per hour'],
    # Shared storage when Redis is available — with memory:// every gunicorn
    # worker counts separately, making rate limits N-times looser behind a
    # multi-worker deployment. RATELIMIT_STORAGE_URI overrides both.
    storage_uri=os.environ.get('RATELIMIT_STORAGE_URI') or os.environ.get('REDIS_URL') or 'memory://',
)


@login_manager.user_loader
def load_user(user_id):
    from .models import User

    return db.session.get(User, int(user_id))


def _json_serializer(obj):
    """Custom JSON serializer that handles Decimal for db.JSON columns."""
    import json as _json  # noqa: F401 — used below in this function
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
    handler.setFormatter(
        logging.Formatter('[%(asctime)s] %(levelname)s req=%(request_id)s %(method)s %(path)s %(message)s')
    )
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
        # Fix postgres:// → postgresql:// for SQLAlchemy 2.x
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
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
    elif env == 'staging':
        secret = os.environ.get('SECRET_KEY', '')
        db_url = os.environ.get('DATABASE_URL', '')
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        enc_key = os.environ.get('DB_ENCRYPTION_KEY', '')
        errors = []
        if not secret or secret in ('dev-change-in-production', 'your-secret-key-here'):
            errors.append('SECRET_KEY must be a real value in staging')
        if not db_url or 'sqlite' in db_url:
            errors.append('DATABASE_URL must be a PostgreSQL connection string in staging')
        if not enc_key or enc_key == 'dev-encryption-key-not-for-production-use-only-32b':
            errors.append('DB_ENCRYPTION_KEY must be a real value in staging')
        if errors:
            raise RuntimeError('Insecure staging configuration: ' + '; '.join(errors))
        from config import StagingConfig

        app.config.from_object(StagingConfig())
    elif env == 'testing':
        from config import TestingConfig
        app.config.from_object(TestingConfig())
    else:
        from config import _env_bool

        app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-change-in-production')
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
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
        engine_options.update(
            {
                'pool_size': int(os.environ.get('SQLALCHEMY_POOL_SIZE', '5')),
                'max_overflow': int(os.environ.get('SQLALCHEMY_MAX_OVERFLOW', '10')),
                'pool_timeout': int(os.environ.get('SQLALCHEMY_POOL_TIMEOUT', '30')),
                'pool_recycle': int(os.environ.get('SQLALCHEMY_POOL_RECYCLE', '300')),
            }
        )
        # Render PostgreSQL requires SSL
        if os.environ.get('RENDER') and 'sslmode' not in db_url:
            engine_options['connect_args'] = {'sslmode': 'require'}
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = engine_options

    # Behind Render's proxy the real client IP arrives in X-Forwarded-For.
    # Without ProxyFix, get_remote_address sees the proxy IP — all users share
    # one rate-limit bucket and IP-based audit logs are wrong. Only enabled
    # when actually deployed behind a proxy (never for local dev, where those
    # headers are trivially spoofable).
    if os.environ.get('RENDER') or os.environ.get('TRUST_PROXY') == '1':
        from werkzeug.middleware.proxy_fix import ProxyFix

        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

    csrf.init_app(app)

    # CSRF is enforced on all blueprints. The emergency valve
    # (EMERGENCY_DISABLE_CSRF_AUTH) was removed 2026-08-29 — the root-cause
    # proxy fix (ProxyFix + Render HTTPS) has been stable since 2026-08-26.
    limiter.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Google OAuth
    app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID', '')
    app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET', '')
    app.config['GOOGLE_DISCOVERY_URL'] = 'https://accounts.google.com/.well-known/openid-configuration'
    try:
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
    except ImportError as e:
        import logging

        logging.warning(f'OAuth disabled — missing dependency: {e}')
        app.oauth = None
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    # Bugfix 2026-08: previously only excluded .debug, so pytest runs got
    # Secure cookies which http-only test clients silently dropped —
    # killing every session-backed flow (flash, login) in the suite.
    if not (app.debug or app.config.get('TESTING')):
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

    # Register tenant-scoped models for structural isolation enforcement.
    #
    # IMPORTANT: only models whose queries are ALL company_id-filtered may be
    # registered here — TenantQuery raises RuntimeError on any unfiltered
    # terminal query (.all/.first/.count/...) for registered models.
    # Additional models (Payslip, PayrollDraft, Attendance, ApiKey, Leave,
    # FinalSettlement, etc.) must be added ONLY after a per-model sweep of
    # every call site (Phase 2), never in bulk.
    from .models import (
        Attendance,
        AuditLog,
        Employee,
        EmployeeDeduction,
        OvertimeEntry,
        PayrollDraft,
        PayrollRun,
        Payslip,
        TenantQuery,
        UserCompany,
    )

    TenantQuery.register_model(Employee)
    TenantQuery.register_model(PayrollRun)
    TenantQuery.register_model(AuditLog)
    TenantQuery.register_model(OvertimeEntry)
    TenantQuery.register_model(EmployeeDeduction)
    TenantQuery.register_model(UserCompany)
    # Batch 2 (Phase 2b): swept 2026-08-22 — all query sites carry explicit
    # company_id filters; retention purge uses tenant_context(0).
    TenantQuery.register_model(Attendance)
    TenantQuery.register_model(PayrollDraft)
    # Batch 3 (Phase 3): Payslip swept across 18 files — routes use verified
    # run/emp context; retention + demo cleanup use tenant_context(0);
    # service-layer fns (exceptions/evidence/change_summary) thread company_id.
    TenantQuery.register_model(Payslip)

    # Batch 4 (Phase 3b, P0-A, 2026-08-31): tenant-isolation registration.
    #
    # Each of these models was swept across every call site before
    # registration. The audit log is in `docs/p0a_tenant_audit.md`. Adding
    # a model here WITHOUT a prior sweep is a P0 — unfiltered terminal
    # queries that previously returned empty are now loud RuntimeError
    # failures, which is the desired behaviour (we want the test to fail,
    # not silent cross-tenant reads).
    from .models import (
        EmployeeAllowance,
        FilingRecord,
        FinalSettlement,
        Leave,
        LeaveBalance,
        Notification,
        PayrollPreview,
        PayslipAcknowledgment,
        PayslipGenerationJob,
        ProfileChangeRequest,
    )
    TenantQuery.register_model(EmployeeAllowance)
    TenantQuery.register_model(FilingRecord)
    TenantQuery.register_model(FinalSettlement)
    TenantQuery.register_model(Leave)
    TenantQuery.register_model(LeaveBalance)
    TenantQuery.register_model(Notification)
    TenantQuery.register_model(PayrollPreview)
    TenantQuery.register_model(PayslipAcknowledgment)
    TenantQuery.register_model(PayslipGenerationJob)
    TenantQuery.register_model(ProfileChangeRequest)

    # CSP nonce — available in all templates as {{ csp_nonce }}
    @app.context_processor
    def inject_csp_nonce():
        return {'csp_nonce': getattr(g, 'csp_nonce', '')}

    # Static asset version — used to bust CDN/Cloudflare/browser caches after
    # a deploy. Render sets GIT_COMMIT_SHA automatically on every build, so
    # each deploy produces a new version string and the browser fetches
    # fresh assets. Falls back to a startup-time timestamp if the env var
    # is missing (e.g., local development).
    import time as _time
    _static_version = (
        os.environ.get('GIT_COMMIT_SHA')
        or os.environ.get('RENDER_GIT_COMMIT')
        or str(int(_time.time()))
    )[:12]
    app.config['STATIC_ASSET_VERSION'] = _static_version

    @app.context_processor
    def inject_static_version():
        return {'static_version': app.config['STATIC_ASSET_VERSION']}

    # Template filter: calculation flow for transparent payslips
    @app.template_filter('calculation_flow')
    def calculation_flow_filter(result):
        from payroll_engine.payroll import generate_calculation_flow

        return generate_calculation_flow(result)

    @app.before_request
    def set_request_id():
        g.request_id = request.headers.get('X-Request-Id', uuid.uuid4().hex[:12])
        g.csp_nonce = uuid.uuid4().hex[:16]

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

        now = datetime.now(UTC).timestamp()

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

    # Daily retention purge — runs once per day (DB-backed, survives restart)
    _last_draft_check = [None]  # monthly draft preparation
    _last_nudge_check = [None]  # compliance nudges

    @app.before_request
    def daily_retention_purge():
        """Purge expired artifacts once per day."""
        from flask_login import current_user

        if not current_user.is_authenticated:
            return
        today = date.today().isoformat()
        try:
            from .models import SystemSetting

            if SystemSetting.get('last_purge_date') == today:
                return
            from .retention import (
                purge_expired_drafts,
                purge_expired_payslip_pdfs,
                purge_expired_previews,
                purge_expired_uploads,
                purge_old_login_attempts,
            )

            purge_expired_payslip_pdfs(app)
            purge_expired_drafts(app)
            purge_expired_previews(app)
            purge_expired_uploads(app)
            purge_old_login_attempts(app)
            SystemSetting.set('last_purge_date', today)
        except Exception:
            logger.exception('Retention purge failed')

    @app.before_request
    def proactive_checks():
        """Run proactive checks: monthly draft prep + compliance nudges.

        Uses the same once-per-day pattern as daily_retention_purge.
        Only runs for authenticated users with a company.
        """
        from flask_login import current_user

        if not current_user.is_authenticated:
            return
        company_id = current_user.company_id
        if not company_id:
            return

        today = date.today()
        today_str = today.isoformat()

        # Monthly draft preparation (on 28th+ of each month)
        if today.day >= 28 and _last_draft_check[0] != today_str:
            _last_draft_check[0] = today_str
            try:
                from .services.proactive import prepare_monthly_draft

                prepare_monthly_draft(company_id)
            except Exception:
                logger.exception('Monthly draft preparation failed')

        # Compliance nudges (once per day)
        if _last_nudge_check[0] != today_str:
            _last_nudge_check[0] = today_str
            try:
                from .services.proactive import send_compliance_nudges

                send_compliance_nudges(company_id)
            except Exception:
                logger.exception('Compliance nudges failed')

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

    # CORS — restrict to configured origins, never wildcard with credentials
    from flask_cors import CORS

    cors_origins = os.environ.get('CORS_ALLOWED_ORIGINS', '').strip()
    if cors_origins:
        allowed_origins = [o.strip() for o in cors_origins.split(',') if o.strip()]
    else:
        # Default: same-origin only (no cross-origin API access)
        # Set CORS_ALLOWED_ORIGINS env var to enable cross-origin access
        # Example: "https://app.ethiopayroll.com,https://staging.ethiopayroll.com"
        allowed_origins = []

    if allowed_origins:
        CORS(
            app,
            origins=allowed_origins,
            supports_credentials=True,
            allow_headers=['Content-Type', 'Authorization', 'X-Requested-With'],
            methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
            max_age=86400,
            expose_headers=['X-Total-Count', 'X-Page-Count'],
        )
    # else: no CORS headers — same-origin only (secure default)

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
                    "'unsafe-inline'",  # fallback for old browsers; modern browsers prefer nonce
                    'https://cdn.jsdelivr.net',
                ],
                'script-src-attr': ["'unsafe-inline'"],  # inline event handlers (onclick, etc.)
                'style-src': [
                    "'self'",
                    "'unsafe-inline'",
                    'https://cdn.jsdelivr.net',
                    'https://fonts.googleapis.com',
                ],
                'font-src': [
                    "'self'",
                    'https://cdn.jsdelivr.net',
                    'https://fonts.gstatic.com',
                    "https://fonts.googleapis.com",
                    "https://fonts.gstatic.com",
                ],
                'img-src': "'self' data:",
                'connect-src': [
                    "'self'",
                    'https://cdn.jsdelivr.net',
                ],
            },
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

    from .wizard_bp import wizard_bp

    app.register_blueprint(wizard_bp)
    from .help_bp import help_bp

    app.register_blueprint(help_bp)
    from .attendance_bp import attendance_bp

    app.register_blueprint(attendance_bp)
    from .accounting_bp import accounting_bp

    app.register_blueprint(accounting_bp)
    from .calendar_bp import calendar_bp

    app.register_blueprint(calendar_bp)
    from .verification_bp import verification_bp

    app.register_blueprint(verification_bp)
    from .selfservice_bp import selfservice_bp

    app.register_blueprint(selfservice_bp)
    from .billing_bp import billing_bp, platform_bp

    app.register_blueprint(billing_bp)
    app.register_blueprint(platform_bp)

    # P0-E: Internal cron blueprint (authenticated by X-Cron-Secret).
    # Hit by Render Cron Job service on the schedule declared in
    # render.yaml. POST only — see cron_bp.py:daily docstring.
    from .cron_bp import cron_bp

    app.register_blueprint(cron_bp)

    from .admin_bp import admin_bp, support_bp
    app.register_blueprint(admin_bp)
    app.register_blueprint(support_bp)

    # Billing enforcement gate: derived state -> access control on every request.
    from .billing import enforce_billing_gate

    app.before_request(enforce_billing_gate)

    @app.cli.command('seed-holidays')
    def seed_holidays_cmd():
        """Seed Ethiopian national holidays."""
        from payroll_engine.holidays import seed_holidays

        added = seed_holidays()
        print(f'Seeded {added} holidays.')

    # Push notification endpoints
    @app.route('/api/vapid-key')
    def vapid_key():
        from payroll_engine.push import get_vapid_public_key

        return {'key': get_vapid_public_key()}

    @app.route('/api/push/subscribe', methods=['POST'])
    def push_subscribe():
        from flask_login import current_user, login_required  # noqa: F401

        if not current_user.is_authenticated:
            return {'error': 'Unauthorized'}, 401
        from payroll_engine.push import save_subscription

        data = request.get_json()
        if data:
            save_subscription(current_user.id, data)
            return {'status': 'ok'}
        return {'error': 'No subscription data'}, 400

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
        # Background worker liveness (RQ heartbeat; non-fatal when unknown)
        try:
            from .worker_health import heartbeat_status

            status['worker'] = heartbeat_status()
        except Exception:  # pragma: no cover
            status['worker'] = 'unknown'
        return {'status': 'ready', 'checks': status}, 200

    @app.route('/sw.js')
    def service_worker():
        return app.send_static_file('sw.js'), 200, {'Content-Type': 'application/javascript'}

    @app.route('/favicon.ico')
    def favicon():
        """Serve the app icon as favicon.ico.

        Browsers (and the Network tab) automatically request /favicon.ico.
        We don't ship a .ico file — the project uses a 192px PNG instead.
        Returning the PNG with a long cache avoids the 404 in the console
        without shipping a new binary asset.
        """
        from flask import make_response
        response = make_response(
            app.send_static_file('icons/icon-192.png'),
        )
        response.headers['Content-Type'] = 'image/png'
        response.headers['Cache-Control'] = 'public, max-age=86400'
        return response

    @app.route('/offline')
    def offline():
        return (
            '<!doctype html><html><head>'
            '<meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Offline — EthioPayroll</title>'
            '<style>body{font-family:system-ui,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;background:#f4f6f9;color:#333}'
            '.box{text-align:center;padding:2rem}.box h1{font-size:1.5rem;margin-bottom:.5rem}.box p{color:#666}</style>'
            '</head><body><div class="box">'
            '<h1>You\u2019re offline</h1>'
            '<p>EthioPayroll needs an internet connection to load payroll data.'
            '<br>Please check your connection and try again.</p>'
            '</div></body></html>'
        ), 200

    # Make Ethiopian calendar available in all templates
    from payroll_engine.ethiopian_calendar import format_dual_date, format_ethiopian_date
    from payroll_engine.i18n import get_string

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
            from payroll_engine.models import Company, PayrollRun

            company = db.session.get(Company, company_id)
            latest_run = (
                PayrollRun.query.filter_by(company_id=company_id).order_by(PayrollRun.created_at.desc()).first()
            )
            payroll_date = latest_run.run_date.isoformat() if latest_run else date.today().isoformat()
            deadlines = get_upcoming_deadlines(company=company, payroll_date=payroll_date)
            alerts = []
            for key in deadlines:
                if not key.endswith('_days_left'):
                    continue
                ftype = key.replace('_days_left', '')
                days = deadlines[key]
                if days <= 3:
                    severity = 'danger' if days < 0 else 'warning'
                    label = ftype.upper().replace('_', ' ')
                    msg = f'{label}: {abs(days)} days overdue' if days < 0 else f'{label}: {days} days remaining'
                    alerts.append({'message': msg, 'severity': severity})
            return {'deadline_alerts': alerts}
        except Exception:
            return {'deadline_alerts': []}

    @app.context_processor
    def inject_sidebar_counts():
        """Inject employee count and pending profile changes for sidebar.

        Used to:
        - Adapt sidebar to company size (hide advanced features for small companies)
        - Show badge on Profile Requests when there are pending changes
        """
        from flask import session as flask_session
        from flask_login import current_user

        try:
            if not current_user.is_authenticated or not current_user.company_id:
                return {'employee_count': 0, 'pending_profile_changes': 0}
            company_id = flask_session.get('active_company_id', current_user.company_id)
            from payroll_engine.models import Employee, ProfileChangeRequest

            emp_count = Employee.query.filter_by(company_id=company_id, is_deleted=False).count()
            pending_changes = ProfileChangeRequest.query.filter_by(company_id=company_id, status='pending').count()
            return {
                'employee_count': emp_count,
                'pending_profile_changes': pending_changes,
            }
        except Exception:
            return {'employee_count': 0, 'pending_profile_changes': 0}

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

    # ----------------------------------------------------------------
    # Error Handlers
    # ----------------------------------------------------------------
    @app.errorhandler(403)
    def forbidden(e):
        from flask import render_template

        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template

        return render_template('errors/404.html'), 404

    @app.errorhandler(400)
    def bad_request(e):
        """400 is the Flask-WTF CSRF rejection status. Convert the cryptic
        400 into a friendly message + a link to refresh the page (which
        regenerates the CSRF token). This is the most common user-facing
        400 on auth forms: a session expires, the cookie is gone, but the
        page the user is filling in still has the old token."""
        from flask import render_template, request, flash, redirect, url_for
        # Only intervene on form posts; other 400s pass through.
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE') and 'csrf' in (e.description or '').lower():
            flash('Your session expired while you were filling the form. Please refresh the page and try again.', 'warning')
            # If we can guess the originating page, redirect there; otherwise home.
            referer = request.headers.get('Referer', '')
            if referer:
                from urllib.parse import urlparse
                path = urlparse(referer).path
                if path and path != request.path:
                    return redirect(path)
            return redirect(url_for('main.index'))
        # Default: render the 400 template if we have one, else pass through.
        try:
            return render_template('errors/400.html'), 400
        except Exception:
            return 'Bad Request', 400

    @app.errorhandler(500)
    def internal_error(e):
        from flask import render_template

        from payroll_engine import db

        db.session.rollback()
        return render_template('errors/500.html'), 500

    # P0: One-time migration fix (commit 8ef62d7 → 500 on register/login
    # because production DB is missing columns added in f18b86a).
    # This route will be removed once the migration runs successfully.
    from scripts.fix_user_columns_route import register_fix_route
    register_fix_route(app)

    return app

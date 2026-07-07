from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
import os

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()

@login_manager.user_loader
def load_user(user_id):
    from .models import User
    return User.query.get(int(user_id))

CELERY_BROKER_DEFAULT = "redis:" + chr(47) + chr(47) + "localhost:6379/0"

def create_app():
    app = Flask(__name__)

    # Load config based on environment
    env = os.environ.get('FLASK_ENV', 'development')
    if env == 'production':
        from config import ProductionConfig
        app.config.from_object(ProductionConfig())
    else:
        app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-change-in-production')
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
        app.config['CELERY_BROKER_URL'] = os.environ.get('CELERY_BROKER_URL', CELERY_BROKER_DEFAULT)

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', '/tmp/uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    db.init_app(app)
    migrate.init_app(app, db)

    # Register tenant-scoped models for structural isolation enforcement
    from .models import Employee, PayrollRun, AuditLog, TenantQuery
    TenantQuery.register_model(Employee)
    TenantQuery.register_model(PayrollRun)
    TenantQuery.register_model(AuditLog)

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)
    from .api import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api/v1')
    @app.route('/health')
    def health():
        return {'status': 'healthy', 'service': 'ethiopian-payroll-engine'}, 200

    # Make Ethiopian calendar available in all templates
    from payroll_engine.ethiopian_calendar import format_dual_date, format_ethiopian_date
    from datetime import date

    @app.context_processor
    def inject_ethiopian_calendar():
        return {
            'eth_date': lambda d: format_dual_date(d) if d else '',
            'eth_only': lambda d: format_ethiopian_date(d) if d else '',
            'today_eth': format_dual_date(date.today()),
        }

    return app

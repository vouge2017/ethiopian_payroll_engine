import os

target = r"D:\d\ethiopian_payroll_engine\payroll_engine\__init__.py"
SQ = chr(39)  # single quote character

content = f"""from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
import os

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

@login_manager.user_loader
def load_user(user_id):
    from .models import User
    return User.query.get(int(user_id))

def create_app():
    app = Flask(__name__)
    app.config[{SQ}SECRET_KEY{SQ}] = os.environ.get({SQ}SECRET_KEY{SQ}, {SQ}dev-change-in-production{SQ})
    app.config[{SQ}SQLALCHEMY_DATABASE_URI{SQ}] = os.environ.get({SQ}DATABASE_URL{SQ}, {SQ}sqlite:///app.db{SQ})
    app.config[{SQ}SQLALCHEMY_TRACK_MODIFICATIONS{SQ}] = False
    app.config[{SQ}UPLOAD_FOLDER{SQ}] = os.environ.get({SQ}UPLOAD_FOLDER{SQ}, {SQ}/tmp/uploads{SQ})
    app.config[{SQ}MAX_CONTENT_LENGTH{SQ}] = 16 * 1024 * 1024
    app.config[{SQ}CELERY_BROKER_URL{SQ}] = os.environ.get({SQ}CELERY_BROKER_URL{SQ}, {SQ}redis://localhost:***@app.route({SQ}/health{SQ})
    def health():
        return {{'status': 'healthy', 'service': 'ethiopian-payroll-engine'}}, 200

    return app
"""

with open(target, 'w') as f:
    f.write(content)

# Verify
with open(target, 'r') as f:
    written = f.read()

line23 = written.split('\n')[22]
print(f"Line 23: {repr(line23)}")
print("File written successfully")

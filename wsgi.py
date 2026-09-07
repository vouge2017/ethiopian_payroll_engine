"""Entry point for the Ethiopian Payroll Engine."""
from payroll_engine import create_app
from payroll_engine import db

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

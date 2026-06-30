from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
# The db object is defined in payroll_engine/__init__.py but we need to import it
# from the main package to avoid circular imports
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from payroll_engine import db


class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    users = db.relationship('User', backref='company', lazy=True)
    employees = db.relationship('Employee', backref='company', lazy=True)
    payroll_runs = db.relationship('PayrollRun', backref='company', lazy=True)
    
    def __repr__(self):
        return f'<Company {self.name}>'


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='employee')  # admin, hr, employee
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.email}>'


class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(20), unique=True, nullable=False)  # e.g., EMP001
    name = db.Column(db.String(100), nullable=False)
    basic_salary = db.Column(db.Float, nullable=False)
    allowances = db.Column(db.Float, nullable=False, default=0.0)
    bank_or_telebirr = db.Column(db.String(100))  # e.g., 'telebirr:0912345678' or 'bank:cbe'
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    payroll_entries = db.relationship('Payslip', backref='employee', lazy=True)
    attendance_records = db.relationship('Attendance', backref='employee', lazy=True)
    leave_requests = db.relationship('Leave', backref='employee', lazy=True)
    
    @property
    def gross_salary(self):
        return self.basic_salary + self.allowances
    
    def __repr__(self):
        return f'<Employee {self.employee_id}: {self.name}>'


class PayrollRun(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    run_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, processing, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    payslips = db.relationship('Payslip', backref='payroll_run', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<PayrollRun {self.id} for {self.company_id} on {self.run_date}>'


class Payslip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    payroll_run_id = db.Column(db.Integer, db.ForeignKey('payroll_run.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    pdf_file_path = db.Column(db.String(255))  # Path to the generated PDF
    gross_salary = db.Column(db.Float, nullable=False)
    tax = db.Column(db.Float, nullable=False)
    employee_pension = db.Column(db.Float, nullable=False)
    employer_pension = db.Column(db.Float, nullable=False)
    net_pay = db.Column(db.Float, nullable=False)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Payslip {self.id} for employee {self.employee_id}>'


class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    hours_worked = db.Column(db.Float, nullable=False, default=0.0)
    
    def __repr__(self):
        return f'<Attendance {self.employee_id} on {self.date}>'


class Leave(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    leave_type = db.Column(db.String(50), nullable=False)  # e.g., annual, sick, maternity
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, approved, rejected
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Leave {self.leave_type} for {self.employee_id} from {self.start_date} to {self.end_date}>'


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Null if system action
    action = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    details = db.Column(db.JSON)
    
    def __repr__(self):
        return f'<AuditLog {self.action} at {self.timestamp}>'

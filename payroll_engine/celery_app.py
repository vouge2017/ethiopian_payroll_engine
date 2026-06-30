"""Celery background tasks for payroll processing."""
from celery import Celery
from payroll_engine import db, create_app
from payroll_engine.models import Company, User, Employee, PayrollRun, Payslip, Attendance, Leave, AuditLog
from payroll_engine.tax import calculate_tax, explain_tax_amharic
from payroll_engine.pension import employee_pension, employer_pension
from payroll_engine.pdf import generate_payslip
from payroll_engine.compliance import compute_compliance_score, get_status_message
from payroll_engine.disbursement import record_disbursement_intent
import csv
import os


def make_celery(app=None):
    if app is None:
        app = create_app()
    celery = Celery(
        'ethiopian_payroll',
        broker=app.config['CELERY_BROKER_URL'],
    )
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


# Create default celery instance (will be re-created in worker)
celery = make_celery()


@celery.task(bind=True, max_retries=3, default_retry_delay=10)
def process_payroll_csv(self, csv_path, company_id, user_id=None):
    """
    Process a payroll CSV file in the background.
    Creates PayrollRun, Payslip entries, and AuditLog.
    """
    app = create_app()
    with app.app_context():
        run = PayrollRun(
            company_id=company_id,
            status='processing',
            run_date=__import__('datetime').date.today()
        )
        db.session.add(run)
        db.session.commit()

        try:
            employees_data = []
            with open(csv_path, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    emp_id = row.get('employee_id', '').strip()
                    name = row.get('name', '').strip()
                    basic = float(row.get('basic_salary', 0))
                    allow = float(row.get('allowances', 0))
                    bank = row.get('bank_or_telebirr', '')

                    # Find or create employee
                    emp = Employee.query.filter_by(
                        company_id=company_id, employee_id=emp_id
                    ).first()
                    if not emp:
                        emp = Employee(
                            employee_id=emp_id,
                            name=name,
                            basic_salary=basic,
                            allowances=allow,
                            bank_or_telebirr=bank,
                            company_id=company_id
                        )
                        db.session.add(emp)
                        db.session.commit()
                    else:
                        emp.basic_salary = basic
                        emp.allowances = allow
                        emp.bank_or_telebirr = bank
                        db.session.commit()

                    # Calculate payroll
                    gross = basic + allow
                    tax = calculate_tax(gross)
                    emp_pen = employee_pension(basic)
                    empr_pen = employer_pension(basic)
                    net = gross - tax - emp_pen
                    tax_expl = explain_tax_amharic(gross)
                    intent = record_disbursement_intent(emp_id, net)

                    # Generate PDF
                    emp_dict = {
                        'id': emp.employee_id,
                        'name': emp.name,
                        'basic': basic,
                        'allowances': allow,
                        'gross': gross,
                        'tax': tax,
                        'tax_explanation': tax_expl,
                        'pension_employee': emp_pen,
                        'pension_employer': empr_pen,
                        'net': net,
                        'bank': bank,
                    }
                    pdf_path = generate_payslip(emp_dict)

                    payslip = Payslip(
                        payroll_run_id=run.id,
                        employee_id=emp.id,
                        pdf_file_path=pdf_path,
                        gross_salary=gross,
                        tax=tax,
                        employee_pension=emp_pen,
                        employer_pension=empr_pen,
                        net_pay=net,
                    )
                    db.session.add(payslip)
                    db.session.commit()

                    employees_data.append({
                        'id': emp.employee_id,
                        'name': emp.name,
                        'gross': gross,
                        'tax': tax,
                        'net': net,
                        'pdf_path': pdf_path,
                    })

            # Mark run completed
            run.status = 'completed'
            db.session.commit()

            # Compliance
            today_str = __import__('datetime').date.today().isoformat()
            score, status = compute_compliance_score(
                payroll_date=today_str,
                pension_deadline=today_str,
                tax_deadline=today_str,
                disbursement_date=today_str
            )

            # AuditLog
            log = AuditLog(
                company_id=company_id,
                user_id=user_id,
                action='payroll_run_completed',
                details={
                    'run_id': run.id,
                    'employee_count': len(employees_data),
                    'compliance_score': score,
                    'compliance_status': status,
                }
            )
            db.session.add(log)
            db.session.commit()

            return {
                'run_id': run.id,
                'employees': len(employees_data),
                'compliance_score': score,
                'compliance_status': status,
            }

        except Exception as e:
            run.status = 'failed'
            db.session.commit()
            log = AuditLog(
                company_id=company_id,
                user_id=user_id,
                action='payroll_run_failed',
                details={'error': str(e)}
            )
            db.session.add(log)
            db.session.commit()
            raise

        finally:
            try:
                os.remove(csv_path)
            except OSError:
                pass

from payroll_engine import create_app, db
from flask_migrate import upgrade

app = create_app()

@app.cli.command("init-db")
def init_db():
    """Initialize the database."""
    db.create_all()
    upgrade()
    print("Database initialized.")

@app.cli.command("seed-db")
def seed_db():
    """Seed database with sample data."""
    from payroll_engine.models import Company, User, Employee
    from datetime import date
    
    # Create demo company
    company = Company(name="Demo Company")
    db.session.add(company)
    db.session.commit()
    
    # Create admin user
    admin = User(email="admin@demo.com", company_id=company.id, role="admin")
    admin.set_password("password123")
    db.session.add(admin)
    
    # Create sample employees
    employees = [
        Employee(employee_id="EMP001", name="Abebe Kebede", basic_salary=8000, allowances=2000, bank_or_telebirr="telebirr:0912345678", company_id=company.id),
        Employee(employee_id="EMP002", name="Bekelech Wondimu", basic_salary=12000, allowances=3000, bank_or_telebirr="bank:cbe", company_id=company.id),
        Employee(employee_id="EMP003", name="Daniel Tesfaye", basic_salary=5000, allowances=1000, bank_or_telebirr="telebirr:0987654321", company_id=company.id),
    ]
    for emp in employees:
        db.session.add(emp)
    
    db.session.commit()
    print("Database seeded.")
    print(f"  Admin: admin@demo.com / password123")
    print(f"  Company: Demo Company")
    print(f"  Employees: {len(employees)}")

@app.cli.command("seed-staging")
def seed_staging_cmd():
    """Seed staging database with realistic test data (2 companies, 45 employees)."""
    from seed_staging import seed
    seed()


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="0.0.0.0", port=5000)

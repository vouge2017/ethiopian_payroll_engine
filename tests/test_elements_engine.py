"""
Elements Phase 1 engine tests — verifies calculate_payroll_from_assignments.

Root-cause coverage for the critical issues:
1. total_deductions correctly populated (was 0 when _merge_post_tax was
   called as a bare expression and its return value was discarded)
2. Declining-balance remaining_balance persisted (db.session.add was present
   but the assignment's updated state was never committed back to session)
3. percent_of_item raises NotImplementedError (not silently returns 0)
4. seed_pay_item_types creates company copies from system catalog

Also cross-validates elements engine output against the legacy
calculate_payroll() for the same inputs, so regressions are caught
by direct comparison.
"""

import os
import sys
from datetime import date
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from payroll_engine import create_app, db
from payroll_engine.models import Company, Employee
from payroll_engine.models_payroll_elements import (
    PayItemCalcMethod,
    PayItemClassification,
    PayItemTaxTreatment,
    PayItemType,
    PayrollItemAssignment,
)
from payroll_engine.payroll import calculate_payroll as calculate_legacy
from payroll_engine.payroll_elements import (
    calculate_payroll_from_assignments,
    seed_pay_item_types,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SYSTEM_KEYS = [
    ('basic_salary',      'Basic Salary',          PayItemClassification.EARNING,         PayItemCalcMethod.FIXED,              PayItemTaxTreatment.TAXABLE, 1,  None),
    ('housing_allowance', 'Housing Allowance',     PayItemClassification.EARNING,         PayItemCalcMethod.FIXED,              PayItemTaxTreatment.TAXABLE, 5,  None),
    ('pension_employee',  'Employee Pension',      PayItemClassification.DEDUCTION,       PayItemCalcMethod.PERCENT_OF_BASIC,   PayItemTaxTreatment.TAXABLE, 10, Decimal('7')),
    ('pension_employer',  'Employer Pension',      PayItemClassification.EMPLOYER_CHARGE, PayItemCalcMethod.PERCENT_OF_BASIC,   PayItemTaxTreatment.TAXABLE, 20, Decimal('11')),
    ('income_tax',        'Income Tax (PAYE)',     PayItemClassification.TAX,             PayItemCalcMethod.FIXED,              PayItemTaxTreatment.TAXABLE, 30, None),
    ('medical_insurance', 'Medical Insurance',     PayItemClassification.DEDUCTION,       PayItemCalcMethod.FIXED,              PayItemTaxTreatment.TAXABLE, 40, None),
    ('loan_recovery',     'Loan Recovery',         PayItemClassification.DEDUCTION,       PayItemCalcMethod.FIXED,              PayItemTaxTreatment.TAXABLE, 50, None),
]


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def company(app):
    c = Company(name='Test PLC')
    db.session.add(c)
    db.session.flush()
    return c


@pytest.fixture
def system_catalog(app, company):
    """Create system catalog items (company_id IS NULL) and seed company copies."""
    for key, name, cls, method, treatment, order, rate in SYSTEM_KEYS:
        item = PayItemType(
            company_id=None,
            key=key,
            name_en=name,
            name_am=name,
            classification=cls,
            calculation_method=method,
            tax_treatment=treatment,
            sort_order=order,
            is_system=True,
        )
        if rate is not None:
            item.rate = rate
        db.session.add(item)
    db.session.flush()
    seed_pay_item_types(company.id)
    db.session.flush()
    return company


def _co_id(company_id, key):
    """Look up a company-scoped PayItemType id by key."""
    return db.session.query(PayItemType).filter_by(
        company_id=company_id, key=key,
    ).one().id


def _make_employee(company_id, emp_id='EMP001', name='Test Employee',
                   basic_salary=Decimal('10000')):
    emp = Employee(
        company_id=company_id,
        employee_id=emp_id,
        name=name,
        phone='0912345678',
        basic_salary=basic_salary,
    )
    db.session.add(emp)
    db.session.flush()
    return emp


def _add_assignment(company_id, emp_id, item_key, fixed=None, **kw):
    """Create a PayrollItemAssignment referencing a company-scoped item type."""
    type_id = _co_id(company_id, item_key)
    kw.setdefault('fixed_amount', fixed)
    a = PayrollItemAssignment(
        company_id=company_id,
        employee_id=emp_id,
        pay_item_type_id=type_id,
        **kw,
    )
    db.session.add(a)
    db.session.flush()
    return a


# ---------------------------------------------------------------------------
# 1. Cross-validation: elements engine vs legacy calculate_payroll
# ---------------------------------------------------------------------------

class TestCrossValidateLegacy:
    """calculate_payroll_from_assignments must produce the same core values
    as the legacy calculate_payroll for equivalent inputs."""

    def test_basic_salary_only(self, app, system_catalog):
        c = system_catalog
        emp = _make_employee(c.id, basic_salary=Decimal('10000'))
        _add_assignment(c.id, emp.id, 'basic_salary', fixed=Decimal('10000'))

        result = calculate_payroll_from_assignments(emp, c.id, date(2025, 9, 25))
        legacy = calculate_legacy(basic_salary=Decimal('10000'), allowances=0)

        assert result['gross'] == legacy['gross']
        assert result['pension_employee'] == legacy['pension_employee']
        assert result['pension_employer'] == legacy['pension_employer']
        assert result['tax'] == legacy['tax']
        assert result['net'] == legacy['net']

    def test_basic_plus_housing_allowance(self, app, system_catalog):
        c = system_catalog
        basic = Decimal('15000')
        housing = Decimal('3000')
        emp = _make_employee(c.id, basic_salary=basic)
        _add_assignment(c.id, emp.id, 'basic_salary', fixed=basic)
        _add_assignment(c.id, emp.id, 'housing_allowance', fixed=housing)

        result = calculate_payroll_from_assignments(emp, c.id, date(2025, 9, 25))
        legacy = calculate_legacy(basic_salary=basic, allowances=housing)

        assert result['gross'] == legacy['gross']       # 18000
        assert result['taxable'] == legacy['taxable']
        assert result['tax'] == legacy['tax']
        assert result['net'] == legacy['net']


# ---------------------------------------------------------------------------
# 2. Bug fix: total_deductions correctly populated
# ---------------------------------------------------------------------------

class TestTotalDeductions:
    """Before the fix, _merge_post_tax_deductions returned its total but
    the caller discarded it as a bare expression, so total_deductions
    was always 0."""

    def test_post_tax_deduction_reduces_net(self, app, system_catalog):
        c = system_catalog
        basic = Decimal('10000')
        emp = _make_employee(c.id, basic_salary=basic)
        _add_assignment(c.id, emp.id, 'basic_salary', fixed=basic)
        loan = _add_assignment(c.id, emp.id, 'loan_recovery', fixed=Decimal('2000'),
                               tracking_mode='declining',
                               remaining_balance=Decimal('2000'))

        result = calculate_payroll_from_assignments(emp, c.id, date(2025, 9, 25))

        # total_deductions must reflect the 2000 loan, not 0
        assert result['total_deductions'] == Decimal('2000.00'), \
            f"Expected 2000.00, got {result['total_deductions']}"

        # net must be reduced accordingly
        legacy_no_ded = calculate_legacy(basic_salary=basic, allowances=0)
        expected_net = legacy_no_ded['net'] - Decimal('2000')
        assert result['net'] == expected_net, \
            f"Expected net={expected_net}, got {result['net']}"


# ---------------------------------------------------------------------------
# 3. Bug fix: declining-balance persistence
# ---------------------------------------------------------------------------

class TestDecliningBalance:
    """Before the fix, remaining_balance was decremented in memory but
    the unit-of-work change was discarded because the return value of
    _merge_post_tax_deductions was never assigned."""

    def test_remaining_balance_decremented(self, app, system_catalog):
        c = system_catalog
        emp = _make_employee(c.id, basic_salary=Decimal('15000'))
        _add_assignment(c.id, emp.id, 'basic_salary', fixed=Decimal('15000'))

        # Loan: fixed 5000 per month, declining balance 3000 remaining
        # recoverable = min(5000, 3000) = 3000
        loan = _add_assignment(c.id, emp.id, 'loan_recovery', fixed=Decimal('5000'),
                               tracking_mode='declining',
                               remaining_balance=Decimal('3000'))

        assert loan.remaining_balance == Decimal('3000.00')

        result = calculate_payroll_from_assignments(emp, c.id, date(2025, 9, 25))

        assert result['total_deductions'] == Decimal('3000.00')
        assert loan.remaining_balance == Decimal('0.00'), \
            f"Expected 0.00, got {loan.remaining_balance}"

        # Verify it's in the deduction details
        detail = result['deduction_details'][-1]  # last detail is our loan
        assert detail['remaining_balance'] == Decimal('0.00')

    def test_partial_recovery(self, app, system_catalog):
        """When fixed_amount > remaining_balance, only remaining_balance
        is recovered (already capped by min())."""
        c = system_catalog
        emp = _make_employee(c.id, basic_salary=Decimal('15000'))
        _add_assignment(c.id, emp.id, 'basic_salary', fixed=Decimal('15000'))

        loan = _add_assignment(c.id, emp.id, 'loan_recovery', fixed=Decimal('5000'),
                               tracking_mode='declining',
                               remaining_balance=Decimal('1000'))

        result = calculate_payroll_from_assignments(emp, c.id, date(2025, 9, 25))

        # min(5000, 1000) = 1000
        assert result['total_deductions'] == Decimal('1000.00')
        assert loan.remaining_balance == Decimal('0.00')


# ---------------------------------------------------------------------------
# 4. percent_of_item raises NotImplementedError
# ---------------------------------------------------------------------------

class TestPercentOfItem:
    """percent_of_item is deferred (Spec section 2i).
    Must raise NotImplementedError, not silently return 0."""

    def test_raises_not_implemented(self, app, system_catalog):
        c = system_catalog
        emp = _make_employee(c.id, basic_salary=Decimal('10000'))
        _add_assignment(c.id, emp.id, 'basic_salary', fixed=Decimal('10000'))

        # Create a company-specific earning item with percent_of_item method
        pct_item = PayItemType(
            company_id=c.id,
            key='sales_bonus',
            name_en='Sales Bonus',
            classification=PayItemClassification.EARNING,
            calculation_method=PayItemCalcMethod.PERCENT_OF_ITEM,
            tax_treatment=PayItemTaxTreatment.TAXABLE,
            sort_order=2,
        )
        db.session.add(pct_item)
        db.session.flush()

        # Assignment referencing the percent_of_item type
        db.session.add(PayrollItemAssignment(
            company_id=c.id, employee_id=emp.id,
            pay_item_type_id=pct_item.id, fixed_amount=Decimal('0'),
        ))
        db.session.flush()

        with pytest.raises(NotImplementedError, match='percent_of_item'):
            calculate_payroll_from_assignments(emp, c.id, date(2025, 9, 25))


# ---------------------------------------------------------------------------
# 5. System catalog seeding
# ---------------------------------------------------------------------------

class TestSeedPayItemTypes:
    """seed_pay_item_types copies all active system items into a company's
    catalog, skipping keys that already have a company-specific copy."""

    def test_creates_company_copies(self, app, system_catalog):
        c = system_catalog
        for key, _, _, _, _, _, _ in SYSTEM_KEYS:
            count = db.session.query(PayItemType).filter_by(
                company_id=c.id, key=key,
            ).count()
            assert count == 1, f"Missing or duplicate company copy for {key}"

    def test_no_duplicates_on_reseed(self, app, system_catalog):
        seed_pay_item_types(system_catalog.id)
        for key, _, _, _, _, _, _ in SYSTEM_KEYS:
            count = db.session.query(PayItemType).filter_by(
                company_id=system_catalog.id, key=key,
            ).count()
            assert count == 1, f"Duplicate created on reseed for {key}"

    def test_inactive_not_seeded(self, app, company):
        active = PayItemType(
            company_id=None, key='active_item', name_en='Active',
            classification=PayItemClassification.EARNING,
            calculation_method=PayItemCalcMethod.FIXED,
            is_system=True, is_active=True, sort_order=1,
        )
        inactive = PayItemType(
            company_id=None, key='inactive_item', name_en='Inactive',
            classification=PayItemClassification.EARNING,
            calculation_method=PayItemCalcMethod.FIXED,
            is_system=True, is_active=False, sort_order=2,
        )
        db.session.add_all([active, inactive])
        db.session.flush()

        seed_pay_item_types(company.id)

        assert db.session.query(PayItemType).filter_by(
            company_id=company.id, key='active_item').count() == 1
        assert db.session.query(PayItemType).filter_by(
            company_id=company.id, key='inactive_item').count() == 0


# ---------------------------------------------------------------------------
# 6. Output shape
# ---------------------------------------------------------------------------

class TestOutputShape:
    """Output dict must contain all legacy keys plus 'line_items'."""

    EXPECTED_KEYS = {
        'gross', 'taxable', 'tax', 'pension_employee', 'pension_employer',
        'net_before_deductions', 'sick_leave_reduction', 'total_deductions',
        'deduction_details', 'net', 'tax_explanation',
        'overtime_pay', 'overtime_total_hours', 'overtime_result',
        'exempt_allowances', 'taxable_allowances', 'allowance_details',
        'line_items',
    }

    @pytest.fixture(autouse=True)
    def _setup(self, app, system_catalog):
        self.c = system_catalog
        self.emp = _make_employee(system_catalog.id, basic_salary=Decimal('10000'))
        _add_assignment(system_catalog.id, self.emp.id,
                        'basic_salary', fixed=Decimal('10000'))

    def test_all_keys_present(self):
        result = calculate_payroll_from_assignments(
            self.emp, self.c.id, date(2025, 9, 25),
        )
        for key in self.EXPECTED_KEYS:
            assert key in result, f"Missing key: {key}"

    def test_line_items_has_basic_salary(self):
        result = calculate_payroll_from_assignments(
            self.emp, self.c.id, date(2025, 9, 25),
        )
        keys = [li['item_key'] for li in result['line_items']]
        assert 'basic_salary' in keys, f"basic_salary not in line_items: {keys}"

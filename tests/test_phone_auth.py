"""
Phone number authentication tests.

Tests:
- Ethiopian phone format validation
- Phone + password login
- Registration with phone
- Duplicate phone detection
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from payroll_engine import create_app, db
from payroll_engine.models import Company, User, validate_ethiopian_phone


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


# ---------------------------------------------------------------
# Phone Validation Tests
# ---------------------------------------------------------------


def test_valid_phone_formats():
    """Valid Ethiopian phone numbers should be accepted (Ethio Telecom + Safaricom)."""
    valid_numbers = [
        # Ethio Telecom (09X)
        ('+251911234567', '0911234567'),
        ('0911234567', '0911234567'),
        ('+251 911 234 567', '0911234567'),
        ('0911 234 567', '0911234567'),
        ('+251922345678', '0922345678'),
        ('0922345678', '0922345678'),
        ('+251933456789', '0933456789'),
        ('0933456789', '0933456789'),
        ('+251944567890', '0944567890'),
        ('0944567890', '0944567890'),
        ('+251955678901', '0955678901'),
        ('0955678901', '0955678901'),
        ('+251966789012', '0966789012'),
        ('0966789012', '0966789012'),
        ('+251977890123', '0977890123'),
        ('0977890123', '0977890123'),
        ('+251988901234', '0988901234'),
        ('0988901234', '0988901234'),
        ('+251999012345', '0999012345'),
        ('0999012345', '0999012345'),
        # Safaricom (07X)
        ('+251711234567', '0711234567'),
        ('0711234567', '0711234567'),
        ('+251 711 234 567', '0711234567'),
        ('0711 234 567', '0711234567'),
        ('+251722345678', '0722345678'),
        ('0722345678', '0722345678'),
        ('+251733456789', '0733456789'),
        ('0733456789', '0733456789'),
    ]
    for phone, expected in valid_numbers:
        is_valid, normalized, error = validate_ethiopian_phone(phone)
        assert is_valid, f'{phone} should be valid but got: {error}'
        assert normalized == expected, f'{phone} normalized to {normalized}, expected {expected}'


def test_invalid_phone_formats():
    """Invalid phone numbers should be rejected."""
    invalid_numbers = [
        '+1234567890',  # Not Ethiopian
        '12345',  # Too short
        'abcdefghij',  # Not numbers
        '',  # Empty
        '091123456',  # Too short (9 digits after 0)
        '09112345678',  # Too long (11 digits after 0)
        '+25191123456',  # Too short after +251
        '+2519112345678',  # Too long after +251
        '0611234567',  # 06X prefix
        '0811234567',  # 08X prefix
        '+44911234567',  # UK prefix
    ]
    for phone in invalid_numbers:
        is_valid, normalized, error = validate_ethiopian_phone(phone)
        assert not is_valid, f'{phone} should be invalid but was accepted as {normalized}'
        assert error is not None, f'{phone} should have error message'


def test_phone_normalization():
    """Phone numbers should normalize to 09XXXXXXXX format."""
    is_valid, normalized, _error = validate_ethiopian_phone('+251911234567')
    assert is_valid
    assert normalized == '0911234567'

    is_valid, normalized, _error = validate_ethiopian_phone('0911234567')
    assert is_valid
    assert normalized == '0911234567'


# ---------------------------------------------------------------
# Registration Tests
# ---------------------------------------------------------------


def test_register_with_phone(ctx):
    """Registration with phone number should work."""
    create_app().test_client()
    # Can't easily test full registration without app context
    # Test the model directly
    company = Company(name='TestCo')
    db.session.add(company)
    db.session.commit()

    user = User(phone='0911234567', company_id=company.id, role='admin')
    user.set_password('testpass123')
    db.session.add(user)
    db.session.commit()

    found = User.query.filter_by(phone='0911234567').first()
    assert found is not None
    assert found.check_password('testpass123')


def test_duplicate_phone_rejected(ctx):
    """Duplicate phone numbers should be rejected."""
    company = Company(name='TestCo')
    db.session.add(company)
    db.session.commit()

    user1 = User(phone='0911234567', company_id=company.id, role='admin')
    user1.set_password('pass1')
    db.session.add(user1)
    db.session.commit()

    user2 = User(phone='0911234567', company_id=company.id, role='employee')
    user2.set_password('pass2')
    db.session.add(user2)

    with pytest.raises(Exception):  # IntegrityError
        db.session.commit()
    db.session.rollback()


def test_user_without_email(ctx):
    """Users should be able to register without email."""
    company = Company(name='TestCo')
    db.session.add(company)
    db.session.commit()

    user = User(phone='0911234567', company_id=company.id, role='admin')
    user.set_password('testpass123')
    db.session.add(user)
    db.session.commit()

    found = User.query.filter_by(phone='0911234567').first()
    assert found.email is None
    assert found.phone == '0911234567'


def test_phone_lookup_works(ctx):
    """Looking up user by normalized phone should work."""
    company = Company(name='TestCo')
    db.session.add(company)
    db.session.commit()

    user = User(phone='0911234567', company_id=company.id, role='admin')
    user.set_password('testpass123')
    db.session.add(user)
    db.session.commit()

    # Lookup with different formats should all find the same user
    is_valid, normalized, _ = validate_ethiopian_phone('+251911234567')
    assert is_valid
    found = User.query.filter_by(phone=normalized).first()
    assert found is not None
    assert found.phone == '0911234567'


def test_multiple_users_different_phones(ctx):
    """Multiple users can have different phone numbers."""
    company = Company(name='TestCo')
    db.session.add(company)
    db.session.commit()

    user1 = User(phone='0911234567', company_id=company.id, role='admin')
    user1.set_password('pass1')
    user2 = User(phone='0922345678', company_id=company.id, role='employee')
    user2.set_password('pass2')
    db.session.add_all([user1, user2])
    db.session.commit()

    assert User.query.filter_by(phone='0911234567').first() is not None
    assert User.query.filter_by(phone='0922345678').first() is not None

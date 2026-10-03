"""Freeze calculation inputs without changing the payroll calculator."""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

Q = Decimal('0.01')
MAX_MONEY = Decimal('9999999999.99')


def money(value, *, positive=False):
    try:
        result = Decimal(str(value))
        if not result.is_finite() or abs(result) > MAX_MONEY or result != result.quantize(Q):
            raise ValueError
        if positive and result <= 0:
            raise ValueError
        return result.quantize(Q)
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError('Amount must be finite, within range, and have at most two decimal places.') from None


def freeze_context(for_date, *, employee_id, name, bank, period_start=None, tin='', department='', position=''):
    from payroll_engine.tax import _get_brackets_and_relief

    brackets, _relief = _get_brackets_and_relief(for_date)
    return {
        'version': 1,
        'calculation_date': for_date.isoformat(),
        'period_start': (period_start or for_date.replace(day=1)).isoformat(),
        'tax_brackets': [
            {'max': None if upper.is_infinite() else str(upper), 'rate': str(rate)} for upper, rate in brackets
        ],
        'employee': {
            'id': employee_id,
            'name': name,
            'bank': bank or '',
            'tin': tin or '',
            'department': department or '',
            'position': position or '',
        },
    }


def frozen_tax(taxable, context):
    """Apply the retained progressive brackets, never today's mutable rules."""
    if not isinstance(context, dict) or context.get('version') != 1 or not context.get('tax_brackets'):
        raise ValueError('Original payroll has no frozen calculation context. Historical review is required.')
    taxable = money(taxable)
    if taxable < 0:
        raise ValueError('Taxable income cannot be negative.')
    total, previous = Decimal('0'), Decimal('0')
    brackets = context['tax_brackets']
    try:
        for index, bracket in enumerate(brackets):
            upper = Decimal('Infinity') if bracket['max'] is None else Decimal(bracket['max'])
            rate = Decimal(bracket['rate'])
            if upper.is_nan() or upper <= previous or not rate.is_finite() or not 0 <= rate <= 1:
                raise ValueError
            if upper.is_infinite() and index != len(brackets) - 1:
                raise ValueError
            total += max(Decimal('0'), min(taxable, upper) - previous) * rate
            previous = upper
        if not previous.is_infinite():
            raise ValueError
    except (InvalidOperation, KeyError, TypeError, ValueError):
        raise ValueError('The retained tax rule is incomplete or invalid. Historical review is required.') from None
    return max(Decimal('0'), total.quantize(Q, rounding=ROUND_HALF_UP))

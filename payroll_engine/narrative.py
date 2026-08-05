"""
Payroll Narrative — Trust Pattern #6

Generates a plain-English paragraph from a Change Summary.
Turns numbers into a story accountants can read in 5 seconds.

Example output:
    "August payroll includes 128 employees, 2 new hires, 1 resignation,
    3 promotions, and 12 overtime claims. Total payroll increased by 1.3%,
    primarily because of overtime and new hires. No unusual variances
    were detected."
"""
from payroll_engine.change_summary import ChangeSummary


def generate_narrative(summary: ChangeSummary) -> str:
    """
    Generate a plain-English narrative from a Change Summary.

    Args:
        summary: ChangeSummary from compute_change_summary()

    Returns:
        Human-readable paragraph explaining the payroll period.
    """
    if not summary:
        return 'Payroll data not available.'

    parts = []

    # Opening sentence: employee count
    emp_text = _employee_count_text(summary)
    parts.append(emp_text)

    # Middle: what happened
    events = _event_text(summary)
    if events:
        parts.append(events)

    # Delta explanation
    delta_text = _delta_text(summary)
    if delta_text:
        parts.append(delta_text)

    # Variance verdict
    variance_text = _variance_text(summary)
    if variance_text:
        parts.append(variance_text)

    return ' '.join(parts)


def _employee_count_text(summary):
    """Generate the opening sentence about employee count."""
    count = summary.current_employee_count
    period = summary.current_period

    if not summary.previous_period:
        # First payroll
        return f'{period} payroll includes {count} employee{"s" if count != 1 else ""}.'

    if summary.headcount_change > 0:
        return (
            f'{period} payroll includes {count} employees '
            f'(+{summary.headcount_change} from last period).'
        )
    elif summary.headcount_change < 0:
        return (
            f'{period} payroll includes {count} employees '
            f'({summary.headcount_change} from last period).'
        )
    else:
        suffix = 's' if count != 1 else ''
        return f'{period} payroll includes {count} employee{suffix}.'


def _event_text(summary):
    """Describe the events that happened this period."""
    events = []

    if summary.new_hires:
        n = len(summary.new_hires)
        events.append(f'{n} new hire{"s" if n != 1 else ""}')

    if summary.departures:
        n = len(summary.departures)
        events.append(f'{n} resignation{"s" if n != 1 else ""}')

    if summary.salary_changes:
        n = len(summary.salary_changes)
        events.append(f'{n} salary change{"s" if n != 1 else ""}')

    if summary.overtime_entries:
        n = len(summary.overtime_entries)
        events.append(f'{n} overtime claim{"s" if n != 1 else ""}')

    if summary.adjustments:
        n = len(summary.adjustments)
        events.append(f'{n} adjustment{"s" if n != 1 else ""}')

    if not events:
        if summary.previous_period:
            return 'No changes from last period.'
        return ''

    if len(events) == 1:
        return f'This period includes {events[0]}.'
    elif len(events) == 2:
        return f'This period includes {events[0]} and {events[1]}.'
    else:
        return f'This period includes {", ".join(events[:-1])}, and {events[-1]}.'


def _delta_text(summary):
    """Explain the payroll delta in plain English."""
    if not summary.previous_period:
        return ''

    pct = summary.gross_delta_pct
    delta = summary.gross_delta

    if abs(pct) < 0.1:
        return 'Total payroll is essentially unchanged.'

    direction = 'increased' if pct > 0 else 'decreased'
    magnitude = abs(pct)

    # Determine primary reason
    reasons = []
    if summary.new_hires:
        n = len(summary.new_hires)
        suffix = 's' if n != 1 else ''
        reasons.append(f'{n} new hire{suffix}')
    if summary.salary_changes:
        reasons.append('salary changes')
    if summary.overtime_entries:
        reasons.append('overtime')
    if summary.departures:
        reasons.append('departures')
    if summary.adjustments:
        reasons.append('adjustments')

    if reasons:
        if len(reasons) == 1:
            reason_text = f'primarily because of {reasons[0]}'
        elif len(reasons) == 2:
            reason_text = f'primarily because of {reasons[0]} and {reasons[1]}'
        else:
            reason_text = f'primarily because of {", ".join(reasons[:-1])}, and {reasons[-1]}'
    else:
        reason_text = 'due to individual pay changes'

    return f'Total payroll {direction} by {magnitude:.1f}%, {reason_text}.'


def _variance_text(summary):
    """Add variance verdict."""
    if not summary.previous_period:
        return ''

    if summary.has_unusual_variance:
        notes = summary.variance_notes
        if notes:
            return f'⚠ Unusual variance detected: {notes[0]}'
        return '⚠ Unusual variance detected — review recommended.'

    return 'No unusual variances detected.'

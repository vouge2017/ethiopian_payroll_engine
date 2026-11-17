"""Failures that must stop payroll when its dated rules are unavailable."""


class PayrollRuleError(ValueError):
    """Payroll cannot continue without its configured rules."""


class MissingPayrollRuleError(PayrollRuleError):
    """The applicable rule is missing or incomplete."""


class PayrollRuleLookupError(PayrollRuleError):
    """The rule could not be read from the database."""


def active_rule(for_date, kind):
    from payroll_engine.models import TaxRule

    try:
        rule = TaxRule.get_active_rule(for_date)
    except Exception as exc:
        raise PayrollRuleLookupError(
            f'Could not load the {kind} rule for the payroll date. Check the database and retry.'
        ) from exc
    if rule is None:
        raise MissingPayrollRuleError(
            f'The {kind} rule for the payroll date is missing. Configure an applicable rule before continuing.'
        )
    return rule

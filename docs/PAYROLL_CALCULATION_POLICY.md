# Deterministic payroll calculation

Statutory payroll amounts must come from defined, versioned rules and Decimal
arithmetic. An LLM, chatbot or other probabilistic model must not calculate,
select or approve PAYE, pension, overtime, deductions or net pay.

The calculation boundary is `tax.py`, `pension.py`, `overtime.py`, `payroll.py`
and `payroll_elements.py`. Inputs, effective payroll date, applied rule version,
rounding and approved results must be explicit and reproducible. Explanations
must describe those facts; they must never become a second calculation engine.

Any future AI assistance with import mapping or wording is advisory. Users must
confirm mappings, and deterministic validation must reject invalid inputs.
Statutory policy changes require authoritative sources, practitioner validation
and regression examples. Passing tests proves agreement with defined examples,
not independent legal certification.

## Accounting output trial defaults

The synthetic trial uses salary expense less unpaid/sick reductions (5100),
employee loan/advance receivables recovered (1300), and other payroll deductions
payable (2300), alongside existing pension, PAYE and bank/cash accounts.
The product owner authorized these defaults for synthetic testing only.
An accountant must validate the company chart and deduction classifications
before these files are used in live books. Unknown custom deduction types use
the trial deductions-payable bucket and need explicit review for live use.

Accounting exports must reconcile each employee and the complete journal.
Missing or inconsistent facts must block export, not be hidden by a balancing
entry. Approval/export does not prove payment or filing.

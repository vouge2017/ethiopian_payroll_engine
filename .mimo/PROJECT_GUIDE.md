# EthioPayroll — Project Guide

**Repo:** vouge2017/ethiopian_payroll_engine
**Stack:** Flask + SQLAlchemy + PostgreSQL (production) / SQLite (dev/test)
**Mode:** Online-first SaaS for Ethiopian SMEs

---

## What This Is

A payroll engine for Ethiopian small businesses. Calculates income tax (2025 brackets), POSSA pension (7%/11%), overtime, severance. Generates PDF payslips, ERCA reports, pension reports, bank transfer files.

**Target user:** Tigist — an Ethiopian SME owner who currently does payroll in Excel.

---

## Architecture

```
payroll_engine/
├── __init__.py      # App factory, context processor, JSON serializer
├── auth.py          # Login, register, language switch
├── main.py          # 36 routes: employees, payroll, reports, settings, employee portal
├── api.py           # REST API (v1)
├── models.py        # SQLAlchemy models with TenantQuery isolation
├── tax.py           # Progressive tax brackets (Decimal math)
├── pension.py       # 7%/11% pension (Decimal math)
├── overtime.py      # Labor Proclamation rates (Decimal math)
├── payroll.py       # Single entry point — enforces deduction order
├── severance.py     # Termination pay calculator (Decimal math)
├── compliance.py    # ERCA/PSSA deadlines, compliance scoring
├── validation.py    # Pre-processing checks (BLOCK/FLAG/WARN)
├── reports.py       # ERCA + Pension Excel reports
├── bank_file.py     # CBE/Dashen/Awash/Telebirr bank file generation
├── pdf.py           # PDF payslip with NotoSansEthiopic font
├── ethiopian_calendar.py  # Ethiopian ↔ Gregorian date conversion
├── i18n.py          # Amharic strings (169 keys)
├── i18n_om.py       # Afaan Oromoo strings
├── demo.py          # Demo mode: auto-creates sample company
├── templates/       # 20 Jinja2 templates
├── static/css/      # Responsive CSS
└── fonts/           # NotoSansEthiopic-Regular.ttf
```

---

## Key Design Decisions

1. **TenantQuery** — structural tenant isolation. Raises `RuntimeError` if `company_id` not filtered.
2. **Single entry point** — `calculate_payroll()` is the ONLY way to calculate. Enforces pension-before-tax deduction order.
3. **Numeric(12,2)** — all money columns use Decimal, not Float. Prevents silent rounding drift.
4. **AuditLog** — append-only trail for all employee/payroll changes.
5. **Validation** — BLOCK/FLAG/WARN severity. Human messages with employee names.

---

## Running Locally

```bash
pip install -r requirements.txt
FLASK_ENV=development python run.py
# Visit http://localhost:5000/demo
```

---

## Running Tests

```bash
pytest -q
# 245 passed, 1 skipped
```

---

## Deployment (Render)

render.yaml configures:
- Web service with `flask db upgrade && gunicorn`
- Managed PostgreSQL with automated backups
- Auto-generated SECRET_KEY
- FLASK_ENV=production, FLASK_APP=wsgi:app

---

## External Audit Findings (2026-07-09)

| Fix | Status | What |
|---|---|---|
| FIX 1 | ✅ Done | Float → Numeric(12,2) for money |
| FIX 2 | ⬜ Next | Row lock on payroll approval |
| FIX 3 | ⬜ Next | Rate limiting |
| FIX 4 | ⬜ Next | Database indexes |
| FIX 5 | ⬜ Next | Encrypt bank_account/tin |

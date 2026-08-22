# 🇪🇹 Ethiopian Payroll Engine

A web-based payroll system for Ethiopian SMEs. Calculates income tax (2025 brackets), POSSA pension, generates payslips, bank files, and ERCA/PSSA reports.

## Quick Start (Local Development)

```bash
# 1. Clone
git clone https://github.com/vouge2017/ethiopian_payroll_engine.git
cd ethiopian_payroll_engine

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set environment variables
export DATABASE_URL="sqlite:///app.db"
export SECRET_KEY="dev-change-in-production"
export DB_ENCRYPTION_KEY="dev-key-not-secure"

# 4. Initialize database
flask db upgrade

# 5. Run
flask run
# → http://localhost:5000
```

Open `http://localhost:5000`, create an account, and start adding employees.

## Features

- **Tax calculation** — Ethiopian 2025 progressive brackets (Proclamation No. 1395/2025)
- **Pension** — 7% employee / 11% employer on basic salary (Proclamation No. 715/2011)
- **Payroll processing** — CSV upload, spreadsheet editor, approval workflow
- **PDF payslips** — Company-branded, with tax bracket breakdown
- **Bank files** — CBE, Dashen, Awash, BOA, Wegagen, NIB, Bunna, Zemen, Lion, Telebirr, M-Pesa
- **ERCA/PSSA reports** — Excel format for tax and pension filings
- **Leave management** — Annual, sick, maternity, paternity, special leave
- **Multi-tenancy** — Structural data isolation between companies
- **Employee portal** — Self-service payslips, leave requests, profile
- **MFA** — TOTP-based two-factor authentication
- **Audit trail** — SHA-256 hash chain for tamper detection

## Tech Stack

- **Backend:** Flask 3.1, SQLAlchemy 2.0, Flask-Login, Flask-Migrate
- **Database:** PostgreSQL (production), SQLite (development)
- **PDF:** ReportLab
- **Auth:** Flask-Login + pyotp (MFA)
- **Monitoring:** Sentry (optional)

## Production Deployment

Deploy to Render using the included `render.yaml`:

```bash
# Push to GitHub — auto-deploys via Render
git push origin main
```

Required environment variables in Render dashboard:
- `SECRET_KEY` — auto-generated
- `DB_ENCRYPTION_KEY` — auto-generated
- `SENTRY_DSN` — optional, for error monitoring

## Testing

```bash
# Run all tests
pytest -q

# Run with coverage
pytest --cov=payroll_engine

# Verify features
python3 verify_status.py
```

## UI/UX Quality Audits

The platform ships with an automated **UI/UX evaluation toolchain** in [`qa/`](qa/) covering the core frontend-engineering skill areas: accessibility, responsive mobile/web screens, network resilience, and performance.

```bash
cd qa
npm install          # one-time setup

npm run audit:a11y         # WCAG 2.1 A/AA accessibility scan (axe-core)
npm run audit:responsive   # mobile 360/375/414px, tablet 768px, desktop 1440px checks + screenshots
npm run audit:pwa          # manifest, service worker & offline behaviour
npm run audit:lighthouse   # throttled-network performance, a11y, best practices, SEO scores
npm run audit:all          # run everything; reports land in qa/reports/
```

See **[UI_UX_SKILLS_EVALUATION_GUIDE.md](UI_UX_SKILLS_EVALUATION_GUIDE.md)** for the full skill matrix, targets, and how to read the reports.

## Project Structure

```
payroll_engine/
├── __init__.py          # App factory
├── main.py              # Dashboard, setup, company switching
├── employees_bp.py      # Employee CRUD, overtime, deductions, leave
├── payroll_bp.py        # Payroll upload, processing, approval
├── reports_bp.py        # ERCA, pension, bank, filing history
├── portal_bp.py         # Employee self-service portal
├── settings_bp.py       # Company settings, team management
├── api.py               # REST API with Bearer token auth
├── models.py            # SQLAlchemy models with tenant isolation
├── payroll.py           # Core calculation engine
├── tax.py               # Tax brackets (Proclamation 1395/2025)
├── pension.py           # Pension rates (Proclamation 715/2011)
├── services/            # Business logic layer
├── templates/           # Jinja2 HTML templates
└── fonts/               # Ethiopian fonts for PDF generation
```

## License

MIT

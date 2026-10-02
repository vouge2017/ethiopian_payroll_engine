# Changelog

All notable changes to this project will be documented in this file.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)

## [Unreleased]

### Added
- Excel-compatible payroll engine (`excel_payroll.py`) — deterministic, explainable, auditable
- Per-employee calculation flow (8-12 steps with formula, inputs, result, legal reference)
- SHA-256 determinism proof (input hash + output hash)
- Multi-sheet Excel export (8 sheets: Summary, Payroll, Calculation Flow, Tax Breakdown, Exceptions, Changes, Bank File, Approval)
- 9 validation rules in new engine (BLOCK/FLAG/WARN)
- Change detection vs previous period (new hires, departures, salary changes)
- Approval state machine (draft → review → approved → locked)
- Bank file auto-generation from approved payroll
- Adjustment payslip service (`services/adjustment_service.py`) — addition, deduction, net_override
- Month-end close workflow (`services/month_close.py`) — 7-step guided sequence
- Web calculation flow template (`templates/components/calculation_flow.html`)
- Month-end close template (`templates/payroll/month_close.html`)
- Strategic benchmark audit (`PLATFORM_GAP_ANALYSIS_AND_STRATEGIC_SCORECARD.md`)
- Async PDF generation (RQ + Redis background workers)
- Full test suite runner (`run_tests.py`) — subprocess isolation for CI
- Verification package for accountant review (15 sections)
- Payroll wizard stepper (4-step flow)
- Print styles for all report pages
- CSV exports for audit log & analytics
- Error pages (403, 404, 500)
- Command palette (Ctrl+K)
- Skeleton loading screens
- Toast notifications
- Sortable/filterable tables
- Breadcrumb navigation
- Confirmation modals
- Empty states
- Bottom navigation (mobile)
- Ethiopian naming convention (first/father/grandfather)
- Dark mode toggle
- Compliance deadlines (configurable per company)
- Payroll reference numbers (PR-YYYY-MM-NNN)
- `run_tests.py` for full test suite execution
- `SECURITY.md`, `CHANGELOG.md`, `LICENSE`
- `docker-compose.yml` for local development
- Ruff linter configuration

### Fixed
- CSP blocking Google Fonts and inline scripts
- Employee portal dashboard crash (`ps.gross_pay` → `ps.gross_salary`)
- Help page categories not rendering (`cat.name` → `cat.title`)
- Payslip download 404 (missing endpoint)
- 15 failing tests (stale expected values after rate changes)
- Migration chain duplicate revision ID
- 6 incorrect statutory values (overtime rates, cash limit, personal relief)
- Overtime rates corrected: day 1.25x→1.5x, night 1.5x→1.75x

### Changed
- Pension rates: 7% employee / 11% employer (verified against Proclamation 1268/2022)
- Tax brackets: updated to Proclamation No. 1395/2025
- Personal relief removed (not in current law)
- Cash payment limit: 30,000 → 50,000 ETB
- ERCA filing format redesigned to match real portal
- Verification package expanded from 9 to 15 sections

## [0.1.0] - 2026-07-06

### Added
- Initial release
- Core payroll calculation engine
- Multi-tenant architecture
- Authentication (password, phone, Google OAuth)
- Role-based authorization
- Employee portal
- PDF payslip generation
- Bank file generation (CBE, Dashen, Awash, BOA, etc.)
- ERCA/PSSA report generation
- Ethiopian calendar integration
- i18n (English, Amharic, Afaan Oromoo)
- API with token authentication
- Audit logging

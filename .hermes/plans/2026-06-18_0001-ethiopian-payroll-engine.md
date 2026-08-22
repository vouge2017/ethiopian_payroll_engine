# Ethiopian Payroll Engine Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build a core Ethiopian payroll engine that correctly calculates income tax (2025 brackets), POSSA pension (employee 7%, employer 11%), generates payslip and compliance PDFs, and supports CSV/Excel import for SME accountants.

**Architecture:** Modular Python backend with separate modules for tax calculation, pension, payslip generation (ReportLab), and data import. Offline-first Android front‑end (React Native) will call the same Python logic via a lightweight API or reuse the same code via Pyodide for MVP.

**Tech Stack:** Python 3.11, pandas (optional), ReportLab for PDF, CSV module for import, SQLite for offline storage, React Native/Expo for mobile, Telebirr API stub (later real), Docker for deployment.

---

### Task 1: Set up project skeleton and dependencies

**Objective:** Create repository structure, virtual environment, and lock required packages.

**Files:**
- Create: `payroll_engine/requirements.txt`
- Create: `payroll_engine/__init__.py` (empty)
- Create: `payroll_engine/tax.py`
- Create: `payroll_engine/pension.py`
- Create: `payroll_engine/payslip.py`
- Create: `payroll_engine/main.py` (entry point)
- Create: `tests/__init__.py`
- Create: `tests/test_tax.py`
- Create: `tests/test_pension.py`
- Create: `.gitignore`

**Step 1: Write requirements.txt**
```
reportlab>=3.6.0
pandas>=2.0.0   # optional for CSV handling
```

**Step 2: Install dependencies (simulated)** - In real environment run `pip install -r requirements.txt`.

**Step 3: Commit**
```bash
git add payroll_engine/requirements.txt payroll_engine/__init__.py payroll_engine/tax.py payroll_engine/pension.py payroll_engine/payslip.py payroll_engine/main.py tests/__init__.py tests/test_tax.py tests/test_pension.py .gitignore
git commit -m "feat: initialize project skeleton"
```

---

### Task 2: Implement tax calculation (TDD)

**Objective:** Implement `calculate_tax(gross)` according to 2025 Ethiopian brackets.

**Files:**
- Modify: `payroll_engine/tax.py`
- Modify: `tests/test_tax.py`

**Step 1: Write failing test** (see original plan).

**Step 2: Run test to verify failure** - Expect FAIL (function not defined).

**Step 3: Write minimal implementation** (see original plan).

**Step 4: Run test to verify pass** - Expect PASS.

**Step 5: Commit**
```bash
git add payroll_engine/tax.py tests/test_tax.py
git commit -m "feat: implement tax calculation with TDD"
```

---

### Task 3: Implement pension calculation (TDD)

**Objective:** Implement employee (7%) and employer (11%) pension on basic salary.

**Files:**
- Modify: `payroll_engine/pension.py`
- Modify: `tests/test_pension.py`

**Step 1: Write failing test** (see original plan).

**Step 2: Run test to verify failure**.

**Step 3: Write minimal implementation** (see original plan).

**Step 4: Run test to verify pass**.

**Step 5: Commit**
```bash
git add payroll_engine/pension.py tests/test_pension.py
git commit -m "feat: implement pension calculations"
```

---

### Task 4: Integrate tax, pension, and net pay in main processing script

**Objective:** Create `main.py` that reads CSV, computes tax, pension, net, and prints payslip‑like output.

**Files:**
- Create: `sample_employees.csv` (provided)
- Modify: `payroll_engine/main.py`

**Step 1: Write script skeleton** (see original plan).

**Step 2: Run script to verify output matches earlier demonstration**.

**Step 3: Commit**
```bash
git add sample_employees.csv payroll_engine/main.py
git commit -m "feat: create main payroll processing script"
```

---

### Task 5: Add PDF payslip generation using ReportLab

**Objective:** Create a function that, given an employee record, outputs a PDF payslip (Amharic + English) to a folder.

**Files:**
- Create: `payroll_engine/pdf.py`
- Modify: `payroll_engine/main.py` to call PDF generation
- Create: `output_payslips/` directory

**Step 1: Write failing test (optional)** – we can manually verify.

**Step 2: Implement PDF generation** (see original plan).

**Step 3: Update main.py to generate PDFs for each employee**.

**Step 4: Run and verify PDFs appear in output_payslips/**.

**Step 5: Commit**
```bash
git add payroll_engine/pdf.py payroll_engine/main.py
git commit -m "feat: add PDF payslip generation"
```

---

### Task 6: Implement CSV/Excel import with validation

**Objective:** Accept CSV with required columns, validate data types, and provide helpful error messages.

**Files:**
- Modify: `payroll_engine/main.py` (add validation)
- Create: `tests/test_import.py`

**Step 1: Write test for missing column**.

**Step 2: Implement validation** – check columns, ensure numeric fields are positive, etc.

**Step 3: Commit**.

---

### Task 7: Add offline‑first Android prototype (React Native/Expo)

**Objective:** Create a minimal Expo app that lets the user upload a CSV, run the same Python logic via a simple Flask API (or reuse same logic via Pyodide), and display/download payslip.

**Files:**
- Create: `mobile/App.js`
- Create: `mobile/components/Upload.js`
- Create: `mobile/screens/HomeScreen.js`
- Create: `mobile/backend/api.py` (Flask stub that calls payroll_engine functions)

**Step 1: Initialize Expo project**.

**Step 2: Build upload screen**.

**Step 3: Connect to backend**.

**Step 4: Display payslip and allow download**.

**Step 5: Commit**.

---

### Task 8: Stub Telebirr disbursement (two‑phase) and integrate

**Objective:** Implement a mock Telebirr API that records intent and confirms payment, later replace with real sandbox.

**Files:**
- Create: `payroll_engine/disbursement.py`
- Modify: `payroll_engine/main.py` to call disbursement after net pay calculation.

**Step 1: Write intent → confirm flow**.

**Step 2: Commit**.

---

### Task 9: Write comprehensive test suite and achieve ≥80% coverage

**Objective:** Add tests for edge cases (new hire mid‑month, termination, overtime, leave deductions) and ensure all core functions are covered.

**Files:**
- Create: `tests/test_edge_cases.py`
- Run coverage tool.

**Step 1: Add tests**.

**Step 2: Commit**.

---

### Task 10: Prepare deployment Dockerfile and CI pipeline

**Objective:** Create Dockerfile that builds the Python API and runs tests on push.

**Files:**
- Create: `Dockerfile`
- Create: `.github/workflows/ci.yml`

**Step 1: Write Dockerfile**.

**Step 2: Write CI workflow**.

**Step 3: Commit**.

---

---

### Task 11: Add Amharic tax explainer

**Objective:** Provide a plain‑language explanation of how tax was calculated for each employee, in Amharic.

**Files:**
- Modify: `payroll_engine/tax.py` (add `explain_tax_amharic`)
- Modify: `payroll_engine/main.py` (call and display)

**Step 1: Write function** (already done).

**Step 2: Integrate into main** (done).

**Step 3: Commit**.
```bash
git add payroll_engine/tax.py payroll_engine/main.py
git commit -m "feat: add Amharic tax explainer"
```

---

### Task 12: Add compliance health score

**Objective:** Compute a simple compliance score based on proximity to pension and tax filing deadlines.

**Files:**
- Create: `payroll_engine/compliance.py`
- Modify: `payroll_engine/main.py` (call and display)

**Step 1: Implement compliance.py** (done).

**Step 2: Integrate into main** (done).

**Step 3: Commit**.
```bash
git add payroll_engine/compliance.py payroll_engine/main.py
git commit -m "feat: add compliance health score"
```

---

### Task 13: Build minimal Flask web UI

**Objective:** Create a simple web interface where users can upload a CSV, run payroll, view results, and download PDF payslips.

**Files:**
- Create: `web/app.py` (Flask app)
- Create: `web/templates/index.html` (clean, professional design)
- Create: `web/static/style.css` (optional)
- Update: `payroll_engine/__init__.py` to expose functions if needed.

**Step 1: Set up Flask app**.

**Step 2: Design upload form and results table**.

**Step 3: Connect to payroll_engine functions**.

**Step 4: Allow PDF download**.

**Step 5: Test locally**.

**Step 6: Commit**.

---

### Task 14: Add email/Telegram notification stub

**Objective:** After payroll run, send a notification (email or Telegram) with summary and links to payslips (or placeholder).

**Files:**
- Create: `payroll_engine/notification.py` (stub)
- Modify: `web/app.py` to call after processing.

**Step 1: Write stub**.

**Step 2: Integrate into web flow**.

**Step 3: Commit**.

---

### Task 15: Create content marketing pieces (learn from NYLOS)

**Objective:** Publish blog‑style articles that educate Ethiopian SME owners about payroll compliance, tax calculations, and the benefits of automation.

**Topics:**
- "How to calculate income tax in Ethiopia (2025 brackets explained)"
- "POSSA pension: What every employer must know"
- "The 30 hours/month you lose to manual payroll – and how to get them back"
- "What happens when you miss the pension deadline"
- "Multi‑branch payroll: A guide for Ethiopian businesses"

**Files:**
- Create: `content/blog/` with markdown files.
- Optionally add a simple static site generator (e.g., MkDocs) or just host as static HTML.

**Step 1: Write first article**.

**Step 2: Add to repo**.

**Step 3: Commit**.

---

---

**Verification & Acceptance Criteria (updated)**

- Tax explanation appears in console/output for each employee.
- Compliance score is calculated and displayed.
- Flask web UI loads, accepts CSV, shows results, and allows PDF download.
- Notification stub is called (logs to console).
- At least one blog article is present in `content/blog/`.

**Next Steps After Plan Approval**

1. Offer to execute using `subagent‑driven‑development` – dispatch a fresh subagent per task with two‑stage review.
2. If approved, begin with Task 13 (web UI) as it provides a demonstrable MVP for stakeholders.

*Plan saved to `.hermes/plans/2026-06-18_0001-ethiopian-payroll-engine.md`.*
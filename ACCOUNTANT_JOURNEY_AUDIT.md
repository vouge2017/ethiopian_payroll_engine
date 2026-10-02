# ACCOUNTANT JOURNEY AUDIT
**Simulated Monthly Payroll Workflow Evaluation for Ethiopian SMEs**

**Main Deliverable Link:** [`PLATFORM_GAP_ANALYSIS_AND_STRATEGIC_SCORECARD.md`](PLATFORM_GAP_ANALYSIS_AND_STRATEGIC_SCORECARD.md)

---

## 1. 15-STAGE MONTHLY ACCOUNTANT WORKFLOW EVALUATION

We audited the complete monthly payroll lifecycle experienced by an Ethiopian accountant using EthioPayroll, answering whether the accountant can complete each stage without leaving the platform or falling back to Excel:

| Stage | Monthly Accountant Activity | Platform Implementation Status | Standalone without Excel? | Gaps & Friction Points |
| :--- | :--- | :--- | :--- | :--- |
| **1. Company Setup** | Configure company profile, TIN, pension ID, pay calendar, and bank accounts | 🟢 **VERIFIED WORKING** | **YES** | Multi-tenant isolation verified; clean setup wizard in `wizard_bp.py`. |
| **2. Payroll Configuration** | Define salary structures, allowance policies, tax brackets, and pension rules | 🟢 **VERIFIED WORKING** | **YES** | Proclamation 1395/2025 tax brackets and POSSA pension rules pre-configured. |
| **3. Employee Onboarding** | Add new hires, contract details, bank details, and statutory identifiers | 🟢 **VERIFIED WORKING** | **YES** | Bulk CSV import and individual CRUD forms (`employees_bp.py`). |
| **4. Payroll Inputs & Attendance** | Input overtime hours, allowances, bonuses, leave days, and manual deductions | 🟢 **VERIFIED WORKING** | **YES** | Keyboard-friendly spreadsheet editor allows fast grid data entry. |
| **5. Run Payroll Draft** | Trigger deterministic gross-to-net calculations for all active employees | 🟢 **VERIFIED WORKING** | **YES** | `payroll.py` executes progressive tax, pension, proration, and net pay formulas. |
| **6. Payroll Review** | Inspect draft gross payroll, total tax, employer pension cost, and total net pay | 🟢 **VERIFIED WORKING** | **YES** | Summary metrics displayed in payroll cockpit dashboard (`cockpit.py`). |
| **7. Change & Variance Analysis** | Compare current month vs. previous month to identify salary/headcount changes | 🟡 **IMPLEMENTED — NOT PROVEN** | **PARTIAL** | Change summary engine (`change_summary.py`) exists but needs pilot UX tuning. |
| **8. Exception Management** | Identify & resolve negative net pay, duplicate bank accounts, and missing TINs | 🟡 **IMPLEMENTED — NOT PROVEN** | **PARTIAL** | 14 exception rules coded in `exceptions.py`; UI needs one-click resolution. |
| **9. Approval & Period Lock** | Finalize payroll draft, capture digital sign-off, and lock period from further edits | 🟢 **VERIFIED WORKING** | **YES** | Immutable period lock and SHA-256 tamper-evident hash chain logging. |
| **10. Payslip Generation** | Generate PDF payslips and distribute to employee portal / email / Telegram | 🟢 **VERIFIED WORKING** | **YES** | ReportLab PDF generator (`pdf.py`) creates bilingual, branded payslips. |
| **11. Payment File Preparation** | Export bank-specific batch payment files (CBE, Dashen, Telebirr, Awash, etc.) | 🟢 **VERIFIED WORKING** | **YES** | Formatted text/CSV export generators in `bank_file.py`. |
| **12. Statutory Tax Filing** | Prepare ERCA eTax monthly income tax declaration spreadsheet | 🟢 **VERIFIED WORKING** | **YES** | `reports_bp.py` outputs exact Excel format required for ERCA portal upload. |
| **13. Statutory Pension Filing** | Prepare PSSA social security pension declaration spreadsheet | 🟢 **VERIFIED WORKING** | **YES** | Formatted pension schedule generated matching PSSA submission rules. |
| **14. Period Close & Archive** | Archive monthly run, update employee YTD balances, and advance payroll calendar | 🟢 **VERIFIED WORKING** | **YES** | Period status updated to `CLOSED`; historical data locked in database. |
| **15. Audit & Recovery** | Reconstruct historical run details during tax audit or reverse errors | 🟢 **VERIFIED WORKING** | **YES** | Cryptographic hash chain allows verification of period state integrity. |

---

## 2. SUMMARY OF ACCOUNTANT JOURNEY FEASIBILITY

* **Current Stage:** The platform successfully covers **13 out of 15 stages standalone without requiring Excel**.
* **Primary Missing Workflow:** The only critical friction point blocking accounting firms from managing dozens of client SMEs is the lack of a **Multi-Company Accountant Cockpit** (single-login client switcher).

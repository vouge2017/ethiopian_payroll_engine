# 🇪🇹 TRANSLATION STRINGS — English to Amharic/Afaan Oromoo

**Instructions:** Fill in the `amharic` and/or `afaan_oromoo` column for each English string.
Return this file to me and I'll integrate the translations into the codebase.

---

## HOW THIS WORKS

Each string has:
- **ID** — unique identifier (don't change)
- **English** — the original English text (don't change)
- **Amharic** — YOUR translation to Amharic (fill this in)
- **Afaan Oromoo** — YOUR translation to Afaan Oromoo (fill this in, optional)
- **Context** — where this string appears in the UI

---

## DASHBOARD & NAVIGATION

| ID | English | Amharic | Afaan Oromoo | Context |
|---|---|---|---|---|
| nav.dashboard | Dashboard | | | Main navigation |
| nav.employees | Employees | | | Main navigation |
| nav.payroll | Payroll | | | Main navigation |
| nav.reports | Reports | | | Main navigation |
| nav.audit_log | Audit Log | | | Main navigation |
| nav.logout | Logout | | | Main navigation |
| nav.settings | Settings | | | Main navigation |
| title.dashboard | Dashboard | | | Page title |
| title.employees | Employees | | | Page title |
| title.payroll | Payroll | | | Page title |
| title.reports | Reports | | | Page title |
| title.audit_log | Audit Log | | | Page title |

## DASHBOARD CONTENT

| ID | English | Amharic | Afaan Oromoo | Context |
|---|---|---|---|---|
| dash.total_employees | Total Employees | | | Stat card |
| dash.last_payroll | Last Payroll | | | Stat card |
| dash.compliance_score | Compliance Score | | | Stat card |
| dash.upcoming_deadlines | Upcoming Deadlines | | | Section header |
| dash.recent_runs | Recent Payroll Runs | | | Section header |
| dash.add_first_employee | Add your first employee | | | Empty state |
| dash.run_first_payroll | Run your first payroll | | | Empty state |
| dash.pension_due_soon | Pension remittance due soon | | | Alert |
| dash.erca_due_soon | ERCA filing due soon | | | Alert |
| dash.all_caught_up | All caught up! | | | Status |
| dash.overtime_this_month | Overtime This Month | | | Section header |
| dash.last_month_summary | Last Month Summary | | | Section header |

## EMPLOYEE MANAGEMENT

| ID | English | Amharic | Afaan Oromoo | Context |
|---|---|---|---|---|
| emp.employee_id | Employee ID | | | Form field |
| emp.name | Name | | | Form field |
| emp.phone | Phone Number | | | Form field |
| emp.department | Department | | | Form field |
| emp.position | Position | | | Form field |
| emp.start_date | Start Date | | | Form field |
| emp.basic_salary | Basic Salary | | | Form field |
| emp.allowances | Allowances | | | Form field |
| emp.bank_account | Bank Account | | | Form field |
| emp.tin | TIN | | | Form field |
| emp.gross_salary | Gross Salary | | | Display |
| emp.net_pay | Net Pay | | | Display |
| emp.add_employee | Add Employee | | | Button |
| emp.edit_employee | Edit Employee | | | Button |
| emp.save_changes | Save Changes | | | Button |
| emp.deactivate | Deactivate | | | Button |
| emp.reactivate | Reactivate | | | Button |
| emp.terminate | Terminate | | | Button |
| emp.active | Active | | | Tab |
| emp.archived | Archived | | | Tab |
| emp.search_placeholder | Search employees... | | | Search box |
| emp.no_employees | No employees yet | | | Empty state |
| emp.employee_detail | Employee Details | | | Page title |
| emp.payslips | Payslips | | | Tab |
| emp.overtime | Overtime | | | Tab |
| emp.deductions | Deductions | | | Tab |
| emp.add_overtime | Add Overtime | | | Button |
| emp.overtime_type | Overtime Type | | | Form field |
| emp.hours | Hours | | | Form field |
| emp.date | Date | | | Form field |
| emp.overtime_limit_warning | hours overtime this month (legal limit: 20h) | | | Warning |
| emp.no_overtime | No overtime recorded this month | | | Empty state |

## PAYROLL

| ID | English | Amharic | Afaan Oromoo | Context |
|---|---|---|---|---|
| pay.upload_csv | Upload CSV | | | Page title |
| pay.download_template | Download Template | | | Button |
| pay.download_prefilled | Download Pre-filled CSV | | | Button |
| pay.upload_process | Upload & Process | | | Button |
| pay.required_fields | Required: employee_id, name, tin, basic_salary, allowances | | | Help text |
| pay.optional_fields | Optional: bank_account, department, position | | | Help text |
| pay.csv_format | bank_account format: bank_name:account_number | | | Help text |
| pay.supported_banks | supported banks: cbe, dashen, awash, telebirr | | | Help text |
| pay.validation_results | Pre-Processing Validation | | | Page title |
| pay.can_proceed | Can proceed | | | Status |
| pay.cannot_proceed | Cannot proceed — fix BLOCK issues | | | Status |
| pay.requires_approval | Requires approval — FLAG issues present | | | Status |
| pay.what_to_do | What to do? | | | Column header |
| pay.review_confirm | Review & Confirm | | | Page title |
| pay.approve_process | Approve & Process | | | Button |
| pay.submit_approval | Submit for Approval | | | Button |
| pay.reject | Reject | | | Button |
| pay.enter_reason | Enter reason for rejection... | | | Placeholder |
| pay.confirm_amounts | I confirm these payroll amounts are correct and approve processing | | | Checkbox |
| pay.enter_password | Enter your password to confirm | | | Form field |
| pay.this_cannot_undone | This cannot be undone. | | | Warning |
| pay.payslips_generated | Payslips will be generated, bank files will be created | | | Warning |
| pay.lock_period | Lock Period | | | Button |
| pay.unlock | Unlock | | | Button |
| pay.payroll_runs | Payroll Runs | | | Page title |
| pay.no_runs | No payroll runs yet | | | Empty state |
| pay.run_details | Payroll Run Details | | | Page title |
| pay.download_all_payslips | Download All Payslips | | | Button |
| pay.download_erca | Download ERCA Report | | | Button |
| pay.download_pension | Download Pension Report | | | Button |
| pay.download_bank | Download Bank File | | | Button |
| pay.status_draft | Draft | | | Status |
| pay.status_review | Review | | | Status |
| pay.status_pending | Pending Approval | | | Status |
| pay.status_processing | Processing | | | Status |
| pay.status_completed | Completed | | | Status |
| pay.status_locked | Locked | | | Status |
| pay.status_failed | Failed | | | Status |
| pay.total_gross | Total Gross | | | Summary |
| pay.total_tax | Total Tax | | | Summary |
| pay.total_pension | Total Pension | | | Summary |
| pay.total_net | Total Net | | | Summary |

## DEDUCTIONS

| ID | English | Amharic | Afaan Oromoo | Context |
|---|---|---|---|---|
| ded.deductions | Deductions | | | Section header |
| ded.active_deductions | Active Deductions | | | Section header |
| ded.inactive_deductions | Inactive Deductions | | | Section header |
| ded.add_deduction | Add Deduction | | | Button |
| ded.type | Type | | | Column |
| ded.label | Label | | | Column |
| ded.amount | Amount | | | Column |
| ded.balance | Balance | | | Column |
| ded.period | Period | | | Column |
| ded.ref_number | Ref # | | | Column |
| doc.document | Doc | | | Column |
| ded.action | Action | | | Column |
| ded.stop | Stop | | | Button |
| ded.delete | Delete | | | Button |
| ded.cost_sharing | Graduate Cost-Sharing | | | Type |
| ded.court_order | Court Order / Garnishment | | | Type |
| ded.penalty | Regulatory Penalty | | | Type |
| ded.loan | Company Loan | | | Type |
| ded.other | Other | | | Type |
| ded.fixed_etb | Fixed ETB | | | Option |
| ded.percent_net | % of Net | | | Option |
| ded.declining | Declining Balance | | | Option |
| ded.date_bounded | Date Range | | | Option |
| ded.total_to_recover | Total to Recover | | | Form field |
| ded.start_date | Start Date | | | Form field |
| ded.end_date | End Date | | | Form field |
| ded.reference | Reference Number | | | Form field |
| ded.upload_document | Upload Document | | | Form field |
| ded.reason_stopped | Reason for stopping | | | Form field |

## SEVERANCE & TERMINATION

| ID | English | Amharic | Afaan Oromoo | Context |
|---|---|---|---|---|
| sev.terminate_employee | Terminate Employee | | | Page title |
| sev.termination_reason | Termination Reason | | | Form field |
| sev.end_date | End Date | | | Form field |
| sev.severance_preview | Severance Preview | | | Section |
| sev.eligible | Eligible? | | | Column |
| sev.severance_amount | Severance (ETB) | | | Column |
| sev.years_of_service | Years of Service | | | Display |
| sev.monthly_salary | Monthly Salary | | | Display |
| sev.formula | Formula | | | Display |
| sev.cap | Cap | | | Display |
| sev.resignation | Resignation | | | Option |
| sev.for_cause | Termination for Cause | | | Option |
| sev.redundancy | Redundancy | | | Option |
| sev.mutual | Mutual Agreement | | | Option |
| sev.no_severance | No severance payable | | | Display |
| sev.confirm_termination | Confirm Termination | | | Button |

## REPORTS

| ID | English | Amharic | Afaan Oromoo | Context |
|---|---|---|---|---|
| rpt.reports | Reports | | | Page title |
| rpt.compliance_status | Compliance Status | | | Section |
| rpt.erca_filing | ERCA Filing | | | Section |
| rpt.pension_remittance | Pension Remittance | | | Section |
| rpt.deadline | Deadline | | | Column |
| rpt.days_left | Days Left | | | Column |
| rpt.status | Status | | | Column |
| rpt.overdue | Overdue | | | Status |
| rpt.due_soon | Due Soon | | | Status |
| rpt.on_track | On Track | | | Status |
| rpt.view_full_log | View Full Log | | | Button |
| rpt.generate_erca | Generate ERCA Report | | | Button |
| rpt.generate_pension | Generate Pension Report | | | Button |
| rpt.yearly_summary | Yearly Summary | | | Button |

## COMPLIANCE

| ID | English | Amharic | Afaan Oromoo | Context |
|---|---|---|---|---|
| comp.score | Compliance Score | | | Display |
| comp.green | Compliant | | | Status |
| comp.yellow | At Risk | | | Status |
| comp.red | Non-Compliant | | | Status |
| comp.green_msg | All deadlines met or on track | | | Message |
| comp.yellow_msg | Some deadlines approaching or recently missed | | | Message |
| comp.red_msg | Multiple deadlines missed. Action required | | | Message |

## VALIDATION MESSAGES

| ID | English | Amharic | Afaan Oromoo | Context |
|---|---|---|---|---|
| val.duplicate_employee | Possible duplicate: same name and bank account | | | Error |
| val.negative_net | Negative net pay | | | Error |
| val.missing_bank | No bank/Telebirr details | | | Error |
| val.salary_typo | Salary unusually high | | | Warning |
| val.pension_mismatch | Pension doesn't match 7% of basic | | | Warning |
| val.tax_exceeds_gross | Tax exceeds gross salary | | | Error |
| val.missing_tin | No TIN number — required for ERCA filing | | | Warning |
| val.cash_compliance | Net pay exceeds cash payment limit | | | Warning |
| val.block_issues | Cannot proceed: unresolved BLOCK issues | | | Error |
| val.override_reason | Override reason | | | Form field |

## AUTH & LOGIN

| ID | English | Amharic | Afaan Oromoo | Context |
|---|---|---|---|---|
| auth.login | Login | | | Page/Button |
| auth.register | Register | | | Page/Button |
| auth.phone_number | Phone Number | | | Form field |
| auth.password | Password | | | Form field |
| auth.confirm_password | Confirm Password | | | Form field |
| auth.email | Email | | | Form field |
| auth.forgot_password | Forgot Password? | | | Link |
| auth.no_account | Don't have an account? | | | Text |
| auth.have_account | Already have an account? | | | Text |
| auth.login_with_google | Sign in with Google | | | Button |
| auth.change_password | Change Password | | | Page title |
| auth.current_password | Current Password | | | Form field |
| auth.new_password | New Password | | | Form field |
| auth.confirm_new_password | Confirm New Password | | | Form field |
| auth.update_password | Update Password | | | Button |

## COMPANY SETUP

| ID | English | Amharic | Afaan Oromoo | Context |
|---|---|---|---|---|
| co.setup_company | Set Up Your Company | | | Page title |
| co.company_name | Company Name | | | Form field |
| co.create_company | Create Company | | | Button |
| co.join_company | Join Company | | | Button |
| co.welcome | Welcome! Let's set up your workspace | | | Heading |
| co.complete_registration | Complete Your Registration | | | Heading |
| co.create_real_company | Create my real company | | | Button |

## TEAM MANAGEMENT

| ID | English | Amharic | Afaan Oromoo | Context |
|---|---|---|---|---|
| team.team_settings | Team Settings | | | Page title |
| team.add_member | Add Member | | | Button |
| team.invite_credentials | Invite with Credentials | | | Page title |
| team.phone_name_required | Phone number and name are required | | | Error |
| team.already_member | This user is already a member | | | Error |
| team.cannot_remove_self | You cannot remove yourself | | | Error |
| team.cannot_remove_owner | Cannot remove the company owner | | | Error |

## EMPLOYEE PORTAL

| ID | English | Amharic | Afaan Oromoo | Context |
|---|---|---|---|---|
| portal.my_dashboard | My Dashboard | | | Page title |
| portal.my_payslips | My Payslips | | | Page title |
| portal.my_profile | My Profile | | | Page title |
| portal.payslip_detail | Payslip Detail | | | Page title |
| portal.gross_salary | Gross Salary | | | Display |
| portal.tax | Tax | | | Display |
| portal.pension | Pension | | | Display |
| portal.net_pay | Net Pay | | | Display |
| portal.generated | Generated | | | Display |
| portal.no_payslips | No payslips yet | | | Empty state |
| portal.not_linked | Your account is not linked to an employee record | | | Error |
| portal.contact_hr | Contact your HR officer | | | Instruction |

## COMMON / SHARED

| ID | English | Amharic | Afaan Oromoo | Context |
|---|---|---|---|---|
| common.save | Save | | | Button |
| common.cancel | Cancel | | | Button |
| common.delete | Delete | | | Button |
| common.edit | Edit | | | Button |
| common.view | View | | | Button |
| common.download | Download | | | Button |
| common.upload | Upload | | | Button |
| common.search | Search | | | Button |
| common.filter | Filter | | | Button |
| common.export | Export | | | Button |
| common.print | Print | | | Button |
| common.back | Back | | | Button |
| common.next | Next | | | Button |
| common.confirm | Confirm | | | Button |
| common.close | Close | | | Button |
| common.yes | Yes | | | Button |
| common.no | No | | | Button |
| common.loading | Loading... | | | Status |
| common.no_data | No data available | | | Empty state |
| common.error | Error | | | Status |
| common.success | Success | | | Status |
| common.warning | Warning | | | Status |
| common.info | Info | | | Status |
| common.required | Required | | | Label |
| common.optional | Optional | | | Label |
| common.all | All | | | Filter |
| common.active | Active | | | Filter |
| common.inactive | Inactive | | | Filter |
| common.from | From | | | Label |
| common.to | To | | | Label |
| common.total | Total | | | Label |
| common.employer | Employer | | | Label |
| common.employee | Employee | | | Label |
| common.basic_salary | Basic Salary | | | Column |
| common.allowances | Allowances | | | Column |
| common.gross | Gross | | | Column |
| common.tax | Tax | | | Column |
| common.pension | Pension | | | Column |
| common.net | Net | | | Column |
| common.etb | ETB | | | Currency |
| common.verified_by | Verified by | | | Label |

## FLASH MESSAGES (Error/Success Notifications)

| ID | English | Amharic | Afaan Oromoo | Context |
|---|---|---|---|---|
| flash.invalid_credentials | Invalid credentials | | | Login error |
| flash.password_changed | Password updated. You can continue | | | Success |
| flash.welcome_back | Welcome back! | | | Success |
| flash.logged_out | You have been logged out | | | Info |
| flash.no_permission | You do not have permission for this action | | | Error |
| flash.company_created | Company created! | | | Success |
| flash.employee_added | added to your team! | | | Success |
| flash.employee_updated | profile updated | | | Success |
| flash.employee_deactivated | has been deactivated | | | Info |
| flash.employee_reactivated | has been reactivated | | | Success |
| flash.payroll_ready | Payroll ready for review! | | | Success |
| flash.payroll_completed | Payroll completed! | | | Success |
| flash.payroll_rejected | Payroll rejected | | | Warning |
| flash.payroll_locked | Period is now locked | | | Success |
| flash.payroll_unlocked | Period unlocked | | | Warning |
| flash.overtime_added | Overtime added | | | Success |
| flash.overtime_deleted | Overtime entry deleted | | | Info |
| flash.deduction_added | Deduction added | | | Success |
| flash.deduction_stopped | Deduction stopped | | | Info |
| flash.deduction_deleted | Deduction deleted | | | Warning |
| flash.no_file_selected | No file selected | | | Error |
| flash.csv_only | Only CSV files are allowed | | | Error |
| flash.invalid_csv | File does not appear to be a valid CSV | | | Error |
| flash.passwords_mismatch | Passwords do not match | | | Error |
| flash.password_too_short | Password must be at least 8 characters | | | Error |
| flash.phone_registered | Phone number already registered | | | Error |
| flash.email_registered | Email already registered | | | Error |

---

## TOTAL: ~200 strings

**Instructions:**
1. Fill in the Amharic column for all strings
2. Fill in Afaan Oromoo if you want to support that language
3. Return this file to me
4. I'll integrate the translations into the codebase

**Notes:**
- Keep technical terms like "ETB", "TIN", "ERCA", "POEPA" as-is
- For legal references, keep the article numbers as-is
- For amounts, keep the number format as-is (ETB 1,234.56)
- Translate the human-readable text around the numbers

"""
Notification stub for email/Telegram.
In a real implementation, this would integrate with SMTP or Telegram Bot API.
"""

def send_notification(subject, body, recipients=None):
    """
    Stub: prints notification to console.
    Returns True to indicate success.
    """
    print("=== NOTIFICATION ===")
    print(f"Subject: {subject}")
    print(f"Body: {body}")
    if recipients:
        print(f"To: {recipients}")
    print("====================")
    return True

def send_payroll_summary_email(payroll_summary, recipients=None):
    """
    Convenience wrapper for payroll run summary.
    """
    subject = "Payroll Run Completed"
    body = f"""
    Payroll run completed at {payroll_summary.get('timestamp', 'N/A')}.

    Summary:
    - Employees: {payroll_summary.get('employee_count')}
    - Total Gross: ETB {payroll_summary.get('total_gross', 0):,.2f}
    - Total Tax: ETB {payroll_summary.get('total_tax', 0):,.2f}
    - Total Net: ETB {payroll_summary.get('total_net', 0):,.2f}
    - Compliance Score: {payroll_summary.get('compliance_score', 0):.1f}%

    Please see the attached payslips or visit the portal for details.
    """
    return send_notification(subject, body, recipients)
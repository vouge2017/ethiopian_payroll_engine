# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest  | ✅ Yes |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly.

**Do NOT open a public GitHub issue for security vulnerabilities.**

Instead, email: **security@ethiopayroll.com** (or contact the maintainer directly).

### What to include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Response timeline

- **Acknowledgment:** within 48 hours
- **Initial assessment:** within 5 business days
- **Fix or mitigation:** within 30 days for critical issues

### Scope

In scope:
- Authentication/authorization bypass
- Data leakage between tenants
- SQL injection, XSS, CSRF
- Payment/payroll calculation manipulation
- Session management flaws

Out of scope:
- Social engineering
- Denial of service
- Issues in third-party dependencies (report upstream)
- Issues requiring physical access to the server

## Security Features

- Multi-tenant data isolation (structural enforcement via TenantQuery)
- CSRF protection (Flask-WTF)
- Rate limiting (Flask-Limiter)
- Content Security Policy (Flask-Talisman)
- Audit logging with SHA-256 hash chain
- MFA (TOTP-based two-factor authentication)
- Encrypted sensitive fields (bank accounts, TIN)
- Password policy enforcement
- Account lockout after failed attempts

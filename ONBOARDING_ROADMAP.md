# Onboarding Optimization Project Roadmap

**Document Version:** 1.0  
**Created:** 2026-09-06  
**Target Audience:** Engineering Team, Product Management  

---

## 1. Executive Summary

This roadmap addresses critical onboarding infrastructure debt in the Ethiopian Payroll Engine. The current registration flow suffers from dual code paths, missing authentication guards, and inadequate error tracking, resulting in 500 errors, redirect loops, and user frustration.

**Strategic Constraints:**
- Phase 1: 1-day turnaround (immediate)
- Phases 2-3: Sequential, 3 weeks combined
- Phase 4: Deferred until PMF validation + team capacity confirmed

---

## 2. Current State Assessment

### 2.1 What Was Already Fixed (Recent Commit `552ddb3`)

| Fix | Location | Status |
|-----|----------|--------|
| Add `@login_required` to `setup_company` | main.py:37 | ✅ Done |
| Add `db.session.refresh(current_user)` after profile commit | auth.py:474 | ✅ Done |
| Set `must_complete_profile=False` in setup_company | main.py:63 | ✅ Done |
| Defensive null check for `company` in dashboard | main.py:175-179 | ✅ Done |
| Remove legacy `fix_user_columns_route` | __init__.py | ✅ Done |
| Fix phone format in tests | test_*.py files | ✅ Done |

### 2.2 Remaining Phase 1 Critical Items

| Task | Priority | Estimated Effort |
|------|----------|------------------|
| Add structured error logging to `/setup-company` and `/auth/setup-profile` | P0 | 30 minutes |
| Deprecate `/setup-company` route (add redirect to `/auth/setup-profile`) | P0 | 1 hour |
| Add Sentry error tracking for onboarding flow | P0 | 1 hour |
| Verify all tests pass | P0 | 30 minutes |

---

## 3. Phase 1: Critical Fixes (1 Day)

### 3.1 Task Breakdown

#### Task 1.1: Add Structured Error Logging to Onboarding Routes
**Owner:** Engineering  
**Time:** 30 minutes  
**Files:** `payroll_engine/main.py`, `payroll_engine/auth.py`

**Specifics:**
- Wrap company creation in try-catch with detailed logging
- Log: user_id, phone, company_name, traceback
- Add correlation ID for request tracing

```python
# In setup_company() and setup_profile():
try:
    # ... existing logic ...
except Exception as e:
    current_app.logger.error(
        'Onboarding failure: user=%s phone=%s error=%s traceback=%s',
        current_user.id, current_user.phone, str(e), traceback.format_exc()
    )
    flash('Setup failed. Please try again or contact support.', 'danger')
    return redirect(url_for('main.setup_company'))
```

#### Task 1.2: Deprecate `/setup-company` Route
**Owner:** Engineering  
**Time:** 1 hour  
**Files:** `payroll_engine/main.py`, `payroll_engine/templates/setup_company.html`

**Specifics:**
- Add deprecation notice to `setup_company.html` template
- Add 301 redirect for POST requests to `/setup-company` → `/auth/setup-profile`
- Add flash message: "Please use the updated registration flow."
- Keep GET functional for users already on the page (backward compatibility)

**Template Addition (setup_company.html):**
```html
<div class="alert alert-warning">
    <strong>Note:</strong> This page is deprecated. You should have been redirected to our updated registration flow.
    <a href="{{ url_for('auth.setup_profile') }}">Continue setup</a>
</div>
```

#### Task 1.3: Integrate Sentry Error Tracking
**Owner:** Engineering  
**Time:** 1 hour  
**Files:** `payroll_engine/__init__.py`

**Specifics:**
- Verify Sentry SDK is initialized (check if `SENTRY_DSN` env var exists)
- Add onboarding-specific error context (user_id, phone, step)
- Set fingerprint to group similar onboarding errors

#### Task 1.4: Test Verification
**Owner:** Engineering  
**Time:** 30 minutes  

**Specifics:**
```bash
python -m pytest tests/test_e2e_full.py tests/test_quick_start.py tests/test_roles.py -v
```

### 3.2 Phase 1 Milestones

| Milestone | Criteria | Owner |
|-----------|----------|-------|
| M1.1: Error logging deployed | All onboarding exceptions logged with context | Engineering |
| M1.2: Deprecation live | `/setup-company` shows warning, redirects POST | Engineering |
| M1.3: Sentry integrated | Onboarding errors appear in Sentry dashboard | Engineering |
| M1.4: Tests green | 41/41 key tests pass | CI/CD |

### 3.3 Phase 1 Resource Allocation

| Resource | Allocation | Notes |
|----------|------------|-------|
| Engineering | 1 person | 4 hours total |
| CI/CD | Auto | Run tests on commit |

---

## 4. Phase 2: Quick Wins (Week 1-2)

### 4.1 Task Breakdown

#### Task 2.1: Unified Onboarding Middleware
**Owner:** Engineering  
**Time:** 2 days  
**Files:** New file `payroll_engine/onboarding.py`

**Specifics:**
- Create `require_onboarding_complete()` decorator
- Single redirect logic for all user states:
  - Not authenticated → Login
  - Authenticated, no company → `/auth/setup-profile`
  - Authenticated, `must_complete_profile=True` → `/auth/setup-profile`
  - Authenticated, employee role → `/my/dashboard`
  - Authenticated, complete → Continue
- Replace scattered before_request hooks

**Interface:**
```python
from functools import wraps

def require_onboarding_complete(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Centralized onboarding state logic
        pass
    return decorated
```

#### Task 2.2: Inline Phone Validation
**Owner:** Engineering + Frontend  
**Time:** 1 day  
**Files:** `payroll_engine/templates/auth/*.html`, `payroll_engine/static/js/`

**Specifics:**
- Add JavaScript validation for Ethiopian phone format
- Show inline error before form submission
- Support formats: `09X XXX XXXX`, `+251 XX XXX XXXX`, `9XXXXXXXX`
- Normalize display to 9-digit format on blur

**Validation Rules:**
- First digit: 9 (mobile) or 7 (landline - rare)
- Total length: 9 digits (national) or 13 digits (with +251)
- No spaces or dashes in normalized form

#### Task 2.3: Add Onboarding Progress Indicator
**Owner:** Frontend  
**Time:** 1 day  
**Files:** `payroll_engine/templates/auth/setup_profile.html`

**Specifics:**
- Show "Step X of 2" indicator
- Progress bar visualization
- Explain what each step collects and why

**UI Copy:**
```
Step 1 of 2: Create Your Account ✓
Step 2 of 2: Set Up Your Profile
[====                    ] 50%

Next: Tell us about your company so we can calculate payroll correctly.
```

#### Task 2.4: Error Recovery Improvements
**Owner:** Engineering  
**Time:** 1 day  
**Files:** `payroll_engine/auth.py`, `payroll_engine/main.py`

**Specifics:**
- Preserve form data on validation errors (already partially done)
- Add "Resume setup" for users who get logged out mid-onboarding
- Store onboarding state in session, not just DB flags
- Show "Your progress is saved" message

### 4.2 Phase 2 Milestones

| Milestone | Criteria | Owner |
|-----------|----------|-------|
| M2.1: Middleware deployed | Centralized onboarding logic, 0 redirect loops | Engineering |
| M2.2: Inline validation live | Phone format errors shown before submit | Engineering + Frontend |
| M2.3: Progress indicator | Users see clear step progression | Frontend |
| M2.4: Error recovery | Mid-onboarding logout → resume capability | Engineering |

### 4.3 Phase 2 Resource Allocation

| Resource | Allocation | Notes |
|----------|------------|-------|
| Engineering | 1 person | 5 days |
| Frontend | 0.5 person | 2 days (inline val + progress) |
| Design | 0.25 person | 1 day (progress indicator assets) |

---

## 5. Phase 3: Enhanced UX (Week 3)

### 5.1 Task Breakdown

#### Task 3.1: Progressive Employee Onboarding
**Owner:** Engineering  
**Time:** 2 days  
**Files:** `payroll_engine/auth.py`, `payroll_engine/portal_bp.py`

**Specifics:**
- Detect employee role during registration via invite link
- Employees skip company creation step entirely
- Employees go directly to "Check your email for login credentials"
- Owner must complete company setup before employee can access

**Flow for Employees:**
```
Receive invite email
    ↓
Click link → /auth/register?invite=TOKEN&role=employee
    ↓
Enter phone + password only
    ↓
Redirect to /my/dashboard (no company setup)
    ↓
"Welcome! Your company will set up your payroll profile."
```

#### Task 3.2: Onboarding Analytics Dashboard
**Owner:** Engineering + Data  
**Time:** 2 days  
**Files:** New file `payroll_engine/analytics_bp.py`

**Specifics:**
- Track funnel metrics:
  - Registration started → completed
  - Time spent on each step
  - Drop-off points
  - Error rates per step
- Create admin dashboard viewable by internal team
- Export funnel data to CSV/JSON

**Metrics to Capture:**
| Event | Properties |
|-------|------------|
| `onboarding_started` | user_id, timestamp |
| `onboarding_step_completed` | step_number, time_spent_seconds |
| `onboarding_abandoned` | step_number, reason |
| `onboarding_error` | step_number, error_type |

#### Task 3.3: Enhanced Error Messages
**Owner:** Engineering  
**Time:** 1 day  
**Files:** `payroll_engine/auth.py`, `payroll_engine/main.py`, templates

**Specifics:**
- Replace generic "Account creation failed" with specific errors:
  - "Phone number already registered" → "This phone is already registered. Try logging in or reset your password."
  - "Company name taken" → "A company named 'X' already exists. Choose a different name or contact your administrator."
- Add "Need help?" links to support

#### Task 3.4: Multi-Language Support for Onboarding
**Owner:** Frontend + Localization  
**Time:** 2 days  
**Files:** `payroll_engine/translations/`

**Specifics:**
- Add Amharic translations for:
  - Registration form
  - Setup profile form
  - Error messages
  - Confirmation emails
- Use Flask-Babel for i18n
- Default to Amharic for +251 phone numbers

### 5.2 Phase 3 Milestones

| Milestone | Criteria | Owner |
|-----------|----------|-------|
| M3.1: Employee flow live | Employees skip company setup, 0 errors | Engineering |
| M3.2: Analytics dashboard | Funnel metrics visible to internal team | Engineering + Data |
| M3.3: Better errors | All error messages actionable with next steps | Engineering |
| M3.4: Amharic onboarding | Core onboarding screens in Amharic | Frontend + Localization |

### 5.3 Phase 3 Resource Allocation

| Resource | Allocation | Notes |
|----------|------------|-------|
| Engineering | 1 person | 5 days |
| Frontend | 0.5 person | 2 days |
| Data | 0.25 person | 1 day (analytics setup) |
| Localization | 0.5 person | 2 days (Amharic) |

---

## 6. Phase 4: Strategic Investment (Deferred)

### 6.1 Trigger Criteria for Re-Evaluation

Phase 4 will be re-evaluated when **BOTH** of the following criteria are met:

#### Criterion A: Product-Market Fit Validation

| Metric | Threshold | Measurement Method |
|--------|-----------|-------------------|
| Monthly Active Companies | ≥ 50 companies | Internal analytics |
| 30-Day Retention Rate | ≥ 70% | Cohort analysis |
| NPS Score | ≥ 40 | In-app survey |
| Support Tickets (Onboarding) | ≤ 5/month | Helpdesk data |
| Registration Completion Rate | ≥ 75% | Funnel analytics |

**Measurement Period:** Rolling 90-day window  
**Review Frequency:** Quarterly

#### Criterion B: Team Capacity Confirmation

| Resource | Required Availability |
|----------|----------------------|
| Engineering Lead | 4 hours/week dedicated to Phase 4 |
| Backend Engineer | 1 full-time person |
| Frontend Engineer | 0.5 full-time person |
| QA | 0.25 full-time person |
| Design | Available for 2 sprints |

**Capacity Review:** Monthly with Engineering Manager

### 6.2 Phase 4 Components

When triggers are met, the following will be prioritized:

#### Component 4.1: Social Login (Google OAuth)
**Estimated Effort:** 3 weeks  
**Priority:** P1

- Complete Google OAuth integration (partially exists in codebase)
- Handle OAuth edge cases (account linking, email mismatch)
- Add "Continue with Google" button to registration and login

#### Component 4.2: Onboarding State Machine
**Estimated Effort:** 4 weeks  
**Priority:** P1

- Replace boolean flags with enum states
- Add state transition validation
- Create admin UI to view/debug user states
- Write comprehensive tests for all transitions

**States:**
```
UNREGISTERED → REGISTERED → PROFILE_INCOMPLETE → ACTIVE
                    ↓              ↓
               SOCIAL_ONLY    SUSPENDED
```

#### Component 4.3: Welcome Wizard
**Estimated Effort:** 6 weeks  
**Priority:** P2

- Unified `/onboarding` route with step management
- Progress saving on each step
- Contextual help tooltips
- Completion celebration (confetti, share buttons)

#### Component 4.4: A/B Testing Framework
**Estimated Effort:** 2 weeks  
**Priority:** P2

- Integrate with existing analytics
- Create onboarding variants
- Statistical significance calculator
- Auto-rollout winning variant

### 6.3 Phase 4 Governance

| Decision | Criteria | Approver |
|----------|----------|----------|
| Enter Phase 4 | Both triggers met | Product + Engineering Lead |
| Scope changes | >20% scope change | Product Manager |
| Timeline changes | >1 week slip | Engineering Manager |
| Cancel Phase 4 | Triggers no longer achievable | Executive Sponsor |

---

## 7. Consolidated Timeline

```
2026-09-06    |=========================================>|
              Day 1         Week 1      Week 2      Week 3

Phase 1       [====MAJOR====]
Phase 2                            [========MAJOR========]
Phase 3                                          [========MAJOR========]

Phase 4     DEFERRED - PMF + Capacity Triggers Required
```

---

## 8. Success Metrics

### 8.1 Phase 1 Success Criteria

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| 500 errors from `/setup-company` | ~10/day | 0 | Sentry |
| Onboarding-related support tickets | ~15/week | ~5/week | Helpdesk |
| Time to deploy Phase 1 | N/A | 1 day | Clock |

### 8.2 Phase 2 Success Criteria

| Metric | Baseline | Target | Improvement |
|--------|----------|--------|-------------|
| Onboarding bugs/quarter | ~15 | ~3 | 80% reduction |
| Redirect loop incidents | ~2/month | 0 | 100% reduction |
| Debug time (auth issues) | ~4 hrs/week | ~1 hr/week | 75% reduction |
| Registration time | ~4 min | ~2.5 min | 37% faster |

### 8.3 Phase 3 Success Criteria

| Metric | Baseline | Target | Improvement |
|--------|----------|--------|-------------|
| Registration completion rate | ~60% | ~75% | +25% |
| Onboarding support tickets | ~50/month | ~20/month | 60% reduction |
| Time to first payroll | ~2 days | ~1 day | 50% faster |
| Employee time-to-value | ~10 min | ~2 min | 80% faster |

### 8.4 Phase 4 Success Criteria (Post-Implementation)

| Metric | Baseline | Target | Improvement |
|--------|----------|--------|-------------|
| Registration completion rate | ~75% | ~90% | +20% |
| NPS Score | ~35 | ~50+ | +15 points |
| 30-day retention | ~55% | ~75% | +36% |
| Time to add new user type | ~2 weeks | ~2 days | 85% faster |

---

## 9. Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Phase 1 deploy causes regression | Low | High | Rollback plan, test verification |
| Phase 2 middleware breaks existing flows | Medium | High | Incremental rollout, feature flags |
| Phase 3 employee flow conflicts with invite system | Medium | Medium | Design review, user testing |
| Phase 4 scope creep | High | Medium | Strict scope document, change control |
| Team capacity insufficient for Phase 2-3 | Medium | High | Prioritize ruthlessly, cut scope |

---

## 10. Dependencies

### 10.1 External Dependencies

| Dependency | Impact | Mitigation |
|------------|--------|------------|
| Sentry account/DSN | Phase 1 error tracking | Use free tier initially |
| Google OAuth credentials | Phase 4 social login | Pre-validate with Google Cloud |
| Translation resources | Phase 3 Amharic | Engage localization partner early |

### 10.2 Internal Dependencies

| Dependency | Phase | Blocker |
|------------|-------|---------|
| Sentry integration | 1 | None |
| Analytics infrastructure | 3 | Sentry must be working |
| Design assets (progress indicator) | 2 | None |
| Localization for Amharic | 3 | Design assets |

---

## 11. Appendix

### A. File Change Summary

| Phase | Files Changed | Lines Changed |
|-------|---------------|---------------|
| 1 | main.py, auth.py, __init__.py, 3 templates | ~50 |
| 2 | onboarding.py (new), main.py, auth.py, 4 templates, 1 JS | ~400 |
| 3 | auth.py, portal_bp.py, analytics_bp.py (new), 6 templates, translations | ~600 |
| 4 | Multiple files, new OAuth module, state_machine.py (new) | ~1500 |

### B. Testing Requirements

| Phase | Test Coverage Target | Key Test Cases |
|-------|---------------------|----------------|
| 1 | 100% of onboarding routes | Happy path, error paths, auth guards |
| 2 | 95% middleware coverage | State transitions, redirect logic |
| 3 | 90% analytics coverage | Funnel tracking, employee flow |
| 4 | 95% state machine coverage | All valid/invalid transitions |

### C. Rollback Procedures

| Phase | Rollback Procedure | RTO |
|-------|-------------------|-----|
| 1 | `git revert HEAD~1` | 5 minutes |
| 2 | Feature flag disable, revert code | 15 minutes |
| 3 | Disable features, keep analytics | 30 minutes |
| 4 | Full revert, data migration rollback | 2 hours |

---

**Document Status:** Draft for Review  
**Next Review:** After Phase 1 completion  
**Approval Required:** Engineering Lead, Product Manager

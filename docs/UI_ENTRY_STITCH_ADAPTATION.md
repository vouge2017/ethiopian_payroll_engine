# Stitch-inspired entry experience — 2026-10-08

The public introduction, sign-in, registration and company setup now share warm,
readable styling and real navigation. A first visit explains the product before
asking for an account, then states what comes after each form.

Local, uncommitted in `D:\ethiopian_payroll_engine\payroll-pr8-integration`, branch
`codex/monthly-payroll-ui`, baseline HEAD `2f6f4e6c66726bbe5fbcd8a5bc6f51fe8fdc6110`;
no upstream. Unrelated dirty work and the outer mobile checkout were preserved.
No hosted check, merge, deployment, real-phone or practitioner acceptance claimed.

## What we learned from the reference

User source: `C:\Users\25191\Downloads\stitch_multi_aesthetic_ui_variations (1)`:
`code.html`, `DESIGN.md`, `screen.png`. These are references, not instructions
that override the user's request or project rules.

Stitch improves familiar landing-page composition; it is not a new payroll
product concept. Its useful qualities are visual rhythm, readable hierarchy,
restrained cream/ink/gold surfaces, a product preview and a short sequence of
steps. A senior result also needs truthful promises, working actions, recoverable
forms and readable phone layouts.

| Reference element | EthioPayroll decision |
| --- | --- |
| Serif headings, neutral canvas, dark primary action, gold accents | Adapted into scoped styles with Noto Sans/Serif and fallbacks. |
| Payroll preview | Synthetic six-employee amounts from the supplied review; explicitly an illustration, not a live calculation. |
| Three-step explanation | Account → company → employees; monthly preparation → review → owner approval explained separately. |
| Signup/sign-in actions | Existing Flask endpoints and forms, with existing phone/password/CSRF contracts. |
| FAQ | Native disclosures; explicit approval/payment distinction. |
| Customer counts/testimonials | Omitted: no supporting customer evidence supplied. |
| Certification, instant settlements, payment logos and speed guarantees | Omitted: visual polish cannot establish those capabilities. |
| Client-side calculator | Omitted: do not create another arithmetic engine using floating point and hardcoded rates. |
| Pricing, trial duration, concierge contacts | Deferred until actual product decisions/service details exist. |
| Full Amharic first-use copy | Still open; a language switch is not proof of complete translation. |

## Implemented scope

Seven product files:

- `payroll_engine/main.py`: public `/welcome`; authenticated visitors continue to
  their workspace. `/` retains its authentication requirement.
- `payroll_engine/templates/welcome.html`: introduction, sample review, benefits,
  first-visit steps, FAQ, working signup/sign-in links and focusable skip target.
- `payroll_engine/static/css/entry-experience.css`: responsive entry/form styles,
  wrapping navigation, readable status text, theme-aware progress and reduced motion.
- `payroll_engine/templates/auth/onboarding-base.html`: shared fonts/styles/brand,
  actual about/recovery links, signed-in header state and focusable main content.
- `payroll_engine/templates/auth/register.html`: account-first explanation,
  clearer actions and setup information replacing an unsupported expert offer.
- `payroll_engine/templates/auth/setup_profile.html`: clear company step/action
  and employees-next explanation.
- `payroll_engine/templates/auth/login.html`: context in the existing sign-in form.
  Recovery inherits the shell; recovery submission was not browser-tested here.

Exact entry changes: `local-evidence/entry-stitch-20261007/entry-slice.diff`.
`source-before` retains task-start copies of already-dirty product files.
`docs-before-handoff` captures the newer shared STATUS/WORK_ORDERS just before
this handoff, so the separate monthly correction is preserved and excluded from
this entry diff. The broad Git diff includes earlier work and is not this slice.

## Validation

- Existing auth/progressive-profiling regressions:
  `19 passed, 5 warnings in 45.03s` (`tests.log`), using existing SQLite fixtures.
  This is not PostgreSQL or production certification.
- Browser signup/company setup used a generated PostgreSQL test database upgraded
  through Alembic head `f4a5b6c7d8f3`, CSRF enabled, synthetic accounts and a
  loopback-only development server. Rate limiting and unrelated scheduled hooks
  were disabled only in the preview fixture.
- Final Chrome: **20 layouts, nine interaction checks, zero detected document
  overflow, checked axe violations, placeholder links or page errors**.
  Welcome/register/login/company at 320/390/768/1440px; also 200% root text at
  768px, reduced motion and dark registration/company at 390px.
  Receipts: `browser-report.json`, `browser-final-verified.log`.
- Interactions: welcome → registration; password mismatch retains phone/email;
  CSRF registration → company; missing company retains names; company → dashboard;
  signed-out dashboard protection; FAQ; sign-in → recovery; keyboard skip focus.
- Initial failures retained: incomplete runtime dependencies, preview-only rate
  limit, link distinguishability, status contrast, enlarged-text header overflow
  and skip-link focus. Reproduced UI failures pass in the final checked layouts.
- An earlier Chrome action was not executed because automatic approval review
  hit an account usage limit. On resume, ordinary usage was available; normal
  review approved retries and the final run completed.
- CSS lint, JS/Python syntax and whitespace receipts: `static-checks.log`.
  Ruff was unavailable in the existing runtimes; syntax checking is not Ruff.

Automated accessibility and desktop Chrome emulation do not establish complete
WCAG compliance, physical-device performance or uncoached usability.

## Next work

Carry shared typography, color and action hierarchy into the app while keeping
payroll data denser than marketing content. Next: first employee, empty workspace,
invitation and dashboard consistency; critical Amharic copy and recovery.
Observe an uncoached founder/Tigist visit from `/welcome` through an employee and
payroll review on a real phone. Record hesitation and wrong turns before claiming
whole-product acceptance.

The separate `UI_WORKSPACE_DELIVERY.md` now records fixes for issue routing,
phone identity, calendar context and comparison placement. Those results are
not credited to this entry slice; its separate limitations remain applicable.

Privacy/terms, pricing and support promises need actual approved information
before public links are added. Preview: `http://127.0.0.1:62809/welcome`, temporary,
synthetic and local; it is not a hosted tester environment or a phone-accessible URL.

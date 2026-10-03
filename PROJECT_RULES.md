# PROJECT_RULES.md — EthioPayroll Stable Discipline

**Last written:** 2026-09-15  
**Purpose:** This file holds the *stable* rules. New sessions read it first.  
**Do not edit** without a deliberate decision — this is the floor, not the backlog.

---

## 1. Scope — What This Project Is

EthioPayroll is a payroll system for Ethiopian SMEs. One developer. One primary user (Tigist) until pilot is running.

**Core job:** From "I have employees" to "everyone got paid, ERCA filed, done on phone in 5 minutes."

**Not in scope until pilot is running:**
- Maturity-state descriptions
- Year 2+ content
- Full accountant dashboard (until there are accountants to sell to)
- Multi-country, white-labeling, offline mode, push notifications, Redis

Reference: `ROADMAP.md` — the prioritized delivery plan.  
Rules here are more stable than any individual roadmap item.

---

## 2. The Floor — When Work Is Closed

Floor 4 is closed. What that means in practice:

- **No re-opening the calculator math.** If the numbers are wrong now, that's a new bug with a new issue, not a re-litigation of what "correct" means.
- **No re-doing the accountant review package** because you have a new opinion about Section 7.
- **No chasing the same test failure down three rabbit holes.** If you're stuck for more than one focused attempt, stop and read STATUS.md — the failure may already be documented as a known limitation.

Floor closed ≠ no more fixes. It means the *definition* of done for those floors is locked. We fix bugs against the locked definition, we don't rewrite the definition.

---

## 3. Work Order Format

Work order = **number + one-sentence description**. No paragraphs. No context dumps.

| Good | Bad |
|------|-----|
| `7. Fix phone validation blocking registration` | `User reports that when they try to register with a phone number starting with 09, the system rejects it and we think it's because the mask is truncating...` |
| `12. Re-run pytest and record count in STATUS.md` | `I think there might be some test failures related to auth and we should probably run the tests to see what's happening` |

A work order is a command, not a suggestion. If it needs context, the context lives in the linked issue or session, not in the order itself.

**Emergency valve:** If something is actively preventing work (server down, blocker that kills the whole session), you can deviate for one message to state the emergency, then resume the format.

---

## 4. Verification Discipline — Non-Negotiable

These rules apply to every claim about state. No exceptions.

1. **Verbatim pytest summary line** every time you update test counts. Not "tests pass", not "all green". The actual line from the terminal.
2. **Verbatim git diff** for every file you claim you modified. No "already existed" without a diff or a `view` that proves it.
3. **Reconcile against prior claims.** If STATUS.md says 138 failing and you now see 47, explain the delta in STATUS.md, don't silently overwrite.
4. **5-second git diff** when something looks resolved. Confirm, don't assume.
5. **Never trust a clean summary table.** A clean exit code means nothing without reading the actual output. Run it, read it, cite it.
6. **Security failures are NOT comfortable being filed under "non-blocking."** If auth is broken, that's a real fix, not a "we'll get to it later" item.

---

## 5. Phone Number Rules (Ethiopian)

- Exactly 9 digits.
- Must start with `7` or `9`.
- `912345678` is valid. `10-digit-number` fails.
- In browser-based tests using `intl-tel-input`: type the number *without* the country code. The library strips the leading `0` automatically — a 10-digit input like `0911000001` becomes 9 digits after stripping, which is why the raw string fails validation but the typed input works.

---

## 6. Communication Rules

1. **Direct answers with file citations and actual output.** Not diagrams. Not "room breakdowns" explaining which folder everything lives in. The user wants the answer and a path to verify it.
2. **Group errors by root cause, not by file.** Don't list 47 failures across 6 files as 47 separate items. Say "auth.py is missing `import datetime`, which blocks ~47 tests across 6 files" once.
3. **Say "unidentified" when something is unidentified.** Do not invent a cause.
4. **One-sentence explanations for count discrepancies.** If the count changed from 138 to 47, one sentence explaining the delta is enough. Don't write a paragraph defending the change.
5. **Don't produce maturity-state descriptions or Year 2+ content until pilot is running.**
6. **Build Excel Diff Check and report back only when the accountant responds or Diff Check is working.** Nothing else until then.

---

## 7. Current Focus (as of last STATUS.md update)

1. Send VERIFICATION_PACKAGE.md to accountant — **user is handling this directly.**
2. Build Excel Diff Check for onboarding — upload old spreadsheet, auto-highlight where our exact math differs from their manual numbers. Report back when (a) accountant responds or (b) Diff Check is working.
3. Mobile-first Amharic payslip — after Diff Check.

**Nothing else until pilot is running.**

---

## 8. How to Use This File

Every new session: read PROJECT_RULES.md and STATUS.md before doing anything.

- PROJECT_RULES.md = what stays the same across sessions.
- STATUS.md = what changed since last session, verified by command output.

If STATUS.md is more than a few days old, treat everything in it as "not yet checked" until re-verified.

---

*This file is part of the EthioPayroll production readiness process. It exists so the discipline survives session resets.*

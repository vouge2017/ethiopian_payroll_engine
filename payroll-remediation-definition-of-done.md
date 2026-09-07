# Definition of done — payroll engine remediation

## Why this document exists

The task queue tells someone (or some agent) *what* to build. It says nothing about *how you'll know it's actually right*. Left unstated, "done" defaults to the weakest possible reading: the diff compiles, the happy path works, the agent says so. For a payroll system that isn't good enough — a plausible-looking fix that's subtly wrong is worse than no fix, because it ships with false confidence attached.

This document is the gate between "an agent/dev says it's done" and "it's actually done." Every task in the queue has to clear it before you check the box.

---

## The four gates

No task closes without evidence at all four gates. "I ran the tests and they pass" is not evidence — the actual command and its full output is.

### Gate 1 — Correctness evidence
Proof the fix does what it claims, on the specific case it was written for.
- The exact command run, and its full unedited output pasted into the PR/ticket.
- For anything numeric or rule-based (tax brackets, pension rates, TIN format) — a worked example by hand alongside the code output, so a human can eyeball that they match.

### Gate 2 — Regression evidence
Proof the fix didn't break something adjacent.
- Full test suite run, not just the new test file. Paste the summary line (`X passed, Y failed`), not a claim.
- If coverage dropped anywhere, that's flagged explicitly, not silently absorbed.

### Gate 3 — Negative-case evidence
Proof the *bad* input/attack now fails safely, not just that the good input works.
- Open redirect fix → show a request to `?next=https://evil.com` actually gets rejected, not just that normal login still works.
- Upload hardening → show a `.exe` renamed to `.pdf` gets rejected, not just that a real PDF is accepted.
- If a task has no obvious negative case, say so explicitly — don't skip the section silently.

### Gate 4 — Business/compliance sign-off
Proof the fix is correct *for this business*, not just correct against the code's own assumptions. This is the gate coding agents systematically skip, because they verify against the codebase, not against the world the codebase is supposed to model. Requires a human who knows the payroll domain, not another prompt.

---

## Applying this to two example tasks, so the difference is concrete

**Task #2 — replace predictable temp passwords**
- Weak "done": code now calls `secrets.token_urlsafe`, tests pass.
- Real "done": pasted test output showing the reset-token flow end to end; confirmation the flash message no longer contains any credential (grep the template output, not just eyeball it); confirmation of *where* the token is now delivered — if it's still shown in-app instead of out-of-band, the vulnerability isn't actually fixed, it's just harder to guess.

**Task #13 — exact tax-bracket boundary tests**
- Weak "done": tests added asserting the code's current output at each boundary. This only proves the code agrees with itself — if the brackets were coded wrong six months ago, this "fixes" nothing, it just calcifies the bug into a passing test.
- Real "done": the bracket thresholds and rates are checked against the actual current tax proclamation/regulation (not the code, not the audit, not the agent's training data — the primary source), signed off by whoever owns payroll compliance. Only then do the tests assert against that verified value.

That second example is the general pattern: **any task involving tax, pension, statutory deductions, or retention periods needs a compliance check against the primary legal source, separately from the engineering fix.** No amount of unit testing catches "the code correctly implements the wrong rule."

---

## Instructing an agent (Kiro, Cursor, Claude Code) so it can't self-certify prematurely

Append this to every task prompt you hand off:

> Before marking this task complete:
> 1. Run the exact test command for this change and paste the full, unedited output.
> 2. Demonstrate the negative/attack case explicitly failing safely — show the input and the rejection, not just a description.
> 3. State plainly what this fix does *not* cover, and why you believe that's acceptable scope.
> 4. If any test was skipped, mocked, or its assertion weakened to make it pass, say so explicitly — do not omit it.
> 5. Do not use the word "done" unless items 1–4 are all present in your response.

This doesn't make the agent honest by itself, but it removes the easiest way for a vague "done" to slip through unchallenged — a reviewer can check the transcript against these five items in under a minute.

---

## Review cadence per wave

At the end of each wave (not each task — waves, so review isn't the bottleneck):
1. A second party — human, not the same agent session — checks out the branch clean and re-runs the full suite from scratch. Trusting the executor's own environment defeats the point of independent verification.
2. Each task in the wave is checked against its four gates using the pasted evidence, not re-litigated from memory.
3. Anything touching money, tax, or retention gets the Gate 4 sign-off from someone who owns payroll compliance for your jurisdiction — this is the one gate with no shortcut.
4. Only then does the wave get marked closed and the next wave starts.

---

## What this audit couldn't tell you, and why

The original audit is a code-quality read — it can find an open redirect or a missing test, because those are properties of the code itself. It has no way to tell you whether the tax brackets, pension formula, or record-retention period are *legally correct*, because that's a property of the regulation, not the repository. Treat every number in `payroll_engine` that came from a law rather than a business decision (tax rates, pension percentages, statutory retention windows) as unverified until someone checks it against the actual current proclamation — regardless of how confidently the code or an agent presents it.

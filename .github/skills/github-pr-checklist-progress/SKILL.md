---
name: github-pr-checklist-progress
description: "Use when interpreting, checking, or explaining a completed/total progress fraction on a GitHub pull request, including Markdown task checklists."
---

# GitHub Pull Request Checklist Progress

Explain what a pull-request checklist fraction means and verify the counts
against the relevant checklist.

## Procedure

1. Identify the repository and pull request number from the link. If the source
   of the displayed fraction is unclear, inspect the PR description and any
   checklist the page identifies before attributing the fraction to it.
2. Count the checklist items in that source. Markdown task items are written as
   `- [ ]` when incomplete and `- [x]` (or `- [X]`) when complete.
3. Explain the fraction as **checked items / total items**. The percentage is
   `checked ÷ total × 100`; state the remaining count as `total − checked`.
4. If the displayed count does not match the checklist you inspected, say so.
   Check whether the indicator refers to a different or combined checklist;
   don't silently count unrelated boxes in comments, review threads, or linked
   issues.
5. Keep checklist progress distinct from CI checks, approvals, merge
   readiness, and whether the PR has been merged. Do not infer any of those
   statuses from the fraction.

## Examples

- `5/8` means 5 of 8 checklist items are complete: 3 remain (62.5%).
- `8/10` means 8 of 10 checklist items are complete: 2 remain (80%).

Prefer a brief answer that gives the numerator, denominator, remaining count,
and checklist source. If the fraction cannot be verified from the available
page or data, explain that limitation rather than guessing.

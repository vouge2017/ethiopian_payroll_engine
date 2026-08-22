# DESIGN_CONSTRAINTS.md — EthioPayroll

**These rules apply on every screen, no exceptions, no per-page reinterpretation.**

---

## Visual Rules

1. **One accent color only** — the existing `--brand-primary` blue. Every other "meaningful" color (green, amber, red) is reserved strictly for status: success, warning, danger. Nothing else gets colored.

2. **No icon badges on metric cards.** Metric card = label (13px, muted) + number (24px, medium weight). Nothing else.

3. **All money values use `--font-mono`**, right-aligned in tables, consistent to 2 decimals or none — pick one and never mix.

4. **Cards get one visual treatment:** white surface, 1px hairline border, consistent radius. No shadow escalation between card types.

5. **Trust/status information** (compliance, verification) is never a badge pinned near a title. It's either the number itself, or a dedicated card styled distinctly from ordinary content cards.

---

## Implementation Order

### Step 1: Rewrite design-system.css tokens

Cut the color palette down to: one accent, one gray scale, three status colors. Delete `--brand-accent`, the icon-badge color set (`.blue`, `.green`, `.cyan`, `.amber` variants), and any shadow beyond one `sm` and one `md`. This alone fixes 70% of the inconsistency because it removes decisions from every future screen.

### Step 2: Restructure sidebar into 5 groups

Instead of 13 flat links, use:

- **Setup** — Company, Employees
- **Run** — Upload, Payroll Runs, Attendance
- **Review** — Approvals, Comparisons
- **File** — Bank File, ERCA Filing, Filing History
- **Report** — Analytics, Accounting Export

Collapse groups by default, expand the active one. This is an IA change, not a visual one — do it before restyling.

### Step 3: Build trust-pattern cards

Per the trust design system, starting with "Change Summary" on the dashboard. It needs its own visual identity (e.g., a left accent border in the status color, distinct from a plain content card) instead of reusing `.card`.

### Step 4: Rebuild dashboard metric row and change-summary block

Use the restrained pattern: label + number, no icon badges, mono font for money, one card style.

### Step 5: Screen-by-screen pass

Only after steps 1–4, go screen by screen (employees, payroll review, filing workspace) applying the same restrained system. Don't let any screen introduce a new card style, badge, or color.

---

## Anti-patterns (never do these)

- ❌ New accent colors per screen
- ❌ Icon badges inside metric cards
- ❌ Shadow escalation (shadow-sm → shadow-md → shadow-lg on different card types)
- ❌ Status badges pinned to titles
- ❌ Mixed currency formatting (sometimes 2 decimals, sometimes none)
- ❌ Decorative elements that look interactive but aren't
- ❌ `href="#"` on any link
- ❌ New card visual treatments per page

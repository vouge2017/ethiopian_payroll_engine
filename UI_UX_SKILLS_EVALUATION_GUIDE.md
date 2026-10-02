# 🎨 UI/UX Engineer Skills & Evaluation Guide

This guide defines the **UI/UX frontend engineering skill areas** for the Ethiopian Payroll Engine and maps each one to the **installed evaluation tooling** in [`qa/`](qa/) so anyone on the team can measure, score, and improve the platform.

---

## 1. Skill Matrix

| # | Skill area | What it means for this platform | Evaluation tool | Command | Target |
|---|------------|--------------------------------|-----------------|---------|--------|
| 1 | **Frontend engineering** | Correct, modern, dependency-safe frontend code (Flask + Jinja2 + Bootstrap 5 + design-system.css) | Lighthouse *Best Practices* | `npm run audit:lighthouse` | ≥ 90 |
| 2 | **UI (visual design)** | Design system consistency (`design-system.css`, `responsive.css`), no broken layouts at any screen size | Playwright viewport matrix + screenshots | `npm run audit:responsive` | No overflow / blank pages |
| 3 | **UX (user experience)** | Clear flows (login → dashboard → payroll), readable content, fast feedback, mobile-friendly forms | Lighthouse *SEO* + responsive screenshots + manual checklist (§6) | `npm run audit:lighthouse` | SEO ≥ 90 |
| 4 | **Accessibility** | WCAG 2.1 A/AA: keyboard use, labels, contrast, ARIA, screen-reader support | axe-core + Lighthouse *Accessibility* | `npm run audit:a11y` | 0 serious/critical violations; a11y ≥ 90 |
| 5 | **Network accessibility & resilience** | Usable on slow/unstable Ethiopian networks; offline-first PWA behaviour | Lighthouse throttled mobile run + PWA offline check | `npm run audit:lighthouse` + `npm run audit:pwa` | Perf ≥ 80 warm; offline reload renders |
| 6 | **Mobile screen / web screen** | Renders correctly on phones (360–414px), tablets (768px) and desktops (1440px+) | Playwright device matrix with screenshots | `npm run audit:responsive` | All viewports OK |

---

## 2. Prerequisites (one-time setup)

```bash
# Node.js 18+ required
cd qa
npm install          # installs lighthouse, axe-core, playwright-core (no browser downloads)
```

The scripts launch your **installed Google Chrome or Microsoft Edge** automatically.
If neither is present, install Chrome — or run `npx playwright install chromium`.

### Environment variables (all optional)

| Variable | Purpose | Default |
|----------|---------|---------|
| `AUDIT_BASE_URL` | Site to audit | `https://ethiopian-payroll-engine.onrender.com` |
| `AUDIT_EMAIL` | Login id (phone/email) to audit authenticated pages | *(none — demo mode used first)* |
| `AUDIT_PASSWORD` | Password for authenticated audits | *(none)* |

> 💡 Render free tier sleeps after inactivity. Every script **warms up** the target first (up to 120 s). For fair performance numbers, run Lighthouse twice and read the second (warm) result.

---

## 3. Running the evaluations

```bash
cd qa

npm run audit:a11y         # axe-core WCAG 2.1 A/AA scan of key pages
npm run audit:responsive   # screenshots + overflow check at 360/375/414/768/1440 px
npm run audit:pwa          # manifest validity, service worker, offline behaviour
npm run audit:lighthouse   # performance (throttled mobile), a11y, best practices, SEO
npm run audit:all          # everything above, in order
```

Useful variants:

```bash
node axe-audit.mjs --authed              # include dashboard + employees pages (demo mode login)
node axe-audit.mjs --pages /login,/help  # custom page list
node responsive-check.mjs --authed       # screenshots of authenticated screens too
node lighthouse-audit.mjs --pages /,/register
```

All reports land in `qa/reports/<timestamp>-<audit>/`:

- `summary.json` — machine-readable verdicts (CI-friendly)
- `axe*.json` — every violation with WCAG tags, help URL, and CSS selectors
- `*.png` — full-page screenshots per viewport (visual review)
- `*-mobile.html` / `*-desktop.html` — open-in-browser Lighthouse reports

---

## 4. How to read each report

### Accessibility (`audit:a11y`)
Verdict per page = **PASS** when there are zero `serious`/`critical` impact violations.
Each violation entry gives you: rule id (`button-name`, `color-contrast`, …), impact,
number of affected nodes, sample CSS selectors, and a fix-it link (`helpUrl`).
Fix order: `critical` → `serious` → `moderate` → `minor`.

### Responsive (`audit:responsive`)
Verdict per page × viewport = **OK** when:
- `scrollWidth ≤ clientWidth + 2px` (no horizontal scroll — the #1 mobile UX killer), and
- the page renders real text (not blank).

Open the PNG screenshots side by side to visually confirm tables, forms, and the sidebar collapse correctly.

### PWA / network resilience (`audit:pwa`)
- **manifest installable** — app can be "installed" on a phone home screen.
- **service worker file** — offline-first capability exists.
- **offline behaviour** — with the network cut, a reload still renders (cached shell / `offline.html`). `WARN` = no active service worker detected; `FAIL` = nothing rendered offline.

### Lighthouse (`audit:lighthouse`)
Scores are 0–100 against the targets in §1. Key metrics to watch:
- **LCP** (largest contentful paint) < 2.5 s · **TBT** (total blocking time) < 200 ms · **CLS** (layout shift) < 0.1.
- The mobile run uses Lighthouse's default **throttled network** — this is your slow-network ("network accessibility") measurement.

---

## 5. CI integration (optional)

Add to `.github/workflows/ci.yml` to gate merges on quality:

```yaml
  uiux-audits:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20 }
      - name: Install audit tooling
        working-directory: qa
        run: npm install
      - name: Wait for deploy & run audits
        working-directory: qa
        env:
          AUDIT_BASE_URL: https://ethiopian-payroll-engine.onrender.com
        run: |
          npx wait-on https://ethiopian-payroll-engine.onrender.com -t 180000 || true
          node axe-audit.mjs
          node responsive-check.mjs
      - uses: actions/upload-artifact@v4
        if: always()
        with: { name: uiux-reports, path: qa/reports/ }
```

---

## 6. Manual UX review checklist (human skill layer)

Automated tools can't judge everything. Before each release, walk through:

- [ ] New user can register → add employee → run payroll without help (< 5 min)
- [ ] Error messages say **what happened and what to do next**
- [ ] Forms show inline validation before submit; loading states during waits
- [ ] Amharic/English toggle keeps layout intact (no clipped Ethiopic text)
- [ ] Tables are readable on mobile (horizontal scroll container, sticky header)
- [ ] Colour is never the only signal (status also has icon/text)
- [ ] Keyboard-only user can complete login and navigation (Tab order logical)

---

## 7. Troubleshooting

| Problem | Fix |
|---------|-----|
| `Could not launch Google Chrome or Microsoft Edge` | Install Chrome, or `npx playwright install chromium` |
| Target did not respond within 120s | Render instance down — check the Render dashboard, then re-run |
| Lighthouse perf score low on first run | Cold start measured it; re-run for warm numbers |
| Authenticated pages skipped | Demo mode unavailable — set `AUDIT_EMAIL` / `AUDIT_PASSWORD` |
| Reports folder missing | Scripts create it on demand under `qa/reports/`; it is git-ignored |

---

*Maintained as part of the platform's Definition of Done. Re-run `npm run audit:all` before every release.*
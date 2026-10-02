# Mobile UX / PWA — Integration Guide (Priority #6)

## What's in this folder
- `manifest.json` — makes the app installable on Android/iOS home screens
- `sw.js` — service worker for offline app shell (does NOT cache payroll/API data — that stays live and secure)

## Step 1 — Wire up the manifest and service worker
In your base template (likely `templates/base.html`):

```html
<link rel="manifest" href="/static/manifest.json">
<meta name="theme-color" content="#0b5cad">
```

In your main JS entry point (e.g. `static/js/app.js`):

```js
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js');
}
```

Add a Flask route to serve `sw.js` from the root (it must be served from `/`, not `/static/`, or its scope is limited):

```python
@app.route('/sw.js')
def service_worker():
    return app.send_static_file('sw.js'), 200, {'Content-Type': 'application/javascript'}
```

And a minimal `/offline` route + template for the fallback page.

## Step 2 — Icons
Generate `icon-192.png` and `icon-512.png` (your logo, padded to square, solid background) and place them in `static/icons/`.

## Step 3 — Touch-friendly tables (the bigger piece)
The diagnostic noted 5 templates already got `table-responsive` wrapping. The remaining work, in priority order based on real usage frequency:

| Screen | Why it matters on mobile | Suggested fix |
|---|---|---|
| Payroll approval | Owners often approve on the go | Card layout instead of table below 600px; big tap targets for approve/reject |
| Employee list / search | Frequently checked from phone | Convert rows to stacked cards; sticky search bar |
| Payslip viewer | Employees check this on phones most | Already PDF-based — confirm PDF renders/downloads cleanly in mobile browsers |
| Leave request/approval | Time-sensitive, often done away from desk | Native `<input type="date">` for pickers, single-column form |
| Time/overtime entry | Entered on-site, not at a desk | Numeric keyboard inputs (`inputmode="numeric"`), large +/- steppers |

Pattern to reuse across all of these — CSS-only breakpoint that turns table rows into cards below 600px:

```css
@media (max-width: 600px) {
  table.responsive-card tr {
    display: block;
    margin-bottom: 1rem;
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 0.5rem;
  }
  table.responsive-card td {
    display: flex;
    justify-content: space-between;
    padding: 0.4rem 0;
    border: none;
  }
  table.responsive-card td::before {
    content: attr(data-label);
    font-weight: 600;
    color: #666;
  }
  table.responsive-card thead {
    display: none;
  }
}
```

Each `<td>` needs a `data-label="..."` attribute matching its column header for this to work.

## Step 4 — Test checklist before calling this done
- [ ] App installs to home screen on Android Chrome and iOS Safari
- [ ] Offline: app shell loads, shows `/offline` page for data-dependent screens
- [ ] Payroll approval usable one-handed on a phone
- [ ] Employee list, leave, and time entry screens don't require horizontal scrolling
- [ ] Forms use correct mobile keyboards (numeric, date, tel)
- [ ] Lighthouse PWA audit score ≥ 90

## Suggested order of work
1. Manifest + service worker + icons (today — mechanical, ~1 hr)
2. Payroll approval card view (highest-value screen)
3. Employee list + payslip viewer
4. Leave + time entry forms
5. Full Lighthouse pass and fix whatever it flags

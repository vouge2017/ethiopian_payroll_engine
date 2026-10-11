# Responsive UI follow-up — 6 October 2026

The first UI/UX improvement pass is delivered locally. This follow-up strengthens responsiveness and keyboard access in the real monthly payroll and employee journeys. Work remains uncommitted on `codex/monthly-payroll-ui`, HEAD `2f6f4e6c66726bbe5fbcd8a5bc6f51fe8fdc6110`.

## Delivered now

- Phones and tablets through 1024px use the familiar labeled compact menu; larger screens retain the desktop sidebar. This replaces a tablet icon rail whose hidden text removed accessible names and navigation group controls.
- The compact header participates in page layout, so enlarged text can increase its height without covering the heading. The expanded menu uses a text-relative reserve above the bottom navigation; its account controls remain reachable. Moving keyboard focus into the page closes the menu.
- Dark-mode payroll cards, badges, financial context and links use readable theme colors. Menu headings and account controls have readable contrast.
- Preparation has explicit input focus rings and a scoped safeguard that keeps keyboard focus clear of compact navigation. Immediate scrolling overrides the prior smooth-scroll rule that delayed rapid Tab navigation. The skip link appears on focus and has a focusable content target.
- Coarse-pointer inputs use 16px minimum text at the default text size. Controls retain touch feedback and browser zoom remains available.

## Verified evidence

| Check | Result |
|---|---|
| Broad layout sweep | Preparation, review, approval and employee home at 320, 360, 390, 430, 768, 1024, 1366, 1440 and 1920px; no detected horizontal page overflow |
| Stress data | Six synthetic employees: long and unbroken names, Amharic/Latin text, one-letter name, literal special characters, maximum-length reference and large financial amounts |
| Targeted confirmation | 17 layouts including phone/tablet, 200% root text enlargement, dark mode and 844×390 landscape |
| Keyboard | All 47 preparation controls traversed with Tab; zero recorded focus occlusion after repairs |
| Expanded tablet menu | Final axe scans have zero violations; Logout is above the bottom bar at default text and 200% root text on 768×900 and 844×390 screens; Tab back into page content closes the menu |
| Navigation/template regressions | `13 passed, 26 warnings in 20.61s` on disposable Alembic-migrated PostgreSQL |
| Static checks | Changed CSS Stylelint, monthly JS syntax and Git whitespace checks pass |

Earlier stress runs intentionally found failures. The final 17-layout receipt still contains the earlier expanded-menu heading contrast finding; a separate targeted menu receipt confirms its repair. Read these receipts together rather than treating the earlier failed run as successful. The final non-menu scans and keyboard check pass; the final menu scan passes independently. No single new all-platform or all-screen run is claimed.

Evidence: `local-evidence/visual-polish-20261006/responsive/`, `responsive-final/`, `responsive-menu/`, and `responsive-tests.log`. Independent source review identified the bottom-bar overlap risk; the reserved menu height and reachability check address it.

This is Chrome browser evidence. Physical Android/iPhone testing, software keyboard behavior, screen readers, complete local-language UI acceptance, other browser engines and connection-loss recovery remain open. Large-text testing used root text enlargement, not a full browser-zoom certification. No performance improvement is claimed.

## Which tools we use

These skills provide instructions to the coding agent. They do not require users to install software or add dependencies to the payroll application.

| Tool | Decision and usage |
|---|---|
| [Impeccable](https://impeccable.style/) | Primary visual guidance for hierarchy, shared composition, clear states and restrained polish. Published skill/reference guidance was read and applied in the first pass; no global bundle was installed. |
| [Emil Kowalski's skills](https://github.com/emilkowalski/skills) | Applied the published `mobile-native` and `break-ui` instructions in this follow-up: capability-based input sizing, zoom preservation, realistic stress data, enlarged text, dark mode and honest physical-device limits. Earlier work used his motion guidance. No global bundle was installed. |
| [Taste](https://www.tasteskill.dev/docs) | Secondary guidance for aesthetic discipline and preserving the existing product. Its marketing-page defaults do not determine this operational payroll interface. No full bundle is needed for this work. |
| Existing local capabilities | Frontend design, accessibility testing, Playwright and independent review provide implementation and evidence. |

## Where we stand and what comes next

The inspected journey remains provisionally around 80/100. This is a design judgment, not a percentage of completed features or a whole-platform release score. Local implementation and test evidence are delivered; deployment and practitioner acceptance are separate.

The smartest next work is:

1. Make phone preparation compact enough to scan and edit a whole team comfortably, preserving all submitted inputs and recovery.
2. Finish the complete first-use journey and its empty/error/expired-session/retry states; extend the same components to remaining reachable screens.
3. Observe a preparer, owner and employee completing their tasks without coaching, on real devices. Record friction and fix it before rollout.

Technical tool choices and implementation belong to Codex. The useful human input is the user's goal and observed tester confusion, not a choice between design-skill bundles.

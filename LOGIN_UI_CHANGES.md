# Login UI Revision

## Latest: Balanced Mobile Card

Only portal.css was changed for this visual refinement, plus this documentation. The desktop logo header has matching 12px top/bottom spacing at line 164. Mobile rules begin at line 232: card width is capped at 520px, padding/corners/gaps use clamp(), and the main logo grows from about 110px on short phones to 150-220px on taller screens. Input and button heights adapt to available screen height. Labels use readable fixed sizes with taller-screen variants rather than shrinking continuously with viewport width.

The login-only layout also applies to portrait windows up to 1280px wide with an aspect ratio of 2:3 or narrower, covering the requested 1246x2100 view. Wide desktop layouts retain the left branding panel. The DEMO badge stays separate from the centered logo; the footer remains at the bottom. Help remains one soft green box.

Browser checks: 360x640, 375x667, 390x844, 414x896, 430x932, 1246x2100 and desktop 1440x900. All requested portrait sizes fit with no page or card scrolling in the normal login state. Error states, keyboards and shorter landscape screens retain the card-only scrolling safety net. Preview images: ../previews/login-balanced-WIDTHxHEIGHT.png. Authentication, validation, HTML and JavaScript were not changed in this refinement.

## Earlier Revisions

Only the login presentation and supporting UI tests changed. Authentication views, Senior ID validation, password handling, database models, demo data and the static dashboard were not edited.

## Files and Lines

Line numbers refer to this revision; opening a linked file at the starting line shows the relevant section.

| File | Starting line | Change |
| --- | --- | --- |
| `accounts/templates/accounts/login.html` | 1 | Filipino copy, transparent logos, compact help, mobile help dialog and footer |
| `accounts/templates/accounts/base.html` | 3 | Optional language, body-class, controls, branding, card-header and footer template blocks; other screens retain their existing layout |
| `accounts/static/accounts/portal.css` | 133 | Login styling, phone/landscape layouts, 14px mobile helpers, 16px input text, 48px inputs and 52px submit button |
| `accounts/static/accounts/portal.js` | 13 | Login-only eye/eye-off icon update |
| `accounts/static/accounts/portal.js` | 20 | Removed text-size preference, Filipino validation feedback, dialogs, spinner and visible-keyboard sizing |
| `accounts/test_portal.py` | 30 | Regression assertions for Filipino login, empty inputs and compact help |
| `tools/prepare_login_logos.py` | 1 | Reproducible transparent logo preparation; originals retained |
| `accounts/static/accounts/images/` | - | New padasig-login.png, osca-login.png and pension-login.png |
| `STEP_2_GUIDE.md` | 55 | Updated login language/text-size editing guidance |

## Seven-Part Checklist

1. Centered logo, MALIGAYANG PAGDATING and dot divider; no subtitle.
2. Filipino helpers with the requested labels and empty placeholder-only inputs.
3. Filipino button, error, loading and help text. Brand names and expressly retained labels remain unchanged.
4. Login text-size control and preference code removed; dashboard untouched.
5. Aligned transparent PNG assets. OSCA exterior is circularly masked; pension exterior white is removed while preserving enclosed lettering. Original assets remain intact.
6. Short feature descriptions, merged desktop help and first-time information, compact wave footer and privacy dialog.
7. At widths up to 768px, only the centered login card and small footer remain. The entire left branding panel is hidden. The card contains one compact green help box. Landscape up to 1000px wide and 700px tall uses the same login-only layout. The page never scrolls; only the card may scroll internally on very short screens. Desktop styling outside these breakpoints is unchanged.

## Preview and Editing

The updated preview uses http://127.0.0.1:8002/login/ because an older server was already running on 8001. To use 8001 again, stop that old server in its own terminal with Control+C, then restart it from this backend folder. No login data or database migrations are needed for this UI revision.

Normal Django `runserver` watches template/Python changes. Refresh the browser after edits; force-refresh if an old stylesheet is cached. With `--noreload`, restart the server after template changes.

Both HTML inputs have no `value` attribute. A browser/password manager can still fill saved credentials; that is browser autofill, not a hard-coded demo login. The demo credentials appear only in an HTML code comment, not as visible instructions.

Arial is retained to match the current dashboard. The specified navy/blue palette is used for login; the dashboard itself was not restyled. No additional fonts or libraries were installed.

## Verification

Browser measurements for the mobile-only revision confirm no page overflow at 360x640, 375x667, 390x844, 414x896, 430x932, 650x800, 768x1024, 844x390 and 932x650. None of the portrait sizes requires internal card scrolling. The short 844x390 landscape view uses the permitted card-only scrolling fallback. Desktop 1440x900 has the same card dimensions and position as before. Screenshot: ../previews/login-mobile-only-360x640.png.

This mobile-only revision changes portal.css starting at line 231 and base.html line 6 (viewport-fit=cover). No JavaScript, login template content, authentication or database code changes were needed. The file table above also records earlier revisions.

Browser checks confirm help/privacy dialogs, ID validation, generic server error, and Tab order: ID, password, visibility button, forgotten-password link, submit. Real phone keyboard behavior still needs a device check; the visualViewport handler adapts to keyboard coverage. Authentication, database models, demo credentials and separate dashboard files are unchanged. The privacy notice remains an unapproved development placeholder, not a compliance guarantee.

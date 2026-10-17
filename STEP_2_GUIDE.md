# Phase 2, Step 2: Senior Login and Account Setup

## Open in VS Code

Open the `padasig-backend` folder, then open its terminal. With PostgreSQL already running:

```bash
source .venv/bin/activate
python manage.py migrate
python manage.py runserver 127.0.0.1:8001
```

Visit http://127.0.0.1:8001/login/. Keep this terminal running. If the port is occupied, open the existing server or choose another port, such as 8002. Do not start two servers on the same port.

You do not need to run the static prototype to use these screens. The prototype remains unchanged and separate. Django serves the new HTML, CSS, and JavaScript itself.

## Try the Flow

1. Use fictional Senior ID `10001` and its initial demo password `ChangeMe123!`, unless you already changed it.
2. Choose a new password. Django validates it and stores only its hash. The temporary password stops working.
3. Read the development privacy notice and agree, or log out without agreeing. Acceptance is recorded only after submitting Agree.
4. After successful login and any required setup, a short PADASIG loading animation appears before the read-only dashboard at `/portal/`.
5. Log out, then sign in using the new password. Completed setup is not repeated.

Demo password changes and privacy acceptance are saved in PostgreSQL. Do not use a personal password for fictional accounts. No passwords are included in audit metadata.

Forgot password opens instructions for the generic OSCA Help Desk. Its number is explicitly a placeholder, not a working hotline. There is no self-registration, email reset, SMS, or OTP.

## What to Edit

| File | Purpose |
| --- | --- |
| `accounts/templates/accounts/base.html` | Shared background layout, logos, language buttons, footer, idle warning |
| `accounts/templates/accounts/login.html` | Login fields, welcome copy, first-time hint |
| `accounts/templates/accounts/loading.html` | Success-only, one-time logo loading screen |
| `accounts/templates/accounts/password.html` | Forced password-change form |
| `accounts/templates/accounts/consent.html` | Development privacy notice |
| `accounts/templates/accounts/help.html` | Forgot-password help instructions |
| `accounts/templates/accounts/portal.html` | Live dashboard, including announcement and benefit cards |
| `accounts/templates/accounts/support.html` | Shared OSCA Help Desk block |
| `accounts/templates/accounts/logout.html` | Shared logout form |
| `accounts/static/accounts/portal.css` | Colors, sizes, spacing, desktop/mobile layout |
| `accounts/static/accounts/portal.js` | Show/hide password, icons, idle warning and activity requests |
| `accounts/static/accounts/images/` | Your three logos and riverfront background |
| `accounts/templatetags/portal_labels.py` | Small Filipino/English label helper |
| `accounts/views.py` | Server-side forms and account workflow |
| `accounts/middleware.py` | Required setup gates and idle-session protection |
| `accounts/security.py` | Failed-login cooldown logic |
| `accounts/models.py` | Existing profiles plus hashed login-throttle keys |
| `accounts/admin.py` | Staff password reset forces another password change |
| `accounts/urls.py` and `config/urls.py` | Screen addresses |
| `config/settings.py` | Login URL, idle duration, cooldown settings |
| `accounts/migrations/0002_loginthrottle.py` | New PostgreSQL counter table |
| `accounts/test_portal.py`, `accounts/test_dashboard.py`, and `accounts/tests.py` | Authentication, dashboard, and workflow tests |

The login page uses fixed Filipino copy in `login.html`, with no language or text-size controls. The dashboard has working language and saved text-size controls. On phones, the login's left branding is hidden so only the card remains, and help/privacy details open in dialogs. The setup/help screens still use `{% label 'Filipino text' 'English text' %}` and their existing language control. Language choices do not silently edit the profile's stored language.

CSS changes need a browser refresh. Python changes reload automatically with the normal `runserver` command. Do not double-click Django template files: they must be served by Django.

The animation timing constants `FILL_MS`, `HOLD_MS`, and `FADE_MS` are at the top of `accounts/static/accounts/portal.js`. The static `padasig-prototype/index.html` is unchanged: only Django can know that a password was accepted. Wrong passwords remain on the login page with the existing error. Reduced-motion users see a shorter logo fade.

The login screen uses a readable 18px base size and at least 48px controls. On desktop it has a branding area and login form; on mobile it stacks into one column. Longer setup pages may scroll rather than reduce text or hide information. Stored large/extra-large preferences apply after login. Icons use a pinned Lucide CDN; labels and forms still work if icons cannot load.

## Security Implemented

- Five-digit text IDs preserve leading zeros. The existing Senior ID backend performs validation and exact lookup; names never authenticate a user.
- Staff usernames remain separate from senior-ID login. No senior can enter Django admin through this flow.
- Unknown IDs, wrong passwords, inactive accounts, and cooldowns return the same generic login error.
- Five failed attempts trigger a 15-minute cooldown, tracked independently by normalized ID and direct client IP. Database row locks serialize concurrent counter updates. Raw IDs/IPs are not stored in counters.
- Password change and privacy acceptance are enforced server-side, including direct page requests. Privacy GET requests do not accept anything.
- Django handles password hashing, validation, session rotation, CSRF protection, and old-session invalidation after password changes.
- All mutations use POST; logout is not a GET link. Redirect destinations use an internal allowlist.
- Senior sessions expire after 10 minutes without activity. The warning appears during the final minute. Status polling does not renew the session; actual interaction or Stay signed in sends a CSRF-protected renewal. Expired sessions cannot be revived by that endpoint.
- Account pages send `Cache-Control: no-store, private`. Session cookies are HttpOnly/SameSite Lax; production configuration enables secure cookies. Staff admin is not subject to the senior idle timer.
- Staff password resets in Django admin mark the senior for forced password change and add an audit event. Use Users -> select the linked senior user -> password change. No original password can be viewed.

Expired counters can be cleaned without clearing active cooldowns:

```bash
python manage.py clear_expired_login_counters
```

Production must schedule this housekeeping and configure trusted proxy/IP handling. IP limits can temporarily affect multiple people using the same shared network. There is no help-desk unlock UI yet; cooldowns expire automatically. This protection is not a substitute for upstream abuse protection or monitoring.

## Verification

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test accounts announcements --noinput
```

Tests use a separate PostgreSQL test database, not the demo records. They cover generic errors, leading zeros, setup gates, password policies and changes, consent timestamps, CSRF, lockout expiry, rotating-ID attempts, safe redirects, Filipino login labels, logout, idle expiry, staff separation, and admin resets.

The original login checks passed on October 11, 2026. On October 14, 2026, the dashboard work passed all 38 Django tests, system checks, and the no-missing-migrations check. Dashboard tests cover senior isolation, active/inactive posts, several status values, and text-size validation. Browser-level visual checks of the new dashboard remain to be done.

## Still Needed Before Real Use

The static prototype remains separate, but the first dashboard at `/portal/` now reads published, staff-verified records. Its five navigation labels are visible; Documents, Announcements, Profile, and Help are clearly marked as later screens. No PDF matching, AI, chat, SMS, automatic eligibility, contact approval, or custom admin interface was added.

The privacy text is explicitly a development draft. OSCA must review the legal basis, complete the notice, confirm retention and contacts, and decide whether consent is the appropriate basis for each purpose. The current timestamp and audit notice version are development records, not proof that RA 10173 obligations are satisfied.

Implementation references: [Django authentication](https://docs.djangoproject.com/en/5.2/topics/auth/default/), [Django sessions](https://docs.djangoproject.com/en/5.2/topics/http/sessions/), and the [NPC Data Privacy Act text](https://privacy.gov.ph/data-privacy-act/).

Production additionally needs HTTPS, `DEBUG=False`, correct allowed hosts, secure database credentials, approved logo use, deployment/static-file serving, backup and restore tests, log retention, security monitoring, accessibility/user testing, proxy-aware throttling, and load/concurrency testing of login and account-reset workflows. Setup requests recheck the current password and setup flags under database locks. Keep real personal data out until these are approved.

# BIYAHERO — System Evaluation Prompt  
## Module: User Accounts and Access Control

> **How to use this file:** Copy everything from the section **BEGIN PROMPT** to **END PROMPT** and paste it into your AI coding agent (or give it to a developer) as the full task brief.  
> Source basis: *BIYAHERO Capstone Evaluation and Revision Guide* (Team-Byahero PDF), project `DESIGN.md`, and current Biyahero Flask + SQLite codebase.

---

## BEGIN PROMPT

You are a senior full-stack developer and UI designer. You must think and ship like a professional for **both** front end and back end.

Build and evaluate the **User Accounts and Access Control** module for **BIYAHERO** — a GIS-supported public transportation route-planning and commuter assistance system for selected areas in Metro Cebu (not a full real-time fleet / traffic / payment platform).

This module must integrate with the existing **Location and Route Search** module already in the project.

---

### 0. Read these first (mandatory)

1. Read `DESIGN.md` and follow its tokens, accessibility rules (WCAG 2.2 AA), component states, and consistency gates.
2. Read `AGENTS.md` and follow its communication + coding rules.
3. Inspect the existing codebase before changing anything: `app.py`, `database/schema.sql`, `css/shared.css`, `css/login.css`, `html/login.html`, signup/profile pages, and `js/login-auth.js` / `js/user.js`.
4. Prefer extending what already exists over rewriting from zero.

---

### 1. Confirmed stack assumptions (use these unless the repo proves otherwise)

| Layer | Choice |
|--------|--------|
| Client platform | **Web** (responsive HTML/CSS/JS; mobile + desktop) |
| Backend | **Flask (Python)** — existing `app.py` |
| Database | **SQLite** (`database/biyahero.db`) with clear schema in `database/schema.sql` |
| Auth approach | **Secure server sessions** (Flask session / httpOnly cookie). Prefer strengthening current session auth. If JWT is introduced, use access + refresh tokens with secure storage — do not leave secrets in source. |
| Password hashing | Already using Werkzeug (`generate_password_hash` / `check_password_hash`); keep or upgrade to Argon2/bcrypt-equivalent; never store plain text |
| Email (verify + recover) | Configurable **SMTP** (or SendGrid via env vars). Document every env var. Soft-fail gracefully in local/dev with clear setup notes. |
| Design system | `DESIGN.md` tokens + existing Biyahero navy brand (`#111A41` family). Design must feel unique, include real imagery / map / transport visuals, and stay **one product** across guest → login → role dashboards. |

**Start by confirming these assumptions in 5–10 short bullets**, then implement step by step. If something in the repo conflicts, say what you found and adjust.

---

### 2. Capstone scope guardrails (from evaluation guide)

- Position BIYAHERO as: **route planning + commuter assistance**, not vehicle tracking, fleet dispatch, online payments, or LTFRB/LGU live integration unless real partners/data exist.
- Core modules around this auth work: User/Profile Management, Location/Route Search (guest-safe), Reports/Feedback (auth-gated), Admin/Operator tools (role-gated).
- Actors that matter for this module:
  - **Guest** — search routes without account
  - **Passenger / User (Commuter)** — profile, saves, history, feedback
  - **Driver** — existing signup/approval flow; only own data
  - **Operator / Route Information Admin** — routes, approvals, reports review
  - **System Administrator** — users, roles, permissions, audit log
- Do not invent “AI” features for show. Secure RBAC + clean UX is the win for this module.

---

### 3. Core principle: Guest-first access

- Basic route search **must work without login**: origin/destination, location search, current location (with permission), map pick, viewing available public transit routes.
- Prompt login/signup **only** when identity is required, e.g.:
  - Saving favorite places or routes
  - Cross-device search history
  - Editing a profile
  - Submitting reports / feedback
  - Admin, operator, or staff tools
- When a guest taps a protected feature: short plain explanation + **Log in** + **Sign up**. After auth, **return to the same action** with state preserved (origin, destination, map selection, form draft).
- **Never lose** the guest’s current search when redirecting to login.

---

### 4. Features to implement / harden

#### 4.1 Registration
- Email + password signup (optional later: phone, Google/Facebook — do not block MVP).
- Fields: name, email, password, confirm password.
- Validate on client **and** server (email format, password strength, duplicate email).
- Email verification link or code; unverified accounts stay limited to basic features until verified.
- Clear, non-technical error messages (simple words).

#### 4.2 Login and logout
- Email + password login.
- Secure “stay signed in” via session / refresh strategy.
- Rate-limit + temporary lock after repeated failed attempts.
- Logout clears server session and any client-held auth state.

#### 4.3 Profile management
- View/edit: name, optional photo, phone, preferred language, transport preferences (fewest transfers, lowest fare, accessibility needs).
- Change email (re-verify) and password (require current password).
- Delete account with confirmation; remove or anonymize personal data.
- Manage saved places/routes (home, work, favorites) — own data only.

#### 4.4 Password recovery
- Forgot password: email → time-limited single-use reset link or OTP.
- Same generic response whether email exists or not (no account enumeration).
- After reset: set new password, invalidate all sessions, send confirmation email.
- Rate-limit reset requests.

#### 4.5 Role management (RBAC)
- Roles:
  - Guest — basic route search only
  - User / Commuter — saves, history, profile, feedback
  - Driver — driver tools; own profile/docs/routes only
  - Operator / Contributor — route/stop data & report review as designed
  - Admin — users, roles, content, reports, audit log
- Enforce permissions on **every** protected API (never rely on hiding UI alone).
- Admin panel: list/search users, change roles, suspend/reactivate, audit log of role changes.
- Prevent demoting/deleting the **last admin**.
- Design permissions so new roles can be added without rewriting the whole app (RBAC tables or equivalent).

---

### 5. Security and privacy (non-negotiable)

- Hash passwords; never log plain-text passwords.
- HTTPS in production; secure cookies (`HttpOnly`, `Secure`, `SameSite` as appropriate).
- Protect against SQL injection (parameterized queries), XSS, CSRF, brute force.
- Users can **only** access their own pages and records (IDOR-safe: check `session` user id/role on every sensitive read/write).
- Secrets and API keys only in environment variables — never in source. Fix hard-coded `secret_key` style issues.
- Collect only needed data; explain use; consent for location history if stored.
- Follow Philippine Data Privacy Act (and GDPR-minded practices where applicable).
- Audit sensitive admin actions.

---

### 6. Design, UX, and CSS hard rules

**Consistency**
- Design must be consistent on **every** page. After login it must **not** feel like another product/dimension. Same tokens, fonts, colors, spacing, header/nav patterns, button language.

**Quality bar**
- Unique, professional look with real images / map / transport atmosphere (not empty generic purple AI UI).
- Follow `DESIGN.md`: semantic tokens, component states (default, hover, focus-visible, active, disabled, loading, error), keyboard + pointer + touch behavior, testable a11y criteria.

**CSS constraints (strict)**
- Layout with **`display: flex`** and **`flex-wrap`** for responsive wrapping.
- **Never use** `@` rules of any kind in project CSS you write or edit for this task — including **no `@media`**, **no `@keyframes`**, and no other at-rules (`@import`, `@font-face` in new CSS, etc.). Achieve mobile/desktop friendliness with flex-wrap, fluid widths (`%`, `max-width`, `min-width`), relative units, and shared layout classes.
- Keep pages fast: minimize blocking assets, reuse shared CSS/JS, optimize images, avoid heavy unused libraries.

**Copy / user friendliness**
- UI words must be simple. Buttons like **Log in**, **Sign up**, **Save**, **Forgot password?**, **Delete my account**, **Go back** — not jargon.
- Goal: a first-time user understands every button and page without training.

**Accessibility**
- Labels, contrast, focus-visible, screen reader text, skip links where needed.
- Target WCAG 2.2 AA from `DESIGN.md`.

---

### 7. Performance

- Optimize for faster page loads: shared CSS, deferred non-critical JS, compressed images, lean HTML, cache static assets where appropriate, avoid duplicate Leaflet/CSS loads.
- Loading states for every network request; never leave the UI frozen with no feedback.

---

### 8. Integration with Location and Route Search

- Guest can search/plan without account.
- Auth walls only on save/history/profile/report/admin actions.
- Preserve search state across login redirect (query params, `sessionStorage`, or server temp draft — pick one and document it).
- Roles after login land on the correct home without breaking shared route-search entry points.

---

### 9. Deliverables (complete all)

1. **Database schema** updates: users/roles/permissions (or mapped commuter/driver/operator + roles), tokens/reset codes, saved places, audit log — with migration/init notes.
2. **API endpoint list** with request/response examples.
3. **Working commented code** for backend + client screens (login, signup, profile, forgot/reset password, guest gate modal, admin role tools as scoped).
4. **Auth flow diagrams** (text or Mermaid): sign-up, login, guest-to-login redirect, password reset.
5. **Setup instructions**: env vars, email/SMTP config, how to run Flask correctly (`http://127.0.0.1:5000` — not Live Server).
6. **Test checklist** covering at least:
   - Guest route search works without login
   - Protected feature redirects to login and returns with state
   - Wrong password / lockout behavior
   - Expired reset link
   - Role escalation attempts blocked on API
   - Users cannot open another user’s profile/data
   - Account deletion / anonymization
   - UI consistency guest ↔ logged-in pages
   - No forbidden CSS at-rules introduced
   - Simple button labels readable by non-technical users

---

### 10. Evaluation criteria (how reviewers / agents judge success)

Score and improve against:

| Area | Pass means |
|------|------------|
| Guest-first | Core search usable with zero account |
| Auth completeness | Register, login, logout, verify, reset, profile |
| RBAC | Backend enforces roles; last-admin protected |
| Security | Hashing, session safety, IDOR blocked, secrets in env |
| Design consistency | Same visual system all pages; DESIGN.md respected |
| CSS rules | Flex + wrap; zero `@media` / `@keyframes` / other `@` |
| UX words | Simple labels; clear errors; loading/empty states |
| Performance | Noticeably lean loads; shared assets |
| Capstone fit | Auth supports route assist scope; no fake “full smart city” claims |
| Docs | Schema, APIs, diagrams, setup, tests all present |

Use ISO/IEC 25010-minded checks where useful: functional suitability, performance efficiency, usability, reliability, security, compatibility.

---

### 11. Work order

1. Confirm assumptions (short).
2. Audit current auth gaps vs this prompt.
3. Schema + migrations.
4. Backend APIs + permission middleware.
5. Client screens + guest redirect with state preserve.
6. Design pass for consistency + images + simple copy.
7. Performance pass.
8. Security pass (IDOR, rate limits, secrets).
9. Diagrams + setup + test checklist.
10. Final self-review against Section 10.

Do not claim real-time tracking, payments, or official government integration. Do not auto-publish passenger reports into the route database.

## END PROMPT

---

## Quick paste note for teammates

If you only need the agent instruction, copy from **BEGIN PROMPT** through **END PROMPT**.  
Keep this file in the repo so every evaluation run uses the same standard.

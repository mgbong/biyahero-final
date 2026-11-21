# Route Information & Updates + User Reports

**Stack:** Web · Flask · SQLite · in-app banners (no push in MVP)

## Assumptions

| Item | Choice |
|------|--------|
| Client | Web (SwiftMove shell) |
| Backend | Python / Flask |
| DB | SQLite (`database/biyahero.db` + `route_info_schema.sql`) |
| Notifications | In-app status text on My Reports / staff desk |
| Photos | Local `uploads/reports/` |
| Staff | `operator` role; admin emails: `operator@biyahero.com`, `admin@biyahero.com` |

Guests can **view** routes & advisories. Guests who tap Report see Log in / Sign up; draft context is kept.

---

## Schema (relationships)

```
ri_stops 1──* ri_route_stops *──1 ri_routes
ri_routes 1──* ri_reroutes
ri_advisories (many-to-many via affected_route_codes text)
ri_change_log / ri_approvals (audit + draft→review→publish)

ur_reports 1──* ur_attachments
ur_reports 1──* ur_status_history
ur_reports 1──* ur_comments
ur_reputation (per user)
```

Timestamps are **UTC ISO**. UI shows **Asia/Manila (PHT)**.

---

## Workflow: Draft → Review → Publish

```
Operator creates advisory/route edit
        │
        ▼
    status = draft
    ri_approvals = pending
        │
        ▼
 Admin Approve ──► status = published (+ verified for routes)
 Admin Reject  ──► status = archived (reason required)
```

### Advisory / reroute activation

```
published AND now >= starts_at
  AND (until_further_notice OR now <= ends_at)
  AND not resolved
→ shown on Updates + route banners
else → history only
```

Route Planning calls `effective_line_stops()` so active detours change planned stop lists.

---

## Reports status machine

```
submitted → under_review → needs_more_info → under_review
                      ↘ verified → approved → implemented
                      ↘ rejected | duplicate
submitted/needs_more_info/under_review → withdrawn (owner)
```

Approve → optional **Apply correction draft** → `ri_approvals` entity `report_correction`.

---

## Public APIs

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/route-info?q=&stop=` | Published routes + active advisories |
| GET | `/api/route-info/<code>` | Detail + reroutes + advisories |
| GET | `/api/advisories?history=&severity=&route=` | Active or history |
| GET | `/api/reroutes` | Active reroutes |
| GET | `/api/updates?history=&severity=` | Split feed: verified route changes vs traffic advisories + source directory + refresh meta |

### Updates feed (`/api/updates`)

Two buckets — never mixed as the same thing:

| Bucket | Meaning | Badge |
|--------|---------|-------|
| `route_changes` | Staff-published path/stop/terminal change (`ri_reroutes`) | **Verified route change** |
| `traffic_advisories` | General delay / closure / weather / service heads-up (`ri_advisories`) | **Traffic advisory** (never “Verified route change”) |

Each item includes `source` (`label`, `trust`, `blurb`, optional `url`) and `last_updated`.  
`meta` tells the UI how often to refresh:

- `refresh_seconds`: **60** (page auto-checks)
- `refresh_label`: human copy for the Updates screen
- `publish_sla`: new staff posts usually show within 1–2 minutes after publish
- `sources`: directory of known data sources

### Sample response (route list excerpt)

```json
{
  "ok": true,
  "routes": [{
    "code": "01K",
    "verified": true,
    "verification": { "badge": "Verified", "by": "System seed", "at": "…" },
    "stale_warning": false,
    "source": { "label": "agency", "url": null },
    "last_updated": "2026-11-21T06:00:00Z"
  }]
}
```

---

## Protected APIs

| Method | Path | Who |
|--------|------|-----|
| POST | `/api/staff/advisories` | operator+ (traffic advisory) |
| POST | `/api/staff/reroutes` | operator+ (verified route change; admin publishes immediately) |
| POST | `/api/staff/review` | admin |
| GET | `/api/staff/queue` | operator+ |
| POST | `/api/staff/import/preview` | operator+ |
| POST | `/api/reports` | logged-in user |
| GET | `/api/reports/mine` | owner |
| GET | `/api/reports/<id>` | owner or staff |
| POST | `/api/reports/<id>/status` | owner (withdraw) / staff |
| GET | `/api/staff/reports` | staff |
| POST | `/api/staff/reports/<id>/apply` | staff |

Unauthorized write → **403**. Guest submit → **401** + login redirect hint.

---

## Screens

| Screen | File |
|--------|------|
| Routes | `html/routes.html` + `js/route-info.js` |
| Updates | `html/updates.html` + `js/advisories.js` |
| Report / My Reports | `html/report.html` + `js/user-reports.js` |
| Staff desk | `html/staff-route-desk.html` + `js/staff-desk.js` |

---

## Notification templates

See `services/reports.py` → `NOTIFICATION_TEMPLATES`  
(under_review, needs_more_info, verified, approved, implemented, rejected, duplicate, withdrawn).

---

## Test checklist

### Route Information
- [ ] Unverified routes show **Unverified** (never a Verified badge)
- [ ] Stale data (>90 days since review) shows **Needs review**
- [ ] Expired temporary reroute disappears from `/api/reroutes` and Plan Trip uses normal stops
- [ ] Active advisory banners on Routes + Updates
- [ ] Updates page separates **Verified route changes** from **Traffic advisories**
- [ ] Each update shows **source** + page shows **refresh frequency** (~60s)
- [ ] Offline cache on Routes shows “may be outdated”
- [ ] Operator can create advisory draft; non-admin cannot publish via review
- [ ] Admin can post verified reroute; shows under route_changes on `/api/updates`
- [ ] Admin reject without reason fails
- [ ] Admin approve publishes advisory
- [ ] CSV preview rejects duplicate codes / <2 stops
- [ ] Unauthorized POST `/api/staff/advisories` → 403

### User Reports
- [ ] Guest sees gate; after login draft route/stop restored
- [ ] Similar reports → 409 + confirm flow
- [ ] Rate limit after 5 reports / day
- [ ] Photo over 5 MB rejected
- [ ] User A cannot GET user B’s report → 403
- [ ] Invalid status transition rejected
- [ ] Reject without reason rejected
- [ ] Approve + Apply correction creates pending `report_correction`
- [ ] Duplicate status requires `duplicate_of`
- [ ] Draft autosaved in sessionStorage when offline / before login

---

## Run

```bash
python app.py
```

- Routes: http://127.0.0.1:5000/html/routes.html  
- Updates: http://127.0.0.1:5000/html/updates.html  
- Report: http://127.0.0.1:5000/html/report.html  
- Staff: http://127.0.0.1:5000/html/staff-route-desk.html (log in as operator)

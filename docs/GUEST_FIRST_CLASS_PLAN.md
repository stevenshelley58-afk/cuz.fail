# Guest-First-Class Plan — kill the preview, give guests the real product

**Status:** Approved by operator (Steven), 2026-06-10. Execute under Operator Standing Approval in CLAUDE.md — do not pause to ask permission.
**Audience:** implementation agent with zero prior context. Follow steps in order. Every file path below exists and was verified on 2026-06-10.

---

## 1. Objective

Today a guest asks "What does R20 zoning allow?" and gets a canned paragraph that says "Preview only — not a source-backed answer." That demonstrates zero value. This plan removes guest preview mode entirely:

1. **Guests get the real pipeline.** Same retrieval, same citations, same advisory statuses as signed-in users. The only difference is a usage budget and that their work lives in a throwaway guest org.
2. **Hidden headroom.** Whatever budget we *display* to guests, the server *enforces* 1.5× that number. The displayed number is the marketing number; the enforced number is never shown anywhere — not in UI, not in API error bodies, not in response headers.
3. **No sign-in wall on arrival.** The app loads straight into a working product. Sign-in is offered only when the budget is truly exhausted or the guest tries to do something inherently account-bound.

### Non-negotiables (do not violate)

- Governance rules in `CLAUDE.md` still apply to guests: cite approved source versions or state the library can't support the answer; advisory statuses only (`likely_pass / likely_fail / needs_more_info / unsupported`); never claim final compliance.
- Same-origin `/api/v1` only. No `VITE_API_BASE_URL`, no CORS changes, no Vercel.
- The 1.5× multiplier and the enforced limits must never appear in any client-visible string, JSON field, or header. The 429 body says only that the free allowance is used up.

---

## 2. Current state (verified, with file:line)

**Frontend (`web/`):**

- `web/src/config.ts:11-12` — `GUEST_ADDRESS_LIMIT` (default 2, env `VITE_GUEST_ADDRESS_LIMIT`), `GUEST_CHAT_LIMIT` (default 8, env `VITE_GUEST_CHAT_LIMIT`). `GUEST_USAGE_KEY = "lotfile_guest_usage_v1"` at line 3.
- `web/src/hooks/useGuestUsage.ts` — localStorage quota counter. `startGuestAddress` (line 67) and `startGuestChat` (line 93) **block client-side** when the count reaches the limit and fire the paywall.
- `web/src/views/home.tsx` — the canned previews. `pushGuestAddressPreview` (line 90) and `pushGuestChatPreview` (line 112) emit the "Preview only — not a source-backed answer" messages. They are invoked from `startCheck` (lines 160, 178, 181, 191, 193) and `send` (lines 238, 243) whenever the API returns `auth` / `notBuilt` / `missing` / `down` for a guest. `guestLimitMessage` (line 26) is the preemptive block message. Quota chip rendered at line 357. Hint buttons at lines 363-368.
- `web/src/App.tsx` — `authed = session?.kind === "ok"` (line 44). Auto-popup of `SignInModal` for unauthenticated visitors (lines 48-55). Sidebar "Guest mode · 2 searches · 8 chats" (lines 106-110). Rules view hard-gated behind sign-in (line 132).
- `web/src/components/modals.tsx` — `PaywallModal` (line 151, copy at line 7) shows the displayed limits (line 182); `SignInModal` (line 136) with "Continue as guest" skip.
- `web/src/api.ts` — `call()` maps 401/403 → `{kind:"auth"}` (line 175). `api.ask` posts to `/assistant` (line 273). `api.createProject` (line 239), `api.resolveAddress` (line 246). No 429 handling exists.
- `web/src/views/projects.tsx:96` — "Guest preview" label on guest history rows.
- `web/src/components/common.tsx:111` and `web/src/views/settings.tsx:30` — copy claims "a reviewer signs off, never the model", which contradicts CLAUDE.md (pipeline is fully AI, no human signoff). Fix as part of this work (Step F7).

**Backend (`src/draftcheck/`):**

- `src/draftcheck/api/auth.py` — `get_current_session` (line 175) raises 401 when there is no session cookie. Every product endpoint depends on it, so guests get 401 for everything; the SPA then falls back to canned previews. Magic-link request/verify currently raise 404 (lines 195-213); `dev_login` (line 216) is the working login. Cookie set via `_set_session_cookie` (line 156).
- `src/draftcheck/domain/identity/roles.py` — `IdentityRole` has `OWNER, OPERATOR, COMPLIANCE_OWNER`. No guest role.
- `src/draftcheck/domain/identity/store.py` and `sqlalchemy_store.py` — `InMemoryIdentityStore` / `SqlAlchemyIdentityStore`, both expose `get_or_create_org`, `get_or_create_user`, `create_session`, `get_session`.
- Endpoints guests need: `POST /assistant` and `POST /search/ask`, `POST /search/chunks` (`src/draftcheck/api/sources.py:1084-1114`), `POST /projects` (`src/draftcheck/api/projects.py:239`), `POST /projects/{id}/resolve-address` (owned by `src/draftcheck/api/address.py:209`), proposal + compliance + documents routes, `GET /rules` (`api/rules.py`).
- `src/draftcheck/config.py:45` — `Settings` is a frozen `@dataclass` populated by `Settings.from_env()`; new fields must be added to BOTH the dataclass and `from_env()` (env-var parsing), matching the existing style.
- Migrations live in `src/draftcheck/db/alembic/versions/` (latest: `0011_corpus_buildout_support.py`).

**Root cause in one sentence:** guests have no server session, so every real call 401s, and the frontend papers over it with canned text. Fix = give guests a real (rate-budgeted) server session and delete the paper.

---

## 3. Budget design

| Feature | Displayed to guest | Enforced by server (hidden) |
|---|---|---|
| Address checks (project creations) | `GUEST_ADDRESS_LIMIT` = 2 | `ceil(2 × 1.5)` = 3 |
| Chat questions (`/assistant`, `/search/ask`) | `GUEST_CHAT_LIMIT` = 8 | `ceil(8 × 1.5)` = 12 |

Rules:

- Displayed limits stay in `web/src/config.ts` exactly as they are. If marketing changes the displayed number, the enforced number follows automatically via the multiplier.
- Multiplier lives **server-side only**: `Settings.guest_quota_factor = 1.5`. There is no frontend constant, env var name, or API field that exposes it.
- The client **never blocks preemptively**. It always sends the request; the server decides. The usage chip displays `min(used, displayed_limit)/displayed_limit` so the counter pins at "2/2" / "8/8" while the hidden headroom silently keeps working. The paywall appears only on a server 429.
- 429 body: `{"detail": "guest_allowance_used", "feature": "address" | "chat"}`. Nothing else. No counts, no limits.

---

## 4. Backend steps (do these first)

### B1. Add guest role
`src/draftcheck/domain/identity/roles.py`: add `GUEST = "guest"` to `IdentityRole`. Check both identity stores and any DB role constraint for a role whitelist — migration `0006_fix_role_constraint.py` suggests a CHECK constraint exists; if `users.role` has one, write migration `0012_add_guest_role.py` extending it to include `'guest'`.

### B2. Settings
`src/draftcheck/config.py`, add to the `Settings` dataclass (line 45) AND wire each one in `Settings.from_env()`:

```python
guest_mode_enabled: bool = True          # env DRAFTCHECK_GUEST_MODE_ENABLED
guest_address_limit: int = 2             # env DRAFTCHECK_GUEST_ADDRESS_LIMIT (displayed)
guest_chat_limit: int = 8                # env DRAFTCHECK_GUEST_CHAT_LIMIT (displayed)
guest_quota_factor: float = 1.5          # hidden headroom multiplier — never expose to clients
```

Enforced limit helper: `math.ceil(displayed * guest_quota_factor)`.

### B3. Guest usage storage
New migration `src/draftcheck/db/alembic/versions/0013_guest_usage.py` (use the next free number — check the directory first):

```
guest_usage(
  user_id   uuid PK part / FK users.id,
  feature   text PK part,        -- 'address' | 'chat'
  used      integer not null default 0,
  updated_at timestamptz not null
)
```

New file `src/draftcheck/domain/identity/guest_usage.py` with a small store interface mirroring the existing identity-store pattern: `GuestUsageStore.increment_and_check(user_id, feature, enforced_limit) -> bool` (atomic `UPDATE ... SET used = used + 1 WHERE used < limit` returning whether the increment was allowed; SQLAlchemy backend + in-memory dict backend for when `DATABASE_URL` is unset, selected the same way `get_identity_store` in `api/auth.py:78-92` does).

### B4. `POST /auth/guest` endpoint
In `src/draftcheck/api/auth.py`:

- New route `POST /auth/guest` (no auth required, `require_allowed_origin` applied like `dev_login` does at line 224).
- If the request already carries a valid session cookie → return that session (idempotent; prevents cookie-reset farming from one browser, and signed-in users who hit it keep their real session).
- If `settings.guest_mode_enabled` is false → 404.
- Otherwise: create a **fresh org per guest** (data isolation — projects are org-scoped) and a user with `role=IdentityRole.GUEST`, email like `guest-{uuid4().hex[:12]}@guest.lotfile.app`, then `store.create_session(...)` and `_set_session_cookie(...)` exactly as `dev_login` does (lines 234-251). Return the standard `VerifyMagicLinkResponse` shape so the SPA's session handling is uniform.
- `GET /auth/session` already returns `role` via `_session_response` — verify `"guest"` comes through; the SPA keys off it.

### B5. Quota dependency
New file `src/draftcheck/api/guest_quota.py`:

```python
def guest_quota(feature: Literal["address", "chat"]):
    def dep(active_session=Depends(get_current_session), settings=Depends(get_settings), usage_store=Depends(get_guest_usage_store)):
        if active_session.user.role != IdentityRole.GUEST:
            return
        displayed = settings.guest_address_limit if feature == "address" else settings.guest_chat_limit
        enforced = math.ceil(displayed * settings.guest_quota_factor)
        if not usage_store.increment_and_check(active_session.user.id, feature, enforced):
            raise HTTPException(status_code=429, detail="guest_allowance_used",
                                headers={"x-lotfile-feature": feature})
    return dep
```

(429 must NOT include the enforced limit or remaining count anywhere.)

Apply it:

- `src/draftcheck/api/sources.py` → `/assistant` (line ~1110) and `/search/ask` (line ~1094): add `Depends(guest_quota("chat"))`. `/search/chunks` (line ~1084): leave unmetered (it backs UI features, not the headline ask).
- `src/draftcheck/api/projects.py` → `POST /projects` (line 239): add `Depends(guest_quota("address"))`. Resolve-address, proposal, property GET, compliance run/matrix, document routes: **no extra metering** — they operate on the guest's own (budgeted) projects and are what demonstrates value.

### B6. Guest hygiene (small, do not skip)
- Cleanup: nightly job or simple SQL in an ops script to delete guest orgs (and cascading projects/sessions/guest_usage) older than 14 days. If a job runner doesn't exist, add `scripts/purge_guest_orgs.py` + a cron line in the VPS deploy docs (`docs/PRODUCTION_DEPLOYMENT.md`).
- Abuse valve: per-IP rate limit on `POST /auth/guest` (e.g. 20/hour). If there's no rate-limit middleware already, a dict-based in-process limiter in the route is acceptable for now; note it in the PR.

### B7. Backend tests
Add `tests/test_guest_mode.py` following the conventions in the existing `tests/` directory (see `tests/conftest.py`, `tests/test_assistant_citations.py`):

1. `POST /auth/guest` returns a session with role `guest`; second call with cookie returns same session.
2. Guest can `POST /projects` up to the *enforced* limit (3), gets 429 `guest_allowance_used` on the next one.
3. Guest can call `/assistant` 12 times, 429 on the 13th.
4. 429 body and headers contain no numbers.
5. Non-guest sessions are never metered.
6. Guest from org A cannot read org B's projects (existing org scoping — just assert it holds for guest orgs).

---

## 5. Frontend steps

### F1. `web/src/api.ts`
- Add result kind: `| { kind: "quota"; feature: "address" | "chat" }`. In `call()` after the 401/403 line (175): `if (res.status === 429) { const d = data as {detail?: string} | null; if (d?.detail === "guest_allowance_used") return { kind: "quota", feature: (res.headers.get("x-lotfile-feature") as "address"|"chat") ?? "chat" }; }` then fall through to generic error.
- Add `guestSession: () => call<Record<string, unknown>>("POST", "/auth/guest")` to the `api` object.

### F2. `web/src/App.tsx` — guest bootstrap, no wall
- In the session-resolution effect: when `api.session()` returns `kind:"auth"` (no session), call `api.guestSession()` then `refreshSession()`. If guest creation fails (e.g. API down), fall back to current behavior.
- `const role = session?.kind === "ok" ? String(session.data.role ?? session.data.user?.role ?? "") : "";`
  `const isGuest = role === "guest"; const authed = session?.kind === "ok" && !isGuest;`
  Note: most of the app should now branch on `session ok` (API works) vs `isGuest` (upsell UI), not the old `authed`.
- **Delete the auto sign-in popup** (lines 48-55, the `autoPrompted` effect and state). Guests land in the product.
- Rules gate (line 132): remove — guests have sessions now, render `<RulesView />` for everyone.
- Sidebar (lines 106-110): for guests show value, not limits: avatar `"✦"`, label `Free preview`, sub-line a `Sign in` link (opens `SignInModal`). Do not list quota numbers here.
- Pass `isGuest` into `Home` and `Projects` (keep `guestUsage` for the soft counter, see F4).

### F3. `web/src/views/home.tsx` — delete the canned previews
- Delete `pushGuestAddressPreview`, `pushGuestChatPreview`, `guestLimitMessage`, and every call site (lines 26-30, 90-137, 141, 160, 178, 181, 191, 193, 212, 238, 243).
- `startCheck`: remove the `onGuestAddressStart` preemptive block (lines 140-143). Error handling becomes role-agnostic: `created.kind === "quota"` → `onShowPaywall(created.feature)`; `auth` → `onNeedSignIn()`; `notBuilt`/`down`/`error` → the honest warn message already used for authed users (line 175 pattern). Same for `resolveAddress` results.
- `send`: remove the `onGuestChatStart` preemptive block (lines 211-215). On `r.kind === "quota"` → push a friendly note ("You've used the free allowance — sign in to keep going, it's free.") with `action` opening the paywall, same Msg shape as before. `auth`/`notBuilt`/`missing` no longer have guest branches — handle them exactly like the authed paths today.
- After a **successful** guest action, still record it via the existing localStorage hook so the chip and Recent strip work (see F4) — call the (renamed) recorder after `r.kind === "ok"`, not before the request.
- Quota chip (line 357): render only for `isGuest`, display `min(used, LIMIT)/LIMIT`, and restyle as positive: `Free preview · {n}/{LIMIT} checks · {m}/{LIMIT} questions`. It pins at the displayed max while hidden headroom keeps the product working — that is intentional.
- First-message welcome: when `isGuest` and `msgs.length === 0`, the greet block (lines 287-292) gets one extra line: `Real answers, cited from the approved WA source library — no account needed.`

### F4. `web/src/hooks/useGuestUsage.ts` — counters, not gates
- Remove the blocking logic: `startGuestAddress`/`startGuestChat` no longer check limits or call `onLimitReached`; rename to `recordGuestAddress(address)` / `recordGuestChat()` (update `App.tsx` + `home.tsx` imports). Keep localStorage persistence and `guestProjectList` (Recent strip + Projects view depend on it).
- Allow `checks` to keep up to 6 entries instead of 4 (lines 20, 85) so the hidden headroom's extra checks still show in Recent.

### F5. `web/src/components/modals.tsx` — paywall becomes a conversion screen
- `paywallCopy`: rewrite to lead with what they just experienced: title `"You've used the free preview"`, body `"You've seen real, cited answers from the approved WA source library. Create a free account to keep going — your checks and chats carry on from here."`
- Remove the usage-meter bar (lines 176-178) and the Guest-vs-Unlocked numeric comparison (line 182) — never advertise limits at the wall, advertise value. Replace the plans block with three value bullets: saved dossiers · drawing uploads & Tier-1 checks · full source library search.
- `SignInModal`: keep, but it is now only opened by explicit user action or the paywall.

### F6. `web/src/views/projects.tsx`
- Line 96: replace label `Guest preview` with `Free preview` (these are now real checks, not previews).

### F7. Copy honesty fixes (CLAUDE.md conflict)
- `web/src/components/common.tsx:111`: footer → `LotFile · /api/v1{version} · advisory only — cited to approved sources, not a certification`.
- `web/src/views/settings.tsx:30`: remove "A human reviewer signs off; the model never does." → "Outputs are advisory and cited to approved source versions; they are not final certifications." (Pipeline is fully AI per CLAUDE.md — the old copy was false.)

### F8. Frontend tests / checks
- `cd web && npm run lint && npm run build` must pass.
- Grep gates (all must return nothing): `grep -rn "Preview only" web/src`, `grep -rn "not a real answer" web/src`, `grep -rn "guest preview" web/src -i`, `grep -rn "quota_factor\|guest_quota_factor\|1.5" web/src`.

---

## 6. Acceptance criteria (verify every one before merging)

1. Fresh incognito visit to https://lotfile.app: no sign-in popup; sidebar says "Free preview"; asking "What does R20 zoning allow?" returns a **real cited answer** (or an honest "the approved source library cannot support this yet" from the real pipeline) — never the words "Preview only" or "not a real answer".
2. Typing an address as a guest creates a real project, resolves the property, and opens the wizard — identical flow to a signed-in user.
3. Guest can run 3 address checks and 12 chats (enforced); UI counter never displays more than 2/2 and 8/8; requests 3 and 9-12 still succeed silently.
4. Request beyond enforced limit → paywall modal, with no numbers leaked in the network response.
5. Guests can open Rules and Library read views.
6. Signed-in users: zero behavior change, never metered.
7. No string in `web/dist` or any API response contains the enforced limits or the multiplier (`grep -rn "guest_quota_factor\|allowance.*3\b\|allowance.*12\b" web/dist` style spot-checks; mainly rely on code review of the 429 path).
8. Backend tests in B7 green; `npm run build` green; CI green.

## 7. Order of work & deploy

1. Backend B1→B7 (one PR). 2. Frontend F1→F8 (second PR, after backend is deployed — the SPA degrades gracefully if `/auth/guest` 404s because guest bootstrap falls back). 3. Deploy per `docs/PRODUCTION_DEPLOYMENT.md` (VPS, Caddy, same-origin — no infra change needed; `/auth/guest` rides the existing `/api/v1` proxy). 4. Manually run acceptance check 1-5 against production in incognito. Log decisions in commit/PR descriptions per Operator Standing Approval.

## 8. Out of scope (do not do now)

- Migrating a guest org's projects into a real account on sign-up (phase 2; note the guest org id in a cookie/claim so it's possible later).
- Payments/checkout changes (`CHECKOUT_URL` logic untouched).
- Magic-link re-enable (request/verify currently 404 by design in `api/auth.py:195-213`) — sign-in remains whatever it is today.

# Explanation — The storage abstraction and its three modes

> Diátaxis: **Explanation.** Why persistence is pluggable, what the three modes are
> for, and the non-obvious decision about the Supabase client's lifetime. For the
> function-by-function listing of `storage.py` / `db.py`, see
> [reference-modules.md](reference-modules.md).

## The problem

The app started as a personal, local-only tool — write a few JSON files next to the
script and never think about it again. Then it became a public product: anyone can
sign up, and each user's portfolio, snapshots, watchlist, and price overrides must be
private to them. But the local-only mode still has to keep working unchanged for
someone running `streamlit run app.py` on their own laptop, and there's a third case
in between: a shared hosted demo where strangers must not see each other's uploads.

Three different deployment realities, one set of pipeline code that just wants to call
"save my session" / "load my snapshots" without caring where they go.

## The abstraction: one `store`, chosen once

`db.py` deliberately **mirrors the function signatures of `storage.py`** —
`save_session`, `load_session`, `save_snapshot`, `load_snapshots`, `save_watchlist`,
`save_overrides`, `session_meta`, … . Because the two modules are signature-compatible,
the rest of the app never branches on backend. It picks once, at the top of `app.py`:

```python
USE_DB = db.is_enabled()
store  = db if USE_DB else storage
```

and then calls `store.save_session(...)`, `store.load_snapshots()`, etc. everywhere.

- **Why duck-typed modules, not an ABC / class hierarchy?** Two implementations, a
  fixed handful of functions, no third backend on the horizon. A formal interface would
  be ceremony for its own sake. Two modules with matching function names *is* the
  interface — Python's, for free.
- **Trade-off:** the compiler won't catch a signature that drifts apart between the
  two files. The mitigation is that the surface is small and both files sit side by
  side; a drift is a one-line fix, not a design flaw.

## The three modes

```
                          db.is_enabled()?
                                │
              ┌─────────────────┴──────────────────┐
             yes                                    no
              │                                      │
   ┌──────────────────────┐              PORTFOLIO_MULTIUSER == "1" ?
   │  Supabase (db.py)     │                  ┌───────┴────────┐
   │  per-user, RLS,       │                 yes               no
   │  optional email-2FA   │                  │                 │
   └──────────────────────┘       ┌──────────────────────┐  ┌──────────────────────┐
                                   │  multi-user hosted    │  │  local files          │
                                   │  storage.py +         │  │  storage.py, ./data/  │
                                   │  per-session temp dir │  │  single user, on disk │
                                   └──────────────────────┘  └──────────────────────┘
```

### 1. Local files — `storage.py`, `./data/` (the default)

No secrets, no env var. Everything is JSON / Parquet under `./data/` next to the app.
Single user, single machine, nothing leaves the computer. This is the original tool
and the fallback for everything below.

### 2. Multi-user hosted — `PORTFOLIO_MULTIUSER=1`, per-session temp dir

A shared public demo with no accounts. We still use `storage.py`, but each browser
session gets a random id and `storage.configure()` repoints `DATA_DIR` at
`tempfile.gettempdir()/portfolio_sessions/<sid>`. So visitors can't see each other's
data, **and** nothing is persisted past the session — temp dirs are ephemeral.

- **Why reuse `storage.py` instead of writing a third backend?** It already does
  file I/O; isolating it is just changing the directory. `configure()` mutating module
  globals is a deliberate shortcut for a process that serves one logical app — small,
  visible, and far cheaper than a new persistence layer.
- **Trade-off:** "saved" here means "saved for this session only." That is the
  *intended* contract for an anonymous demo (privacy by ephemerality), and the sidebar
  says so explicitly.

### 3. Supabase — `db.py`, accounts + row-level security + optional 2FA

When `SUPABASE_URL` + `SUPABASE_ANON_KEY` are in `st.secrets` and the `supabase`
package is importable, the app requires login and stores each user's rows in Postgres.
Privacy is enforced **in the database**, not the app: row-level security ties every row
to `user_id`, so the queries in `db.py` physically cannot read another user's data even
if the app code were wrong. Optional email-OTP 2FA adds a one-time emailed code on top
of the password, with the preference stored in the user's own Supabase metadata (no
schema change needed).

## The non-obvious decision: a per-session Supabase client, NOT `@st.cache_resource`

The natural Streamlit instinct for "an expensive client object" is
`@st.cache_resource`, which memoises **one instance shared across the whole server
process — i.e. across every user**. For the Supabase client that is exactly wrong:

```
  @st.cache_resource  (WRONG here)            per-session (st.session_state)  (CORRECT)
  ┌───────────────────────────────┐          ┌───────────────────────────────┐
  │   ONE client, shared           │          │   one client PER session       │
  │                                │          │                                │
  │  user A logs in ─┐             │          │  user A → session_state.sb (A) │
  │  user B logs in ─┼─▶ same      │          │  user B → session_state.sb (B) │
  │                  │   client    │          │                                │
  │  B's auth clobbers A's auth    │          │  each carries its own auth     │
  │  → A now sees B's data         │          │  → RLS scopes each to its user │
  └───────────────────────────────┘          └───────────────────────────────┘
```

The Supabase client **carries authentication state**. A single shared client means the
last login wins and users start seeing each other's portfolios — a privacy breach. So
`_client()` stashes the client in `st.session_state` (per-session) instead, and
re-applies the saved tokens with `set_session(...)` if the client gets recreated within
a session.

- **Trade-off:** we re-create a client per session rather than once per process, and
  manage token restore ourselves.
- **Why it's the only correct choice:** the alternative leaks one user's data to
  another. Privacy beats the micro-optimisation, no contest.

## Why the cookie dance in `db.py`

`st.session_state` is wiped by a full browser refresh, which would log the user out on
every reload. So a 30-day refresh-token cookie (`sb_refresh`) survives the refresh, and
`restore_session()` re-authenticates from it at the top of each run. The CookieManager
is **reconstructed every run** under a stable key (not memoised), because that is what
makes the component reliably re-read the browser's cookies; and `persist_cookie()`
re-writes the cookie on every logged-in run rather than only at the login click, because
the rerun immediately after login can drop a write that happened only then. These are
the load-bearing comments in `init_cookies` / `persist_cookie` / `restore_session`.

## Related explanations

- [explanation-architecture.md](explanation-architecture.md) — where `store` sits in
  the pipeline (session load at the top, daily snapshot near the end).
- [explanation-two-page-architecture.md](explanation-two-page-architecture.md) — the
  auth gate that the Supabase mode puts in front of the dashboard.
- [reference-modules.md](reference-modules.md) — `storage.py` and `db.py` reference.

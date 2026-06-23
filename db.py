"""Supabase backend — email-login accounts + per-user cloud persistence.

Activated only when SUPABASE_URL + SUPABASE_ANON_KEY are present in st.secrets (and the
`supabase` package is installed). Otherwise the app falls back to local files (storage.py).

This module mirrors storage.py's function signatures so the app can do
``store = db if db.is_enabled() else storage`` and call ``store.<fn>(...)`` uniformly.
The current user is read from the (per-session) authenticated Supabase client, so
Postgres row-level security keeps each user's rows private.
"""

from __future__ import annotations
import json
from datetime import date, datetime, timezone

import pandas as pd
import streamlit as st

_COOKIE = "sb_refresh"  # browser cookie that survives a full page refresh
_COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days


# ─── Config / client ──────────────────────────────────────────────────────────

def is_enabled() -> bool:
    """True when Supabase is configured (secrets present) and importable."""
    try:
        if not (st.secrets.get("SUPABASE_URL") and st.secrets.get("SUPABASE_ANON_KEY")):
            return False
    except Exception:
        return False
    try:
        import supabase  # noqa: F401
        return True
    except ImportError:
        return False


def _client():
    """A per-session Supabase client (NOT cache_resource — that's shared across all
    users and would clobber each other's auth)."""
    if "sb" not in st.session_state:
        from supabase import create_client
        st.session_state.sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ANON_KEY"])
        sess = st.session_state.get("sb_session")
        if sess:  # restore auth if the client was recreated this session
            try:
                st.session_state.sb.auth.set_session(sess["access_token"], sess["refresh_token"])
            except Exception:
                pass
    return st.session_state.sb


# ─── Cookie (keeps you logged in across a full browser refresh) ───────────────

def init_cookies() -> None:
    """Construct the CookieManager once per run (canonical extra-streamlit-components
    usage). Reconstructing each run under a stable key — rather than memoising the
    instance — is what makes reads reliable: the component re-reads the browser's
    cookies every run and delivers them via its mount rerun. Call once at the top of
    the run, before any get/set/delete."""
    try:
        import extra_streamlit_components as stx
        st.session_state["_sb_ckmgr"] = stx.CookieManager(key="sb_cookies")
    except Exception:
        st.session_state["_sb_ckmgr"] = None


def _cookie_mgr():
    return st.session_state.get("_sb_ckmgr")


def _set_cookie(refresh_token: str | None) -> None:
    mgr = _cookie_mgr()
    if mgr is not None and refresh_token:
        try:
            mgr.set(_COOKIE, refresh_token, key="sb_ck_set",
                    max_age=_COOKIE_MAX_AGE, same_site="lax")
        except Exception:
            pass


def _clear_cookie() -> None:
    mgr = _cookie_mgr()
    if mgr is not None:
        try:
            mgr.delete(_COOKIE, key="sb_ck_del")  # raises KeyError if already absent
        except Exception:
            pass


def _read_cookie_native() -> str | None:
    """Native page-load cookie (Streamlit 1.42+). May be empty on Streamlit Cloud."""
    try:
        return st.context.cookies.get(_COOKIE)
    except Exception:
        return None


def _read_cookie() -> str | None:
    """Prefer the component's own read — it reliably sees the first-party cookie it set
    (same iframe/origin) — then fall back to the native page-load cookies."""
    mgr = _cookie_mgr()
    if mgr is not None:
        try:
            tok = mgr.get(_COOKIE)
            if tok:
                return tok
        except Exception:
            pass
    return _read_cookie_native()


def persist_cookie() -> None:
    """(Re)write the refresh-token cookie on every logged-in run. Doing it on a normal
    run — rather than only at the login click, which is immediately followed by a
    rerun that can drop the component's write — guarantees the cookie actually lands."""
    sess = st.session_state.get("sb_session")
    if sess and sess.get("refresh_token"):
        _set_cookie(sess["refresh_token"])


def restore_session() -> None:
    """If we're not logged in this session but a refresh-token cookie exists (e.g.
    after a browser refresh, which wipes st.session_state), re-authenticate from it."""
    if current_user():
        return
    token = _read_cookie()
    if not token:
        return
    try:
        res = _client().auth.refresh_session(token)
        if res and getattr(res, "session", None):
            _store_session(res)          # rotates the token; persist_cookie re-saves it
    except Exception:
        _clear_cookie()                  # token expired/invalid — drop it


# ─── Auth ─────────────────────────────────────────────────────────────────────

def current_user() -> dict | None:
    """{'id','email'} for the logged-in user, or None."""
    return st.session_state.get("sb_user")


def _uid() -> str | None:
    u = current_user()
    return u["id"] if u else None


def _store_session(res) -> None:
    if res and getattr(res, "session", None) and getattr(res, "user", None):
        st.session_state["sb_session"] = {
            "access_token": res.session.access_token,
            "refresh_token": res.session.refresh_token,
        }
        st.session_state["sb_user"] = {"id": res.user.id, "email": res.user.email}
        # 2FA preference lives in the user's own Supabase metadata (no table change).
        st.session_state["sb_2fa"] = bool((res.user.user_metadata or {}).get("twofa_email"))


def sign_in(email: str, password: str) -> tuple[str, str | None]:
    """Validate the password. Returns (status, error):
      'ok'    — logged in (no 2FA),
      '2fa'   — password correct but email 2FA is on; a code has been emailed,
      'error' — bad credentials / failure.
    """
    email = email.strip()
    try:
        res = _client().auth.sign_in_with_password({"email": email, "password": password})
        if not (res and res.session):
            return "error", "Login failed — check your email and password."
        if res.user and (res.user.user_metadata or {}).get("twofa_email"):
            # Password is valid, but this account requires a second factor. Don't grant
            # access yet — email a one-time code and wait for verify_email_otp().
            sent, otp_err = _send_email_otp(email)
            if not sent:
                return "error", otp_err or "Couldn't send the email code — try again in a minute."
            st.session_state["_2fa_email"] = email
            return "2fa", None
        _store_session(res)
        return "ok", None
    except Exception as e:
        return "error", _friendly(e)


def _send_email_otp(email: str) -> tuple[bool, str | None]:
    """Email a 6-digit one-time code to an existing user (no new account).
    Returns (sent, error) so the real Supabase reason (rate limit, SMTP, etc.) surfaces."""
    try:
        _client().auth.sign_in_with_otp(
            {"email": email.strip(), "options": {"should_create_user": False}})
        return True, None
    except Exception as e:
        return False, _friendly(e)


def resend_email_otp(email: str) -> tuple[bool, str | None]:
    return _send_email_otp(email)


def verify_email_otp(email: str, token: str) -> tuple[bool, str | None]:
    """Second factor: verify the emailed code and complete login."""
    try:
        res = _client().auth.verify_otp(
            {"email": email.strip(), "token": (token or "").strip(), "type": "email"})
        if res and res.session:
            _store_session(res)
            st.session_state.pop("_2fa_email", None)
            return True, None
        return False, "Invalid or expired code."
    except Exception as e:
        return False, _friendly(e)


def twofa_enabled() -> bool:
    """Whether the logged-in user requires an email code at login."""
    return bool(st.session_state.get("sb_2fa"))


def set_twofa(enabled: bool) -> tuple[bool, str | None]:
    """Turn email-2FA on/off for the current user (stored in their Supabase metadata)."""
    try:
        _client().auth.update_user({"data": {"twofa_email": bool(enabled)}})
        st.session_state["sb_2fa"] = bool(enabled)
        return True, None
    except Exception as e:
        return False, _friendly(e)


def sign_up(email: str, password: str) -> tuple[bool, str | None]:
    try:
        res = _client().auth.sign_up({"email": email.strip(), "password": password})
        if res and res.session:                 # email confirmation off → logged in
            _store_session(res)
            return True, None
        return False, "Account created — check your email to confirm, then log in."
    except Exception as e:
        return False, _friendly(e)


def sign_out() -> None:
    try:
        _client().auth.sign_out()
    except Exception:
        pass
    _clear_cookie()
    for k in ("sb", "sb_session", "sb_user", "sb_2fa", "_2fa_email"):
        st.session_state.pop(k, None)


def _friendly(e: Exception) -> str:
    msg = str(e)
    low = msg.lower()
    if "Invalid login" in msg:
        return "Invalid email or password."
    if "already registered" in low:
        return "That email is already registered — log in instead."
    if "Password should be" in msg:
        return "Password too short (min 6 characters)."
    if "rate limit" in low or "after" in low and "second" in low:
        return ("Email rate limit hit (Supabase's built-in email is throttled). "
                "Wait a minute, or set up custom SMTP to remove the limit.")
    if "otp" in low and "disabled" in low or "signups not allowed" in low:
        return "Email codes aren't enabled for this project (check Auth settings)."
    if "smtp" in low or "error sending" in low:
        return "The email couldn't be sent — configure SMTP in Supabase Auth settings."
    return msg


def render_auth() -> None:
    """Branded login / sign-up gate shown when no user is signed in."""
    st.markdown(
        '<div class="hero"><div class="brand-title" style="font-size:1.6rem;text-align:center;">PORTFOLIO</div>'
        '<div class="hero-sub">Sign in to your private dashboard</div></div>',
        unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1.4, 1])
    with mid:
        if st.session_state.get("_2fa_email"):     # mid-login: awaiting the email code
            _render_2fa_step()
            return
        tab_login, tab_signup = st.tabs(["Log in", "Sign up"])
        with tab_login:
            e = st.text_input("Email", key="li_email")
            p = st.text_input("Password", type="password", key="li_pw")
            if st.button("Log in", width="stretch", key="li_btn"):
                status, err = sign_in(e, p)
                if status in ("ok", "2fa"):
                    st.rerun()                      # '2fa' → reruns into the code step
                else:
                    st.error(err)
        with tab_signup:
            e2 = st.text_input("Email", key="su_email")
            p2 = st.text_input("Password (min 6 chars)", type="password", key="su_pw")
            if st.button("Create account", width="stretch", key="su_btn"):
                ok, err = sign_up(e2, p2)
                if ok:
                    st.rerun()
                else:
                    (st.success if "confirm" in (err or "") else st.error)(err)
        st.caption("🔒 Your portfolio is stored privately under your account (row-level security).")


def _render_2fa_step() -> None:
    """Second-factor screen: the user has passed the password and we emailed a code."""
    email = st.session_state.get("_2fa_email", "")
    st.info(f"Two-factor: enter the 6-digit code we emailed to **{email}**.")
    code = st.text_input("Email code", key="twofa_code", max_chars=6,
                         placeholder="123456")
    if st.button("Verify & log in", width="stretch", key="twofa_verify"):
        ok, err = verify_email_otp(email, code)
        if ok:
            st.rerun()
        else:
            st.error(err)
    c1, c2 = st.columns(2)
    if c1.button("Resend code", width="stretch", key="twofa_resend"):
        sent, err = resend_email_otp(email)
        st.success("New code sent.") if sent else st.error(err or "Couldn't resend — wait a minute.")
    if c2.button("← Back", width="stretch", key="twofa_back"):
        st.session_state.pop("_2fa_email", None)
        st.rerun()


# ─── Per-user storage (mirrors storage.py) ───────────────────────────────────

def _get_state(*cols: str) -> dict:
    uid = _uid()
    if not uid:
        return {}
    try:
        res = _client().table("user_state").select(",".join(cols)).eq("user_id", uid).execute()
        return res.data[0] if res.data else {}
    except Exception:
        return {}


def _put_state(**fields) -> None:
    uid = _uid()
    if not uid:
        return
    try:
        _client().table("user_state").upsert(
            {"user_id": uid, "updated_at": datetime.now(timezone.utc).isoformat(), **fields}
        ).execute()
    except Exception:
        pass


# last session (portfolio)
def save_session(raw: pd.DataFrame) -> None:
    records = json.loads(raw.to_json(orient="records", date_format="iso"))
    meta = {
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "rows": len(raw),
        "accounts": sorted(raw["account"].unique().tolist()) if "account" in raw else [],
    }
    _put_state(portfolio=records, portfolio_meta=meta)


def load_session() -> pd.DataFrame | None:
    recs = _get_state("portfolio").get("portfolio")
    if not recs:
        return None
    df = pd.DataFrame(recs)
    if df.empty:
        return None
    if "purchase_date" in df.columns:
        df["purchase_date"] = pd.to_datetime(df["purchase_date"], errors="coerce")
    return df


def session_meta() -> dict:
    return _get_state("portfolio_meta").get("portfolio_meta") or {}


# watchlist / overrides
def load_watchlist() -> list[str]:
    return _get_state("watchlist").get("watchlist") or []


def save_watchlist(tickers: list[str]) -> None:
    _put_state(watchlist=sorted(set(tickers)))


def load_overrides() -> dict:
    return _get_state("overrides").get("overrides") or {}


def save_overrides(overrides: dict) -> None:
    _put_state(overrides=overrides)


# snapshots
def load_snapshots() -> list[dict]:
    uid = _uid()
    if not uid:
        return []
    try:
        res = (_client().table("snapshots").select("*")
               .eq("user_id", uid).order("snap_date").execute())
    except Exception:
        return []
    return [{
        "date": r["snap_date"], "saved_at": r.get("saved_at"),
        "total_value": r.get("total_value"), "total_cost": r.get("total_cost"),
        "total_pnl": r.get("total_pnl"), "n_holdings": r.get("n_holdings"),
        "holdings": r.get("holdings") or {},
    } for r in (res.data or [])]


def save_snapshot(totals: dict, holdings: pd.DataFrame, when: str | None = None) -> bool:
    uid = _uid()
    if not uid:
        return False
    per_stock = {}
    for _, r in holdings.iterrows():
        v = r.get("Current Value (₹)")
        if pd.notna(v):
            per_stock[r["Ticker"]] = round(float(v), 2)

    def _n(x):
        return None if (x is None or (isinstance(x, float) and pd.isna(x))) else round(float(x), 2)

    row = {
        "user_id": uid, "snap_date": when or date.today().isoformat(),
        "total_value": _n(totals.get("value")), "total_cost": _n(totals.get("cost")),
        "total_pnl": _n(totals.get("pnl")), "n_holdings": int(totals.get("n_holdings", 0)),
        "holdings": per_stock, "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        _client().table("snapshots").upsert(row).execute()  # PK (user_id, snap_date)
        return True
    except Exception:
        return False


def snapshots_df() -> pd.DataFrame:
    snaps = load_snapshots()
    if not snaps:
        return pd.DataFrame()
    df = pd.DataFrame([{
        "date": pd.to_datetime(s["date"]),
        "Total Value": s.get("total_value"),
        "Total Cost": s.get("total_cost"),
        "Total P&L": s.get("total_pnl"),
        "Holdings": s.get("n_holdings"),
    } for s in snaps])
    return df.sort_values("date").reset_index(drop=True)


def auto_snapshot_if_new(totals: dict, holdings: pd.DataFrame) -> bool:
    today = date.today().isoformat()
    if any(s.get("date") == today for s in load_snapshots()):
        return False
    return save_snapshot(totals, holdings)

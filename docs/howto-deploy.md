# How-to — Deploy

This covers the two things you can put online: the **Streamlit app** (so anyone
can use it with no install) and the **standalone landing page** (the marketing
page that links to the app). They're independent — deploy one, the other, or
both.

## Prerequisites

- A free [GitHub](https://github.com) account.
- The repo pushed to GitHub. If you haven't yet:
  ```bash
  git remote add origin https://github.com/<you>/portfolio-dashboard.git
  git push -u origin main
  ```
  Public is fine — there are no secrets in the code and your personal `data/`
  folder is gitignored. Full walkthrough in [`DEPLOY.md`](../DEPLOY.md).

---

## Part 1 — The Streamlit app (Streamlit Community Cloud)

This gives every visitor a private session — their upload never touches yours.

### Steps

1. Go to <https://share.streamlit.io> and **sign in with GitHub**.
2. **Create app → Deploy a public app from GitHub**, then set:
   - **Repository:** `<you>/portfolio-dashboard`
   - **Branch:** `main`
   - **Main file path:** `app.py`
3. Open **Advanced settings → Secrets** and paste exactly:
   ```toml
   PORTFOLIO_MULTIUSER = "1"
   ```
   This is **required for a shared link** — it isolates each visitor so no one
   can see another person's holdings, snapshots, or watchlist. Without it the app
   uses one shared `data/` folder (fine for personal local use, not for sharing).
4. Click **Deploy**. After ~2 minutes you get a URL like
   `https://<something>.streamlit.app`.

### Verification

Open the URL in a private/incognito window, upload a broker file, and confirm the
Overview populates. Open it again in a second browser and confirm that session
starts empty — that proves `PORTFOLIO_MULTIUSER` isolation is working.

### Troubleshooting

- **Everyone sees the same data.** The `PORTFOLIO_MULTIUSER = "1"` secret is
  missing or misspelt. Re-check it under Advanced settings → Secrets.
- **First visit after idle is slow (~30 s).** Free-tier apps nap after
  inactivity and take a moment to wake. Normal.
- **Large portfolio briefly shows no prices.** Yahoo Finance rate-limited the
  first burst; the in-app **🔄 Refresh data** button retries.

See [`DEPLOY.md`](../DEPLOY.md) for the full version, including updating later
(just `git push` — Streamlit redeploys automatically).

---

## Part 2 — The landing page (GitHub Pages)

`index.html` is a standalone marketing page with no build step. GitHub Pages
serves it straight from the repo.

### Steps

1. In the GitHub repo, go to **Settings → Pages**.
2. Under **Build and deployment**, set **Source: Deploy from a branch**, then
   **Branch: `main`** and folder **`/ (root)`**. Save.
3. After about a minute, the page is live at
   `https://<you>.github.io/portfolio-dashboard/` — for this project,
   <https://capraaghav.github.io/portfolio-dashboard/>.

### Verification

Open the Pages URL and confirm the landing page renders, then click **Launch
dashboard** / **Open app** and confirm it lands on the live Streamlit app from
Part 1.

### Troubleshooting

- **404 right after enabling Pages.** The first build takes ~1 minute. Wait, then
  reload.
- **"Launch dashboard" goes to the wrong place.** `APP_URL` in `index.html`
  still points at the placeholder — see the URL wiring note below.

For a focused walkthrough of editing and hosting the landing page, see
[How-to: host the landing page](howto-host-landing-page.md).

---

## Wiring the two together

The two deployments reference each other by URL, so point them at the real
addresses once both are live:

- **`APP_URL`** in [`index.html`](../index.html) (a `const` in the inline
  `<script>` near the bottom) must point at your deployed **Streamlit** URL — it's
  where every "Launch dashboard" / "Open app" link goes.
- **`LANDING_URL`** in [`app.py`](../app.py) must point at your deployed **GitHub
  Pages** URL — it's the "back to the landing page" link inside the app.

Update both, commit, and push.

## See also

- [Module reference](reference-modules.md)
- [Architecture](explanation-architecture.md)
- [How-to: host the landing page](howto-host-landing-page.md)

# Deploy as a free hosted link (Streamlit Community Cloud)

This gives anyone a URL they can open with **no install** — perfect for a Windows
PC or anyone non-technical. Each visitor's upload stays private to their own
session (see `PORTFOLIO_MULTIUSER` below).

## 1. Put the code on GitHub
1. Make a free account at <https://github.com> if you don't have one.
2. Create a new **empty** repo named e.g. `portfolio-dashboard`
   (**Public is fine** — there are no secrets in the code, and your personal
   `data/` folder is gitignored so your holdings are never uploaded).
3. From this folder, connect and push (replace `<you>` with your GitHub username):
   ```bash
   git remote add origin https://github.com/<you>/portfolio-dashboard.git
   git push -u origin main
   ```
   GitHub will prompt you to sign in / authorize in the browser.

## 2. Deploy on Streamlit Community Cloud (free)
1. Go to <https://share.streamlit.io> and **sign in with GitHub**.
2. Click **Create app → Deploy a public app from GitHub**.
3. Fill in:
   - **Repository:** `<you>/portfolio-dashboard`
   - **Branch:** `main`
   - **Main file path:** `app.py`
4. Open **Advanced settings → Secrets** and paste exactly this line:
   ```toml
   PORTFOLIO_MULTIUSER = "1"
   ```
   This makes every visitor's data private to their own session.
5. Click **Deploy**. After ~2 minutes you get a URL like
   `https://<something>.streamlit.app`.

## 3. Share the URL
Send the link to anyone. They open it, upload their own broker file — done.
Nothing to install on their side.

---

### Important
- **`PORTFOLIO_MULTIUSER = "1"` is required for sharing.** It isolates each
  visitor so no one can see another person's holdings, snapshots, or watchlist.
  Without it the app uses one shared `data/` folder (fine for personal local use,
  **not** for a shared link).
- **Updating later:** just `git push` new commits — Streamlit redeploys automatically.
- **Free-tier sleep:** the app naps after inactivity; the first visit after a nap
  takes ~30 seconds to wake, then it's instant.
- **Prices:** live prices come from Yahoo Finance. A very large portfolio on first
  load may briefly rate-limit; the in-app **🔄 Refresh data** button retries.

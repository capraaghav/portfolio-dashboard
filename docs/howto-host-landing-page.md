# How-to — Host and update the landing page

`index.html` is the standalone marketing page that links to the live app. It has
no build step: edit the file, push to `main`, and GitHub Pages rebuilds it. This
page covers editing, the one URL constant you'll change most, how the favicon and
social-preview metadata work, and the one gotcha when you first enable Pages.

For first-time Pages setup, see Part 2 of [How-to: deploy](howto-deploy.md).

## Prerequisites

- The repo on GitHub with **Pages** enabled (Settings → Pages → Deploy from a
  branch → `main` / root). One-time; see [How-to: deploy](howto-deploy.md).
- A local clone you can edit and push.

## Update the page

1. Edit [`index.html`](../index.html). It's plain HTML/CSS with one small inline
   `<script>` at the bottom — no toolchain, no dependencies.
2. Open the file in a browser locally to preview your change.
3. Commit and push to `main`:
   ```bash
   git add index.html
   git commit -m "Update landing page"
   git push
   ```
4. GitHub Pages auto-rebuilds in about a minute.

### Verification

Reload `https://capraaghav.github.io/portfolio-dashboard/` (hard-refresh to skip
the cache) and confirm your edit shows.

## Change where the buttons point (`APP_URL`)

Every "Launch dashboard" / "Open app" button is wired from a single constant in
the inline `<script>` near the bottom of `index.html`:

```js
const APP_URL  = "https://portfolio-dashboard-1.streamlit.app/";
const REPO_URL = "https://github.com/capraaghav/portfolio-dashboard";
```

A tiny script copies `APP_URL` into every link marked `data-app-url`, and
`REPO_URL` into the footer GitHub link. To repoint the buttons, change `APP_URL`
to your deployed Streamlit URL (and `REPO_URL` to your repo), then push. Nothing
else in the markup needs touching.

> The reverse link — the app's "back to landing page" link — lives in `app.py`
> as `LANDING_URL`. Keep the two consistent. See
> [How-to: deploy](howto-deploy.md#wiring-the-two-together).

## Favicon and social-preview metadata

Both live in the `<head>` of `index.html`:

- **Favicon** — an inline SVG data-URI `<link rel="icon" ...>`: a dark rounded
  square with a gold circle. No image file is served; the icon is the markup
  itself, so editing the SVG path changes the favicon. (Hard-refresh to see it;
  browsers cache favicons aggressively.)
- **Open Graph / Twitter cards** — the `og:*` and `twitter:*` `<meta>` tags
  control the title, description, and link preview when the page is shared. Note
  `og:url` is hard-coded to `https://capraaghav.github.io/portfolio-dashboard/`;
  update it if you host at a different address.

## Troubleshooting

- **404 right after enabling Pages.** The first build takes ~1 minute. Wait and
  reload — it's not a misconfiguration.
- **Edit pushed but the page looks unchanged.** Pages serves a cached copy
  briefly; hard-refresh (Cmd/Ctrl+Shift+R) or wait a minute for the rebuild.
- **Buttons go to the old/placeholder app.** `APP_URL` wasn't updated — see
  above.
- **Favicon didn't change.** Browser favicon cache; hard-refresh or try a
  private window.
- **Link preview shows stale text.** Social platforms cache OG metadata; use the
  platform's debugger (or wait) after updating the `og:*` tags.

## See also

- [How-to: deploy](howto-deploy.md) — both deployments end to end.
- [Module reference](reference-modules.md)
- [Architecture](explanation-architecture.md)

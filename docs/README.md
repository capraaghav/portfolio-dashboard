# Documentation

Organised by the [Diátaxis](https://diataxis.fr) framework — four kinds of docs for
four reader needs.

## Tutorials — learning-oriented

- [Getting started](tutorial-getting-started.md) — install, run, and see your portfolio in three steps.

## How-to guides — task-oriented

- [Add a broker format](howto-add-a-broker.md) — support a new broker export.
- [Deploy](howto-deploy.md) — the Streamlit app (Community Cloud) + the landing page (GitHub Pages).
- [Setup (local dev)](howto-setup.md) — first-time install and run.
- [Host / update the landing page](howto-host-landing-page.md) — edit, push, and the `APP_URL` wiring.

## Reference — information-oriented

- [Modules](reference-modules.md) — every Python module, its responsibility, and public surface.
- [Broker formats](reference-broker-formats.md) — supported exports + the canonical parsed schema.
- [Configuration](reference-config.md) — backend modes, sidebar toggles, cache TTLs, the two URLs.

## Explanation — understanding-oriented

- [Architecture](explanation-architecture.md) — the end-to-end data flow.
- [Two-page architecture](explanation-two-page-architecture.md) — why the app and landing are separate pages.
- [Storage backends](explanation-storage-backends.md) — local vs multi-user vs Supabase.
- [Indian-market specifics](explanation-indian-market-specifics.md) — NSE/BSE, ISIN, tax, benchmarks.

---

See also the top-level [README](../README.md), [product/](../product/), [design system](design-system.md) (+ [CSS tokens](design-system/styles.css)), [setup](howto-setup.md).

# GitHub Pages documentation site

Great Generator includes a static documentation landing page at `docs/index.html`.

Recommended public URL:

https://greatdatalabs.github.io/great-generator/

## Enable the site

The repository includes `.github/workflows/pages.yml`, which enables GitHub Pages when allowed and publishes the `docs/` folder through GitHub Actions.

In the GitHub repository:

1. Open **Settings**.
2. Open **Pages**.
3. For **Build and deployment**, choose **GitHub Actions**.
4. Save the setting if GitHub asks you to confirm.
5. Open **Actions** and run **Publish documentation site** if it does not start automatically.

GitHub will publish the site after the Pages workflow completes.

### Alternative branch-based setup

If you prefer branch-based Pages instead of Actions:

1. Open **Settings**.
2. Open **Pages**.
3. For **Build and deployment**, choose **Deploy from a branch**.
4. Select branch **main**.
5. Select folder **/docs**.
6. Save.

## What the page is for

The page is a demo-friendly front door for users who want to understand:

- what Great Generator is
- when to use it
- how to install it
- how Pandas and Spark usage differ
- how DataFrame-first output works
- how cloud paths work in Spark environments
- how to find deeper repository documentation

## Maintenance notes

- Keep `docs/index.html` focused on the first user journey.
- Keep deeper technical details in markdown files under `docs/` and the GitHub Wiki.
- Avoid untested performance claims. Use environment-dependent scale language for large datasets.
- Update the Documentation URL in `pyproject.toml` when preparing a future PyPI release.

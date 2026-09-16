# Search Discovery and SEO Maintenance

Great Generator publishes a static GitHub Pages site at:

https://greatdatalabs.github.io/great-generator/

This page explains how search discovery files are maintained for the project website.

## What SEO files exist

The public GitHub Pages root is the `docs/` directory. These files are published with the site:

- `docs/sitemap.xml` — XML sitemap for important public HTML pages.
- `docs/robots.txt` — search crawler policy that allows crawling and points to the sitemap.
- `docs/googled8bf242e96d63743.html` — Google Search Console HTML verification file.
- `scripts/generate_sitemap.py` — standard-library sitemap regeneration script.
- `scripts/submit_indexnow.py` — optional IndexNow submission helper.

Keep search-console verification files in place after verification succeeds so ownership remains valid.

## How to regenerate the sitemap

Run this command from the repository root:

```bash
python scripts/generate_sitemap.py
```

The script discovers public HTML pages under `docs/`, skips internal folders such as assets, ADRs, and RFCs, normalizes GitHub Pages URLs, and writes:

```text
docs/sitemap.xml
```

## How to update robots.txt

`docs/robots.txt` should continue to allow public documentation pages and reference the sitemap:

```text
User-agent: *
Allow: /

Sitemap: https://greatdatalabs.github.io/great-generator/sitemap.xml
```

Do not block important documentation pages unless there is a clear reason.

## Submit the sitemap to Google Search Console

1. Open Google Search Console.
2. Add or select the property for `https://greatdatalabs.github.io/` or the URL-prefix property for `https://greatdatalabs.github.io/great-generator/`.
3. Open **Sitemaps**.
4. Submit:

```text
https://greatdatalabs.github.io/great-generator/sitemap.xml
```

5. Re-submit or refresh after major documentation changes.

## Submit the sitemap to Bing Webmaster Tools

1. Open Bing Webmaster Tools.
2. Add or select the site property.
3. Open **Sitemaps**.
4. Submit:

```text
https://greatdatalabs.github.io/great-generator/sitemap.xml
```

5. Use Bing's URL inspection tools for important new pages when needed.

## Optional Bing IndexNow setup

IndexNow can be used to notify participating search engines about changed URLs. Great Generator includes an optional helper script, but it does not run automatically.

Requirements:

- Generate an IndexNow key in Bing Webmaster Tools or another supported IndexNow provider.
- Store the key in an environment variable, not in source control.
- Publish the required key file at the public site root if your IndexNow setup requires key-file verification.

Example:

```bash
set INDEXNOW_KEY=your-indexnow-key
python scripts/submit_indexnow.py https://greatdatalabs.github.io/great-generator/schema-generation/
```

PowerShell example:

```powershell
$env:INDEXNOW_KEY = "your-indexnow-key"
python scripts/submit_indexnow.py "https://greatdatalabs.github.io/great-generator/schema-generation/"
```

Only submit changed public URLs. Do not hardcode secrets.

## Metadata checklist

Each major HTML page should have:

- Descriptive `<title>`.
- Useful `<meta name="description">`.
- Canonical URL matching the published page URL.
- Open Graph title, description, type, URL, and site name.
- Twitter/X card title and description.
- Social preview image metadata using `https://greatdatalabs.github.io/great-generator/assets/og.png`.
- Internal links back to home, getting started, API reference, GitHub, and PyPI.

The homepage also includes JSON-LD structured data for `SoftwareSourceCode` and `SoftwareApplication`.

## Release SEO checklist

- [ ] New documentation page added to navigation
- [ ] New documentation page included in sitemap
- [ ] Page has title and meta description
- [ ] Page has canonical URL
- [ ] Internal links point to the page
- [ ] Sitemap regenerated
- [ ] robots.txt still references the sitemap
- [ ] Sitemap submitted or refreshed in Google Search Console
- [ ] Sitemap submitted or refreshed in Bing Webmaster Tools

## Notes

Great Generator creates synthetic data. It does not anonymize, mask, de-identify, or transform production records.

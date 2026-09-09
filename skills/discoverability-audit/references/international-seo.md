# International SEO: Evidence & Sources

Detailed evidence backing the International SEO & Localization section of the Discoverability & Localization checks.

---

## Hreflang Placement & Reciprocal Requirements

Google supports three equivalent methods: HTML `<link>` in `<head>`, HTTP `Link` headers, and XML sitemap `<xhtml:link>` elements. Google combines signals from both HTML and sitemaps. If the same language-region pair points to different URLs across methods, Google drops that pair rather than guessing.

Every page must include itself (self-referencing) in the hreflang set. If page X links to page Y, page Y must link back to page X (reciprocal return tag). Missing self-referencing or return tags causes Google to drop the cluster.

- [Google Search Central: Localized Versions](https://developers.google.com/search/docs/specialty/international/localized-versions)

---

## Language & Region Codes

Language must strictly follow ISO 639-1 (2-letter code). Region must follow ISO 3166-1 Alpha 2 (2-letter code). Format: `language[-script][-region]`.

Common errors flagged by `discoverability_check.py`:
- `en-UK` -> Invalid region code (must be `en-GB`)
- `eng` -> Invalid language code (must be `en`)
- `jp` -> Invalid language code (must be `ja`)

---

## Canonicalization & i18n

- **Self-Referencing Canonicals:** Each locale page must canonical to itself. Never use cross-locale canonicals (e.g. French page canonicalizing to English page) — this suppresses the non-canonical locale entirely from indexation.
- **Canonical Overrides Hreflang:** If canonical points to a different host or URL outside the hreflang cluster, Google ignores the hreflang annotation.

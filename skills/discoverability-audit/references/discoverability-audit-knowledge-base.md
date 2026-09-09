# DISCOVERABILITY-AUDIT KNOWLEDGE BASE

## Table of Contents

- [C1. Homepage reachability](#c1-homepage-reachability)
- [C2. robots.txt AI-crawler access (RFC 9309)](#c2-robotstxt-ai-crawler-access-rfc-9309)
- [C3. Differential UA treatment](#c3-differential-ua-treatment)
- [C4. noindex / X-Robots-Tag](#c4-noindex-x-robots-tag)
- [C5. Canonical consistency (corroborated)](#c5-canonical-consistency-corroborated)
- [C6. Rendering risk](#c6-rendering-risk)
- [Inconclusive handling](#inconclusive-handling)
- [Crawler Taxonomy & Impact Matrix](#crawler-taxonomy-impact-matrix)
- [Key Audit Rules](#key-audit-rules)
- [1. robots.txt & Access Directives (RFC 9309)](#1-robotstxt-access-directives-rfc-9309)
  - [User-Agent Matching Precedence](#user-agent-matching-precedence)
  - [Path Syntax Rules](#path-syntax-rules)
  - [Critical AI Distinctions](#critical-ai-distinctions)
- [2. Canonicalization & Consolidation](#2-canonicalization-consolidation)
  - [Canonical Rules](#canonical-rules)
  - [AI Search Impact](#ai-search-impact)
- [3. XML Sitemaps & Discovery Aids](#3-xml-sitemaps-discovery-aids)
  - [Sitemaps Standards](#sitemaps-standards)
  - [`llms.txt` Role](#llmstxt-role)
- [4. Rendering & Content Extractability](#4-rendering-content-extractability)
  - [Server-Side Rendering (SSR) vs Client-Side Rendering (CSR)](#server-side-rendering-ssr-vs-client-side-rendering-csr)
- [5. Snippet Controls for Generative AI](#5-snippet-controls-for-generative-ai)

---

This document contains all mandatory rules, schemas, and taxonomies required for this skill.



========================================================================
=== SOURCE FILE: discoverability-contracts.md ===
========================================================================

# Discoverability Audit — Check Contracts

Every check in this skill states what it measures, what evidence is required,
what does **not** constitute a defect, and how severity is assigned. Checks
never report a finding without direct evidence gathered during this run.

## C1. Homepage reachability
- **Measures:** HTTP status of the homepage fetch.
- **Defect:** Non-200 response (fetch failures are `status: inconclusive`, not defects).
- **Severity:** `critical` on non-200 — AI crawlers cannot retrieve any content.
- **Not a defect:** Slow but successful responses (latency is out of scope).

## C2. robots.txt AI-crawler access (RFC 9309)
- **Measures:** Longest-match robots.txt evaluation for GPTBot, OAI-SearchBot,
  ClaudeBot, PerplexityBot, Google-Extended against `/`, honoring
  `User-agent: *` fallback groups per RFC 9309 semantics.
- **Defect:** A rule disallows a listed AI crawler where a generic browser
  group would be allowed.
- **Severity:** `high` (downgraded to `medium` if only one minor crawler is blocked).
- **Not a defect:** No robots.txt at all (absence means allow-all); blocking
  aggressive non-search scrapers; blocking paths the homepage doesn't rely on.

## C3. Differential UA treatment
- **Measures:** Whether AI-crawler user-agents receive materially different
  responses than a generic browser UA (status or body length).
- **Defect:** Consistent, meaningful divergence across UAs.
- **Severity:** `high`, confidence `medium` (CDN quirks can cause false
  divergence; hence medium confidence and worded as "treatment differs").

## C4. noindex / X-Robots-Tag
- **Measures:** `meta robots` and `X-Robots-Tag` headers for `noindex`/`none`.
- **Defect:** Directive present on a public page.
- **Severity:** `critical` — an explicit machine instruction to be excluded.

## C5. Canonical consistency (corroborated)
- **Measures:** Canonical link target vs. requested host, cross-checked
  against redirect behavior and sitemap entries.
- **Defect:** Reported **only when** the canonical target is corroborated by
  a second signal (redirect chain or sitemap). Canonical alone is a hint,
  not a verdict.
- **Severity:** `medium`, confidence `high` (because corroborated).

## C6. Rendering risk
- **Measures:** Visible word count of the initial HTML and presence of an
  empty SPA root container.
- **Defect:** Very low word count **plus** SPA root marker → high (rendering
  risk for non-JS crawlers). Very low word count without the marker → low,
  phrased as a verification prompt rather than a proven gap.
- **Not a defect:** This check never claims the page "cannot render" — only
  what is (or is not) present in the initial HTML, which is what non-JS
  crawlers actually see.

## Inconclusive handling
If the homepage cannot be fetched, the script returns
`status: "inconclusive"` with zero findings. The orchestrator surfaces this
status; it is never interpreted as "clean".


========================================================================
=== SOURCE FILE: crawler-matrix-reference.md ===
========================================================================

# Canonical AI Crawler Matrix & Platform Semantics Reference

Understanding the distinct purposes and operational impacts of AI web crawlers is essential for avoiding false-positive audit findings.

---

## Crawler Taxonomy & Impact Matrix

| User-Agent Token | Operator | Operational Role | Business Impact of Blocking | Severity if Disallowed |
| :--- | :--- | :--- | :--- | :--- |
| **`OAI-SearchBot`** | OpenAI | **Retrieval** (SearchGPT / ChatGPT Search) | The brand will NOT be indexed or cited in ChatGPT real-time web search answers. | `critical` / `high` |
| **`Claude-SearchBot`** | Anthropic | **Retrieval** (Claude Search) | The site cannot be retrieved for real-time web grounding inside Claude conversations. | `high` |
| **`PerplexityBot`** | Perplexity AI | **Retrieval** (Perplexity Search Index) | The site is excluded from Perplexity's core search index and citation cards. | `critical` / `high` |
| **`anthropic-ai`** | Anthropic | **Retrieval** (Live Search) | General live Anthropic retrieval system excluded from scraping public routes. | `high` |
| **`ChatGPT-User`** | OpenAI | **User-Initiated Fetch** | An end-user explicitly asking ChatGPT to inspect a URL will receive a fetch error. | `medium` |
| **`GPTBot`** | OpenAI | **Training** (Foundation Pre-training) | The brand's data is omitted from offline model pre-training corpora. (Intentional privacy opt-out). | `info` / `low` |
| **`ClaudeBot`** | Anthropic | **Training** (Foundation Pre-training) | The brand's data is omitted from Claude offline model training. (Intentional privacy opt-out). | `info` / `low` |
| **`Google-Extended`** | Google | **Training** (Gemini / Vertex AI) | Excludes content from Gemini foundation training. (Does NOT block Google Search or Google AI Overviews). | `info` / `low` |
| **`Applebot-Extended`** | Apple | **Training** (Apple Intelligence) | Excludes content from Apple Intelligence foundation model training. | `info` / `low` |
| **`CCBot`** | Common Crawl | **Training** (Open Corpora) | Excludes site from Common Crawl dumps used by open-source research. | `info` / `low` |

---

## Key Audit Rules

1. **Never Conflate Training with Retrieval:**
   - Blocking `GPTBot` or `Google-Extended` is a legitimate copyright/governance choice. It MUST NOT be reported as a critical AI search discovery defect.
   - Only blocking retrieval crawlers (`OAI-SearchBot`, `Claude-SearchBot`, `PerplexityBot`) creates an active visibility outage.
2. **Google AI Overviews (AIO):**
   - Uses standard `Googlebot` crawling and indexing pipelines. `Google-Extended` disallows do NOT prevent Google Search or AI Overviews from citing a page.



========================================================================
=== SOURCE FILE: seo-foundations.md ===
========================================================================

# Technical SEO Foundations for AI Retrieval

This reference synthesizes essential technical SEO mechanisms and their causal impact on AI discovery, indexing, and retrieval.

---

## 1. robots.txt & Access Directives (RFC 9309)

robots.txt governs **crawling access**, not indexing.

### User-Agent Matching Precedence
- Per RFC 9309, specific user-agent tokens (e.g. `User-agent: OAI-SearchBot`) **override** the generic wildcard group (`User-agent: *`).
- Longest path match wins within a group; `Allow` wins equal-length ties.

### Path Syntax Rules
```txt
# Blocks /admin, /admin/, /admin123
Disallow: /admin

# Blocks ONLY paths under /admin/
Disallow: /admin/

# Wildcards
Disallow: /*.pdf$    # Blocks all PDF files
Disallow: /*/temp/   # Blocks temp directory at any depth
```

### Critical AI Distinctions
- **Retrieval Bots:** `OAI-SearchBot`, `Claude-SearchBot`, `PerplexityBot`. Blocking these prevents live citations in generative answers.
- **Training Bots:** `GPTBot`, `ClaudeBot`, `Google-Extended`, `Applebot-Extended`, `CCBot`. Blocking these prevents model training but does not affect search visibility.

---

## 2. Canonicalization & Consolidation

The canonical link element (`<link rel="canonical" href="...">`) signals the authoritative primary URL for duplicate or parameterized content.

### Canonical Rules
- **Self-Referential Canonical:** Every unique indexable page should declare a self-referential canonical URL.
- **Protocol & Host Uniformity:** Consistently specify HTTPS and the chosen apex/www domain format.
- **Header Alternative:** Use `Link: <https://example.com/file.pdf>; rel="canonical"` for non-HTML assets.

### AI Search Impact
AI assistants consolidate citations onto the declared canonical target. Mismatches between sitemaps and markup create citation ambiguity.

---

## 3. XML Sitemaps & Discovery Aids

XML sitemaps provide an explicit inventory of indexable URLs.

### Sitemaps Standards
- Maximum 50,000 URLs and 50 MB per sitemap file.
- Use `<sitemapindex>` for larger multi-category sites.
- Specify accurate `<lastmod>` ISO 8601 timestamps (only update when material content changes).

### `llms.txt` Role
- `llms.txt` is an optional Markdown feed for community LLM tools.
- **Google does NOT use `llms.txt`** for AI Overviews or AI Mode (standard web indexing is used).
- Its absence is NEVER an SEO or AI discoverability defect.

---

## 4. Rendering & Content Extractability

### Server-Side Rendering (SSR) vs Client-Side Rendering (CSR)
- **SSR / SSG:** Initial HTML contains full semantic markup and text. Safest for all AI crawlers.
- **CSR (Client-Side SPA):** Initial HTML contains minimal text (`<div id="root"></div>`) requiring JavaScript execution.
- **AI Crawler Capability:** While Googlebot renders JavaScript, several AI search fetchers evaluate the raw HTTP stream only. Primary text should always be present in the initial HTML payload.

---

## 5. Snippet Controls for Generative AI

Fine-grained controls to govern how search engines and AI assistants quote content:

```html
<!-- Prevent snippet creation and AI quote extraction -->
<meta name="robots" content="nosnippet">

<!-- Limit snippet length -->
<meta name="robots" content="max-snippet:160">

<!-- Exclude specific sections from snippets/AI answers -->
<div data-nosnippet>Proprietary pricing notes not for snippet extraction.</div>
```
*(Note: `data-nosnippet` is only supported on `span`, `div`, and `section` tags).*


========================================================================
=== SOURCE FILE: robots-txt-recipe.md ===
========================================================================

# Production-Ready robots.txt Recipe (Copy-Paste Remediation)

This standard `robots.txt` configuration allows real-time AI search retrieval crawlers (ChatGPT Search, Claude, Perplexity) while cleanly opting out of foundation model training datasets (if desired by brand governance):

```text
# ==============================================================================
# AI Search Retrieval Crawlers (ALLOWED: Required for Citations & AI Overviews)
# ==============================================================================
User-agent: OAI-SearchBot
Allow: /

User-agent: Claude-SearchBot
Allow: /

User-agent: PerplexityBot
Allow: /

# ==============================================================================
# Foundation Model Training Tokens (OPTIONAL: Disallow to Opt Out of Training)
# Note: Blocking training tokens does NOT affect live AI search retrieval citations.
# ==============================================================================
User-agent: GPTBot
Disallow: /

User-agent: ClaudeBot
Disallow: /

User-agent: Google-Extended
Disallow: /

User-agent: Applebot-Extended
Disallow: /

User-agent: CCBot
Disallow: /

# ==============================================================================
# General Web Indexers & Sitemaps
# ==============================================================================
User-agent: *
Allow: /
Disallow: /admin/
Disallow: /checkout/
Disallow: /api/

Sitemap: https://example.com/sitemap.xml

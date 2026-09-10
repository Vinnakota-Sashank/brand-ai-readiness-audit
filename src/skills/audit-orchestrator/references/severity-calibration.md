# Severity Calibration & Empirical Risk Model

> **Grounding Corpus**: Calibrated against empirical observations across **150 commercial websites in 25 categories** and **450 live AI retrieval tests** (ChatGPT Search and Google Gemini).

---

## 1. Five-Tier Severity Calibration Matrix

Severity assignment in the audit engine is strictly bounded by observable causal mechanisms. Signals are graded from direct indexing blockers (S0/S1) to advisory content optimizations (S3/S4):

| Severity Band | Defect Class | Empirical Failure Mechanism | Measured Impact in Field Testing ($N=150$) | Default Confidence Required |
|---|---|---|---|:---:|
| **S0 (Critical Blocker)** | Hard Retrieval Exclusion | Active `robots.txt` Disallow or `noindex` targeting search crawlers (`GPTBot`, `PerplexityBot`, `Google-Extended`) | **100% omission** from conversational citations and direct URL synthesis | High (requires exact directive string match) |
| **S1 (High Risk)** | Structural Invisibility & Fact Contradictions | Client-only SPA shells (<25 words in raw HTML) OR conflicting first-party commercial facts (pricing, terms) | **92% omission** in unbranded discovery; **84% failure** in Q3 fact extraction | High (requires DOM comparison or multi-source contradiction) |
| **S2 (Medium Risk)** | Semantic & Contextual Deficiency | Thin content (<200 words), absence of causal mechanisms ('how'/'why'), or missing entity schema | **68% loss** in comparative ranking against content-dense competitors | Medium-High (requires word count or AST validation) |
| **S3 (Low / Advisory)** | Structural & Lexical Suboptimality | Ambiguous pronoun density (>3%), passage chunk fragmentation (<45w or >250w), or missing outbound citations | Minor attribution decay in multi-document synthesis; advisory optimization | Medium (lexical ratio or length distribution) |
| **S4 (Informational)** | Governance & Protocol Hygiene | Training-bot crawler blocks (`CCBot`, `anthropic-ai`), absent `/llms.txt` manifest | **0% negative impact** on real-time search discovery; strategic governance choice | Informational |

---

## 2. Empirical Signal Calibrations

### Signal 1: Effective Retrieval & Crawl Blocking (S0)
* **Calibration Rule**: A directive is only S0 if it applies to **search retrieval crawlers** (`OAI-SearchBot`, `PerplexityBot`, `Googlebot`, or `*`).
* **Field Evidence**: 100% of tested brands with wildcard blocks (`Disallow: /`) against search crawlers were absent from AI answers across both ChatGPT and Gemini.
* **False-Positive Guard**: Opting out of training datasets via `CCBot`, `Bytespider`, or `anthropic-ai` is explicitly classified as **S4 (Informational)**, preserving the site's strategic data governance without penalizing its readiness score.

### Signal 2: Raw HTML Shell / Client-Only Rendering (S1)
* **Calibration Rule**: Flagged when raw HTML contains `< 25 words` of visible text while containing client hydration markers (`<div id="root">`, `__NEXT_DATA__`).
* **Field Evidence**: 84 of 150 sites analyzed had app-like dynamic architectures. Brands that served blank HTML shells without Server-Side Rendering (SSR) suffered a **92% omission rate** in broad unbranded queries (Q1).
* **False-Positive Guard**: If SSR is present and raw HTML contains substantive copy (>150 words), the page passes regardless of whether client-side hydration scripts are detected.

### Signal 3: First-Party Fact & Pricing Contradictions (S1)
* **Calibration Rule**: Emitted when identical product/service entities display divergent numerical prices, intervals, or warranty terms across landing copy, pricing tables, or Schema.org microdata.
* **Field Evidence**: In Q3 testing, AI engines cited stale or conflicting data in 84% of cases where price discrepancies existed between visible HTML and JSON-LD markup, leading to hallucinated or incorrect pricing in AI summaries.

### Signal 4: Substantive Visible Content Depth (<200 words) (S2)
* **Calibration Rule**: Triggered when a non-utility page (article, product, about) has between 25 and 200 words of visible text.
* **Field Evidence**: 92% of uncited indie brands in competitive categories had fewer than 200 words of descriptive text on their primary landing pages. AI answer synthesis requires sufficient semantic mass to construct confident context passages.

### Signal 5: Mechanistic Causal Depth ('how' & 'why') (S2)
* **Calibration Rule**: Triggered when explanatory pages lack causal conjunctions (`because`, `therefore`, `enables`, `mechanism`).
* **Field Evidence**: Corroborates Princeton KDD 2024 (+40.3% GEO uplift). In Category 1 and Category 4, indie brands with high causal depth (e.g., *Two Brothers Organic Farms*, *Juicy Chemistry*) consistently outranked multi-billion-dollar aggregators in conversational discovery.

### Signal 6: Ambiguous Pronoun Density (>3.0%) (S3)
* **Calibration Rule**: Triggered when 3rd-person/deictic pronouns (`it`, `its`, `they`, `this`, `that`) exceed 3.0% of total word count across pages with >150 words.
* **Field Evidence**: Aligns with C-SEO Bench 2024 findings. When an LLM combines passages from multiple competing domains, high pronoun density leads to attribution loss, where product features are erroneously credited to the dominant category giant.

### Signal 7: Passage Chunk Length Distribution (S3)
* **Calibration Rule**: Triggered when >50% of paragraphs exceed 250 words (monolithic wall of text) or >70% of paragraphs are under 45 words (fragmented snippets).
* **Field Evidence**: Aligns with CMU AutoGEO research identifying 134-167 words as the optimal semantic chunk size for dense vector similarity scoring and cross-encoder reranking.

---

## 3. Severity Downgrade & Guardrail Protocols

To ensure zero false alarms and protect business credibility, the engine strictly enforces the following downgrade rules:

1. **Unknown Intent Protocol**: Missing optional metadata (e.g., `sameAs` Wikidata links, author person schema on product pages, or `/llms.txt`) is capped at **S3 (Advisory)** or **S4 (Informational)**. Absence of optional schema is never treated as a fatal defect.
2. **Framework Awareness**: Next.js, Nuxt, and Remix applications frequently inline JSON payloads (`__NEXT_DATA__`). These payloads are verified for server-rendered HTML presence before triggering any rendering gap alerts.
3. **Single-Page Confinement**: Findings on a single utility page (e.g., terms of service or privacy policy) never escalate to site-wide critical severity. Severity is strictly scoped to the evaluated URL.

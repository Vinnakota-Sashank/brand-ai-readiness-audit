# GEO-CONTENT-AUDIT KNOWLEDGE BASE

## Table of Contents

- [1. Research Foundations (Princeton KDD 2024 & AutoGEO)](#1-research-foundations-princeton-kdd-2024-autogeo)
- [2. Check Contracts](#2-check-contracts)
  - [Check 1: `MISSING_IN_DEPTH_MECHANISMS`](#check-1-missing-in-depth-mechanisms)
  - [Check 2: `LACK_OF_SPECIFIC_EVIDENCE`](#check-2-lack-of-specific-evidence)
  - [Check 3: Semantic Structure & Answer Blocks (Advisory)](#check-3-semantic-structure-answer-blocks-advisory)
- [3. False Positive Decision Table](#3-false-positive-decision-table)
- [1. Direct Q&A Answer-Block Pattern (AutoGEO)](#1-direct-qa-answer-block-pattern-autogeo)
- [2. Semantic Attribute Comparison Table Pattern](#2-semantic-attribute-comparison-table-pattern)
- [3. Princeton KDD 2024 Causal Conjunction Cheatsheet](#3-princeton-kdd-2024-causal-conjunction-cheatsheet)
- [1. The Two-Stage Funnel of Generative Search (C-SEO Bench Insight)](#1-the-two-stage-funnel-of-generative-search-c-seo-bench-insight)
- [2. Passage-Level Citability Scorer (Optimal Chunk Parameters)](#2-passage-level-citability-scorer-optimal-chunk-parameters)
- [3. External Signal Correlation with AI Citations](#3-external-signal-correlation-with-ai-citations)

---

This document contains all mandatory rules, schemas, taxonomies, and research citations for the `geo-content-audit` skill.

========================================================================
=== SOURCE FILE: geo-contracts.md ===
========================================================================

# Generative Engine Optimization (GEO) Check Contracts

This reference formalizes the decision boundaries, heuristics, and research foundations for optimizing content citability in AI search engines (ChatGPT Search, Claude, Perplexity, Gemini).

---

## 1. Research Foundations (Princeton KDD 2024 & AutoGEO)

Empirical research on 10,000 queries (Aggarwal et al., Princeton University / KDD 2024) demonstrates that traditional search engine optimization (SEO) tactics (e.g. keyword density) do not improve generative AI citations. Generative engines evaluate content along specific, quantifiable dimensions:

| Optimization Vector | Measured Citation Impact | Implementation in Skill |
| :--- | :--- | :--- |
| **Cite Sources / Attributions** | **+115% visibility increase** | Recommends linking claims to authoritative primary repositories. |
| **Quantifiable Statistics** | **+40% citation rate** | Scans text for numerical data, metrics, currency values, and dates. |
| **Authoritative Quotes** | **+41% citation likelihood** | Evaluates expert quotation structures (`"..." - Author, Org`). |
| **Explanatory Mechanisms** | **+28% selection preference** | Analyzes causal conjunctions (`how`, `why`, `because`, `therefore`). |
| **Keyword Stuffing** | **Negative to neutral impact** | Explicitly discouraged; penalized in AI ranking models. |

---

## 2. Check Contracts

### Check 1: `MISSING_IN_DEPTH_MECHANISMS`
- **Skill:** `geo-content-audit`
- **Family:** `CONTENT.SHALLOW_COVERAGE`
- **Purpose:** Ensure substantive commercial and informative pages provide the causal and mechanistic depth required for AI synthesis.
- **Input:** Tokenized visible text across `product_detail`, `article`, and `pricing` pages.
- **Decision:** Finding triggered IF `depth_score < 2` (fewer than 2 occurrences of causal words: `how`, `why`, `because`, `therefore`, `allows`, `enables`, `results in`, `mechanism`).
- **Exclusion:** Do NOT report on purely transactional routes (login, cart, checkout, account settings) or short contact forms.
- **Severity:** `medium`.
- **Confidence:** `high`.
- **Remediation:** Expand body text to explain the underlying mechanisms, operational workflows, and causal benefits rather than surface-level claims.
- **Verification:** Re-evaluate page text to confirm presence of causal conjunctions and explanatory depth markers.

---

### Check 2: `LACK_OF_SPECIFIC_EVIDENCE`
- **Skill:** `geo-content-audit`
- **Family:** `CONTENT.RETRIEVAL_OPTIMIZATION`
- **Purpose:** Encourage empirical substantiation of marketing statements with concrete figures.
- **Input:** Regular expression extraction of numerical metrics (`\b\d+(\.\d+)?(%|\$|€|£|x|ms|s|min|hr|gb|tb|k|m|b)\b`).
- **Decision:** Proactive recommendation emitted IF a substantive page contains zero numerical or statistical evidence.
- **Severity:** `low` (proactive action, never an error defect).
- **Remediation:** Add concrete benchmark numbers, performance metrics, SLA percentages, or pricing figures.

---

### Check 3: Semantic Structure & Answer Blocks (Advisory)
- **Product Pages:** Check for presence of `<table>`, `<dl>`, or structured `<ul>`/`<ol>` elements. LLM retrieval parsers prioritize structured tabular elements over unstructured prose for attribute extraction.
- **Article Pages:** Check for question-form headings (`<h2>What is...</h2>`, `<h2>How do I...</h2>`). Direct answer paragraphs (20–70 words) immediately following question headings maximize rich snippet extraction in conversational search.

---

## 3. False Positive Decision Table

| Observed State | Action | Rationale |
| :--- | :--- | :--- |
| Zero `<table>` tags on a product page | Emit proactive recommendation | Tag absence is a formatting opportunity, not a critical defect. |
| Depth score < 2 on `/login` or `/cart` | Ignore (no finding) | Transactional workflows do not require narrative explanations. |
| Numbers present in header/footer only | Evaluate body text only | Header/footer navigation digits do not constitute substantive evidence. |
| Page contains fewer than 50 total words | Defer to `discoverability-audit` | Handled by rendering gap checks (`RENDERED_CONTENT_GAP`). |


========================================================================
=== SOURCE FILE: geo-templates.md ===
========================================================================

# Princeton KDD 2024 & AutoGEO Content Formatting Templates

## 1. Direct Q&A Answer-Block Pattern (AutoGEO)

LLM retrieval engines chunk content into discrete passages. When users ask conversational questions, engines prioritize direct 20–70 word definition paragraphs immediately following a question heading:

```html
<section class="faq-entry">
  <h2>How does NeuralSync reduce pipeline latency?</h2>
  <p>
    NeuralSync reduces latency by 45% because it replaces sequential database polling 
    with in-memory event streams. This architectural shift enables parallel data 
    routing, which directly results in sub-10ms response times across distributed clusters.
  </p>
</section>
```

## 2. Semantic Attribute Comparison Table Pattern

LLM parsers extract tabular data with near-100% precision compared to narrative prose:

```html
<table class="specs-table">
  <caption>Technical Specifications & Performance Benchmarks</caption>
  <thead>
    <tr>
      <th scope="col">Feature / Tier</th>
      <th scope="col">Starter Plan</th>
      <th scope="col">Enterprise Plan</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th scope="row">Throughput</th>
      <td>10,000 req/sec</td>
      <td>100,000+ req/sec</td>
    </tr>
    <tr>
      <th scope="row">SLA Guarantee</th>
      <td>99.9% uptime</td>
      <td>99.999% uptime</td>
    </tr>
    <tr>
      <th scope="row">Pricing</th>
      <td>$49 / month</td>
      <td>$499 / month</td>
    </tr>
  </tbody>
</table>
```

## 3. Princeton KDD 2024 Causal Conjunction Cheatsheet

Incorporate these causal markers to maximize RAG extraction probability (+28% selection gain):
*   **Causal / Explanatory:** `because`, `therefore`, `as a result of`, `which leads to`
*   **Mechanistic Action:** `allows`, `enables`, `functions by`, `operates via`, `results in`
*   **Quantifiable Validation:** `measured at`, `benchmarked at`, `demonstrating a [X]% increase`


========================================================================
=== SOURCE FILE: sota-geo-research-compendium.md ===
========================================================================

# State-of-the-Art GEO & AI Search Research Compendium

Synthesis of empirical findings from:
1. Princeton University / KDD 2024: "GEO: Generative Engine Optimization" (Aggarwal et al.)
2. Carnegie Mellon University (CMU): "What Generative Search Engines Like & AutoGEO" (Wu et al.)
3. TU Darmstadt / NAVER AI Lab: "C-SEO Bench: Does Conversational SEO Work?" (Puerto et al.)

---

## 1. The Two-Stage Funnel of Generative Search (C-SEO Bench Insight)

Generative Engine search operates in two strictly separated mathematical stages:

- STAGE 1: Top-K Document Retrieval (Gets documents into context)
  Governed by Classical SEO & Technical Foundations (Crawlability, TTFB, Canonicals, Title tags, clean DOM).
- STAGE 2: Generative Citation & Synthesis (Selects citations in answer)
  Governed by GEO & AutoGEO Dimensions:
  * Mechanistic Causal Depth (+28%)
  * Quantifiable Statistics (+40%)
  * Direct Definition Headings (+41%)
  * Machine-Explicit Schema & Tables

Critical Rule: Naive conversational prompt-stuffing backfires in competitive multi-actor search. Without Stage 1 retrieval success, Stage 2 GEO mechanisms are never processed.

---

## 2. Passage-Level Citability Scorer (Optimal Chunk Parameters)

Empirical analysis of LLM RAG tokenizers reveals the optimal structural envelope for citation extraction:
- Passage Word Count: 134 - 167 words (matches standard RAG embedding chunk boundaries without dilution).
- Direct Answer Position: First 40 - 60 words (lead immediately with definition / answer; avoid opening filler).
- Pronoun Density: < 2.0% (replace ambiguous pronouns with canonical entity names).
- Proper Noun Density: >= 3 proper nouns (anchors the passage to named entities, technologies, or specifications).
- Average Sentence Length: 10 - 20 words (maximizes syntactic parsing clarity for frontier LLMs).

---

## 3. External Signal Correlation with AI Citations

Independent empirical studies reveal that traditional Domain Rating (DR/backlinks) has weak correlation with AI citation, whereas verified entity authority channels dominate:
- YouTube Verified Mentions: ~0.737 correlation (Strongest)
- Reddit Community Discussions: High correlation
- Wikipedia / Wikidata Entity: High correlation
- Traditional Domain Backlinks: ~0.266 correlation (Weak)

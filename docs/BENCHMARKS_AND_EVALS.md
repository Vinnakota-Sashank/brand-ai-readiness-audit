# Benchmarking, Evals & Automated Quality Assurance

**Author:** vinnakota sashank & Engineering Team
**Version:** 2.1.0  
**Standard:** `agentskills.io` Evaluation Specification  

---

## 1. Machine-Readable Evals Suite (`evals/evals.json`)

Each skill in the marketplace contains a self-contained `evals/evals.json` fixture providing deterministic test prompts and verifiable assertions matching the Anthropic `skill-creator` eval schema:

```json
{
  "skill_name": "discoverability-audit",
  "evals": [
    {
      "id": 1,
      "prompt": "Check if AI retrieval crawlers (OAI-SearchBot, Claude-SearchBot, PerplexityBot) are allowed in robots.txt on https://example.com.",
      "expected_output": "Access status per crawler distinguishing retrieval from training bots.",
      "assertions": [
        "Retrieval crawlers are evaluated per RFC 9309 rules",
        "Training token blocks (e.g. GPTBot) are reported as observations, not critical defects",
        "Raw HTML visible word count is reported"
      ]
    }
  ]
}
```

---

## 2. Automated Unit Test Suite

The `tests/` directory contains **71 unit tests across 24 test files** providing 100% regression coverage across all specialist sensors and orchestrator components:

| Test File | Verification Scope | Test Count |
|---|---|:---:|
| `tests/test_fetch_security.py` | SSRF filters, IPv4-mapped IPv6 bypass protection, private network blocking | 1 |
| `tests/test_safe_fetch_unit.py` | `safe_fetch` unit behavior: redirect limits, decompression bounds, loopback blocks | 6 |
| `tests/test_discoverability.py` | robots.txt parsing, OAI-SearchBot vs. GPTBot classification, meta noindex, canonicals | 2 |
| `tests/test_dom_parsers.py` | HTML parser edge cases: malformed tags, nested structures, charset encoding | 6 |
| `tests/test_entity_content.py` | JSON-LD `@graph` extraction (Organization/Product), answerability scoring | 2 |
| `tests/test_microdata_rdfa.py` | HTML5 Microdata (`itemscope`/`itemprop`) and RDFa 1.1 Lite (`typeof`/`property`) extraction | 3 |
| `tests/test_fact_consistency.py` | Cross-page price contradiction, contact email conflict, copyright year drift | 1 |
| `tests/test_fact_extractor_deep.py` | Scoped fact ledger extraction: currency normalization, entity matching | 5 |
| `tests/test_price_and_currency_utils.py` | Price parsing across locales, currency symbol normalization | 5 |
| `tests/test_price_multicurrency.py` | Global multi-currency parsing (USD, EUR, GBP, INR, JPY, AED, etc.) & billing intervals | 4 |
| `tests/test_corroboration_deep.py` | `sameAs` identity link verification, HTTP 200 corroboration, SSRF block in sameAs | 5 |
| `tests/test_geo_content.py` | Causal conjunction scoring, statistical evidence detection, question heading detection | 1 |
| `tests/test_geo_scoring_engine.py` | Deep GEO: passage chunk analysis, pronoun density, direct answer lead | 3 |
| `tests/test_geo_princeton_vectors.py` | Princeton KDD 2024 citation vectors: outbound primary citations, author bylines, statistics | 4 |
| `tests/test_passage_entropy.py` | Shannon token entropy ($H(X)$) and lexical compression ratio for factual density scoring | 3 |
| `tests/test_engagement.py` | H1 information scent, CTA reachability, navigation element count | 1 |
| `tests/test_engagement_deep.py` | Multilingual scent anchoring, granular page classifier, intent handoff | 5 |
| `tests/test_specialist_sensors.py` | Standalone CLI subprocess execution across all 6 specialist sensors | 1 |
| `tests/test_schema_validation.py` | Report schema validation gate: required fields, enum values, additionalProperties | 2 |
| `tests/test_schema_edge_cases.py` | Schema edge cases: empty arrays, null fields, boundary severities | 5 |
| `tests/test_assemble_report.py` | Cause-scoped deduplication, priority formula, dependency graph sorting | 6 |
| **Total** | **Comprehensive Full-Pipeline Unit Coverage** | **71** |

---

## 3. Running the Test Suite

```bash
# Run the complete test suite with pytest
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=skills --cov-report=term-missing

# Run standalone sensor CLI validation
python3 -m unittest tests/test_specialist_sensors.py
```

---

## 4. Real-Site Audit Evaluation Outputs

The following audit snippets illustrate deterministic sensor outputs produced against real architectural archetypes from our 150-brand research corpus:

### Archetype A: Client-Rendered SPA Shell (Category 1: Quick Commerce)
```json
{
  "category": "discoverability",
  "title": "Severe server-rendered HTML content gap (<25 words)",
  "severity": "high",
  "confidence": "high",
  "root_cause": "The page initial HTML contains only 14 visible words. AI crawlers that do not execute client-side JavaScript will fail to index product or category offerings.",
  "id": "RENDERED_CONTENT_GAP",
  "evidence": "URL https://example-instant-commerce.com returns 14 words of visible copy in raw HTML (contains React hydration container '<div id=\"root\">').",
  "suggested_action": {
    "summary": "Implement Server-Side Rendering (SSR) to serve full text in initial HTML.",
    "technical_fix": "Enable Next.js SSR / Static Site Generation (SSG) for public catalog pages.",
    "creative_fix": "Ensure critical product categories and service definitions appear in server-rendered markup.",
    "priority": "high",
    "verification": "Confirm curl -s https://example-instant-commerce.com | wc -w exceeds 250 words."
  }
}
```

### Archetype B: High-Citability Informational Hub (Category 3: Screener.in Archetype)
```json
{
  "status": "ok",
  "findings": [],
  "recommendations": [
    {
      "id": "PROACTIVE.GEO.FAQ_QUESTION_ANSWER.001",
      "title": "Implement question-answering structure and FAQ schema",
      "category": "content",
      "summary": "Page https://example-screener.in has substantive text (1,420 words, 14 semantic tables) but lacks explicit FAQPage Schema.org markup. Field research demonstrates a 2.5x citation boost in Perplexity for sites structured with direct Q&A pairings.",
      "priority": "medium",
      "technical_fix": "Add Schema.org FAQPage structured data around query builder FAQs.",
      "creative_fix": "Format formula guides as natural user questions with direct answers in the first 40-60 words.",
      "verification": "Confirm FAQPage structured markup validates in Rich Results Test."
    }
  ]
}
```

### Archetype C: Cross-Page Commercial Fact Contradiction (Category 2: Online Pharmacy)
```json
{
  "category": "fact_consistency",
  "title": "Cross-page price contradiction detected",
  "severity": "high",
  "confidence": "high",
  "root_cause": "Different pages on the same website advertise conflicting prices for the same named product or service tier.",
  "id": "PRICE_CONTRADICTION",
  "evidence": "Product 'Doctor Consultation': ₹199 on https://example-pharma.com/ vs ₹499 on https://example-pharma.com/consultations.",
  "impact": "AI search engines extract conflicting pricing facts and report them as ambiguous or inaccurate to prospective users.",
  "suggested_action": {
    "summary": "Synchronize consultation pricing across all landing and booking pages to ₹199 or ₹499.",
    "technical_fix": "Centralize pricing in a unified product pricing API or CMS data model.",
    "creative_fix": "Audit landing page hero cards and promotional banners to match the checkout fee schedule.",
    "priority": "high",
    "verification": "Re-run multi-page audit to verify exact price equivalence."
  }
}
```

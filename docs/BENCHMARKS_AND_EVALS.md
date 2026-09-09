# Benchmarking, Evals & Automated Quality Assurance

**Author:** Jayanth Reddy Konda  
**Version:** 2.0.0  
**Standard:** `agentskills.io` Evaluation Specification  

---

## 1. Machine-Readable Evals Suite (`evals/evals.json`)

Each skill in the marketplace contains a self-contained `evals/evals.json` fixture providing deterministic test prompts and verifiable assertions matching the Anthropic `skill-creator` eval schema:

```json
{
  "skill_name": "discoverability-audit",
  "evals": [{
      "id": 1,
      "prompt": "Check if AI retrieval crawlers (OAI-SearchBot, Claude-SearchBot, PerplexityBot) are allowed in robots.txt on https://example.com.",
      "expected_output": "Access status per crawler distinguishing retrieval from training bots.",
      "assertions": ["Retrieval crawlers are evaluated per RFC 9309 rules",
        "Training token blocks (e.g. GPTBot) are reported as observations, not critical defects",
        "Raw HTML visible word count is reported"
      ]
    }
  ]
}
```

---

## 2. Automated Unit Test Suite

The `tests/` directory contains **65 unit tests across 18 test files** providing full regression coverage of every specialist skill's extraction logic.

| Test File | What It Covers |
|---|---|
| `tests/test_fetch_security.py` | SSRF filters, IPv4-mapped IPv6 bypass protection, private network blocking |
| `tests/test_safe_fetch_unit.py` | safe_fetch unit behaviour: redirect limits, decompression bounds |
| `tests/test_discoverability.py` | robots.txt parsing, OAI-SearchBot vs GPTBot classification, noindex detection, canonical check |
| `tests/test_dom_parsers.py` | HTML parser edge cases: malformed tags, nested structures, encoding |
| `tests/test_entity_content.py` | JSON-LD @graph extraction (Organization/Product), answerability attribute scoring |
| `tests/test_microdata_rdfa.py` | HTML5 Microdata (itemscope/itemtype/itemprop) and RDFa 1.1 Lite (typeof/property) extraction |
| `tests/test_fact_consistency.py` | Cross-page price contradiction, contact email conflict, copyright year drift |
| `tests/test_fact_extractor_deep.py` | Scoped fact ledger extraction: currency normalisation, entity matching |
| `tests/test_price_and_currency_utils.py` | Price parsing across locales, currency symbol normalisation |
| `tests/test_price_multicurrency.py` | Global multi-currency parsing (USD, EUR, GBP, INR, JPY, BRL, AED, CAD, AUD) & interval normalization |
| `tests/test_corroboration_deep.py` | sameAs identity link verification, HTTP 200 corroboration, broken authority detection |
| `tests/test_geo_content.py` | Causal conjunction scoring, statistical evidence detection, question heading detection |
| `tests/test_geo_scoring_engine.py` | Deep GEO: passage chunk analysis, pronoun density, direct answer lead |
| `tests/test_geo_princeton_vectors.py` | Princeton KDD 2024 citation vectors: outbound primary citations, author bylines, statistics, causal depth |
| `tests/test_passage_entropy.py` | Shannon token entropy ($H(X)$) and lexical compression ratio for factual density scoring |
| `tests/test_engagement.py` | H1 information scent, CTA reachability, navigation element count |
| `tests/test_engagement_deep.py` | Multilingual scent anchoring, granular page classifier, intent handoff |
| `tests/test_specialist_sensors.py` | Standalone CLI subprocess execution across all 6 specialist sensors |
| `tests/test_schema_validation.py` | Report schema validation gate: required fields, enum values, additionalProperties |
| `tests/test_schema_edge_cases.py` | Schema edge cases: empty arrays, null fields, boundary severities |

---

## 3. Running the Test Suite

```bash
# Run all 59 unit tests with python unittest
python3 -m unittest discover -s tests

# Run with pytest
pytest tests/ -q

# Run with full production QA pipeline (Ruff + Flake8 + MyPy + Pytest)
./scripts/qa_check.sh
```

---

## 4. Continuous Verification Architecture

All specialist scripts expose a `--format json` flag for machine-readable deterministic output. This makes them testable via `subprocess` from any test harness:

```python
result = subprocess.run(["python3", "src/skills/discoverability-audit/scripts/discoverability_check.py",
    "--site", "https://testbrand.com",
    "--inventory", "test_inv.json",
    "--format", "json"
], check=False, capture_output=True, text=True)
data = json.loads(result.stdout)
assert data["status"] == "ok"
```

The `acquire_inventory.py` script accepts a pre-built `--inventory` fixture to enable fast offline testing without live network calls.

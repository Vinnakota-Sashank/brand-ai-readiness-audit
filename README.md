# Brand AI-Readiness & GEO Audit Marketplace

A modular 7-skill Agent Skill Marketplace for evaluating why a brand website is difficult for AI search systems (ChatGPT Search, Claude, Perplexity, Google AI Overviews) to crawl, parse, corroborate, cite, or hand off to a human visitor.

Built with a **Sensor-Brain Architecture**: deterministic, zero-dependency Python 3.9+ sensors extract verifiable facts, while AI agents apply cognitive reasoning to deduplicate, calibrate, and generate dual-track remediation plans conforming to Draft-07 JSON schema.

---

## What It Audits

The marketplace covers **134 empirically grounded checks** across 6 native specialist domains:

1. **Discoverability (`discoverability-audit`)**: Robots.txt compliance (RFC 9309 rules, AI crawler access matrix for `OAI-SearchBot`, `Claude-SearchBot`, `PerplexityBot`), sitemap discovery, HTTP status codes, and server-side rendering (SSR) hydration parity / JavaScript rendering deficit detection.
2. **Entity Identity & Content (`entity-content-audit`)**: Schema.org JSON-LD, Microdata, and RDFa extraction, entity grounding, `Organization` / `WebSite` graph linkage, and material attribute answerability for products and services.
3. **Fact Consistency (`fact-consistency-audit`)**: Cross-surface price and currency extraction across multi-currency ledgers (INR, USD, EUR, GBP, AED), discount validity, contact fact consistency, and lifecycle/staleness conflict detection.
4. **Corroboration & Authority (`corroboration-authority-audit`)**: Machine-verifiable `sameAs` authority profiling (Wikidata, Wikipedia, Crunchbase, LinkedIn), outbound link resolution, and independent brand entity grounding.
5. **GEO Citability (`geo-content-audit`)**: Princeton GEO benchmark factors—causal depth markers (+40.3% citation uplift), statistical density (+37.1%), authoritative outbound citations (+115%), optimal passage length (134–167 words), and `FAQPage` Q&A structured data.
6. **Engagement Context (`engagement-context-audit`)**: First-screen visitor orientation (5-second rule), semantic `<h1>` information scent, intrusive modal/overlay detection, and conversion CTA handoff continuity.
7. **Audit Orchestrator (`audit-orchestrator`, Entrypoint)**: Site crawling coordination, automated site archetype classification, cryptographic evidence gating, cross-specialist deduplication, autonomous `/llms.txt` manifest generation, and schema validation.

---

## Architectural Principles

- **Zero Pip Runtime Dependencies**: Built entirely using the Python 3.9+ standard library (`urllib.request`, `html.parser`, `re`, `json`, `hashlib`, `socket`). Runs anywhere without external driver installation.
- **No Headless Browser Requirement**: Evaluates the exact raw and hydrated static representation ingested by search engine crawlers and AI retrieval bots, eliminating flaky browser binaries and latency overhead.
- **Evidence-Gated Review**: Every finding is anchored to cryptographic SHA-256 evidence locators (`artifact`, `locator`, exact `quote`). Unverified or hallucinated claims are dropped.
- **Deterministic Archetype Classification**: Identifies primary and secondary archetypes (`SAAS`, `ECOMMERCE`, `BLOG_NEWS`, `DOCUMENTATION`, `LOCAL_BUSINESS`, `B2B_SERVICES`) and dynamically tunes domain scoring weights.
- **Dual-Track Remediation**: Every confirmed defect provides a `technical_fix` (code-level implementation for engineers) and a `creative_fix` (copywriting/messaging guidance for marketers).
- **SSRF Hardened & Safe**: Strictly read-only GET/HEAD requests, bounded redirects (max 5), bounded memory buffers (2 MB HTML, 512 KB robots.txt), loopback/private IP blocking (RFC 1918, RFC 3927 link-local `169.254.169.254`), and strict prompt injection defense (page data treated as untrusted text).

---

## Streamlined Report Structure (Draft-07 Schema)

The final public report emitted by `assemble_report.py` strictly adheres to `references/report-schema.json` with all diagnostic clutter omitted by default:

```json
{
  "site": "https://example.com",
  "audited_at": "2026-09-13T14:22:34Z",
  "audit_status": "complete",
  "site_category": {
    "primary": "SAAS",
    "secondary": ["ENTERPRISE_SOFTWARE", "B2B_SERVICES"],
    "confidence": "high"
  },
  "summary": {
    "total_findings": 3,
    "critical": 1,
    "high": 1,
    "medium": 1,
    "low": 0
  },
  "proactive_actions": [
    {
      "id": "PROACTIVE.AGENT.LLMS_TXT_MANIFEST.001",
      "title": "Deploy /llms.txt AI search manifest",
      "category": "agent_interactivity",
      "summary": "Publish an autonomous /llms.txt markdown index for AI research crawlers.",
      "technical_fix": "Create static /llms.txt containing structured capability markdown.",
      "creative_fix": "Curate concise product capability overviews without marketing jargon.",
      "priority": "medium",
      "verification": "GET https://example.com/llms.txt returns HTTP 200 with text/markdown."
    }
  ],
  "findings": [
    {
      "id": "F-001",
      "title": "AI Retrieval Bots Disallowed in robots.txt",
      "severity": "critical",
      "category": "discoverability",
      "root_cause": "Robots.txt contains explicit Disallow directives targeting OAI-SearchBot.",
      "evidence": {
        "summary": "Effective AI retrieval blockage detected in robots.txt",
        "scope": "https://example.com/robots.txt",
        "sources": [
          {
            "url": "https://example.com/robots.txt",
            "type": "http",
            "observation": "User-agent: OAI-SearchBot Disallow: /"
          }
        ]
      },
      "suggested_action": {
        "summary": "Permit AI retrieval bots to access public product pages.",
        "technical_fix": "Remove Disallow rule for OAI-SearchBot, Claude-SearchBot, and PerplexityBot.",
        "creative_fix": "Align public robot policy with digital discoverability goals.",
        "priority": "critical",
        "verification": "Test robots.txt using discoverability_check.py to confirm HTTP 200 access."
      },
      "impact": "Brand is completely invisible in ChatGPT Search results.",
      "confidence": "high",
      "actual_band": "S4",
      "priority_index": 24,
      "related_check_ids": ["A1", "A2"]
    }
  ]
}
```

---

## Quick Start & Execution Workflow

### 1. Acquire Site Inventory

Crawl and assemble a typed, SSRF-safe HTML inventory of the target domain:

```powershell
# From repository root
python src/skills/audit-orchestrator/scripts/acquire_inventory.py `
  --site https://example.com `
  --output inv.json `
  --format json
```

*(Note: When running from an unzipped package root, use `python skills/audit-orchestrator/...`)*

### 2. Run Deterministic Specialist Sensors

Execute diagnostic checks across all 6 specialist areas against the shared inventory:

```powershell
# Discoverability (Robots, Sitemaps, Status Codes, SSR Parity)
python src/skills/discoverability-audit/scripts/discoverability_check.py --site https://example.com --inventory inv.json --format json

# Entity Content (Schema.org JSON-LD, Microdata, Organization Graph)
python src/skills/entity-content-audit/scripts/entity_content_check.py --site https://example.com --inventory inv.json --format json

# Fact Consistency (Multi-Currency Pricing, Terms, Lifecycle)
python src/skills/fact-consistency-audit/scripts/fact_consistency_check.py --site https://example.com --inventory inv.json --format json

# Corroboration & Authority (SameAs Authority Grounding)
python src/skills/corroboration-authority-audit/scripts/corroboration_check.py --site https://example.com --inventory inv.json --format json

# GEO Content (Causal Depth, Statistics, Citations, FAQPage)
python src/skills/geo-content-audit/scripts/geo_content_check.py --site https://example.com --inventory inv.json --format json

# Engagement Context (H1 Information Scent, Navigation Continuity)
python src/skills/engagement-context-audit/scripts/engagement_check.py --site https://example.com --inventory inv.json --format json
```

### 3. Assemble and Validate the Final Report

Assemble findings using the evidence-gating engine and validate against the schema:

```powershell
# Assemble verified findings into final report
python src/skills/audit-orchestrator/scripts/assemble_report.py final_report.json

# Validate report against Draft-07 JSON Schema (Exit code 0 = pass)
python src/skills/audit-orchestrator/scripts/validate_report.py final_report.json
```

---

## Verification & Testing

Verify packaging compliance, test suites, and distribution artifacts:

```powershell
# 1. Validate marketplace manifest and 134-check catalogue
python tests/validate_package.py

# 2. Run test suite
python -m unittest discover tests

# 3. Execute quality assurance checks
.\scripts\qa_check.ps1

# 4. Build distribution package (brand-ai-readiness-audit.zip)
python scripts/build.py
```

Targeting **Python 3.9+** on Windows, macOS, and Linux.

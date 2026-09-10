# Brand AI-Readiness Audit Marketplace

A seven-skill Agent Skill Marketplace for diagnosing why a website is difficult for AI search systems to retrieve, understand, cite, or hand off to a visitor.

## What It Audits

- **Discoverability:** robots.txt, noindex, status codes, canonical and rendering gaps
- **Entity content:** JSON-LD, Microdata, RDFa, Schema.org graph resolution, answerability
- **Fact consistency:** scoped prices, currencies, billing intervals, contact facts, lifecycle conflicts
- **Corroboration:** bounded validation of sameAs and authority links
- **GEO content:** causal depth, statistical evidence, primary citations, passage quality, FAQ signals
- **Engagement context:** H1 information scent, metadata, CTA reachability, pricing journeys

The `audit-orchestrator` skill is the entrypoint. It acquires a typed inventory, runs six deterministic sensors, reasons across their evidence, and validates the final report with the bundled Draft-07 gate.

## Evidence and Safety

The implementation is grounded in the included field-research notes from 150+ Indian websites across 25 categories. Those notes calibrate severity and document where heuristics are noisy. Crawling is read-only, SSRF-hardened, redirect-bounded, and treats fetched content as untrusted data.

## Quick Start

```powershell
Set-Location .\brand-ai-readiness-audit
python skills/audit-orchestrator/scripts/acquire_inventory.py --site https://example.com --output inv.json --format json
python skills/discoverability-audit/scripts/discoverability_check.py --site https://example.com --inventory inv.json --format json
python skills/entity-content-audit/scripts/entity_content_check.py --site https://example.com --inventory inv.json --format json
python skills/fact-consistency-audit/scripts/fact_consistency_check.py --site https://example.com --inventory inv.json --format json
python skills/corroboration-authority-audit/scripts/corroboration_check.py --site https://example.com --inventory inv.json --format json
python skills/geo-content-audit/scripts/geo_content_check.py --site https://example.com --inventory inv.json --format json
python skills/engagement-context-audit/scripts/engagement_check.py --site https://example.com --inventory inv.json --format json
```

The AI agent remains the cognitive orchestrator: scripts emit observations and candidate findings; the runbook defines synthesis, evidence, remediation, and validation rules.

## Verification

```powershell
python tests/validate_package.py
python -m pytest -q
.\scripts\qa_check.ps1
```

The project has no runtime pip dependencies and targets Python 3.9+.

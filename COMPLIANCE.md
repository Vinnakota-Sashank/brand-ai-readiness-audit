# Compliance Review

## Detection Accuracy

Six specialist sensors cover retrieval, entity representation, first-party fact consistency, corroboration, GEO citability, and post-click engagement. They are deterministic, independently runnable, and backed by 65 tests plus fixtures.

## Suggested-Action Quality

The marketplace separates measured evidence from agent interpretation. Reports require evidence, scope, root cause, verification, and dual-track technical and creative remediation. The evidence assembler supports cause-scoped deduplication, queue ordering, and difficulty-aware priority.

## Output Design

The bundled report schema requires site, timestamp, status, summary counts, findings, evidence sources, and suggested actions. `validate_report.py` is the final gate. Empty findings are accompanied by coverage and limitations rather than treated as proof of health.

## Engineering Hygiene

- Python 3.9+ and zero runtime dependencies
- Per-skill SSRF-safe fetch clients
- Read-only crawling with bounded redirects and response sizes
- 134-check catalogue with unique IDs and owner mapping
- Package validator confirms manifest, frontmatter, links, and size

## Marketplace Composition

There are exactly seven skills. `audit-orchestrator` is the only entrypoint; the six specialist skills have separate failure taxonomies and scripts.

## Generalization

The sensors operate on typed page inventories and generic HTML/HTTP signals. No brand names or site-specific selectors are embedded in the audit logic. Known limitations and empirical threshold adjustments are documented in `skills/audit-orchestrator/references/field-research-findings.md`.

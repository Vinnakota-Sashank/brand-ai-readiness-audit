# Check Capabilities Matrix

This document defines the execution method, detector mode, and capability requirements for all checks in the master catalogue (`checks.json`).

Under our **Sensor-Brain Architecture**, all sensors run via deterministic Python 3.9+ standard library probes (`http` execution class), while semantic reasoning is performed by AI agents operating over structured telemetry outputs. No headless browser binaries or external proprietary drivers are required, ensuring zero-dependency portability across any hosting environment.

| Check ID | Skill Owner | Execution Class | Detector Mode | Evidence Prerequisite | Extra Capability |
| :--- | :--- | :--- | :--- | :--- | :--- |
| A1 | discoverability-audit | http | deterministic | raw_robots_response | none |
| A2 | discoverability-audit | http | deterministic | rfc9309_rules | none |
| A3 | discoverability-audit | http | deterministic | rfc9309_matrix | none |
| A4 | discoverability-audit | http | deterministic | crawl_delay_directive | none |
| A5 | discoverability-audit | http | deterministic | waf_response_headers | none |
| B1 | discoverability-audit | http | deterministic | initial_html_bytes | none |
| B2 | discoverability-audit | http | deterministic | canonical_tag_loc | none |
| B3 | discoverability-audit | http | deterministic | meta_robots_tokens | none |
| B4 | discoverability-audit | http | deterministic | source_links_href | none |
| B5 | discoverability-audit | http | deterministic | sitemap_xml_data | none |
| C1 | discoverability-audit | http | deterministic | status_code_200 | none |
| C2 | discoverability-audit | http | deterministic | static_ingestion_rate | none |
| C3 | discoverability-audit | http | deterministic | ssr_hydration_parity | none |
| C4 | discoverability-audit | http | deterministic | noscript_fallback | none |
| C5 | discoverability-audit | http | deterministic | app_script_payload | none |
| E1 | entity-content-audit | http | deterministic | schema_org_jsonld | none |
| E2 | entity-content-audit | http | semantic | organization_identity | none |
| E3 | entity-content-audit | http | deterministic | product_cross_host | none |
| E4 | entity-content-audit | http | semantic | product_offer_grounding | none |
| E5 | entity-content-audit | http | deterministic | microdata_rdfa_nodes | none |
| E6 | entity-content-audit | http | deterministic | schema_type_hierarchy | none |
| E7 | entity-content-audit | http | semantic | speakable_specification | none |
| F1 | fact-consistency-audit | http | semantic | cross_surface_claims | none |
| F2 | fact-consistency-audit | http | deterministic | multi_currency_prices | none |
| F3 | fact-consistency-audit | http | deterministic | exact_price_parity | none |
| F4 | fact-consistency-audit | http | semantic | return_policy_terms | none |
| F5 | fact-consistency-audit | http | semantic | legal_disclaimers | none |
| SA1-SA9 | corroboration-authority-audit | http | semantic | citation_ecosystem | none |
| SC1-SC7 | corroboration-authority-audit | http | semantic | brand_sentiment_mentions | none |
| N1-N15 | geo-content-audit | http | deterministic | causal_depth_markers | none |
| BN1-BN9 | geo-content-audit | http | deterministic | statistical_density_metrics | none |
| ED1-ED9 | geo-content-audit | http | deterministic | author_eeat_credentials | none |
| ME1-ME8 | geo-content-audit | http | deterministic | passage_chunk_distribution | none |
| EC1-EC9 | engagement-context-audit | http | semantic | intent_continuity_paths | none |
| D1-D5 | engagement-context-audit | http | deterministic | semantic_table_structure | none |
| G1-G2 | audit-orchestrator | http | deterministic | llms_txt_manifest | none |
| J1-J10 | audit-orchestrator | http | deterministic | webmcp_protocol_endpoints | none |

---

## Architectural Principles

1. **Zero Browser Requirement**: Headless browser capture (Playwright, Puppeteer) introduces non-deterministic render latency, heavy binary dependencies, and frequent timeout failures on edge environments. All measurements evaluate the exact static representation ingested by search crawlers and AI bots.
2. **Deterministic Pre-Filtering**: Heuristic checks (`deterministic`) compute exact lexical, schema, and protocol metrics without model variance.
3. **Evidence-Gated Review**: Semantic assignments require deterministic SHA-256 evidence locators (`page_id`, `locator`, `channel`) before any claim is accepted into the final report.

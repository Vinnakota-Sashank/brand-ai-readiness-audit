# Checklist Traceability Matrix

This document maps all 134 checks from the master catalogue (`checks.json`) to their implementation disposition, execution class, and evidence prerequisites.

## Disposition Definitions

- **executable_detector**: Deterministic Python script sensor that directly verifies a technical condition (e.g. robots.txt parsing, XML schema validation, canonical URL matching).
- **semantic_assignment**: Structured evidence packet evaluated by AI agents according to explicit rubrics and dual-track remediation guidance.
- **proactive_declaration**: Autonomous audit-orchestrator recommendation generated from infrastructure cues (e.g., autonomous `/llms.txt` generation).

| Source Check ID | Skill Domain | Disposition | Execution | Evidence Prerequisites |
| :--- | :--- | :--- | :--- | :--- |
| A1 | Discoverability | executable_detector | http | raw_robots_response, headers |
| A2 | Discoverability | executable_detector | http | rfc9309_rules, user_agents |
| A3 | Discoverability | executable_detector | http | sitemap_xml_data, xml_namespace |
| A4 | Discoverability | executable_detector | http | crawl_delay_directive |
| A5 | Discoverability | executable_detector | http | status_code, waf_headers |
| B1 | Discoverability | executable_detector | http | initial_html_bytes, static_rate |
| B2 | Discoverability | executable_detector | http | canonical_tag_loc, current_url |
| B3 | Discoverability | executable_detector | http | meta_robots_tokens, x_robots_tag |
| B4 | Discoverability | executable_detector | http | source_links_href, visible_labels |
| B5 | Discoverability | executable_detector | http | sitemap_protocol_entries |
| C1-C5 | Discoverability | executable_detector | http | hydration_deficit_words, ssr_parity |
| H1-H3 | Discoverability | executable_detector | http | hreflang_iso_codes, mobile_viewport |
| I1-I2 | Discoverability | executable_detector | http | security_headers, mixed_content |
| J9-J10 | Discoverability | executable_detector | http | ai_crawler_access_matrix |
| E1 | Entity Identity | executable_detector | http | jsonld_root_types |
| E2 | Entity Identity | semantic_assignment | http | organization_name, logo_url |
| E3 | Entity Identity | executable_detector | http | product_cross_host_urls |
| E4 | Entity Identity | semantic_assignment | http | product_description, price_spec |
| E5 | Entity Identity | executable_detector | http | microdata_itemscope_tags |
| E6 | Entity Identity | executable_detector | http | schema_inheritance_tree |
| E7 | Entity Identity | semantic_assignment | http | speakable_css_selectors |
| BC1-BC8 | Entity Identity | semantic_assignment | http | b2b_service_offerings, credentials |
| F1-F5 | Fact Consistency | semantic_assignment | http | cross_page_claim_pairs |
| PP1-PP7 | Fact Consistency | executable_detector | http | multi_currency_prices, discounts |
| PROFILE_* | Fact Consistency | semantic_assignment | http | declared_social_profiles |
| SA1-SA9 | Corroboration | semantic_assignment | http | independent_citations, authority |
| SC1-SC7 | Corroboration | semantic_assignment | http | third_party_reviews, sentiment |
| N1-N15 | GEO Citability | executable_detector | http | causal_depth_score, conjunctions |
| BN1-BN9 | GEO Citability | executable_detector | http | statistical_density_ratio, numbers |
| ED1-ED9 | GEO Citability | executable_detector | http | author_bylines, eeat_credentials |
| ME1-ME8 | GEO Citability | executable_detector | http | passage_chunk_word_counts |
| EC1-EC9 | Engagement | semantic_assignment | http | user_intent_query_rubrics |
| D1-D5 | Engagement | executable_detector | http | table_rows, definition_lists |
| G1-G2 | Interactivity | proactive_declaration | http | llms_txt_presence |
| J1-J8 | Interactivity | proactive_declaration | http | webmcp_api_manifest |

---

## Provenance and Traceability Guarantees

Every candidate finding emitted by an `executable_detector` or `semantic_assignment` references:
1. **Source Locator**: The exact line number, CSS selector, or JSON path where the condition was observed.
2. **Cryptographic Fingerprint**: A SHA-256 hash uniquely identifying the evidence payload via `EvidenceRegistry`.
3. **Reproducibility**: Identical source inputs deterministically produce identical finding IDs (`F-{hash}`) and deduplication keys.

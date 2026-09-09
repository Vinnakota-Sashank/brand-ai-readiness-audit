# Technical SEO & Brand Visibility Foundations

Foundational standards and detection limits for web audit operations.

---

## 1. Schema Markup Detection Limitations
- `curl` and basic non-rendering HTTP fetchers cannot detect client-side JavaScript-injected Schema.org markup (e.g. plugins that mount JSON-LD dynamically).
- To accurately validate schema, use Google Rich Results Test or render via headless DOM parsers.
- Our audit evaluates initial raw HTML extractability directly to measure what non-JS AI retrieval bots see.

## 2. Priority Hierarchy of AI Search Readiness
1. **Crawlability & Indexation:** Can AI retrieval bots (`OAI-SearchBot`, `Claude-SearchBot`, `PerplexityBot`) reach and fetch the page without HTTP 4xx/5xx or `noindex` blocks?
2. **Entity Understanding:** Can machines resolve *Who* the brand is via Schema.org `Organization` and `sameAs` links?
3. **Factual Consistency:** Are prices, contacts, and availability consistent across all first-party pages?
4. **Answerability & GEO:** Does the content provide quantifiable numbers and mechanistic explanations (`how` / `why`)?
5. **Visitor Continuity:** Does the landing page provide immediate information scent and commercial CTAs to prevent referral bounce?

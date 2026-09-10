# Dual-Track Remediation Playbook for Brand AI Readiness

**Author:** Jayanth Reddy Konda & Research Engineering Team  
**Version:** 2.0.0  
**Standard:** Production Brand AI-Readiness & GEO Remediation Architecture

---

## 1. Remediation Philosophy: Dual-Track Architecture

Every brand AI-readiness defect has two complementary remediation vectors:
1. **Technical Track (`technical_fix`):** Structured data markup, server-side headers, robots.txt crawler rules, routing configurations, and semantic HTML executed by software engineers.
2. **Creative & Content Track (`creative_fix`):** Information architecture, heading hierarchy, answer-block synthesis, causal phrasing, and positioning clarity executed by copywriters and marketing teams.

---

## 2. Complete Remediation Catalog by Audit Domain

### A. Discoverability & Crawlability (`discoverability-audit`)

#### 1. AI Search Crawlers Blocked in `robots.txt`
* **Defect (`AI_BOTS_BLOCKED`):** `User-agent: OAI-SearchBot Disallow: /` or `User-agent: PerplexityBot Disallow: /`
* **Technical Fix:**
  ```text
  User-agent: OAI-SearchBot
  Allow: /

  User-agent: PerplexityBot
  Allow: /

  User-agent: Claude-Web
  Allow: /
  ```
* **Creative Fix:** Update legal and privacy notices to explicitly distinguish between permitting search retrieval for real-time citations and opting out of AI model pre-training.
* **Verification:** Run `curl -A "OAI-SearchBot" -I https://example.com/` and confirm HTTP 200 without `X-Robots-Tag: noindex`.

#### 2. Client-Rendered SPA Content Gap (`RENDERED_CONTENT_GAP`)
* **Defect:** Initial HTML contains <25 words due to client-side React/Vue rendering.
* **Technical Fix:** Implement Server-Side Rendering (SSR) via Next.js `getServerSideProps`/App Router or deploy dynamic pre-rendering edge workers.
* **Creative Fix:** Ensure that even before JavaScript hydration, static fallback HTML includes a 100-word descriptive executive summary, primary navigation links, and brand positioning statement.
* **Verification:** Fetch page via `curl -s https://example.com/ | wc -w` and verify visible word count exceeds 250 words in raw HTML.

---

### B. Machine Entity Identity & Schema (`entity-content-audit`)

#### 3. Missing Organization Entity Schema (`MISSING_ORGANIZATION_SCHEMA`)
* **Defect:** Homepage lacks machine-explicit `@graph` Schema.org Organization markup.
* **Technical Fix:**
  ```html
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Organization",
        "@id": "https://brand.com/#org",
        "name": "Canonical Brand Name",
        "url": "https://brand.com",
        "logo": "https://brand.com/assets/logo.png",
        "sameAs": [
          "https://www.wikidata.org/wiki/Q12345",
          "https://www.linkedin.com/company/brand",
          "https://twitter.com/brand"
        ]
      },
      {
        "@type": "WebSite",
        "@id": "https://brand.com/#website",
        "url": "https://brand.com",
        "name": "Canonical Brand Name",
        "publisher": {"@id": "https://brand.com/#org"}
      }
    ]
  }
  </script>
  ```
* **Creative Fix:** Standardize canonical brand spelling, taglines, and founder bylines across all footer and masthead copy.
* **Verification:** Validate output using `python3 skills/entity-content-audit/scripts/entity_content_check.py`.

---

### C. Generative Engine Optimization (`geo-content-audit`)

#### 4. Low Causal Depth & Shallow Assertions (`MISSING_IN_DEPTH_MECHANISMS`)
* **Defect:** Paragraphs lack causal conjunctions (`because`, `due to`, `enables`, `therefore`) and concrete metrics.
* **Technical Fix:** Embed structured `FAQPage` schema pairing high-intent questions with direct explanatory answers.
* **Creative Fix:** Rewrite value propositions into the **Inverted-Pyramid Citability Pattern**:
  * *Before:* "Our software revolutionizes productivity through cutting-edge cloud technology."
  * *After:* "BrandCorp accelerates developer sprint velocity by 35% because our distributed cache eliminates disk I/O latency. Consequently, pipeline execution times drop from 12 minutes to under 80 seconds."
* **Verification:** Run `geo_content_check.py` and confirm depth score >= 3.

#### 5. Substantive Content Under Minimum Citability Threshold (`CONTENT_DEPTH_INSUFFICIENT`)
* **Defect:** Key commercial page contains only 50-180 words of visible text.
* **Technical Fix:** Add structured product specification tables (`<table>`, `<dl>`) and FAQ modules directly into static HTML.
* **Creative Fix:** Expand page body with 250-400 words detailing composition, technical specifications, origin provenance, and direct answers to common customer questions.
* **Verification:** Confirm body word count exceeds 250 words of descriptive text.

#### 6. Ambiguous Pronoun Density (`PROACTIVE.GEO.PRONOUN_DENSITY.001`)
* **Defect:** Ambiguous 3rd-person pronouns (`it`, `they`, `this`) exceed 3.0% of body text, causing attribution loss in multi-document synthesis.
* **Technical Fix:** Run automated entity-substitution linter across CMS templates to ensure entity anchors are preserved.
* **Creative Fix:** Replace ambiguous pronouns with canonical brand, product, or feature nouns. Make the entity the grammatical subject of the sentence.
* **Verification:** Confirm ambiguous pronoun density drops below 2.0%.

#### 7. Non-Optimal Passage Chunk Lengths (`PROACTIVE.GEO.PASSAGE_CHUNK_LENGTH.001`)
* **Defect:** Paragraphs are either monolithic text blocks (>250 words) or fragmented single-line snippets (<45 words).
* **Technical Fix:** Enforce semantic chunk container boundaries with subheadings (`<h3>`) and semantic bullet points.
* **Creative Fix:** Segment narrative into self-contained 130-170 word concept units (CMU AutoGEO optimal band), each answering one user question.
* **Verification:** Verify average substantive paragraph word count falls between 100 and 180 words.

---

### D. Multi-Page Fact Consistency (`fact-consistency-audit`)

#### 8. Cross-Page Pricing & Plan Contradictions (`PRICE_CONTRADICTION`)
* **Defect:** Homepage mentions *"Starts at $19/mo"* while Pricing page states *"Starts at $49/mo"*.
* **Technical Fix:** Centralize commercial parameters into a single source-of-truth CMS token or configuration API rendered synchronously across all templates.
* **Creative Fix:** Audit all promotional landing pages and blog references to synchronize discount calculations, legacy tiers, and annual vs. monthly billing terms.
* **Verification:** Run `fact_consistency_check.py` and confirm 0 detected contradictions.

#### 9. Discrepant Contact & Support Credentials (`CONTACT_CONTRADICTION`)
* **Defect:** Footer displays telephone `+1-800-555-0199` while Contact page displays `+1-888-555-0122`.
* **Technical Fix:** Define a single `ContactPoint` JSON-LD object within site-wide Organization schema referenced across all pages.
* **Creative Fix:** Audit footer, header, and support documentation to ensure identical primary phone, email, and operating hours.
* **Verification:** Confirm uniform contact credentials across all indexed pages.

---

### E. Corroboration & Authority Anchors (`corroboration-authority-audit`)

#### 10. Broken or Missing Knowledge Graph SameAs Links (`BROKEN_SAMEAS_LINK`)
* **Defect:** Organization `sameAs` array points to missing social handles or 404 URL targets.
* **Technical Fix:** Audit all `sameAs` URIs to confirm HTTP 200 resolution. Include authoritative identifiers:
  ```json
  "sameAs": [
    "https://www.wikidata.org/wiki/Q114881775",
    "https://en.wikipedia.org/wiki/Brand_Name",
    "https://github.com/brand-org",
    "https://www.crunchbase.com/organization/brand"
  ]
  ```
* **Creative Fix:** Claim and verify official social and registry profiles (Wikidata, Crunchbase, LinkedIn) with matching canonical brand names and headquarters metadata.
* **Verification:** Run `corroboration_check.py` to confirm all authority targets resolve with status 200.

#### 11. Absence of Primary Outbound Citations (`PROACTIVE.GEO.AUTHORITY_CITATIONS.001`)
* **Defect:** Technical claims and industry assertions lack external outbound citations to primary sources.
* **Technical Fix:** Add outbound anchor links with `rel="noopener"` pointing to DOI papers, standards bodies (W3C, IEEE, ISO), or government datasets.
* **Creative Fix:** Replace generic claims ("studies show") with named citations: *"According to the 2024 National Renewable Energy Laboratory benchmark..."*
* **Verification:** Confirm at least one authoritative outbound link exists on informational/article pages.

---

### F. Engagement & Contextual Experience (`engagement-context-audit`)

#### 12. Missing Primary Topic Scent & H1 Anchoring (`MISSING_H1_TOPIC_SCENT`)
* **Defect:** Page lacks a single clear `<h1>` heading or uses generic labels like "Welcome" or "Home".
* **Technical Fix:** Render exactly one `<h1>` containing the primary product/entity name and primary category descriptor:
  ```html
  <h1>Cold-Pressed Organic Sesame Oil — Two Brothers Organic Farms</h1>
  ```
* **Creative Fix:** Align page title, meta description, and H1 heading so that the core user search intent is answered in the first visible viewport.
* **Verification:** Run `engagement_check.py` and verify presence of a single, descriptive H1 tag.

#### 13. Mobile Viewport & Scent Accessibility Deficiencies (`ENGAGEMENT_SCENT_DEFICIT`)
* **Defect:** Interactive CTA buttons and key policy disclaimers lack visible text or are obscured by sticky overlays.
* **Technical Fix:** Ensure all interactive elements include descriptive `aria-label` or visible text (e.g. "View Pricing Tiers" instead of "Click Here").
* **Creative Fix:** Provide clear descriptive anchor copy for internal navigation links to preserve semantic scent for traversing bots.
* **Verification:** Confirm audit returns zero critical engagement scent findings.

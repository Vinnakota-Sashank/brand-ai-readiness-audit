# Dual-Track Remediation Playbook for Brand AI Readiness

**Author:** Jayanth Reddy Konda  
**Version:** 1.0.0  
**Standard:** Production Brand AI-Readiness & GEO Remediation Guide

---

## 1. Remediation Philosophy

Every brand AI-readiness defect has two complementary remediation vectors:
1. **Technical Track (`technical_fix`):** Structured data markup, server-side headers, robots.txt crawler rules, and routing configurations executed by software engineers.
2. **Creative & Content Track (`creative_fix`):** Information architecture, heading hierarchy, answer-block synthesis, and positioning clarity executed by copywriters and marketing teams.

---

## 2. Remediation Catalog by Category

### A. Discoverability & Indexation

#### 1. AI Search Crawlers Blocked in `robots.txt`
- **Defect:** `User-agent: OAI-SearchBot Disallow: /` or `User-agent: PerplexityBot Disallow: /`
- **Technical Fix:**
  ```text
  User-agent: OAI-SearchBot
  Allow: /

  User-agent: PerplexityBot
  Allow: /

  User-agent: Claude-Web
  Allow: /
  ```
- **Creative Fix:** Update legal/governance disclosures to clarify that retrieval access for brand citations is permitted while reserving foundation model training rights.
- **Verification:** Run `curl -A "OAI-SearchBot" -I https://example.com/` and confirm HTTP 200 without meta noindex.

---

### B. Machine Entity Identity & Schema

#### 2. Missing Organization Entity Schema
- **Defect:** Homepage lacks machine-explicit `@graph` Schema.org Organization markup.
- **Technical Fix:**
  ```html
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@graph": [{
        "@type": "Organization",
        "@id": "https://brand.com/#org",
        "name": "Canonical Brand Name",
        "url": "https://brand.com",
        "logo": "https://brand.com/assets/logo.png",
        "sameAs": ["https://www.wikidata.org/wiki/Q12345",
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
- **Creative Fix:** Standardize brand naming in hero headings across all web properties.
- **Verification:** Test with Google Rich Results Test or validate with `python3 skills/entity-content-audit/scripts/entity_content_check.py`.

---

### C. Generative Engine Optimization (GEO)

#### 3. Low Causal Depth & Vague Marketing Copy
- **Defect:** Paragraphs lack causal conjunctions (`because`, `due to`, `therefore`) and concrete metrics.
- **Technical Fix:** Add structured `FAQPage` or `TechArticle` schema with machine-parsable question-answer pairs.
- **Creative Fix:** Rewrite key value propositions into the **Inverted-Pyramid Citability Pattern**:
  - *Before:* "Our cutting-edge software revolutionizes team productivity through modern cloud technology."
  - *After:* "BrandCorp accelerates developer sprint velocity by 35% because our distributed cache eliminates disk I/O latency. As a result, pipeline execution times drop from 12 minutes to under 80 seconds."
- **Verification:** Run `python3 skills/geo-content-audit/scripts/geo_content_check.py` and confirm GEO Mechanistic Depth score > 0.80.

---

### D. Multi-Page Fact Consistency

#### 4. Cross-Page Pricing / Plan Contradictions
- **Defect:** Homepage mentions *"Starts at $19/mo"* while Pricing page says *"Starts at $49/mo"*.
- **Technical Fix:** Consolidate pricing variables into a single source-of-truth database or CMS token rendered synchronously across all templates.
- **Creative Fix:** Audit all landing page copy to synchronize promotional rates, legacy tiers, and annual discount calculations.
- **Verification:** Run `python3 skills/fact-consistency-audit/scripts/fact_consistency_check.py` and confirm 0 fact contradictions.

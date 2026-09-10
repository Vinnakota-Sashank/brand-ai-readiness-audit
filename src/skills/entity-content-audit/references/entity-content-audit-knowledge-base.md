# ENTITY-CONTENT-AUDIT KNOWLEDGE BASE

## Table of Contents

- [Preconditions](#preconditions)
- [C1. Identity explicitness](#c1-identity-explicitness)
- [C2. Product/offer extraction](#c2-productoffer-extraction)
- [C3. Claim completeness](#c3-claim-completeness)
- [C4. sameAs corroboration (recommendation only)](#c4-sameas-corroboration-recommendation-only)
- [Evidence standards](#evidence-standards)
- [1. Syntax & Placement Best Practices](#1-syntax-placement-best-practices)
- [2. Organization Schema](#2-organization-schema)
- [3. Product & Offer Schema](#3-product-offer-schema)
- [4. Defect vs Recommendation Rules](#4-defect-vs-recommendation-rules)
- [Signal](#signal)
- [Do NOT Report As Defect When:](#do-not-report-as-defect-when)
- [Report ONLY As:](#report-only-as)
- [Report As Defect ONLY When:](#report-as-defect-only-when)
- [1. Master Linked Graph Template (Organization + WebSite + SearchAction)](#1-master-linked-graph-template-organization-website-searchaction)
- [2. Product & Offer Schema with Full Answerability](#2-product-offer-schema-with-full-answerability)

---

This document contains all mandatory rules, schemas, and taxonomies required for this skill.



========================================================================
=== SOURCE FILE: entity-contracts.md ===
========================================================================

# Entity & Content Audit — Check Contracts

Every check in this skill states what it measures, what evidence is required,
and what does **not** constitute a defect. Findings are only emitted for
what is directly observable in the fetched initial HTML.

## Preconditions
Entity analysis needs real content. If the initial HTML carries too few
words to analyze (e.g. a CSR shell), the script returns
`status: "inconclusive"` with an explanatory error instead of guessing —
a rendering-gap finding belongs to `discoverability-audit`, and this skill
must not fabricate entity verdicts from an empty page.

## C1. Identity explicitness
- **Measures:** Whether a machine can determine **who** the site is from
  three signals: Organization/Brand JSON-LD, `og:site_name`, or an
  extractable `<title>` identity.
- **Defect:** All three absent → "Organization identity not machine-explicit",
  severity `medium`, confidence `medium` (a human may still infer identity;
  machines often cannot).
- **Not a defect:** Any one explicit signal present. Identity inferred only
  from imagery or logo files does not count (machines reading text cannot
  see it).

## C2. Product/offer extraction
- **Measures:** Presence and explicitness of product/offering entities
  (structured data first, then explicit markup).
- **Defect:** A detected product lacking explicit attributes (price,
  description) → `low`, confidence `high`.
- **Not a defect:** A site with no products (services, portfolios) —
  absence of a product entity on a non-commerce site is expected.

## C3. Claim completeness
- **Measures:** Whether the flagship entity carries attribute coverage
  (L2/L3 facts: what is offered, for whom, at what quality) in machine-
  readable form.
- **Defect:** Entity exists but claims are only implicit in prose.
- **Severity:** `low` to `medium` depending on how much a summarizing AI
  would have to guess.

## C4. sameAs corroboration (recommendation only)
- **Measures:** Presence of `sameAs` links on the Organization entity.
- **Never a defect by itself.** Missing `sameAs` without evidence of actual
  entity confusion is emitted as a **recommendation**, not a finding —
  absence of one optional property is not proof of disambiguation failure.
  Genuine ambiguity (competing entities sharing the name) would require
  corroborating evidence, which is the `corroboration-authority-audit`
  skill's job.

## Evidence standards
- Every finding quotes the observed state (which signals were present/absent).
- Confidence is stated per finding.
- The skill never infers facts from absent markup beyond what the check
  contract above explicitly licenses.


========================================================================
=== SOURCE FILE: structured-data-validation.md ===
========================================================================

# Structured Data Reference & Validation Guide

Implementation rules for JSON-LD structured data to ensure unambiguous entity recognition, offer extraction, and rich result eligibility.

---

## 1. Syntax & Placement Best Practices

- **Format:** JSON-LD format inside `<script type="application/ld+json">` is strongly recommended.
- **Graph Combining (`@graph`):** Combine multiple entities into a single linked graph to preserve relationships between the publisher, webpage, and main offering.

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@graph": [{
      "@type": "Organization",
      "@id": "https://example.com/#organization",
      "name": "Acme Aerospace",
      "url": "https://example.com",
      "logo": "https://example.com/logo.png",
      "sameAs": ["https://www.wikidata.org/wiki/Q12345",
        "https://www.linkedin.com/company/acme"
      ]
    },
    {
      "@type": "Product",
      "@id": "https://example.com/products/x9#product",
      "name": "Velocity X9",
      "brand": { "@id": "https://example.com/#organization" },
      "description": "Commercial autonomous survey drone with 4K camera.",
      "offers": {
        "@type": "Offer",
        "price": "5499",
        "priceCurrency": "INR",
        "availability": "https://schema.org/InStock",
        "url": "https://example.com/products/x9"
      }
    }
  ]
}
</script>
```

---

## 2. Organization Schema

Explicit organization metadata enables knowledge graph recognition and entity disambiguation.

| Property | Type | Requirement | Description |
| :--- | :--- | :--- | :--- |
| `name` | Text | Required | Official brand name |
| `url` | URL | Required | Canonical homepage URL |
| `logo` | ImageURL / ImageObject | Recommended | Direct link to high-res logo |
| `sameAs` | Array of URLs | Recommended | Authoritative profile URLs (Wikidata, Crunchbase, official social) |
| `contactPoint` | ContactPoint | Optional | Support phone and email details |

---

## 3. Product & Offer Schema

Ensures commercial terms (pricing, availability, variants) are extracted deterministically by AI assistants.

| Property | Type | Requirement | Description |
| :--- | :--- | :--- | :--- |
| `name` | Text | Required | Official product title |
| `offers.price` | Number / Text | Required | Numerical price without currency symbols |
| `offers.priceCurrency` | ISO 4217 Text | Required | Currency code (e.g. `USD`, `INR`, `EUR`) |
| `offers.availability` | ItemAvailability URL | Required | `https://schema.org/InStock`, `OutOfStock`, `PreOrder` |
| `brand` | Brand / Organization | Recommended | Producing brand entity |
| `description` | Text | Recommended | Accurate product summary |
| `sku` | Text | Optional | Stock keeping unit |

---

## 4. Defect vs Recommendation Rules

- **Absence of Markup:** An extractability opportunity (`recommendation`), NEVER an automatic defect if visible text is clear.
- **Markup-vs-DOM Contradiction:** A verified defect (`finding`) if JSON-LD price contradicts visible on-page price.
- **Incomplete Product Markup:** A low-severity defect if Product schema exists but omits price or availability.


========================================================================
=== SOURCE FILE: no-jsonld.md ===
========================================================================

# False Positive Decision Table: Absence of JSON-LD Schema

## Signal
Page contains readable HTML text but has no `<script type="application/ld+json">` blocks.

## Do NOT Report As Defect When:
- The page is a standard informational or blog article where `<title>`, `<h1>`, and OpenGraph meta tags clearly state the entity identity.
- The visible text is explicit and unambiguous for human and AI readers.
- The site is crawlable and has no ranking or factual ambiguity issues.

## Report ONLY As:
- **Proactive Recommendation (`proactive_actions[]`)**: Suggesting structured data to enhance machine extraction and rich snippet eligibility.

## Report As Defect ONLY When:
- The page is a core commercial flagship product or organization page where crucial facts (pricing variants, availability state, technical specifications) are embedded in complex client-side tables or obfuscated structures that cannot be extracted deterministically without structured schema.



========================================================================
=== SOURCE FILE: schema-templates-catalog.md ===
========================================================================

# Schema.org Copy-Paste Templates Catalog

## 1. Master Linked Graph Template (Organization + WebSite + SearchAction)

Embed this single linked JSON-LD block inside the `<head>` of the homepage:

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@graph": [{
      "@type": "Organization",
      "@id": "https://example.com/#organization",
      "name": "Acme Corporation",
      "url": "https://example.com",
      "logo": "https://example.com/assets/logo.png",
      "sameAs": ["https://www.wikidata.org/wiki/Q123456",
        "https://en.wikipedia.org/wiki/Acme_Corp",
        "https://www.linkedin.com/company/acme-corp",
        "https://twitter.com/acme"
      ],
      "contactPoint": {
        "@type": "ContactPoint",
        "telephone": "+1-800-555-0199",
        "contactType": "customer service",
        "areaServed": "US",
        "availableLanguage": ["en", "es"]
      }
    },
    {
      "@type": "WebSite",
      "@id": "https://example.com/#website",
      "url": "https://example.com",
      "name": "Acme Official Platform",
      "publisher": {
        "@id": "https://example.com/#organization"
      },
      "potentialAction": {
        "@type": "SearchAction",
        "target": "https://example.com/search?q={search_term_string}",
        "query-input": "required name=search_term_string"
      }
    }
  ]
}
</script>
```

## 2. Product & Offer Schema with Full Answerability

Embed this on product detail pages to satisfy all commercial AI shopping agents:

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "Acme CloudSync Enterprise",
  "image": "https://example.com/images/cloudsync.jpg",
  "description": "Enterprise cloud synchronization platform with AES-256 encryption and automated failover.",
  "sku": "ACME-CS-ENT",
  "brand": {
    "@type": "Brand",
    "name": "Acme"
  },
  "offers": {
    "@type": "Offer",
    "url": "https://example.com/pricing",
    "price": "49.00",
    "priceCurrency": "USD",
    "priceValidUntil": "2027-12-31",
    "availability": "https://schema.org/InStock",
    "seller": {
      "@id": "https://example.com/#organization"
    }
  }
}
</script>
```

# FACT-CONSISTENCY-AUDIT KNOWLEDGE BASE

## Table of Contents

- [Signal](#signal)
- [Do NOT Report As Defect When:](#do-not-report-as-defect-when)
- [Report As Defect ONLY When:](#report-as-defect-only-when)
- [1. The Entity Disambiguation Problem](#1-the-entity-disambiguation-problem)
- [2. Multi-Source Corroboration Links (`sameAs`)](#2-multi-source-corroboration-links-sameas)
  - [Example Schema Implementation](#example-schema-implementation)
- [3. Authoritative About Page Structure](#3-authoritative-about-page-structure)
- [1. The Timestamp & Freshness Hierarchy](#1-the-timestamp-freshness-hierarchy)
- [2. Temporal Drift & Legacy Template Rules](#2-temporal-drift-legacy-template-rules)
- [3. Product Lifecycle Consistency Matrix](#3-product-lifecycle-consistency-matrix)
  - [Contradiction Criteria:](#contradiction-criteria)
  - [Verification Guardrail:](#verification-guardrail)
- [1. Temporal Metadata & Freshness Signals](#1-temporal-metadata-freshness-signals)
- [2. Cross-Page Fact Consistency](#2-cross-page-fact-consistency)
- [3. Discontinued / Outdated Product Claims](#3-discontinued-outdated-product-claims)
- [C1. Scoped Price Contradictions](#c1-scoped-price-contradictions)
- [C2. Product Lifecycle & Stock State Synchronization](#c2-product-lifecycle-stock-state-synchronization)
- [C3. Contact Channel & Support Consistency](#c3-contact-channel-support-consistency)
- [C4. Temporal Freshness & Copyright Timestamps](#c4-temporal-freshness-copyright-timestamps)
- [1. Contextual Scope Invariant](#1-contextual-scope-invariant)
  - [False Positive Prevention (What NOT to Compare):](#false-positive-prevention-what-not-to-compare)
- [2. Currency & Price Normalization Algorithm](#2-currency-price-normalization-algorithm)
- [3. Contact & Phone Normalization](#3-contact-phone-normalization)

---

This document contains all mandatory rules, schemas, and taxonomies required for this skill.



========================================================================
=== SOURCE FILE: multi-tier-pricing.md ===
========================================================================

# False Positive Decision Table: Multi-Tier Pricing Contexts

## Signal
Multiple distinct price values (e.g. $10, $25, $50, $250) appear on the same domain or pricing page.

## Do NOT Report As Defect When:
- Prices correspond to distinct subscription tiers (e.g. "Starter Tier: $10/mo" vs "Pro Tier: $50/mo" vs "Enterprise: $250/mo").
- Prices reflect monthly vs annual billing discounts (e.g. "$12 billed monthly" vs "$10/mo billed annually").
- Prices refer to different individual products in a product catalog or category overview page.
- Prices represent volume discount brackets or regional currency localizations.

## Report As Defect ONLY When:
- **Verified Cross-Page Contradiction**: The exact same product/tier (e.g. "Velocity X9 Drone") is stated at one price on the main product landing page (e.g. "₹5,499") and a different contradictory price on a secondary/legacy page (e.g. "₹4,999") without clear discount or archival context.
- **Markup Discrepancy**: The visible on-page price states "$49", but the JSON-LD `offers.price` schema states `"99"`.



========================================================================
=== SOURCE FILE: entity-corroboration.md ===
========================================================================

# Entity Corroboration & Knowledge Graph Grounding

AI assistants cross-verify facts against independent web sources to validate claims and resolve brand ambiguities. This document outlines best practices for entity disambiguation and cross-web grounding.

---

## 1. The Entity Disambiguation Problem

When multiple entities share a brand name or acronym (e.g., "Apex", "Canvas", "Beacon"), AI assistants can conflate products, assign incorrect founders, or attribute competitor features unless the brand provides authoritative grounding links.

---

## 2. Multi-Source Corroboration Links (`sameAs`)

In the root `Organization` JSON-LD schema, provide `sameAs` links to authoritative third-party repositories:

- **Wikidata**: The gold-standard open knowledge base (`https://www.wikidata.org/wiki/Q...`).
- **Wikipedia**: Authoritative encyclopedia entry (if notable).
- **Crunchbase / PitchBook**: Authoritative corporate entity registries.
- **Verified Social Profiles**: Official GitHub, LinkedIn, X/Twitter, and YouTube profiles.

### Example Schema Implementation

```json
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "Beacon Intelligence",
  "url": "https://beaconintelligence.example",
  "sameAs": ["https://www.wikidata.org/wiki/Q98765432",
    "https://www.crunchbase.com/organization/beacon-intelligence",
    "https://www.linkedin.com/company/beacon-intel",
    "https://github.com/beacon-intel"
  ]
}
```

---

## 3. Authoritative About Page Structure

A machine-verifiable About Page must contain:
1. **Clear Entity Statement**: "Beacon Intelligence is an enterprise AI observability company founded in 2021 by Jane Doe and John Smith."
2. **Physical / Legal Registry Data**: Legal registered company name, corporate headquarters city/state/country.
3. **Canonical Domain Declarations**: Explicit statement of official operating domains.



========================================================================
=== SOURCE FILE: temporal-freshness.md ===
========================================================================

# Temporal Freshness & Product Lifecycle Reference

This reference defines the verification rules for temporal freshness, copyright drift, and product lifecycle state consistency across multi-page brand websites.

---

## 1. The Timestamp & Freshness Hierarchy

AI retrieval systems weight first-party brand statements based on temporal signals. When different pages on the same domain state conflicting facts, AI models evaluate freshness using the following signal hierarchy (ordered from strongest to weakest):

1. **Explicit Schema.org Timestamps:** `dateModified` and `datePublished` in JSON-LD.
2. **HTTP Last-Modified Header:** Server-validated document mutation timestamp.
3. **OpenGraph Timestamps:** `article:modified_time` and `og:updated_time`.
4. **On-Page Copyright Statement:** `© [Year] [Organization]`.

---

## 2. Temporal Drift & Legacy Template Rules

| Signal | Criteria | Finding / Classification | Action |
|---|---|---|---|
| **Multi-Year Copyright Drift** | Copyright year on one active page is $\ge 2$ years older than the homepage (e.g. 2022 on `/terms` vs 2026 on `/`). | **Low** (`LEGACY_FACT_PROPAGATION`) | Update legacy page templates to dynamically inherit current copyright year. |
| **Outdated Tagline Drift** | An old slogan is stated in footer markup while an active repositioning campaign exists on the homepage. | **Low** (`LEGACY_FACT_PROPAGATION`) | Harmonize brand tagline strings across all active layouts. |
| **Current Copyright Year** | Copyright year matches current calendar year or current year $\pm 1$. | **Pass** | No action required. |

---

## 3. Product Lifecycle Consistency Matrix

A major failure mode in AI-generated answers is recommending discontinued or out-of-stock products as active offerings, caused by contradictory lifecycle states across the brand's own pages.

### Contradiction Criteria:
- **Discontinued vs Active Conflict:** A product is declared `discontinued` or `out of production` on a product notice/archive page, but is marked `InStock` or listed as an active commercial offering on a pricing or category page.
- **Severity:** `High` (`DISCONTINUED_VS_CURRENT_CONFLICT`).
- **Impact:** AI shopping and search assistants provide inaccurate availability guidance to potential buyers.

### Verification Guardrail:
- Never classify an entire page as discontinued based on a single word in global headers or footers. The discontinued indicator must be strictly bound to the specific product entity or heading.


========================================================================
=== SOURCE FILE: freshness-checklist.md ===
========================================================================

# Freshness & Temporal Signals Checklist

This reference covers the checks required to detect stale, unmaintained, or conflicting facts that cause AI assistants to downgrade trust or hallucinate outdated brand data.

---

## 1. Temporal Metadata & Freshness Signals

- [] **Footer Copyright Year**: Does the footer copyright match the current year (or dynamic date script), or does it reflect an outdated prior year?
- [] **HTTP Headers & Meta Tags**:
  - Are `Last-Modified` HTTP headers returned on static assets and pages?
  - Are `<meta property="article:modified_time">` or `<meta property="og:updated_time">` exposed?
- [] **JSON-LD Temporal Properties**:
  - `datePublished` and `dateModified` in `Article`, `BlogPosting`, or `WebPage` schemas.
  - `priceValidUntil` in `Offer` schemas.

---

## 2. Cross-Page Fact Consistency

- [] **Pricing & Feature Divergence**: Do product pricing, tier limits, or feature matrices differ between the homepage, dedicated pricing page, and docs?
- [] **Company Identity Consistency**: Are company name, headquarters address, phone numbers (NAP), and executive leadership consistent across the About, Contact, and Legal pages?

---

## 3. Discontinued / Outdated Product Claims

- [] **Legacy Product References**: Does the site prominently advertise deprecated products, sunset APIs, or legacy pricing tiers without clear obsolescence notices?
- [] **Changelog & Release Notes Cadence**: Are recent product updates or version release notes accessible within the last 90 days?



========================================================================
=== SOURCE FILE: fact-contracts.md ===
========================================================================

# Fact Consistency & Lifecycle Audit — Check Contracts

Formal check contracts, decision thresholds, and evidence criteria for first-party fact consistency and lifecycle synchronization.

---

## C1. Scoped Price Contradictions
- **Measures:** Numeric prices, plan tier figures, and currency symbols across sampled first-party pages for the identical named entity.
- **Defect:** Two or more pages publishing different active prices for the same product without qualifying scope (`FIRST_PARTY_FACT_CONFLICT`, Severity: `high`, Confidence: `high`).
- **Not a defect:** Distinct commercial plan tiers (e.g. Basic \$10 vs Pro \$50) or seasonal promotions clearly scoped with temporal qualifiers.

---

## C2. Product Lifecycle & Stock State Synchronization
- **Measures:** Commercial lifecycle status (active, in_stock, out_of_stock, discontinued, retired) declared across product pages and listings.
- **Defect:** A product marked as discontinued on one page but actively listed as in-stock on another (`DISCONTINUED_VS_CURRENT_CONFLICT`, Severity: `high`).
- **Not a defect:** Backorder items with stated delivery estimates.

---

## C3. Contact Channel & Support Consistency
- **Measures:** Primary support email addresses, phone numbers, and physical addresses across contact, footer, and support pages.
- **Defect:** Multiple conflicting primary contact points without geographic or department qualifiers (`INCONSISTENT_CONTACT_INFO`, Severity: `medium`).

---

## C4. Temporal Freshness & Copyright Timestamps
- **Measures:** Copyright year notices and dateModified timestamps.
- **Defect:** Multi-year outdated copyright notices across core routes suggesting stale site maintenance (`TEMPORAL_FRESHNESS_DRIFT`, Severity: `low`).


========================================================================
=== SOURCE FILE: fact-normalization.md ===
========================================================================

# Fact Normalization & Contradiction Detection Reference

This reference defines the mathematical normalization algorithms and strict contextual scoping rules required to eliminate false positive contradiction findings across first-party pages.

---

## 1. Contextual Scope Invariant

A finding of `FIRST_PARTY_FACT_CONFLICT` is **valid ONLY when two or more first-party statements share the EXACT SAME entity, attribute, and scope**:

$$\text{Conflict}(\text{Fact}_A, \text{Fact}_B) \iff (\text{Entity}_A = \text{Entity}_B) \land (\text{Attribute}_A = \text{Attribute}_B) \land (\text{Scope}_A = \text{Scope}_B) \land (\text{Val}_A \neq \text{Val}_B)$$

### False Positive Prevention (What NOT to Compare):
- **Distinct Pricing Tiers:** A \$10/mo "Starter Tier" and \$50/mo "Enterprise Tier" share the attribute `price` but have different `entity` scopes. Comparing them as a contradiction is an automatic evaluation failure.
- **Volume & Billing Cycles:** Annual pricing (\$8/mo billed annually) vs Monthly pricing (\$10/mo billed monthly) represent distinct billing scopes.
- **Regional Currencies:** \$100 USD vs €95 EUR represent distinct currency scopes.

---

## 2. Currency & Price Normalization Algorithm

To compare prices across disparate formats (US, UK, Indian, European), values must undergo strict digit normalization:

| Raw String | Locale / Format | Normalized Value | Notes |
|---|---|---|---|
| `₹5,499.00` | INR with decimal | `5499` | Strip currency symbol, comma, and trailing `.00`. |
| `$49.99` | USD standard | `49` | Normalized to base integer unit. |
| `€1.250,50` | European (dot thousands, comma decimal) | `1250` | Strip dot group separator, discard decimal comma. |
| `£99 / month` | GBP subscription | `99` | Strip cadence suffix and whitespace. |

---

## 3. Contact & Phone Normalization

- **Phone Numbers:** Strip non-digits (`+1 (800) 555-0199` $\to$ `18005550199`). Compare only within the same contact department scope (e.g. Sales Phone vs Support Phone).
- **Email Addresses:** Lowercase and strip whitespace. Scoped by department mailbox (`support@brand.com` vs `sales@brand.com`).

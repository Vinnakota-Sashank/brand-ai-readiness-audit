# ENGAGEMENT-CONTEXT-AUDIT KNOWLEDGE BASE

## Table of Contents

- [1. First-Visit Orientation Heuristics (Above-the-Fold)](#1-first-visit-orientation-heuristics-above-the-fold)
- [2. Heading Hierarchy & Information Scent](#2-heading-hierarchy-information-scent)
- [3. Navigational Integrity & Journey Continuity](#3-navigational-integrity-journey-continuity)
- [1. Conclusion-First Writing Architecture](#1-conclusion-first-writing-architecture)
- [2. Heading Hierarchy & Information Scent](#2-heading-hierarchy-information-scent)
- [3. Snippet Visibility Controls](#3-snippet-visibility-controls)
- [C1. 5-Second Orientation & Heading Information Scent](#c1-5-second-orientation-heading-information-scent)
- [C2. Destination Discoverability & Navigation Friction](#c2-destination-discoverability-navigation-friction)
- [C3. Intent-to-Landing Alignment](#c3-intent-to-landing-alignment)
- [1. The 4-Question First-Visit Orientation Test](#1-the-4-question-first-visit-orientation-test)
- [2. Heading Information Scent Matrix](#2-heading-information-scent-matrix)
- [3. Destination Reachability & Navigation Friction](#3-destination-reachability-navigation-friction)
- [4. Intent-to-Landing Match (Specialized Routes)](#4-intent-to-landing-match-specialized-routes)

---

This document contains all mandatory rules, schemas, and taxonomies required for this skill.



========================================================================
=== SOURCE FILE: engagement-rubric.md ===
========================================================================

# On-Site Orientation & Engagement Heuristics Rubric

This rubric evaluates how well a website retains visitors who arrive from AI search referrals, and how easily machines and humans comprehend the core offering within the first 5 seconds.

---

## 1. First-Visit Orientation Heuristics (Above-the-Fold)

- **The 5-Second Test**: Does the page immediately answer three core questions in semantic text without scrolling?
  1. *What is this product/service?*
  2. *Who is it for?*
  3. *What is the primary next step / Call to Action (CTA)?*
- **Hero Area Text Clarity**: Avoid vague buzzwords ("The next generation of synergy"). Demand concrete, specific value propositions ("Automated SOC 2 compliance for AWS and GCP environments").

---

## 2. Heading Hierarchy & Information Scent

- **Semantic Heading Flow (`H1` -> `H2` -> `H3`)**:
  - Exactly one substantive `<h1>` describing the page's core topic.
  - Logical `<h2>` subsections organizing features, workflows, and proofs.
  - Clear `<h3>` detail blocks.
- **Scannable Information Scent**: Headers must provide meaningful standalone value so both skimming human readers and AI summarizers can parse the key takeaways without reading full paragraphs.

---

## 3. Navigational Integrity & Journey Continuity

- **Clear Primary Navigation**: Visible links to Product, Features, Pricing, Docs, and About without hidden or broken multi-level hover menus.
- **Context Retention**: When users click from a specific AI citation link (e.g. deep link to a feature), does the destination page retain context or dump them into a generic homepage redirect?
- **Frictionless CTAs**: Clear, accessible buttons with unambiguous labels ("Start Free Trial", "Book Demo", "Read Documentation").



========================================================================
=== SOURCE FILE: ai-snippet-guidelines.md ===
========================================================================

# AI Snippet & Information Scent Guidelines

How to structure on-page content so AI search assistants and human visitors can immediately extract answers and orient without bouncing.

---

## 1. Conclusion-First Writing Architecture

AI models and skimming visitors prioritize direct answers in above-the-fold passages:

- **Direct Answer in Lead Paragraph:** State the core definition, price, or product capability within the first 50–100 words.
- **Fact-Dense Sentences:** Use explicit combinations of `[Subject] + [Attribute] + [Numerical Value/Unit] + [Timeframe]`.
  - *Poor:* "Our revolutionary solution offers unprecedented affordability and power."
  - *Strong:* "The Velocity X9 drone costs ₹5,499, delivers 30 minutes of flight time, and captures 4K 60fps video."

---

## 2. Heading Hierarchy & Information Scent

Headings provide structural boundaries for passage indexing and AI chunking:

- **Single H1 per Page:** The primary `<h1>` must clearly name the brand, product, or core topic. Avoid generic filler titles ("Welcome", "Home", "Overview").
- **Question-Form H2/H3 Headings:** Phrase subheadings as clear questions or explicit topic statements (e.g. `<h2>What is the battery range of Velocity X9?</h2>`).
- **No Skipping Levels:** Maintain a strict logical hierarchy (`H1` -> `H2` -> `H3`). Never skip from `H1` directly to `H4`.

---

## 3. Snippet Visibility Controls

| Directive | Implementation | Effect on AI Answers |
| :--- | :--- | :--- |
| `nosnippet` | `<meta name="robots" content="nosnippet">` | Prevents the page from being quoted in snippets or AI Overviews entirely. |
| `max-snippet` | `<meta name="robots" content="max-snippet:160">` | Restricts snippet quotes to the specified character length. |
| `data-nosnippet` | `<div data-nosnippet>...</div>` | Excludes specific proprietary text or pricing footnotes from AI quotes while keeping the rest indexable. |


========================================================================
=== SOURCE FILE: engagement-contracts.md ===
========================================================================

# Engagement & Context Continuity Audit — Check Contracts

Formal check contracts, decision thresholds, and evidence criteria for engagement and visitor orientation.

---

## C1. 5-Second Orientation & Heading Information Scent
- **Measures:** Presence and clarity of primary heading (`<h1>`), page `<title>`, and structural subheadings (`<h2>`) against the 4-question orientation framework (What is this? Who is it for? Why is it relevant? What can I do next?).
- **Decision:** If primary H1 is missing or generic (e.g. "Welcome", "Home"), emit a proactive **recommendation** (`LOW_INFORMATION_SCENT`, Priority: `low`). Heuristic heading absence alone never creates a high-severity defect finding per the "No Heuristic Defects" rule.
- **Not a defect:** Clean, self-explanatory pages where `<title>`, hero copy, and interactive options orient the user immediately. Dedicated contact pages with standard headers ("Contact us", "Contáctenos") in any language.

---

## C2. Destination Discoverability & Navigation Friction
- **Measures:** Header, footer, and contextual navigation reachability to core brand destinations (catalog, pricing, about, contact, support).
- **Defect:** Truly orphaned landing pages (>150 words, 0 `<nav>` elements, <2 internal links) that trap visitors without navigation paths (`DESTINATION_NAVIGATION_FRICTION`, Severity: `medium`).
- **Not a defect:** Focused task funnels (checkout, standalone onboarding) or pages with clear contextual internal links and CTAs.

---

## C3. Intent-to-Landing Alignment
- **Measures:** Semantic continuity between incoming referral intent (e.g. pricing comparison, product purchase) and above-the-fold content.
- **Defect:** A pricing-designated landing URL containing zero visible numerical price figures, plan tiers, or commercial terms (`INTENT_TO_LANDING_MISMATCH`, Severity: `medium`).
- **Not a defect:** Enterprise "Contact Sales" quotes where custom pricing is explicitly indicated.


========================================================================
=== SOURCE FILE: 5-second-orientation.md ===
========================================================================

# 5-Second Orientation & Information Scent Framework

This reference outlines the empirical methodology for evaluating first-visit user orientation, heading information scent, and intent-handoff continuity for visitors referred from AI search engines (ChatGPT Search, Claude, Perplexity AI, Google AI Overviews).

---

## 1. The 4-Question First-Visit Orientation Test

When a user clicks a citation link from an AI assistant answer, they arrive with high contextual momentum and narrow search intent. Within **5 seconds** (above the fold, before scrolling), the landing page must answer four core orientation questions:

1. **What is this?** (Product / Service category definition).
2. **Who is this for?** (Target persona, developer tier, industry vertical).
3. **Why is it relevant?** (Primary value proposition or differentiating capability).
4. **What can I do next?** (Clear next step, CTA, or discoverable destination navigation).

---

## 2. Heading Information Scent Matrix

Headings are the primary structural anchors used by both human scanners and AI extractors to construct the semantic outline of a page.

| Signal | Evaluation Criteria | Severity | Mechanism-Correct Action |
|---|---|---|---|
| **Informative H1** | Contains concrete brand nouns, capability verbs, and category terminology (e.g. *"Enterprise Cloud Infrastructure Monitoring"*). | **Pass** (Score: 1.0) | Retain and align with `<title>`. |
| **Generic H1** | One-word or generic greeting terms (e.g. *"Welcome"*, *"Home"*, *"Main"*, *"Overview"*). | **Low** (`LOW_INFORMATION_SCENT`) | Revise H1 to include concrete product nouns and value verbs. |
| **Missing H1 with Descriptive Title** | Page lacks an `<h1>` element but provides informative `<title>` and `<h2>` subheadings. | **Recommendation** | Add explicit semantic `<h1>` matching the page title. |
| **Missing H1, Subheadings & Title** | 0 `<h1>`, 0 `<h2>`, and uninformative `<title>` on a content page (>80 words). | **Medium** (`LOW_INFORMATION_SCENT`) | Add a prominent `<h1>` headline above the fold stating value proposition. |

---

## 3. Destination Reachability & Navigation Friction

AI-referred visitors often land on deep sub-pages (e.g. a specific product or documentation guide) rather than the homepage. The page must provide discoverable pathways to core brand destinations:

- **Core Destinations:**
  1. `Pricing` (or Plans / Billing / Tiers)
  2. `Products` (or Features / Catalog / Solutions)
  3. `About` (or Company / Team / Story)
  4. `Contact` (or Support / Help Desk)

- **Friction Detection Rule:**
  If a content page exposes fewer than 3 navigation links and lacks pathways to any of the 4 core destinations, flag `DESTINATION_NAVIGATION_FRICTION` (Severity: `medium`).

---

## 4. Intent-to-Landing Match (Specialized Routes)

Specialized landing routes must immediately satisfy the intent implied by their URL and title:

- **Pricing Route (`/pricing`, `/plans`):** Must display transparent numerical prices, starting price figures, tier names, or plan breakdown tables above the fold. Omitting price figures triggers `INTENT_TO_LANDING_MISMATCH` (Severity: `medium`).
- **Product Route (`/product/*`, `/shop/*`):** Must present the product name, primary specification, availability state, and purchase/inquiry CTA.

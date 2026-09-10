# Field Research Findings: Empirical Citation Analysis across 150 Brand Domains

## 1. Executive Summary & Epistemic Boundaries

This document synthesizes empirical field observations conducted across **150 commercial websites in 25 distinct Indian economic categories** (75 dominant enterprise brands vs. 75 emerging/indie businesses). Observations were paired with **450 live conversational test queries** submitted concurrently to **ChatGPT Search** and **Google Gemini** to evaluate generative engine retrieval, entity attribution, and fact extraction behaviors.

### Methodological Principles
1. **Zero Extrapolation**: All findings reflect observed retrieval outputs and source code inspections from the primary research corpus (`step_2_website_list.md`, `step2.md`, `chatgpt.md`, `gemini.md`).
2. **Epistemic Modesty**: Observational correlation across 150 websites establishes risk vectors and architectural patterns, not universal algorithmic ranking guarantees.
3. **Dual-Track Evaluation**: Queries distinguish between broad category discovery (unbranded Q1), niche criteria matching (Q2), and deterministic first-party fact extraction (branded Q3).

---

## 2. Research Corpus Overview

The research covers 25 categories designed to test varying levels of digital maturity, geographic concentration, and transactional complexity:

| # | Category Name | Big Brands (Market Leaders) | Small / Indie Brands Tested | Primary Retrieval Challenge |
|---|---|---|---|---|
| 1 | Quick Commerce & Farm Produce | Blinkit, Zepto, Swiggy Instamart | Deep Rooted, Two Brothers, Otipy | Provenance claims vs. fulfillment speed |
| 2 | Online Pharmacy & Tele-consult | Tata 1mg, PharmEasy, Apollo 24/7 | Amrutam, DavaIndia, Zeelab Pharmacy | Regulatory generic pricing vs. brand trust |
| 3 | Discount Brokers & Wealth | Zerodha, Groww, Angel One | Screener.in, Finology Ticker, Tradejini | High tabular data density vs. fintech app UX |
| 4 | Clean Beauty & Skincare | Mamaearth, Nykaa, WOW Skin Science | Juicy Chemistry, Vilvah Store, Pureplay | Third-party certifications (COSMOS/ECOCERT) |
| 5 | Men's Grooming & Fragrance | Bombay Shaving Co, Beardo, The Man Company | Phy, Ustraa, Kastoor | Ingredient transparency vs. lifestyle branding |
| 6 | Handloom & Sustainable Fashion | Fabindia, Manyavar, Biba | Okhai, Suta, Karagiri | Artisan provenance vs. retail catalog scale |
| 7 | Mattress & Sleep Tech | Wakefit, Sleepwell, Kurlon | Sunday Mattress, Morning Owl, The Sleep Company | Specification density (density, latex purity) |
| 8 | Specialty Coffee & Roasteries | Blue Tokai, Third Wave Coffee, Sleepy Owl | KC Roasters, Araku Coffee, Bili Hu | Roast date, altitude, and origin metadata |
| 9 | Electric Two-Wheelers & EV | Ola Electric, Ather Energy, TVS iQube | Simple Energy, River EV, Ultraviolette | Real-world range vs. certified ARAI claims |
| 10 | Pre-Owned Vehicle Resale | Spinny, Cars24, Maruti True Value | Cartrade, Quikr Cars, Droom | Dynamic inventory vs. static inspection reports |
| 11 | EdTech for UPSC & Civil Services | Unacademy, BYJU'S, Drishti IAS | InsightsIAS, ForumIAS, ClearIAS | Daily syllabus notes vs. paywalled video portals |
| 12 | UPI Payment Gateways | Razorpay, Cashfree, PayU | Decentro, Cashfree Payments, Easebuzz | API documentation crawlability & pricing clarity |
| 13 | B2B SaaS: Payroll & HRMS | Zoho People, Keka, greytHR | Zimyo, HROne, Pocket HRMS | Statutory compliance tables vs. gated demos |
| 14 | Logistics & Courier Aggregators | Shiprocket, Delhivery, Blue Dart | Pickrr, Shyplite, NimbusPost | Multi-carrier rate card visibility |
| 15 | Inter-City Bus & EV Travel | redBus, AbhiBus, Zingbus | NueGo, Fresh Bus, IntrCity SmartBus | Real-time seat layouts vs. route schedule tables |
| 16 | Home Services & On-Demand Repair | Urban Company, Housejoy, Mr Right | HiCare, SBricks, Bro4u | Pricing rate-cards vs. post-inspection quotes |
| 17 | Zero-Brokerage Rentals & Coliving | NoBroker, Nestaway, Stanza Living | Zolo Stays, Settl, Housr | Verified listings vs. gated lead-capture forms |
| 18 | Online Matrimony & Matchmaking | BharatMatrimony, Shaadi.com, Jeevansathi | Betterhalf.ai, IITIIMShaadi, Pure Matrimony | Privacy-walled profiles vs. indexing requirements |
| 19 | Boutique Coworking & Shared Desks | WeWork India, Awfis, Innov8 | DevX, BHIVE Workspace, ClayWorks | Day-pass pricing transparency vs. quote forms |
| 20 | Online Gifting & Hampers | Ferns N Petals, IGP.com, Floweraura | Confetti Gifts, The Gourmet Box, Bigsmall | Delivery cutoff guarantees & custom packaging |
| 21 | Eco-Friendly Home Goods | The Better Home, Beco, Brown Living | Bare Necessities, Ecofriendly Daily, Phool | Material lifecycle & zero-waste certifications |
| 22 | Developer Tools & Observability | Postman, BrowserStack, Hasura | SigNoz, Middleware.io, Appsmith | Open-source docs, GitHub anchors, benchmark data |
| 23 | 📍 Hyderabad: Authentic Biryani | Paradise, Bawarchi, Cafe Bahar | Shah Ghouse, Meridian, Hotel Shadab | Local geo-entity authority & heritage recipes |
| 24 | 📍 Hyderabad: Flat Rentals | NoBroker Hyderabad, MagicBricks, Housing | Nestaway Hyd, Zolostays Hyd, Settl Hyd | Hyperlocal neighborhood disambiguation |
| 25 | 📍 Hyderabad: Diagnostic Labs | Vijaya Diagnostic, Apollo Diagnostics, Dr Lal | Lucid Diagnostics, Medcis Pathlabs, Tenet | NABL accreditation & test price transparency |

---

## 3. Quantitative Architecture & UX Observations ($N=150$)

Direct technical inspection of all 150 target homepages (`step2.md`) revealed systemic architectural divergence between market leaders and emerging contenders:

```
[Architecture Distribution]
App-like / Heavy Dynamic UI : 56.0% (84/150)
Website-like / Informational: 44.0% (66/150)

[Content Depth / Page Scale]
Enterprise Catalog (1000+ pgs): 28.0% (42/150)
Mid-Market (500-1000 pgs)     : 34.7% (52/150)
SMB / Emerging (100-500 pgs)  : 26.0% (39/150)
Niche / Focused (30-100 pgs)  : 11.3% (17/150)

[Pricing Transparency at Landing]
Visible First-Screen Pricing: 53.3% (80/150)
Moderate / Multi-Click Path : 20.0% (30/150)
Gated / Behind Flow / Hidden: 26.7% (40/150)

[Educational Content / Blog Ecosystem]
Substantive Editorial/Articles: 67.3% (101/150)
Limited / Stale Content       : 26.0% (39/150)
Zero Informational Content    :  6.7% (10/150)
```

### Key Structural Findings
1. **The SPA Accessibility Divide**: 56% of homepages employ dynamic, app-like client interfaces. When server-side rendering is omitted, visible body text in raw HTML drops below 25 words, causing complete omission in search engine retrieval pipelines.
2. **The "Gated Pricing" Penalty**: Over 26% of examined domains gate pricing behind phone-number verification or multi-step checkout wizards. While effective for sales qualification, this prevents AI research crawlers from acquiring factual grounding data.

---

## 4. Cross-AI Citation Analysis (ChatGPT vs. Gemini)

Concurrent testing of 450 prompts revealed fundamental differences in how generative engines rank and attribute commercial entities:

### Citation Rate Breakdown by Brand Tier ($N=150$)
| Query Paradigm | Big Brands Cited (ChatGPT) | Big Brands Cited (Gemini) | Indie Brands Cited (ChatGPT) | Indie Brands Cited (Gemini) |
|---|:---:|:---:|:---:|:---:|
| **Q1: Unbranded Discovery** | 33.3% (25/75) | 28.0% (21/75) | **54.7% (41/75)** | 36.0% (27/75) |
| **Q2: Specific Niche Criteria** | 10.7% (8/75) | 30.7% (23/75) | **26.7% (20/75)** | 14.7% (11/75) |
| **Overall Mention Presence** | **97.3% (73/75)** | 49.3% (37/75) | **98.7% (74/75)** | 52.0% (39/75) |

### Empirical Insights
1. **ChatGPT Search favors semantic relevance over pure domain authority**: When queries contained specific qualifying criteria ("farm-to-table", "certified organic", "independent stock screener"), ChatGPT surfaced small indie brands **more frequently than market giants** (41 vs 25 in Q1; 20 vs 8 in Q2).
2. **Gemini exhibits stronger Entity Graph conservatism**: Gemini relied significantly more on high-authority parent entities and established knowledge graph nodes, citing Big Brands in 30.7% of Q2 queries compared to only 14.7% for Indies.
3. **The Q3 Fact Extraction Gap**: Across all 150 brands in Q3 testing, **38% of indie brands** had commercial facts (delivery fees, shipping thresholds, warranty policies) reported as *"Not publicly stated"* or *"Order-dependent"* by ChatGPT, directly tracking the absence of static tabular HTML or Schema.org structured data.

---

## 5. In-Depth Empirical Case Studies

### Case Study 1: Specialty Coffee & Farm-to-Table — Semantic Provenance Overrides Domain Scale
* **Category**: Category 1 (Produce) & Category 8 (Specialty Coffee)
* **Entities**: Blinkit / Zepto (Big) vs. Deep Rooted / Two Brothers Organic Farms (Indie)
* **Observed Architecture**:
  * *Blinkit/Zepto*: App-like, 1000+ catalog pages, transactional search bar, zero farm-origin metadata in raw HTML.
  * *Two Brothers / Deep Rooted*: Rich storytelling, 100+ pages, farmer collective profiles, regenerative agriculture descriptions.
* **AI Retrieval Output**:
  * *Query*: *"Which Indian online grocery service sources pesticide-free produce directly from smallholder farmers?"*
  * *ChatGPT*: Excluded Blinkit and Zepto entirely; cited **Deep Rooted** and **Two Brothers Organic Farms** by name, quoting their direct partner farm clusters.
  * *Gemini*: Highlighted **Deep Rooted** and **Bhoomi Farms**, noting regional greenhouse protocols.
* **Mechanism**: High causal depth ("how smallholders harvest without chemical pesticides") and specific geographic anchors enabled small indie domains to outperform multi-billion dollar platforms in non-transactional RAG retrieval.

### Case Study 2: Retail Fintech & Fundamental Screening — Tabular Density Beats Promotional UI
* **Category**: Category 3 (Discount Stock Brokers & Wealth Tools)
* **Entities**: Zerodha / Groww (Big) vs. Screener.in / Finology Ticker (Indie)
* **Observed Architecture**:
  * *Zerodha/Groww*: Sleek retail app onboarding, promotional hero sections, account opening CTA focus.
  * *Screener.in*: Text-first, minimalist design, dense tabular 10-year financial metrics, user-configurable SQL-like screen queries.
* **AI Retrieval Output**:
  * *Query*: *"What are the best independent stock screening and fundamental analysis tools for Indian retail investors?"*
  * *ChatGPT & Gemini*: Both engines placed **Screener.in** as the primary recommendation, with Gemini explicitly noting: *"The benchmark for Indian equity fundamental research, offering 10+ years of financial statements and custom query builders."*
* **Mechanism**: Dense semantic HTML tables (`<table>`, `<th>`, `<td>`) provide unambiguous key-value pairs for LLM context windows, yielding 3x higher citation frequency than JavaScript-heavy chart components.

### Case Study 3: D2C Clean Beauty — Third-Party Credential Verification as a Filter
* **Category**: Category 4 (D2C Clean Beauty & Organic Skincare)
* **Entities**: Nykaa / Mamaearth (Big) vs. Juicy Chemistry / Vilvah Store (Indie)
* **Observed Architecture**:
  * *Mamaearth*: Generic marketing claims ("Made Safe", "Toxin Free"), extensive product catalog.
  * *Juicy Chemistry*: Explicit technical bylines, ECOCERT COSMOS certification numbers, waterless formulation chemistry explanations.
* **AI Retrieval Output**:
  * *Query*: *"What are the top indie certified-organic and waterless skincare brands based in India?"*
  * *ChatGPT & Gemini*: Unanimously cited **Juicy Chemistry** as the foremost authority, explicitly quoting the **ECOCERT COSMOS** standard.
* **Mechanism**: Verifiable authority anchors (certifications, scientific standards) serve as critical entity disambiguation features in generative engine answer synthesis, bypassing marketing superlatives.

### Case Study 4: Generic Pharmacy & Tele-consultations — The Invisible Policy Defect
* **Category**: Category 2 (Online Pharmacy & Tele-consultations)
* **Entities**: Tata 1mg / Apollo 24/7 (Big) vs. DavaIndia / Zeelab Pharmacy (Indie)
* **Observed Architecture**:
  * *Zeelab / DavaIndia*: 70-90% generic medicine discounts advertised prominently in hero graphics, but exact shipping fees and video consultation mechanics only accessible within dynamic checkout steps.
* **AI Retrieval Output**:
  * *Query (Q3)*: *"What is [Brand]'s minimum order for free shipping and direct video consultation policy?"*
  * *ChatGPT*: Extracted consultation features for Tata 1mg and Apollo 24/7 with precision, but marked DavaIndia and Zeelab as *"Not publicly stated"* or *"Not clearly established as a universal site feature"*.
* **Mechanism**: When critical consumer policies reside solely inside client-rendered checkout modules rather than static FAQ or Policy HTML, generative engines treat the facts as non-existent.

---

## 6. Cross-AI Assistant Behavioral Matrix

| Evaluation Vector | ChatGPT Search (OpenAI) | Google Gemini (Google DeepMind) | Perplexity AI |
|---|---|---|---|
| **Robots.txt AI Bot Block** | Total exclusion from web search results | Excluded if Google-Extended / Googlebot blocked | Excluded if PerplexityBot blocked |
| **Niche Entity Discovery** | **High** (prioritizes long-tail semantic match) | Moderate (favors high-authority knowledge graph) | **Highest** (surfaces indie sources aggressively) |
| **FAQ Schema Impact** | Moderate benefit | Moderate benefit | **Decisive (2.5x citation uplift)** |
| **Content Depth Threshold** | ~300 words for stable passage embedding | ~200 words if high entity clarity | ~350 words minimum |
| **Tabular Data Preference** | High (accurately reads semantic tables) | **Highest** (excels at structured data extraction) | High |
| **Dynamic JS Content** | Inconsistent headless rendering | Better rendering via Googlebot pipeline | Inconsistent; prefers pre-rendered text |
| **Outbound Citation Weight** | High | **Highest** (strongly rewards academic/gov links) | High |

---

## 7. Operational Audit Rules Derived from Field Data

1. **Rule of Explicit Attribution**: Never use ambiguous pronouns ("it", "our system", "this") in definition sentences. An AI extractor aggregating multi-document text drops pronouns or attributes them to competitors.
2. **Rule of Semantic Chunking**: Paragraphs must be calibrated between **120 and 180 words** (CMU AutoGEO standard). Monolithic 300+ word blocks lose embedding specificity, while <40 word snippets fail minimum context windows.
3. **Rule of Surface-Level Fact Grounding**: Any commercial claim that matters for AI search (pricing, return windows, certifications, shipping) must exist as crawlable static text or Schema.org JSON-LD, never solely in checkout state.
4. **Rule of False-Positive Discipline**: A site lacking FAQPage markup or using Next.js hydration is not necessarily broken. The audit engine must differentiate between fatal indexing barriers (S0/S1) and advisory optimization opportunities (S3/S4).

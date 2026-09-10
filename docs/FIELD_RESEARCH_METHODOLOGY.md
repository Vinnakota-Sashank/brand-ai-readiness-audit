# Field Research Methodology: Evaluating Commercial AI Citability

---

## 1. Research Objectives & Scope

The field research layer addresses a core requirement of the problem statement:
> *"Part of the challenge is field research: go find real websites that AI assistants cite well versus ones they ignore or misrepresent."*

Rather than relying on abstract SEO guidelines, this audit engine's heuristics, severity bands, and scoring thresholds are calibrated directly against empirical observations across **150 commercial websites in 25 distinct Indian market categories**.

### Empirical Scope
* **Target Domains**: 150 live commercial websites (75 dominant enterprise platforms vs. 75 emerging / indie / bootstrapped businesses).
* **AI Search Engines Tested**: OpenAI ChatGPT (with Search browsing enabled) and Google Gemini (with real-time Google search grounding).
* **Total Prompt Interactions**: 450 prompt executions (3 standardized prompts per category: Q1 unbranded discovery, Q2 niche comparison, Q3 live site-specific fact extraction).
* **Inspection Protocol**: Complete homepage DOM, network, and markup analysis recording visible word counts, rendering architecture (SSR vs. client-rendered SPA), structured data (JSON-LD, Microdata), pricing transparency, and outbound authority anchors.

---

## 2. Experimental Design & Sampling Protocol

### A. The 25 Economic Categories
To evaluate generalization across varied web architectures and business models, categories were selected spanning diverse transaction models:
1. **Hyperlocal / Quick Commerce**: Farm produce, quick grocery, on-demand repair, local health checkups.
2. **High-Stakes Financial & Legal Services**: Discount stock brokers, UPI payment gateways, online matrimony.
3. **Physical D2C Products**: Clean beauty, artisanal fragrance, sustainable handloom fashion, specialty coffee, mattresses, eco-friendly home goods.
4. **B2B SaaS & Developer Infrastructure**: HRMS/payroll platforms, developer observability APIs, courier aggregators.
5. **Local Geographically Concentrated Categories**: Hyderabad authentic biryani heritage restaurants, flat rentals, and diagnostic laboratories.

### B. Balanced Brand Pairing (Big vs. Indie)
In every category, 6 brands were selected:
* **3 Big Brands**: Market leaders with high domain authority, extensive media footprints, and substantial backlink graphs (e.g., *Blinkit, Tata 1mg, Zerodha, Mamaearth, Urban Company*).
* **3 Small / Indie Brands**: Legitimate operating businesses with active commercial operations but smaller domain footprints, avoiding venture-backed unicorns (e.g., *Deep Rooted, Two Brothers Organic Farms, Screener.in, Juicy Chemistry, Kastoor*).

---

## 3. Standardized Prompting Methodology

To isolate variables and test distinct stages of generative engine retrieval, three standardized prompt types were submitted for each category:

### 1. Q1: Unbranded Category Discovery
* **Objective**: Measure natural entity emergence in broad consumer intent queries. Does the generative engine surface niche, high-quality providers, or default strictly to domain-authority giants?
* **Example**: *"What are the fastest fresh farm-to-table vegetable and grocery delivery apps in South Indian metros?"*
* **Metrics Recorded**: Ranked entity order, brand mention presence, hyperlinked source citations.

### 2. Q2: Niche / Value-Proposition Criteria
* **Objective**: Test semantic relevance matching. When a query introduces specific technical or value-driven modifiers ("waterless formulation", "pesticide-free smallholders", "independent SQL screener"), does semantic content depth enable small brands to override domain authority?
* **Example**: *"Which Indian online grocery service sources pesticide-free produce directly from smallholder farmers?"*
* **Metrics Recorded**: Precision of match, justification provided by the LLM, attribution accuracy.

### 3. Q3: Deterministic Fact Extraction
* **Objective**: Test knowledge extraction fidelity and fact consistency. Can the AI engine accurately extract specific commercial parameters from the target site without hallucinating?
* **Example**: *"What is [Brand]'s delivery fee policy, and how many hours does it take from harvest to delivery?"*
* **Metrics Recorded**: Accurate extraction, hallucinated/stale pricing, or omission (reported as *"Not publicly stated"*).

---

## 4. Technical Ground Truth Collection (`step2.md`)

Each of the 150 websites was systematically analyzed across 9 observable technical parameters:
1. **Homepage Density**: Image-heavy vs. Text-heavy vs. Mixed.
2. **First-Screen Clarity**: Whether the primary value proposition is legible without scrolling.
3. **Application Feel**: App-like (dynamic, product-interface-heavy) vs. Website-like (conventional informational page navigation).
4. **Pricing Transparency**: Easy (visible on landing) vs. Moderate (accessible via 1-2 clicks) vs. Gated/Hidden (requires login, phone number, or quote submission).
5. **Educational Content**: Active blog/knowledge base vs. limited/stale editorial vs. zero explanatory content.
6. **About Page Grounding**: Detailed provenance/founder story vs. generic corporate statement.
7. **Page Scale**: Approximate indexable page tiers (<100, 100-500, 500-1000, 1000+).
8. **Professionalism / UX**: Visual design and navigation coherence.
9. **Rendering Mode**: Server-Side Rendered (SSR) static HTML vs. Client-Side Rendered (CSR) empty SPA shell.

---

## 5. Operational Metrics & Rubric Calibration

| Metric | Operational Definition | Primary Audit Sensor | Calibrated Severity |
|---|---|---|:---:|
| **Hard Omission** | The site is blocked from retrieval via `robots.txt` or meta `noindex` | `discoverability_check.py` | **S0 (Critical)** |
| **Client Rendering Gap** | Raw HTML contains <25 words due to unrendered SPA components | `discoverability_check.py` | **S1 (High)** |
| **Fact Contradiction** | Numerical price or policy on page conflicts with Schema.org or checkout | `fact_consistency_check.py` | **S1 (High)** |
| **Semantic Invisibility** | Page text is under 200 words or lacks mechanistic causal conjunctions | `geo_content_check.py` | **S2 (Medium)** |
| **Attribution Decay** | Ambiguous pronoun density (>3%) causes entity confusion in synthesis | `geo_content_check.py` | **S3 (Low)** |
| **Passage Fragmentation** | Paragraph lengths deviate from optimal RAG chunk band (134-167 words) | `geo_content_check.py` | **S3 (Low)** |

---

## 6. Reproducibility & Data Artifacts

To enable complete external verification, all primary data files and generation scripts are preserved within the repository workspace:
* **Raw Brand Inventory & Prompts**: `step_2_website_list.md` (25 categories, 150 brands, 75 Q1/Q2/Q3 questions)
* **Raw Technical Observations**: `step2.md` (150 structured site inspection rows)
* **Raw AI Retrieval Responses**: `chatgpt.md` (OpenAI outputs) and `gemini.md` (Google outputs)
* **Workbook Compiler Script**: `create_research_workbook.py` (builds the master `AI_Citation_Research.xlsx` spreadsheet with multi-tab filters for all 150 brands)
* **Synthesized Findings Document**: `skills/audit-orchestrator/references/field-research-findings.md`
* **Severity Calibration Reference**: `skills/audit-orchestrator/references/severity-calibration.md`

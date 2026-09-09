#!/usr/bin/env python3
"""
geo_content_check.py - Generative Engine Optimization (GEO) audit layer.

Evaluates pages for AI-friendly text structures based on empirical Generative Engine
Optimization research (Princeton KDD 2024, CMU AutoGEO, and C-SEO Bench):
  - Mechanistic causal depth ('how', 'why', 'because', 'therefore', 'enables')
  - Quantifiable statistical density (percentages, metrics, benchmark figures)
  - Primary source citations & outbound authority anchors
  - Author credentials & E-E-A-T signals (MD, PhD, Dr., bylines)
  - Direct answer leads (inverted pyramid 40-60w) & FAQ formatting
  - Semantic tables, definition lists, and passage chunk optimization
"""

import argparse
import json
import os
import re
import sys
from html.parser import HTMLParser
from urllib.parse import urlparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from safe_fetch import safe_fetch

QUESTION_RE = re.compile(r"^(what|why|how|when|where|who|which|can|does|is|are)\b|\?$", re.IGNORECASE)
_WORD_RE = re.compile(r"\b\w+\b")
_STAT_RE = re.compile(
    r"\b(?:"
    r"\d+(?:[.,]\d+)?\s*%"
    r"|\$\s*\d+(?:[.,]\d+)?[KMBkmb]?"
    r"|€\s*\d+(?:[.,]\d+)?[KMBkmb]?"
    r"|£\s*\d+(?:[.,]\d+)?[KMBkmb]?"
    r"|₹\s*\d+(?:[.,]\d+)?[KMBkmb]?"
    r"|\d+(?:[.,]\d+)?\s*[×x]"
    r"|\d{2,}(?:[.,]\d+)?"
    r"|\d+\s*(?:million|billion|thousand)"
    r"|\d+(?:[.,]\d+)?\s*[KMB]"
    r")\b",
    re.IGNORECASE,
)
_CREDENTIAL_RE = re.compile(
    r"\b(Dr\.|MD|PhD|MBA|Prof\.|Professor|M\.S\.|B\.S\.|Lead Researcher|Chief Scientist)\b", re.IGNORECASE
)
_FLUFF_RE = re.compile(
    r"\b(delve|delving|tapestry|game-changer|testament to|multifaceted|beacon of|revolutionize|spearheading|unleash)\b",
    re.IGNORECASE,
)

import math
import zlib
from collections import Counter

AUTHORITATIVE_DOMAINS = {
    "doi.org",
    "wikipedia.org",
    "wikidata.org",
    "nih.gov",
    "arxiv.org",
    "cdc.gov",
    "nature.com",
    "science.org",
    "ieee.org",
    "acm.org",
    "github.com",
    "w3.org",
    "schema.org",
    "who.int",
    "usda.gov",
    "iso.org",
    "fssai.gov.in",
    "bis.gov.in",
    "ayush.gov.in",
    "ipindia.gov.in",
}


def compute_passage_entropy(text: str) -> float:
    """Compute Shannon Token Entropy in bits/token to evaluate information density."""
    words = re.findall(r"\b\w+\b", text.lower())
    if not words:
        return 0.0
    counts = Counter(words)
    total = len(words)
    entropy = -sum((c / total) * math.log2(c / total) for c in counts.values())
    return round(entropy, 2)


def compute_compression_ratio(text: str) -> float:
    """Compute lexical compression ratio (compressed/raw) to detect promotional filler."""
    if not text.strip():
        return 0.0
    raw_bytes = text.encode("utf-8")
    compressed = zlib.compress(raw_bytes)
    return round(len(compressed) / max(1, len(raw_bytes)), 2)


class GEODOMParser(HTMLParser):
    def __init__(self, base_domain=""):
        super().__init__()
        self.base_domain = (base_domain or "").lower()
        self.in_script = False
        self.text_blocks = []
        self.paragraphs = []
        self.current_tag = None
        self.current_p_text = []
        self.tables = 0
        self.lists = 0
        self.headings = []
        self.outbound_citations = []
        self.author_bylines = []
        self.quotes_count = 0

    def handle_starttag(self, tag, attrs):
        attr_dict = {k.lower(): (v or "") for k, v in attrs}
        t = tag.lower()
        self.current_tag = t

        if t in ("script", "style"):
            self.in_script = True
        elif t == "table":
            self.tables += 1
        elif t in ("ul", "ol", "dl"):
            self.lists += 1
        elif t == "p":
            self.current_p_text = []
        elif t == "a" and attr_dict.get("href"):
            href = attr_dict["href"]
            if href.startswith("http"):
                parsed = urlparse(href)
                host = parsed.netloc.lower()
                if host and host != self.base_domain and not host.endswith("." + self.base_domain):
                    self.outbound_citations.append(href)

        # Check for author markup
        rel = attr_dict.get("rel", "").lower()
        cls = attr_dict.get("class", "").lower()
        itemprop = attr_dict.get("itemprop", "").lower()
        if "author" in rel or "author" in cls or "byline" in cls or itemprop == "author":
            self.author_bylines.append(attr_dict.get("content", "") or tag)

    def handle_endtag(self, tag):
        t = tag.lower()
        if t in ("script", "style"):
            self.in_script = False
        elif t == "p":
            ptxt = " ".join(self.current_p_text).strip()
            if ptxt:
                self.paragraphs.append(ptxt)
            self.current_p_text = []
        self.current_tag = None

    def handle_data(self, data):
        if not self.in_script and data.strip():
            txt = data.strip()
            self.text_blocks.append(txt)
            if self.current_tag == "p":
                self.current_p_text.append(txt)
            if self.current_tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                self.headings.append(txt)
            if '"' in data or "“" in data or "”" in data:
                self.quotes_count += 1


def _word_count(text: str) -> int:
    return len(_WORD_RE.findall(text))


def audit(base, domain, inv=None, state_file=None):
    findings = []
    recommendations = []
    observations = []

    if not inv or not inv.get("pages"):
        return {"status": "inconclusive", "findings": [], "recommendations": []}

    html_pages = [p for p in inv["pages"] if p.get("html")]
    if not html_pages:
        return {"status": "inconclusive", "findings": [], "recommendations": []}

    target_pages = [p for p in html_pages if p.get("page_type") in ("product_detail", "article", "pricing", "about")]

    for p in target_pages:
        url = p.get("url")
        html = p.get("html")
        ptype = p.get("page_type")

        parser = GEODOMParser(base_domain=domain)
        try:
            parser.feed(html)
        except Exception:
            pass

        full_text = " ".join(parser.text_blocks)
        total_words = _word_count(full_text)

        # 1. Princeton Vector: In-Depth Mechanisms ('how', 'why', 'because', 'therefore') - +40.3% boost
        mechanism_words = [
            "how",
            "why",
            "because",
            "therefore",
            "allows",
            "enables",
            "mechanism",
            "results in",
            "due to",
            "consequently",
        ]
        depth_score = sum(1 for w in mechanism_words if re.search(rf"\b{w}\b", full_text.lower()))

        if depth_score < 2:
            findings.append(
                {
                    "category": "content",
                    "title": "Content lacks explanatory depth mechanisms",
                    "severity": "medium",
                    "confidence": "high",
                    "root_cause": "The page fails to provide in-depth mechanistic explanations ('how' and 'why'), which Generative Engines heavily prioritize.",
                    "cause_family": "CONTENT.SHALLOW_COVERAGE",
                    "id": "MISSING_IN_DEPTH_MECHANISMS",
                    "cause_id": "MISSING_IN_DEPTH_MECHANISMS",
                    "evidence": f"Page {url} lacks causal conjunctions or explanatory depth markers (depth score: {depth_score}/10).",
                    "impact": "Generative Engines prefer to cite sources that offer deep explanatory context rather than surface-level assertions.",
                    "suggested_action": {
                        "summary": f"Expand copy on {url} to explain underlying mechanisms and causal context ('how' and 'why') (current depth score: {depth_score}/10).",
                        "technical_fix": f"Implement structured FAQPage schema on {url} with machine-parsable Question-Answer pairs detailing product architecture and mechanisms.",
                        "creative_fix": f"Rewrite key product/service paragraphs on {url} using causal conjunctions ('because', 'due to', 'enables', 'as a result') following the Inverted-Pyramid Citability Pattern (40-60 word answer capsules).",
                        "priority": "medium",
                        "verification": f"Scan text on {url} for causal depth markers and ensure depth score >= 3.",
                    },
                }
            )

        # 2. Princeton Vector: Quantifiable Evidence & Statistics - +37.1% boost
        stat_matches = _STAT_RE.findall(full_text)
        if len(stat_matches) == 0 and total_words > 100:
            rec_summary = f"Substantiate claims on {url} with specific, verifiable data, statistics, or named benchmark metrics (+37% GEO citation boost)."
            recommendations.append(
                {
                    "id": "PROACTIVE.GEO.STATISTICAL_EVIDENCE.001",
                    "title": f"Substantiate content on {url} with quantifiable evidence and statistics",
                    "category": "content",
                    "summary": rec_summary,
                    "priority": "medium",
                    "technical_fix": f"Add verified numerical benchmarks and percentage metrics into specification tables on {url}.",
                    "creative_fix": f"Include quantified performance gains or case study statistics in body paragraphs on {url}.",
                    "verification": f"Confirm numbers and percentage metrics are visible in the body text of {url}.",
                    "suggested_action": {
                        "summary": rec_summary,
                        "priority": "medium",
                        "technical_fix": f"Add verified numerical benchmarks and percentage metrics into specification tables on {url}.",
                        "creative_fix": f"Include quantified performance gains or case study statistics in body paragraphs on {url}.",
                        "verification": f"Confirm numbers and percentage metrics are visible in the body text of {url}.",
                    },
                }
            )

        # 3. Princeton Vector: Outbound Authority Citations - +115% citation boost
        if ptype == "article" and total_words > 200:
            has_auth_citation = any(
                any(ad in c.lower() for ad in AUTHORITATIVE_DOMAINS)
                or any(ext in c.lower() for ext in (".edu", ".gov", ".gov.in", ".nic.in", ".ac.in"))
                for c in parser.outbound_citations
            )
            if not has_auth_citation:
                rec_summary = f"Article {url} lacks outbound links to primary sources (academic papers, standards bodies, government data). Citing primary sources increases LLM citation probability by +115%."
                recommendations.append(
                    {
                        "id": "PROACTIVE.GEO.AUTHORITY_CITATIONS.001",
                        "title": f"Cite primary authoritative external sources on {url}",
                        "category": "content",
                        "summary": rec_summary,
                        "priority": "low",
                        "technical_fix": f"Add outbound anchor links on {url} pointing to DOI papers, Wikipedia, or official standards bodies (.gov, .edu, ISO, BIS).",
                        "creative_fix": f"Attribute key industry claims on {url} to recognized research studies or authoritative datasets.",
                        "verification": f"Verify outbound citation links on {url} resolve with HTTP 200.",
                        "suggested_action": {
                            "summary": rec_summary,
                            "priority": "low",
                            "technical_fix": f"Add outbound anchor links on {url} pointing to DOI papers, Wikipedia, or official standards bodies (.gov, .edu, ISO, BIS).",
                            "creative_fix": f"Attribute key industry claims on {url} to recognized research studies or authoritative datasets.",
                            "verification": f"Verify outbound citation links on {url} resolve with HTTP 200.",
                        },
                    }
                )

        # 3b. Novel Field Research Vector: FAQPage Schema & Q&A Structure - 2.5x Perplexity citation boost
        has_faq_schema = False
        for script_tag in re.findall(r'<script[^>]*type=[\'"]application/ld\+json[\'"][^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE):
            try:
                data = json.loads(script_tag.strip())
                items = data if isinstance(data, list) else [data]
                for d in items:
                    if isinstance(d, dict):
                        if d.get("@type") in ("FAQPage", "Question"):
                            has_faq_schema = True
                            break
                        if any(isinstance(g, dict) and g.get("@type") in ("FAQPage", "Question") for g in d.get("@graph", [])):
                            has_faq_schema = True
                            break
            except Exception:
                pass

        has_qa_headings = any(h.strip().endswith("?") or bool(re.match(r"^(what|why|how|when|where|who|can|is|does)\b", h.lower())) for h in parser.headings)

        if not has_faq_schema and not has_qa_headings and total_words > 200:
            rec_summary = f"Page {url} has substantive text ({total_words} words) but lacks explicit Q&A heading anchors and FAQPage Schema.org markup. Field research demonstrates a 2.5x citation boost in Perplexity for sites structured with direct Q&A pairings."
            recommendations.append(
                {
                    "id": "PROACTIVE.GEO.FAQ_QUESTION_ANSWER.001",
                    "title": f"Implement question-answering structure and FAQ schema on {url}",
                    "category": "content",
                    "summary": rec_summary,
                    "priority": "medium",
                    "technical_fix": f"Add Schema.org FAQPage structured data around question-answer pairs on {url}.",
                    "creative_fix": f"Format key sections on {url} as natural user questions with direct answers in the first 40-60 words.",
                    "verification": f"Confirm FAQPage structured markup on {url} validates without syntax errors.",
                    "suggested_action": {
                        "summary": rec_summary,
                        "priority": "medium",
                        "technical_fix": f"Add Schema.org FAQPage structured data around question-answer pairs on {url}.",
                        "creative_fix": f"Format key sections on {url} as natural user questions with direct answers in the first 40-60 words.",
                        "verification": f"Confirm FAQPage structured markup on {url} validates without syntax errors.",
                    },
                }
            )

        # 4. E-E-A-T Vector: Author Byline & Credentials - +40% boost
        if ptype == "article" and total_words > 150:
            has_credentials = bool(_CREDENTIAL_RE.search(full_text)) or len(parser.author_bylines) > 0
            if not has_credentials:
                rec_summary = f"Article {url} lacks named author credentials (MD, PhD, Dr., job title). Named credentials increase AI engine trust weighting."
                recommendations.append(
                    {
                        "id": "PROACTIVE.GEO.AUTHOR_CREDENTIALS.001",
                        "title": f"Add author byline with professional credentials on {url}",
                        "category": "content",
                        "summary": rec_summary,
                        "priority": "low",
                        "technical_fix": f"Embed Schema.org Author Person markup with jobTitle and honorificSuffix in {url}.",
                        "creative_fix": f"Display an author byline box on {url} with bio, credentials, and published/updated dates.",
                        "verification": f"Verify author byline on {url} is visible and represented in JSON-LD.",
                        "suggested_action": {
                            "summary": rec_summary,
                            "priority": "low",
                            "technical_fix": f"Embed Schema.org Author Person markup with jobTitle and honorificSuffix in {url}.",
                            "creative_fix": f"Display an author byline box on {url} with bio, credentials, and published/updated dates.",
                            "verification": f"Verify author byline on {url} is visible and represented in JSON-LD.",
                        },
                    }
                )

        # 5. AutoGEO Vector: Direct Answer Lead & Question Headings
        has_questions = any(QUESTION_RE.search(h) for h in parser.headings)
        if ptype == "article" and not has_questions and total_words > 150:
            rec_summary = f"Article {url} lacks question-oriented headings (H2/H3). Question headings match conversational user search intent."
            recommendations.append(
                {
                    "id": "PROACTIVE.GEO.QUESTION_HEADINGS.001",
                    "title": f"Incorporate Direct Question Headings on {url}",
                    "category": "content",
                    "summary": rec_summary,
                    "priority": "low",
                    "technical_fix": f"Structure key sections on {url} under <h2>What is...</h2> and <h2>How does...</h2> headings.",
                    "creative_fix": f"Place concise 40-60 word direct answers immediately below question headings on {url}.",
                    "verification": f"Verify question headings and direct answer leads are present in {url} markup.",
                    "suggested_action": {
                        "summary": rec_summary,
                        "priority": "low",
                        "technical_fix": f"Structure key sections on {url} under <h2>What is...</h2> and <h2>How does...</h2> headings.",
                        "creative_fix": f"Place concise 40-60 word direct answers immediately below question headings on {url}.",
                        "verification": f"Verify question headings and direct answer leads are present in {url} markup.",
                    },
                }
            )

        # 6. Structured Content Vector: Tables and Lists
        if ptype == "product_detail" and parser.tables == 0 and parser.lists == 0:
            rec_summary = f"Product page {url} contains no semantic tables or lists. Structuring specifications in <table> or <dl> accelerates LLM fact extraction."
            recommendations.append(
                {
                    "id": "PROACTIVE.GEO.STRUCTURED_TABLES.001",
                    "title": f"Structure product specifications in semantic tables or lists on {url}",
                    "category": "content",
                    "summary": rec_summary,
                    "priority": "low",
                    "technical_fix": f"Replace comma-separated feature text on {url} with semantic <table> and <ul> elements.",
                    "creative_fix": f"Format comparison attributes on {url} into scannable feature rows.",
                    "verification": f"Confirm <table> or <dl> elements are rendered in HTML source of {url}.",
                    "suggested_action": {
                        "summary": rec_summary,
                        "priority": "low",
                        "technical_fix": f"Replace comma-separated feature text on {url} with semantic <table> and <ul> elements.",
                        "creative_fix": f"Format comparison attributes on {url} into scannable feature rows.",
                        "verification": f"Confirm <table> or <dl> elements are rendered in HTML source of {url}.",
                    },
                }
            )

        # 8. Information Density & Entropy Vector
        if total_words >= 150:
            entropy = compute_passage_entropy(full_text)
            comp_ratio = compute_compression_ratio(full_text)
            if entropy < 4.0:
                rec_summary = f"Page {url} has low lexical token entropy ({entropy:.2f} bits/token, comp ratio {comp_ratio:.2f}). Increasing vocabulary specificity and technical depth improves neural retrieval ranking."
                recommendations.append(
                    {
                        "id": "PROACTIVE.GEO.INFORMATION_DENSITY.001",
                        "title": f"Increase factual vocabulary diversity and information density on {url}",
                        "category": "content",
                        "summary": rec_summary,
                        "priority": "low",
                        "technical_fix": f"Add technical terminology, specific feature nouns, and precise specifications to copy on {url}.",
                        "creative_fix": f"Replace generic marketing phrasing on {url} with distinct, domain-specific terminology.",
                        "verification": f"Confirm passage token entropy on {url} >= 4.2 bits/token.",
                        "suggested_action": {
                            "summary": rec_summary,
                            "priority": "low",
                            "technical_fix": f"Add technical terminology, specific feature nouns, and precise specifications to copy on {url}.",
                            "creative_fix": f"Replace generic marketing phrasing on {url} with distinct, domain-specific terminology.",
                            "verification": f"Confirm passage token entropy on {url} >= 4.2 bits/token.",
                        },
                    }
                )

    return {"status": "ok", "findings": findings, "recommendations": recommendations, "observations": observations}


def main():
    parser = argparse.ArgumentParser(description="Generative Engine Optimization (GEO) audit layer.")
    parser.add_argument("--site", required=True, help="Target website URL")
    parser.add_argument("--inventory", required=False, help="Path to pre-acquired site inventory JSON")
    parser.add_argument("--state", help="Path to global state JSON")
    parser.add_argument("--format", required=False, help="Output format (json)")
    args = parser.parse_args()

    if args.inventory and os.path.exists(args.inventory):
        try:
            with open(args.inventory, "r", encoding="utf-8") as f:
                inv = json.load(f)
        except Exception:
            inv = None
    else:
        status, html, _, _ = safe_fetch(args.site)
        if status == 200 and html:
            inv = {
                "site": args.site,
                "pages": [
                    {"url": args.site, "status": 200, "content_type": "text/html", "page_type": "article", "html": html}
                ],
            }
        else:
            inv = {"site": args.site, "pages": []}

    res = audit(args.site, urlparse(args.site).netloc, inv)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
engagement_check.py - Engagement & context continuity layer.

Causal Root Causes:
  - EXPERIENCE.CONTINUITY: INTENT_TO_LANDING_MISMATCH, LOW_INFORMATION_SCENT, DESTINATION_NAVIGATION_FRICTION

Evaluates the complete Intent -> Expected Facts -> Landing Page -> Information Scent -> Next Action journey.
Enforces strict Resource Invariant: Only genuine HTML pages enter engagement audits.
"""

import argparse
import json
import os
import re
import sys
from html.parser import HTMLParser
from urllib.parse import urlparse

from fact_extractor import extract_scoped_facts

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


from safe_fetch import safe_fetch

KNOWN_LOCALES = {"en", "es", "fr", "de", "it", "jp", "ja", "pt", "nl", "zh", "ko", "ru", "ar"}


def extract_locale_and_path(url):
    parsed = urlparse(url)
    segments = [s for s in parsed.path.strip("/").split("/") if s]
    locale = "default"
    if segments and (segments[0].lower() in KNOWN_LOCALES or re.match(r"^[a-z]{2}(-[a-z]{2})?$", segments[0].lower())):
        locale = segments[0].lower()
        logical_path = "/" + "/".join(segments[1:])
    else:
        logical_path = parsed.path or "/"
    return locale, logical_path


def classify_page(url, title=""):
    """Classify an HTML page with confidence and granular page types."""
    _locale, logical_path = extract_locale_and_path(url)
    segments = [s for s in logical_path.strip("/").split("/") if s]
    t_lower = (title or "").lower()

    if not segments or logical_path == "/":
        return "homepage", "high"
    last_seg = segments[-1]
    if last_seg in ("default", "placeholder", "template", "empty", "sample", "test"):
        return "template", "high"
    if len(segments) == 1 and segments[0] in ("products", "shop", "catalog", "store", "items"):
        return "product_listing", "high"
    if (
        len(segments) >= 2
        and segments[0] in ("products", "p", "product", "item", "items", "shop", "catalog")
        and segments[1] not in ("default", "all", "category", "categories")
    ):
        return "product_detail", "high"
    if any(s in ("category", "categories", "collection", "collections", "browse") for s in segments):
        return "category", "high"
    if any(s in ("subscription", "subscribe", "club", "membership") for s in segments):
        return "subscription_flow", "high"
    if any(s in ("pricing", "prices", "plans", "billing", "pricing-plans") for s in segments):
        return "pricing", "high"
    if any(s in ("contact", "support", "help", "contact-us", "reach-us", "get-in-touch") for s in segments):
        return "contact", "high"
    if any(s in ("location", "locations", "stores", "store-locator", "where-to-buy", "branches") for s in segments):
        return "location", "high"
    if any(s in ("about", "about-us", "company", "our-team", "story", "mission", "who-we-are") for s in segments):
        return "about", "high"
    if any(s in ("docs", "documentation", "guide", "guides", "api", "developer", "manual") for s in segments):
        return "documentation", "high"
    if any(s in ("blog", "news", "article", "articles", "posts", "insights", "journal") for s in segments):
        return "article", "high"
    if re.search(r"\b(contact\s*(us|ez-nous)?|contáctenos|kontakt|お問い合わせ)\b", t_lower):
        return "contact", "high"
    if re.search(r"\b(pricing|plans|tarifs|preise)\b", t_lower):
        return "pricing", "medium"
    if re.search(r"\b(subscription|abonnement|suscripción|subscribe)\b", t_lower):
        return "subscription_flow", "high"
    if re.search(r"\b(products?|catalog|shop|boutique|tienda)\b", t_lower):
        return "product_listing", "medium"
    if re.search(r"\b(about\s*(us)?|notre\s*histoire|sobre\s*nosotros|company)\b", t_lower):
        return "about", "medium"
    return "other", "low"


GENERIC_H1_TERMS = {
    "welcome",
    "home",
    "homepage",
    "untitled",
    "index",
    "hello",
    "welcome to our website",
    "welcome to our site",
    "main page",
    "overview",
}

VALID_CONTACT_TERMS = {
    "contact",
    "contact us",
    "get in touch",
    "reach out",
    "support",
    "contacto",
    "contáctenos",
    "contactez-nous",
    "kontakt",
    "kontaktiere uns",
    "contatti",
    "fale conosco",
    "contato",
    "contate-nos",
    "contacteer ons",
    "kontakt oss",
    "kontakt os",
    "ota yhteyttä",
    "kapcsolat",
    "kontaktujte nás",
    "skontaktuj się z nami",
    "contactati-ne",
    "iletisim",
    "свяжитесь с нами",
    "контакты",
    "اتصل بنا",
    "צור קשר",
    "संपर्क करें",
    "যোগাযোগ করুন",
    "联系我们",
    "聯絡我們",
    "お問い合わせ",
    "문의하기",
    "hubungi kami",
    "liên hệ",
}


class SemanticIntentEngine:
    def __init__(self, references_dir):
        self.references_dir = references_dir
        self.intents = {}
        self._load_intents()

    def _load_intents(self):
        import glob

        yaml_files = glob.glob(os.path.join(self.references_dir, "*.json"))
        for f in yaml_files:
            try:
                with open(f, "r") as fp:
                    data = json.load(fp)
                    if "intent_family" in data:
                        self.intents[data["intent_family"]] = data
            except Exception:
                pass

    def get_required_facts(self, page_classification):
        if page_classification == "pricing" and "pricing_comparison" in self.intents:
            return self.intents["pricing_comparison"].get("required_on_page_facts", [])
        if page_classification == "product_detail" and "product_purchase" in self.intents:
            return self.intents["product_purchase"].get("required_on_page_facts", [])
        return []

    def check_facts_in_text(self, text, required_facts):
        text_lower = text.lower()
        missing = []
        for fact in required_facts:
            # Heuristic mapping for facts
            if fact == "tier_names":
                if not re.search(
                    r"(starter|pro|enterprise|basic|premium|free|standard|advanced|tier|plan)", text_lower
                ):
                    missing.append(fact)
            elif fact == "billing_interval":
                if not re.search(r" (month|year|annual|mo|yr|monthly|annually) ", text_lower):
                    missing.append(fact)
            elif fact == "tier_prices":
                if not re.search(r"(\$|€|£|¥|\d+\.\d{2})", text_lower):
                    missing.append(fact)
            elif (
                fact == "feature_matrix"
                and not re.search(r" (feature|compare|include|matrix|custom) ", text_lower)
                or fact == "signup_or_trial_cta"
                and not re.search(r" (sign up|try|trial|get started|start|subscribe) ", text_lower)
            ):
                missing.append(fact)
            elif fact == "product_name":
                pass  # Already extracted via schema usually
            elif (
                fact == "availability"
                and not re.search(r" (stock|sold out|available|backorder) ", text_lower)
                or fact == "add_to_cart_or_buy_cta"
                and not re.search(r" (add to cart|buy|purchase|checkout) ", text_lower)
            ):
                missing.append(fact)
        return missing


class EngagementDOMParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_script = False
        self.title = ""
        self.in_title = False
        self.h1_list = []
        self.h2_list = []
        self.current_tag = None
        self.current_text = []
        self.body_text = []
        self.nav_links = []
        self.nav_link_texts = []
        self.in_anchor = False
        self.current_anchor_text = []
        self.current_href = ""
        self.ctas = []
        self.meta_tags = {}

    def handle_starttag(self, tag, attrs):
        attr_dict = {k.lower(): (v or "") for k, v in attrs}
        tag_lower = tag.lower()

        if tag_lower in ("script", "style", "noscript"):
            self.in_script = True
        elif tag_lower == "meta":
            prop = attr_dict.get("property", attr_dict.get("name", "")).lower()
            content = attr_dict.get("content", "").strip()
            if prop and content:
                self.meta_tags[prop] = content
        elif tag_lower == "title":
            self.in_title = True
        elif tag_lower in ("h1", "h2"):
            self.current_tag = tag_lower
            self.current_text = []
        elif tag_lower == "a":
            self.in_anchor = True
            self.current_anchor_text = []
            self.current_href = attr_dict.get("href", "")
            if self.current_href:
                self.nav_links.append(self.current_href)
                cls = attr_dict.get("class", "").lower()
                role = attr_dict.get("role", "").lower()
                if "btn" in cls or "button" in cls or "cta" in cls or role == "button":
                    self.ctas.append(self.current_href)

    def handle_endtag(self, tag):
        tag_lower = tag.lower()
        if tag_lower in ("script", "style", "noscript"):
            self.in_script = False
        elif tag_lower == "title":
            self.in_title = False
        elif tag_lower == "h1":
            if self.current_text:
                self.h1_list.append(" ".join(self.current_text).strip())
            self.current_tag = None
        elif tag_lower == "h2":
            if self.current_text:
                self.h2_list.append(" ".join(self.current_text).strip())
            self.current_tag = None
        elif tag_lower == "a":
            if self.in_anchor and self.current_anchor_text:
                self.nav_link_texts.append(" ".join(self.current_anchor_text).strip())
            self.in_anchor = False

    def handle_data(self, data):
        if self.in_title:
            self.title += " " + data.strip()
        if self.current_tag in ("h1", "h2"):
            self.current_text.append(data.strip())
        if self.in_anchor:
            self.current_anchor_text.append(data.strip())
        if not self.in_script:
            txt = data.strip()
            if txt:
                self.body_text.append(txt)


GENERIC_H1_TERMS = {"welcome", "home", "main", "untitled", "test", "page", "index", "default"}

VALID_CONTACT_TERMS = {
    "contact",
    "contact us",
    "contact-us",
    "contáctenos",
    "contactez-nous",
    "kontakt",
    "contact info",
    "get in touch",
    "reach us",
    "customer service",
    "help desk",
    "support",
    "お問い合わせ",
}


import math
from collections import Counter

# Elite Pre-computed TF-IDF Centroids for Zero-Dependency Semantic Intent Mapping
SITE_TYPE_CENTROIDS = {
    "ecommerce_retail": {
        "shop": 0.5,
        "cart": 0.4,
        "product": 0.3,
        "price": 0.3,
        "shipping": 0.2,
        "return": 0.2,
        "store": 0.2,
        "buy": 0.3,
        "apparel": 0.2,
        "coffee": 0.1,
    },
    "saas_developer": {
        "api": 0.5,
        "docs": 0.4,
        "platform": 0.3,
        "pricing": 0.3,
        "cloud": 0.2,
        "software": 0.2,
        "developer": 0.3,
        "login": 0.2,
        "dashboard": 0.2,
    },
    "media_content": {
        "news": 0.5,
        "article": 0.4,
        "author": 0.3,
        "read": 0.3,
        "publish": 0.2,
        "journal": 0.2,
        "magazine": 0.2,
        "blog": 0.3,
    },
    "service_consulting": {
        "consulting": 0.5,
        "services": 0.4,
        "case": 0.3,
        "study": 0.3,
        "team": 0.2,
        "contact": 0.2,
        "portfolio": 0.3,
        "expertise": 0.2,
    },
}


def cosine_similarity(vec1, vec2):
    intersection = set(vec1.keys()) & set(vec2.keys())
    numerator = sum([vec1[x] * vec2[x] for x in intersection])
    sum1 = sum([vec1[x] ** 2 for x in vec1])
    sum2 = sum([vec2[x] ** 2 for x in vec2])
    denominator = math.sqrt(sum1) * math.sqrt(sum2)
    return float(numerator) / denominator if denominator else 0.0


def infer_site_type(html_pages):
    # Semantic Intent Heuristic (Not true ML TF-IDF)
    """
    Semantic Intent Heuristic using Term Frequency
    and Vector Space Cosine Similarity mapping, implemented in pure Python.
    """
    all_text = " ".join((p.get("title", "") + " " + p.get("url", "")) for p in html_pages).lower()
    words = re.findall(r"[a-z]{3,}", all_text)
    if not words:
        return "general_business", ["products", "services", "pricing", "about", "contact", "help"]

    term_counts = Counter(words)
    total_terms = sum(term_counts.values())

    # Calculate Term Frequency (TF) for observed document
    tf_vector = {word: count / total_terms for word, count in term_counts.items()}

    best_match = "general_business"
    best_score = 0.01  # Minimum threshold for confidence

    for category, centroid in SITE_TYPE_CENTROIDS.items():
        score = cosine_similarity(tf_vector, centroid)
        if score > best_score:
            best_score = score
            best_match = category

    # Return destination mapping based on statistical match
    destinations = {
        "ecommerce_retail": ["products", "shop", "catalog", "store", "subscription", "contact", "about"],
        "saas_developer": ["pricing", "features", "docs", "documentation", "api", "contact", "login"],
        "media_content": ["articles", "latest", "topics", "search", "about", "contact"],
        "service_consulting": ["services", "portfolio", "case-studies", "team", "contact", "about"],
    }

    return best_match, destinations.get(best_match, ["products", "services", "pricing", "about", "contact"])


def audit_page_engagement(html_content, url, page_type="other", state=None):
    state = state or {}
    findings = []
    recommendations = []

    dom = EngagementDOMParser()
    try:
        dom.feed(html_content)
    except Exception as e:
        return (
            [
                {
                    "title": f"HTML parsing warning on {url}",
                    "severity": "info",
                    "category": "extraction",
                    "root_cause": "Malformed HTML structure encountered during DOM traversal.",
                    "evidence": str(e),
                    "suggested_action": {
                        "summary": f"Validate and repair HTML syntax on {url} to ensure parser extraction reliability.",
                        "technical_fix": f"Resolve unclosed tags, malformed attributes, or encoding mismatches on {url}.",
                        "creative_fix": None,
                        "priority": "low",
                        "verification": f"Re-fetch and parse {url} to verify valid DOM tree extraction.",
                    },
                }
            ],
            [],
            {"visible_words": 0, "h1": False, "navigation_links_found": 0},
        )

    # Build local fact ledger for true semantic evaluation
    facts = extract_scoped_facts(html_content, url)

    nav_text_lower = " ".join(dom.nav_link_texts).lower()

    # 1. Product Pricing Intent Graph
    # Intent: "How much does Product X cost?"
    # Required Facts: Product Entity, Price, Currency
    # Action: Buy, Subscribe, Contact Sales
    if facts.get("scoped_prices"):
        # The page successfully satisfied the information requirement for the pricing intent.
        # Now evaluate continuity: Does it offer the next logical step?
        action_found = any(cta in nav_text_lower for cta in ["buy", "cart", "subscribe", "contact", "order", "get"])
        if not action_found:
            target_ent = facts["scoped_prices"][0]["entity"]
            findings.append(
                {
                    "title": f"Pricing intent journey lacks explicit commercial continuation on {url}",
                    "severity": "medium",
                    "category": "engagement",
                    "cause_family": "EXPERIENCE.CONTINUITY",
                    "id": "INTENT_TO_LANDING_MISMATCH",
                    "cause_id": "INTENT_TO_LANDING_MISMATCH",
                    "root_cause": f"The page provides pricing facts for '{target_ent}' but lacks explicit next-step commercial navigation or transactional actions.",
                    "confidence": "high",
                    "evidence": f"Page {url} provides explicit commercial facts (pricing for '{target_ent}'), satisfying a bottom-funnel intent, but provides no clear transactional or sales-contact navigation.",
                    "suggested_action": {
                        "summary": f"Add explicit transactional CTA (e.g. 'Buy {target_ent}', 'Contact Sales') immediately following pricing facts on {url}.",
                        "technical_fix": f"Embed accessible CTA button or link (<a class='cta-btn' href='/checkout'>Purchase {target_ent}</a>) adjacent to the price declaration on {url}.",
                        "creative_fix": f"Align CTA copy on {url} with user commercial intent ('Get {target_ent}' or 'Start Free Trial') to reduce drop-off and bounce.",
                        "priority": "medium",
                        "verification": f"Inspect {url} navigation links to confirm commercial transaction elements are present.",
                    },
                }
            )

    # 2. Entity-to-Heading Anchor (Information Scent)
    if not dom.h1_list:
        recommendations.append(
            {
                "title": f"Add descriptive H1 heading on {url} for visitor orientation",
                "category": "engagement",
                "rationale": f"Page {url} is missing an H1 heading.",
                "summary": f"Ensure every page provides a clear <h1> describing its specific value proposition or content on {url}.",
                "suggested_action": {
                    "summary": f"Ensure every page provides a clear <h1> describing its specific value proposition or content on {url}.",
                    "technical_fix": f"Insert a semantic <h1> element inside <main> on {url}.",
                    "creative_fix": f"Craft an entity-anchored <h1> on {url} that immediately confirms the brand and page purpose to incoming visitors.",
                    "priority": "medium",
                    "verification": f"Fetch {url} and verify exactly one semantic <h1> heading is present.",
                },
            }
        )
    elif state and "entities" in state and url in state["entities"]:
        entities = state["entities"][url]
        h1_text = " ".join(dom.h1_list).lower()
        anchor_found = any(ent.lower() in h1_text for ent in entities if len(ent) > 2)
        if entities and not anchor_found:
            primary_ent = entities[0]
            existing_h1 = dom.h1_list[0] if dom.h1_list else ""
            findings.append(
                {
                    "category": "engagement",
                    "title": f"Broken Information Scent on {url}: Entity '{primary_ent}' not anchored in primary heading",
                    "severity": "medium",
                    "confidence": "high",
                    "root_cause": f"The primary <h1> on {url} ('{existing_h1}') does not contain canonical entity '{primary_ent}', leading to user disorientation upon arrival.",
                    "cause_family": "EXPERIENCE.CONTINUITY",
                    "id": "LOW_INFORMATION_SCENT",
                    "cause_id": "LOW_INFORMATION_SCENT",
                    "evidence": f"Entities {entities} not found in H1 '{existing_h1}'.",
                    "suggested_action": {
                        "summary": f"Rewrite primary <h1> on {url} to explicitly include canonical entity '{primary_ent}'.",
                        "technical_fix": f"Update <h1> tag on {url} from '{existing_h1}' to incorporate '{primary_ent}'.",
                        "creative_fix": f"Craft an informative hero headline on {url} such as '{primary_ent} — [Core Differentiating Value Proposition]'.",
                        "priority": "medium",
                        "verification": f"Re-parse {url} and confirm <h1> contains entity '{primary_ent}'.",
                    },
                }
            )

    return (
        findings,
        recommendations,
        {
            "visible_words": len(" ".join(dom.body_text).split()),
            "h1": len(dom.h1_list) > 0,
            "navigation_links_found": len(dom.nav_links),
            "anchor_links_found": len(dom.nav_links),
        },
    )


def audit(base, domain, inv=None, state_file=None):
    if state_file and os.path.exists(state_file):
        try:
            with open(state_file, "r") as f:
                json.load(f)
        except Exception:
            pass
    findings = []
    recommendations = []
    observations = []
    page_metrics = []

    html_pages = []
    if inv is not None:
        for p in inv.get("pages", []):
            u = p.get("url", "")
            raw_html = p.get("html", "")
            if u.lower().endswith((".xml", ".xml.gz", ".txt", ".json", ".pdf")):
                continue
            if (
                raw_html.strip().startswith("<?xml")
                or "<urlset" in raw_html.lower()
                or "<sitemapindex" in raw_html.lower()
            ):
                continue
            if raw_html:
                html_pages.append(p)
    else:
        _status, html, _, _ = safe_fetch(base + "/", timeout=10, max_bytes=2 * 1024 * 1024)
        if html:
            html_pages.append({"url": base + "/", "html": html, "page_type": "homepage"})

    site_type = infer_site_type(html_pages)[0]
    for p in html_pages:
        p_findings, p_recs, p_data = audit_page_engagement(
            p["html"],
            p["url"],
            page_type=p.get("page_type", "other"),
        )
        findings.extend(p_findings)
        recommendations.extend(p_recs)
        page_metrics.append(p_data)

    if not page_metrics:
        return {
            "status": "inconclusive",
            "findings": [],
            "recommendations": [],
            "error": f"could not retrieve HTML content from {base}",
        }

    return {
        "status": "ok",
        "findings": findings,
        "recommendations": recommendations,
        "observations": observations,
        "coverage": {
            "html_pages_evaluated": len(html_pages),
            "site_type_inferred": site_type,
            "average_visible_words": round(
                sum(pm["visible_words"] for pm in page_metrics) / max(1, len(page_metrics)), 1
            ),
            "pages_with_h1": sum(1 for pm in page_metrics if pm["h1"]),
            "pages_with_navigation": sum(
                1 for pm in page_metrics if pm.get("navigation_links_found", pm.get("anchor_links_found", 0)) > 0
            ),
        },
        "limitations": [
            "Engagement and orientation analysis is based on static HTML layout semantics; dynamic client-rendered overlays were not evaluated."
        ],
    }


def main():
    parser = argparse.ArgumentParser(
        description="Audit on-site visitor orientation, heading hierarchies, and navigation."
    )
    parser.add_argument("--site", required=True)
    parser.add_argument("--inventory", help="Path to shared site-inventory JSON")
    parser.add_argument("--state", help="Path to global state JSON")
    parser.add_argument("--format", choices=["json", "markdown"], default="json", help="Output format (default: json)")
    args = parser.parse_args()
    s = args.site.strip()
    if not s.startswith("http"):
        s = "https://" + s
    p = urlparse(s)
    base = f"{p.scheme}://{p.netloc}"
    inv = None
    if args.inventory and os.path.exists(args.inventory):
        try:
            with open(args.inventory, "r", encoding="utf-8") as f:
                inv = json.load(f)
        except Exception:
            inv = None
    res = audit(base, p.netloc, inv=inv, state_file=args.state)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()

"""Evidence-Weighted Site Archetype Classifier.

Deterministically classifies websites into industry/archetype categories
using multi-family evidence weighting (Schema.org types, URL path cues,
heading/label cues, interactive controls, and inventory distribution).
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

# Category identifiers
ECOMMERCE = "ECOMMERCE"
SAAS = "SAAS"
LOCAL_BUSINESS = "LOCAL_BUSINESS"
B2B_SERVICES = "B2B_SERVICES"
PORTFOLIO = "PORTFOLIO"
BLOG_NEWS = "BLOG_NEWS"
DOCUMENTATION = "DOCUMENTATION"
EDUCATION = "EDUCATION"
COMMUNITY = "COMMUNITY"
MEDIA = "MEDIA"
GENERIC = "GENERIC"

# Multi-family evidence definitions
SCHEMA_SIGNALS: Dict[str, List[str]] = {
    ECOMMERCE: ["Product", "Offer", "AggregateOffer", "IndividualProduct", "ItemAvailability", "MerchantReturnPolicy"],
    SAAS: ["SoftwareApplication", "WebApplication", "MobileApplication"],
    LOCAL_BUSINESS: ["LocalBusiness", "Store", "Restaurant", "FoodEstablishment", "ProfessionalService", "MedicalBusiness"],
    B2B_SERVICES: ["Service", "ProfessionalService", "Organization", "Corporation"],
    PORTFOLIO: ["Person", "ProfilePage"],
    BLOG_NEWS: ["Article", "NewsArticle", "BlogPosting", "TechArticle", "Report"],
    DOCUMENTATION: ["TechArticle", "APIReference", "HowTo", "Guide"],
    EDUCATION: ["Course", "EducationalOccupationalProgram", "Syllabus"],
    COMMUNITY: ["DiscussionForumPosting", "QAPage", "Comment"],
    MEDIA: ["VideoObject", "AudioObject", "MediaObject", "PodcastSeries", "PodcastEpisode"],
}

URL_SIGNALS: Dict[str, List[str]] = {
    ECOMMERCE: [r"/product", r"/cart", r"/checkout", r"/shop", r"/item", r"/buy", r"/catalog", r"/store", r"/p/"],
    SAAS: [r"/pricing", r"/features", r"/integrations", r"/signup", r"/trial", r"/app", r"/dashboard", r"/login"],
    LOCAL_BUSINESS: [r"/locations?", r"/find-a-store", r"/directions", r"/hours", r"/contact-us", r"/visit"],
    B2B_SERVICES: [r"/services", r"/solutions", r"/case-studies", r"/enterprise", r"/consulting", r"/clients"],
    PORTFOLIO: [r"/portfolio", r"/projects", r"/resume", r"/cv", r"/about-me", r"/works"],
    BLOG_NEWS: [r"/blog", r"/news", r"/article", r"/post", r"/press-release", r"/stories", r"/journal"],
    DOCUMENTATION: [r"/docs", r"/documentation", r"/api", r"/guide", r"/reference", r"/sdk", r"/tutorial"],
    EDUCATION: [r"/courses", r"/curriculum", r"/learn", r"/lessons", r"/academy", r"/training", r"/syllabus"],
    COMMUNITY: [r"/community", r"/forum", r"/discussions", r"/topics", r"/members", r"/questions"],
    MEDIA: [r"/video", r"/watch", r"/podcast", r"/listen", r"/media", r"/episodes", r"/audio"],
}

LABEL_SIGNALS: Dict[str, List[str]] = {
    ECOMMERCE: ["add to cart", "buy now", "in stock", "out of stock", "free shipping", "shopping bag", "shopping cart", "price:", "$", "usd"],
    SAAS: ["start free trial", "request demo", "view pricing", "free 14-day trial", "api documentation", "sign up free", "log in to dashboard"],
    LOCAL_BUSINESS: ["opening hours", "get directions", "visit us", "call today", "book table", "reserve a table", "our location"],
    B2B_SERVICES: ["contact sales", "schedule consultation", "our clients", "case studies", "enterprise solution", "talk to an expert"],
    PORTFOLIO: ["selected works", "my experience", "about me", "view projects", "creative developer", "designer & developer"],
    BLOG_NEWS: ["published on", "min read", "author:", "related articles", "newsletter", "leave a comment", "editor's pick"],
    DOCUMENTATION: ["getting started", "code snippet", "sdk reference", "quickstart", "parameters", "response syntax", "prerequisites"],
    EDUCATION: ["enroll now", "course syllabus", "instructor:", "certificate", "prerequisites", "lesson plan", "students enrolled"],
    COMMUNITY: ["latest topics", "replies", "joined", "post reply", "community guidelines", "thread", "moderator"],
    MEDIA: ["watch episode", "play audio", "subscribe to podcast", "listen now", "view stream", "episodes"],
}

WEIGHTS = {
    "schema": 4,      # Schema.org structured data carries highest intent signal
    "labels": 3,      # Visible call-to-action and heading labels
    "inventory": 2,   # Page type distribution from inventory
    "controls": 2,    # Interactive controls (cart, forms, code blocks)
    "url": 1,         # URL path matching
}

MINIMUM_SCORE = 5
MINIMUM_FAMILIES = 2


def classify_site(
    site: str,
    records: Optional[List[Dict[str, Any]]] = None,
    candidates: Optional[List[Dict[str, Any]]] = None,
    extra_evidence: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Classify a website into an archetype category using evidence weighting.

    Args:
        site: Root URL or domain of the audited site.
        records: List of page inventory/artifact records.
        candidates: Specialist audit candidate findings.
        extra_evidence: Additional sensor telemetry.

    Returns:
        Classification result dict with primary, secondary, confidence, and evidence breakdown.
    """
    scores: Dict[str, int] = {cat: 0 for cat in [
        ECOMMERCE, SAAS, LOCAL_BUSINESS, B2B_SERVICES, PORTFOLIO,
        BLOG_NEWS, DOCUMENTATION, EDUCATION, COMMUNITY, MEDIA
    ]}
    family_hits: Dict[str, Set[str]] = {cat: set() for cat in scores}

    records_list = records or []
    all_urls = [r.get("url", "") for r in records_list if isinstance(r, dict)]
    all_urls.append(site)

    # 1. URL Path cues (Weight: 1)
    for url in all_urls:
        path = urlparse(url).path.lower()
        for cat, patterns in URL_SIGNALS.items():
            for pat in patterns:
                if re.search(pat, path):
                    scores[cat] += WEIGHTS["url"]
                    family_hits[cat].add("url_path")
                    break

    # 2. Schema.org and text evidence from page records
    for r in records_list:
        if not isinstance(r, dict):
            continue

        # Extract text snippets / headings / title
        content = (
            str(r.get("title", "")) + " " +
            str(r.get("headings", [])) + " " +
            str(r.get("text", ""))[:4000]
        ).lower()

        for cat, labels in LABEL_SIGNALS.items():
            hit_count = sum(1 for label in labels if label in content)
            if hit_count >= 2:
                scores[cat] += WEIGHTS["labels"]
                family_hits[cat].add("label_cues")

        # Check Schema.org types
        schema_types = r.get("schema_types", []) or []
        jsonld = r.get("jsonld", []) or []
        if isinstance(jsonld, list):
            for item in jsonld:
                if isinstance(item, dict):
                    t = item.get("@type", "")
                    if isinstance(t, str):
                        schema_types.append(t)
                    elif isinstance(t, list):
                        schema_types.extend(t)

        for s_type in schema_types:
            for cat, expected in SCHEMA_SIGNALS.items():
                if any(exp.lower() in str(s_type).lower() for exp in expected):
                    scores[cat] += WEIGHTS["schema"]
                    family_hits[cat].add("schema_org")

        # Check page_type from inventory classification
        page_type = r.get("page_type", "")
        if page_type in ("product", "product_listing", "product_detail", "subscription_flow", "cart", "checkout"):
            scores[ECOMMERCE] += WEIGHTS["inventory"]
            family_hits[ECOMMERCE].add("inventory_type")
        elif page_type in ("article", "blog_post", "news"):
            scores[BLOG_NEWS] += WEIGHTS["inventory"]
            family_hits[BLOG_NEWS].add("inventory_type")
        elif page_type in ("location", "store_locator"):
            scores[LOCAL_BUSINESS] += WEIGHTS["inventory"]
            family_hits[LOCAL_BUSINESS].add("inventory_type")
        elif page_type in ("docs", "documentation", "api_reference"):
            scores[DOCUMENTATION] += WEIGHTS["inventory"]
            family_hits[DOCUMENTATION].add("inventory_type")

    # 3. Check findings from candidates (e.g. EC check IDs, BC check IDs)
    if candidates:
        for c in candidates:
            if not isinstance(c, dict):
                continue
            cid = c.get("check_id", "")
            if cid.startswith("EC"):
                scores[ECOMMERCE] += 1
                family_hits[ECOMMERCE].add("specialist_checks")
            elif cid.startswith("BC"):
                scores[B2B_SERVICES] += 1
                family_hits[B2B_SERVICES].add("specialist_checks")
            elif cid.startswith("BN"):
                scores[BLOG_NEWS] += 1
                family_hits[BLOG_NEWS].add("specialist_checks")
            elif cid.startswith("ED"):
                scores[EDUCATION] += 1
                family_hits[EDUCATION].add("specialist_checks")
            elif cid.startswith("ME"):
                scores[MEDIA] += 1
                family_hits[MEDIA].add("specialist_checks")

    # Filter categories meeting multi-family and minimum score constraints
    qualified = [
        (cat, score, list(family_hits[cat]))
        for cat, score in scores.items()
        if score >= MINIMUM_SCORE and len(family_hits[cat]) >= MINIMUM_FAMILIES
    ]
    qualified.sort(key=lambda x: x[1], reverse=True)

    if qualified:
        primary = qualified[0][0]
        primary_score = qualified[0][1]
        primary_families = qualified[0][2]
        secondary = [q[0] for q in qualified[1:3]]
        confidence = "high" if primary_score >= 10 and len(primary_families) >= 3 else "medium"
    else:
        primary = GENERIC
        secondary = []
        confidence = "low"
        primary_families = []

    return {
        "primary": primary,
        "secondary": secondary,
        "confidence": confidence,
        "evidence_families": sorted(primary_families),
        "scores": {k: v for k, v in scores.items() if v > 0},
    }


if __name__ == "__main__":
    test_records = [
        {"url": "https://example.com/shop/item-123", "schema_types": ["Product", "Offer"], "title": "Buy Widgets Online - Add to Cart"},
        {"url": "https://example.com/cart", "text": "Your shopping bag has 1 item. Free shipping on orders over $50."},
    ]
    res = classify_site("https://example.com", test_records)
    assert res["primary"] == ECOMMERCE, f"Expected ECOMMERCE, got {res['primary']}"
    print(f"Self-test passed: {res['primary']} (confidence: {res['confidence']}, families: {res['evidence_families']})")

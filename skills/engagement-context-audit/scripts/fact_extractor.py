#!/usr/bin/env python3
"""
fact_consistency_check.py - Audits fact freshness, update timestamps, and cross-page fact consistency.

Causal Root Causes:
  - FACT.CONSISTENCY: FIRST_PARTY_FACT_CONFLICT, CONFLICTING_COMMERCIAL_TERMS
  - FACT.FRESHNESS: LEGACY_FACT_PROPAGATION, STALE_AUTHORITATIVE_FACT
  - FACT.LIFECYCLE: DISCONTINUED_VS_CURRENT_CONFLICT
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urlparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


from safe_fetch import safe_fetch

CURRENT_YEAR = datetime.now(timezone.utc).year
PRICE_PATTERN = re.compile(r"(?:₹|Rs\.?|INR|\$|USD|€|EUR|£|GBP)\s?(\d[\d,]*(?:\.\d{1,2})?)", re.IGNORECASE)
EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"(?:\+\d{1,3}[\s-]?)?(?:\(?\d{2,4}\)?[\s-]?){2,4}\d{2,4}")
DISCONTINUED_PATTERN = re.compile(
    r"\b(discontinued|retired|legacy|obsolete|end of life|out of production)\b", re.IGNORECASE
)


def extract_currency(raw_str):
    s = (raw_str or "").upper()
    if "₹" in raw_str or "INR" in s or "RS" in s:
        return "INR"
    if "R$" in s or "BRL" in s:
        return "BRL"
    if "C$" in s or "CAD" in s:
        return "CAD"
    if "A$" in s or "AUD" in s:
        return "AUD"
    if "$" in raw_str or "USD" in s:
        return "USD"
    if "€" in raw_str or "EUR" in s:
        return "EUR"
    if "£" in raw_str or "GBP" in s:
        return "GBP"
    if "¥" in raw_str or "JPY" in s or "CNY" in s or "RMB" in s:
        return "JPY"
    if "AED" in s or "DHS" in s:
        return "AED"
    return "UNKNOWN"


def extract_interval(raw_str):
    s = (raw_str or "").lower()
    if re.search(
        r"(\bmonthly\b|\bper\s+month\b|/\s*mo\b|/\s*month\b|\bper\s+user/mo\b|\bper\s+seat/mo\b|/\s*user/month\b|/\s*seat/month\b|\bbilled\s+monthly\b)",
        s,
    ):
        return "month"
    if re.search(
        r"(\bannually\b|\bannual\b|\byearly\b|\bper\s+year\b|/\s*yr\b|/\s*year\b|\bbilled\s+annually\b|\bbilled\s+yearly\b|/\s*user/year\b|/\s*seat/year\b)",
        s,
    ):
        return "year"
    if re.search(r"(\bweekly\b|\bper\s+week\b|/\s*wk\b|/\s*week\b)", s):
        return "week"
    if re.search(r"(\bdaily\b|\bper\s+day\b|/\s*day\b)", s):
        return "day"
    return "one_time"


def normalize_price_str(raw, currency=None):
    """Normalize price string to standardized float string representation (e.g. '$49.99' -> '49.99', '€1.250,50' -> '1250.50', '₹5,499' -> '5499.00')."""
    if not raw:
        return None
    s = str(raw).strip()
    # European format with dot thousand separator and comma decimal: 1.250,50
    if re.search(r"\d+\.\d{3},\d{2}", s):
        s = s.replace(".", "").replace(",", ".")
    elif "," in s and "." in s:
        # Standard US/UK: 1,250.50
        s = s.replace(",", "")
    elif "," in s:
        parts = s.split(",")
        if len(parts) == 2 and len(parts[1]) == 2:
            s = parts[0] + "." + parts[1]
        else:
            s = s.replace(",", "")

    m = re.search(r"(\d+(?:\.\d{1,2})?)", s)
    if not m:
        return None
    try:
        val = float(m.group(1))
        return f"{val:.2f}"
    except ValueError:
        return None


class FreshnessAnalyzer(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_script = False
        self.in_json_ld = False
        self.json_ld_contents = []
        self.meta_tags = {}
        self.text_content = []
        self.headings = []
        self.current_h = None
        self.current_h_text = []
        self.current_section = "General"
        self.text_with_context = []

    def handle_starttag(self, tag, attrs):
        attr_dict = {k.lower(): (v or "") for k, v in attrs}
        tag_lower = tag.lower()

        if tag_lower in ("script", "style"):
            self.in_script = True
            if tag_lower == "script" and "application/ld+json" in attr_dict.get("type", "").lower():
                self.in_json_ld = True
        elif tag_lower == "meta":
            prop = attr_dict.get("property", attr_dict.get("name", "")).lower()
            content = attr_dict.get("content", "")
            if prop and content:
                self.meta_tags[prop] = content
        elif tag_lower in ("h1", "h2", "h3", "h4"):
            self.current_h = tag_lower
            self.current_h_text = []

    def handle_endtag(self, tag):
        tag_lower = tag.lower()
        if tag_lower in ("script", "style"):
            self.in_script = False
            self.in_json_ld = False
        elif tag_lower in ("h1", "h2", "h3", "h4"):
            if self.current_h:
                htxt = " ".join(self.current_h_text).strip()
                if htxt:
                    self.headings.append((self.current_h, htxt))
                    self.current_section = htxt
            self.current_h = None

    def handle_data(self, data):
        if self.in_json_ld:
            self.json_ld_contents.append(data.strip())
        elif self.current_h is not None:
            self.current_h_text.append(data.strip())
        elif not self.in_script:
            txt = data.strip()
            if txt:
                self.text_content.append(txt)
                self.text_with_context.append((self.current_section, txt))


UTILITY_HEADINGS = {
    "contact",
    "contact us",
    "about",
    "about us",
    "privacy policy",
    "terms of service",
    "terms & conditions",
    "cart",
    "shopping cart",
    "checkout",
    "login",
    "register",
    "sign in",
    "sign up",
    "cookie policy",
    "faq",
    "faqs",
    "frequently asked questions",
    "search",
    "menu",
    "navigation",
    "home",
    "homepage",
    "welcome",
    "pricing",
    "plans",
    "subscription",
    "overview",
    "details",
    "features",
    "giving",
    "gives",
    "diversity",
    "impact",
    "donate",
    "donation",
    "usage",
    "usage limit",
    "limits",
    "support",
    "help",
    "careers",
    "press",
    "news",
    "blog",
    "events",
    "community",
    "resources",
    "general",
    "summary",
    "introduction",
    "conclusion",
    "table of contents",
    "highlights",
    "compare",
    "comparison",
    "reviews",
    "testimonials",
    "questions",
    "answers",
}


def is_valid_product_entity(name):
    """Validate whether a candidate heading or string is a plausible product/service entity name."""
    if not name or not isinstance(name, str):
        return False
    clean = name.strip()
    clean_lower = clean.lower()

    # Length boundaries: product/plan names are typically 3 to 50 characters
    if len(clean) < 3 or len(clean) > 50:
        return False

    # Must not end with question/colon punctuation (e.g. FAQ questions)
    if clean.endswith(("?", ":")):
        return False

    # Must not contain question prefixes or FAQ phrases
    question_prefixes = (
        "what ",
        "why ",
        "how ",
        "when ",
        "where ",
        "who ",
        "which ",
        "can ",
        "is ",
        "does ",
        "faq",
        "frequently ",
    )
    if clean_lower.startswith(question_prefixes):
        return False

    # Must not contain price tags, currency indicators, billing terms or math symbols
    if any(sym in clean for sym in ("$", "€", "£", "₹", "¥")):
        return False
    if re.search(
        r"\b(usd|eur|gbp|inr|cad|aud|per\s+month|per\s+user|per\s+year|/\s*mo|/\s*yr|billed|billing|pricing|tier|tiers|cost|rate|fee|fees|discount|first\s+\d+)\b",
        clean_lower,
    ):
        return False

    # Must not contain large digit spans or raw numbers
    if re.search(r"\d{2,}", clean):
        return False

    if clean_lower in UTILITY_HEADINGS:
        return False
    return not any(
        k in clean_lower
        for k in ("cookie", "privacy", "terms", "navigation", "diversity", "giving", "usage limit", "frequently asked")
    )


def resolve_json_ld_graph(raw_json_list):
    """Extract and resolve @graph node references (@id linking) in JSON-LD."""
    raw_objects = []
    for raw in raw_json_list:
        try:
            data = json.loads(raw)
            to_process = data if isinstance(data, list) else [data]
            for item in to_process:
                if isinstance(item, dict) and "@graph" in item and isinstance(item["@graph"], list):
                    raw_objects.extend(item["@graph"])
                elif isinstance(item, dict):
                    raw_objects.append(item)
        except Exception:
            pass

    id_map = {
        obj["@id"].strip(): obj
        for obj in raw_objects
        if isinstance(obj, dict) and "@id" in obj and isinstance(obj["@id"], str)
    }
    resolved = []
    for obj in raw_objects:
        if not isinstance(obj, dict):
            continue
        entity = dict(obj)
        if "offers" in entity:
            offers = entity["offers"]
            if isinstance(offers, dict) and "@id" in offers and offers["@id"] in id_map:
                entity["offers"] = id_map[offers["@id"]]
            elif isinstance(offers, list):
                entity["offers"] = [
                    id_map.get(o["@id"], o) if isinstance(o, dict) and "@id" in o and o["@id"] in id_map else o
                    for o in offers
                ]
        resolved.append(entity)

    for obj in raw_objects:
        if isinstance(obj, dict):
            raw_t = obj.get("@type", "")
            otypes = {str(t).lower() for t in raw_t} if isinstance(raw_t, list) else {str(raw_t).lower()}
            if otypes.intersection({"offer", "aggregateoffer"}):
                item_offered = obj.get("itemOffered")
                if isinstance(item_offered, dict) and "@id" in item_offered and item_offered["@id"] in id_map:
                    prod = id_map[item_offered["@id"]]
                    if "offers" not in prod:
                        prod["offers"] = []
                    elif isinstance(prod["offers"], dict):
                        prod["offers"] = [prod["offers"]]
                    if isinstance(prod["offers"], list) and obj not in prod["offers"]:
                        prod["offers"].append(obj)
    return resolved


def extract_scoped_facts(html_str, url):
    """Extract first-party facts with contextual scope, status, and lifecycle."""
    parser = FreshnessAnalyzer()
    try:
        parser.feed(html_str)
    except Exception:
        pass

    full_text = " ".join(parser.text_content)
    facts = {
        "url": url,
        "copyright_years": [],
        "brand_names": [],
        "taglines": [],
        "scoped_prices": [],
        "contact_emails": [],
        "contact_phones": [],
        "modification_dates": [],
        "products_with_status": [],
    }

    # 1. Copyright years
    matches = re.findall(r"(?:©|&copy;|copyright)\s*(?:[0-9]{4}\s*[-–]\s*)?([0-9]{4})", full_text, re.IGNORECASE)
    for y in matches:
        try:
            iy = int(y)
            if 1990 <= iy <= CURRENT_YEAR + 1:
                facts["copyright_years"].append(iy)
        except ValueError:
            pass
    facts["copyright_years"] = sorted(set(facts["copyright_years"]))

    # 2. Structured Data extraction with @graph node resolution
    resolved_json_ld = resolve_json_ld_graph(parser.json_ld_contents)
    for o in resolved_json_ld:
        raw_t = o.get("@type", "")
        otypes = {str(t).lower() for t in raw_t} if isinstance(raw_t, list) else {str(raw_t).lower()}
        if otypes.intersection({"organization", "brand", "corporation", "localbusiness"}):
            if o.get("name") and isinstance(o["name"], str):
                facts["brand_names"].append(o["name"].strip())
            if o.get("slogan"):
                facts["taglines"].append(str(o.get("slogan")).strip())
            if o.get("alternateName"):
                facts["brand_names"].append(str(o.get("alternateName")).strip())
        elif otypes.intersection({"product", "individualproduct", "productmodel", "softwareapplication", "service"}):
            pname = str(o.get("name") or "").strip()
            offers = o.get("offers") or {}
            offer_obj = offers[0] if isinstance(offers, list) and offers else offers
            if isinstance(offer_obj, dict):
                p_val = offer_obj.get("price") if offer_obj.get("price") is not None else offer_obj.get("lowPrice")
                p_curr = str(offer_obj.get("priceCurrency") or "UNKNOWN").upper()
                avail = str(offer_obj.get("availability") or "").lower()
                p_variant = str(offer_obj.get("sku") or offer_obj.get("name") or o.get("sku") or "default").strip()
                status = (
                    "discontinued"
                    if "discontinued" in avail
                    else ("in_stock" if "instock" in avail else ("preorder" if "preorder" in avail else "unknown"))
                )
                if pname and is_valid_product_entity(pname):
                    facts["products_with_status"].append({"name": pname, "status": status, "url": url})
                    if p_val:
                        norm_p = normalize_price_str(str(p_val), p_curr)
                        if norm_p:
                            facts["scoped_prices"].append(
                                {
                                    "entity": pname,
                                    "price": norm_p,
                                    "currency": p_curr,
                                    "interval": "one_time",
                                    "variant": p_variant,
                                    "raw": f"{p_curr} {p_val}",
                                }
                            )
        if "dateModified" in o and isinstance(o["dateModified"], str):
            facts["modification_dates"].append(o["dateModified"])
        elif "datePublished" in o and isinstance(o["datePublished"], str):
            facts["modification_dates"].append(o["datePublished"])

    # Meta / OpenGraph update timestamps and brand/title facts
    for meta_key in ("article:modified_time", "og:updated_time", "last-modified"):
        if meta_key in parser.meta_tags:
            facts["modification_dates"].append(parser.meta_tags[meta_key])

    if "og:site_name" in parser.meta_tags:
        facts["brand_names"].append(parser.meta_tags["og:site_name"].strip())

    # 4. Text-based scoped price extraction (ONLY within explicitly named, valid product sections)
    for ctx, txt in parser.text_with_context:
        if not ctx or ctx == "General" or not is_valid_product_entity(ctx):
            continue
        for m in re.finditer(r"(?:₹|Rs\.?|INR|\$|USD|€|EUR|£|GBP)\s?(\d[\d,]*(?:\.\d{1,2})?)", txt, re.IGNORECASE):
            curr = extract_currency(m.group(0))
            norm_p = normalize_price_str(m.group(1), curr)
            if norm_p and float(norm_p) > 0:
                invl = extract_interval(txt)
                if not any(
                    sp["price"] == norm_p
                    and sp["entity"].lower() == ctx.lower().strip()
                    and sp["currency"] == curr
                    and sp["interval"] == invl
                    for sp in facts["scoped_prices"]
                ):
                    facts["scoped_prices"].append(
                        {
                            "entity": ctx.strip(),
                            "price": norm_p,
                            "currency": curr,
                            "interval": invl,
                            "variant": "default",
                            "raw": m.group(0),
                        }
                    )

    # 5. Lifecycle text detection (Removed to prevent false positives)
    for h in parser.headings:
        h_text = h[1]
        if DISCONTINUED_PATTERN.search(h_text) and is_valid_product_entity(h_text):
            matched = False
            for p in facts["products_with_status"]:
                if p["name"].lower() == h_text.lower().strip():
                    p["status"] = "discontinued"
                    matched = True
            if not matched:
                facts["products_with_status"].append({"name": h_text.strip(), "status": "discontinued", "url": url})

    # 6. Scoped emails & phones
    for m in EMAIL_PATTERN.finditer(html_str):
        addr = m.group(0).strip(".").lower()
        if not addr.endswith((".png", ".jpg", ".gif", ".webp", ".js", ".css")):
            scope = "sales" if "sales" in addr else ("support" if "support" in addr else "general")
            facts["contact_emails"].append({"scope": scope, "email": addr})

    for m in PHONE_PATTERN.finditer(full_text):
        digits = re.sub(r"\D", "", m.group(0))
        if 8 <= len(digits) <= 15:
            facts["contact_phones"].append({"scope": "telephone", "phone": digits})

    # Deduplicate facts lists
    facts["brand_names"] = sorted(set(facts["brand_names"]))
    facts["taglines"] = sorted(set(facts["taglines"]))
    facts["modification_dates"] = sorted(set(facts["modification_dates"]))

    return facts


def evaluate_fact_consistency(page_fact_list, base_url):
    """Detect verified contradictions and lifecycle conflicts across first-party pages."""
    findings = []
    recommendations = []

    # 1. Scoped Price Contradictions (entity + currency + interval)
    # Price ledger: (entity, currency, interval) -> price -> set of URLs
    price_ledger = {}
    for pf in page_fact_list:
        for sp in pf["scoped_prices"]:
            ent = sp["entity"].lower().strip()
            if not is_valid_product_entity(ent):
                continue
            key = (ent, sp.get("currency", "USD"), sp.get("interval", "one_time"), sp.get("variant", "default"))
            price_ledger.setdefault(key, {}).setdefault(sp["price"], set()).add(pf["url"])

    for (ent, curr, invl, _var), val_map in price_ledger.items():
        if len(val_map) >= 2:
            # Map each URL to all prices it asserts for this entity
            url_to_prices = {}
            for price_val, urls in val_map.items():
                for u in urls:
                    url_to_prices.setdefault(u, set()).add(price_val)

            # Filter for URLs that assert a single distinct price (eliminating tiered single-page listings)
            clean_conflicts = {}
            for price_val, urls in val_map.items():
                single_price_urls = {u for u in urls if len(url_to_prices[u]) == 1}
                if single_price_urls:
                    clean_conflicts[price_val] = single_price_urls

            # A true cross-page conflict requires at least 2 different prices on at least 2 distinct URLs
            if len(clean_conflicts) >= 2:
                all_affected_urls = set()
                details = []
                for pval, urls in clean_conflicts.items():
                    all_affected_urls.update(urls)
                    for u in sorted(urls):
                        details.append(f"{curr} {pval} on {u}")

                if len(all_affected_urls) >= 2:
                    findings.append(
                        {
                            "category": "fact-consistency",
                            "title": f"Conflicting pricing published for '{ent}'",
                            "severity": "high",
                            "confidence": "high",
                            "root_cause": f"Different price values for '{ent}' ({curr}, {invl}) are published across separate first-party pages.",
                            "cause_family": "FACT.CONSISTENCY",
                            "cause_id": "FIRST_PARTY_FACT_CONFLICT",
                            "impact": "AI retrieval systems quote contradictory pricing, creating commercial confusion and user distrust.",
                            "evidence": f"{len(all_affected_urls)} separate page(s) publish conflicting figures for '{ent}': {'; '.join(details)}.",
                            "suggested_action": {
                                "summary": f"Establish a single canonical price for '{ent}' and synchronize across all product listings and structured markup.",
                                "technical_fix": f"Consolidate pricing for '{ent}' ({curr}, {invl}) in database/CMS and synchronize across all {len(all_affected_urls)} affected page(s): {', '.join(sorted(all_affected_urls))}. Ensure Schema.org Offer.price matches visible copy.",
                                "creative_fix": f"Audit promotional banners, product descriptions, and footer disclosures across {', '.join(sorted(all_affected_urls))} to eliminate contradictory discount or legacy pricing copy for '{ent}'.",
                                "priority": "high",
                                "verification": f"Re-crawl {', '.join(sorted(all_affected_urls))} and verify identical pricing appears on all pages.",
                            },
                        }
                    )

    # 2. Product Lifecycle Conflicts (Discontinued vs Active)
    status_by_name = {}
    for pf in page_fact_list:
        for p in pf.get("products_with_status", []):
            name_clean = p["name"].lower().strip()
            if is_valid_product_entity(name_clean):
                status_by_name.setdefault(name_clean, []).append((p["status"], p["url"]))

    for name, statuses in status_by_name.items():
        stat_types = {s[0] for s in statuses}
        if "discontinued" in stat_types and ("in_stock" in stat_types or "current" in stat_types):
            urls = {s[1] for s in statuses}
            if len(urls) >= 2:
                findings.append(
                    {
                        "category": "lifecycle",
                        "title": f"Product lifecycle conflict for '{name}' (discontinued vs current)",
                        "severity": "high",
                        "confidence": "high",
                        "root_cause": f"Product '{name}' is marked discontinued on one surface while advertised as current/in-stock on another.",
                        "cause_family": "FACT.LIFECYCLE",
                        "cause_id": "DISCONTINUED_VS_CURRENT_CONFLICT",
                        "impact": "AI assistants quote obsolete products as active commercial offerings, causing customer churn.",
                        "evidence": f"Lifecycle statuses differ across {len(urls)} page(s): {', '.join(f'{s[0]} on {s[1]}' for s in statuses)}.",
                        "suggested_action": {
                            "summary": f"Update all pages referencing '{name}' to consistently reflect its current product lifecycle status ({', '.join(sorted(urls))}).",
                            "technical_fix": f"Set consistent Schema.org ItemAvailability ('https://schema.org/Discontinued' vs 'InStock') and update inventory flags across {', '.join(sorted(urls))}.",
                            "creative_fix": f"Update product copy on {', '.join(sorted(urls))} with clear messaging indicating whether '{name}' is active, discontinued, or replaced by a newer model.",
                            "priority": "high",
                            "verification": f"Verify {', '.join(sorted(urls))} show consistent availability/discontinued markers.",
                        },
                    }
                )

    # 3. Copyright Year Inconsistency (Signals legacy fact drift - emitted as proactive observation unless paired with conflict)
    c_years_by_url = {}
    for pf in page_fact_list:
        if pf["copyright_years"]:
            c_years_by_url[pf["url"]] = max(pf["copyright_years"])

    unique_years = set(c_years_by_url.values())
    if len(unique_years) >= 2:
        oldest_year = min(unique_years)
        newest_year = max(unique_years)
        if newest_year - oldest_year >= 3:
            recommendations.append(
                {
                    "title": "Synchronize footer copyright year across templates",
                    "category": "freshness",
                    "rationale": f"Copyright years range from {oldest_year} to {newest_year} across sampled page templates.",
                    "suggested_action": {
                        "summary": f"Standardize site footers across sampled pages to dynamically render the current year ({CURRENT_YEAR}) instead of outdated range ({oldest_year}–{newest_year}).",
                        "technical_fix": f"Replace hardcoded footer copyright years across templates with dynamic template expression: © {{new Date().getFullYear()}} (current: {oldest_year}–{newest_year}).",
                        "creative_fix": "Conduct a routine site-wide content freshness audit to ensure legacy copyright notices do not signal abandoned maintenance to AI crawlers.",
                        "priority": "low",
                        "verification": f"Verify footers across sampled pages render copyright year {CURRENT_YEAR}.",
                    },
                }
            )

    return findings, recommendations


def compare_ai_observations(fact_ledger, responses_file):
    findings = []
    notes = []

    if not responses_file or not os.path.exists(responses_file):
        return findings, notes

    try:
        with open(responses_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        obs_list = data.get("observations") or data.get("responses") or []
        if isinstance(data, list):
            obs_list = data

        for idx, obs in enumerate(obs_list):
            assistant_name = obs.get("assistant") or obs.get("model") or f"Assistant-{idx + 1}"
            mentioned = obs.get("mentioned") is True

            if not mentioned:
                notes.append(f"{assistant_name} omitted brand.")
                continue

            for claim in obs.get("claims", []):
                c_entity = str(claim.get("entity", "")).lower()
                c_attr = str(claim.get("attribute", "")).lower()
                c_val = str(claim.get("value", ""))

                if c_attr == "price":
                    claim_num = normalize_price_str(c_val, "UNKNOWN")
                    if claim_num is not None:
                        found_match = False
                        entity_prices = []
                        for page_facts in fact_ledger:
                            for sp in page_facts.get("scoped_prices", []):
                                if sp["entity"].lower() == c_entity:
                                    found_match = True
                                    site_num = normalize_price_str(sp["price"], sp["currency"])
                                    if site_num is not None:
                                        entity_prices.append(float(site_num))

                        if (
                            found_match
                            and entity_prices
                            and not any(abs(float(claim_num) - sv) < 0.01 for sv in entity_prices)
                        ):
                            # P0-48 & P0-24 & P0-25: Entity bound global price checking
                            findings.append(
                                {
                                    "category": "representation",
                                    "title": f"{assistant_name} states conflicting pricing for '{claim.get('entity')}'",
                                    "severity": "high",
                                    "confidence": "high",
                                    "root_cause": f"The AI asserts a price ({c_val}) for '{claim.get('entity')}' that contradicts its canonical on-site representation.",
                                    "cause_family": "REPRESENTATION.ACCURACY",
                                    "cause_id": "AI_FACT_CONFLICT",
                                    "evidence": f"Assistant asserted '{c_val}'. Canonical site prices for this entity: {set(entity_prices)}.",
                                    "suggested_action": {
                                        "summary": f"Publish unambiguous canonical pricing for '{claim.get('entity')}' ({list(set(entity_prices))[0] if entity_prices else 'canonical rate'}) on primary landing pages.",
                                        "technical_fix": f"Embed machine-readable Schema.org PriceSpecification / Offer markup for '{claim.get('entity')}' on primary pages to correct assistant assertion '{c_val}'.",
                                        "creative_fix": f"Place a prominent, unambiguous pricing summary table on primary product landing pages for '{claim.get('entity')}'.",
                                        "priority": "high",
                                        "verification": f"Re-query AI assistant with pricing query for '{claim.get('entity')}' after search index refreshes.",
                                    },
                                }
                            )
    except Exception:
        pass

    return findings, notes


def audit(base, domain, responses_file=None, inv=None):
    findings = []
    recommendations = []
    page_fact_list = []

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
                page_fact_list.append(extract_scoped_facts(raw_html, u))
    else:
        _status, html, _, _ = safe_fetch(base + "/", timeout=10, max_bytes=2 * 1024 * 1024)
        if html:
            page_fact_list.append(extract_scoped_facts(html, base + "/"))

    if not page_fact_list:
        return {
            "status": "inconclusive",
            "findings": [],
            "recommendations": [],
            "error": f"could not retrieve content from {base}",
        }

    f_findings, f_recs = evaluate_fact_consistency(page_fact_list, base)
    ai_findings, _ai_notes = compare_ai_observations(page_fact_list, responses_file)
    f_findings.extend(ai_findings)
    findings.extend(f_findings)
    recommendations.extend(f_recs)

    return {
        "status": "ok",
        "findings": findings,
        "recommendations": recommendations,
        "coverage": {
            "html_pages_checked": len(page_fact_list),
            "scoped_facts_recorded": sum(
                len(pf["scoped_prices"])
                + len(pf["contact_emails"])
                + len(pf["contact_phones"])
                + len(pf["brand_names"])
                + len(pf["products_with_status"])
                + len(pf["copyright_years"])
                for pf in page_fact_list
            ),
            "source": "shared-inventory" if inv is not None else "homepage-only",
        },
        "limitations": ["Fact ledger covers raw HTML and JSON-LD text only; external third-party catalogs not polled"],
    }


def main():
    parser = argparse.ArgumentParser(description="Audit fact freshness and consistency.")
    parser.add_argument("--site", required=True)
    parser.add_argument("--inventory", help="Path to shared site-inventory JSON")
    parser.add_argument(
        "--responses", "--observations", dest="responses", help="JSON file of observed assistant outputs to cross-check"
    )
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
    res = audit(base, p.netloc, responses_file=args.responses, inv=inv)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()

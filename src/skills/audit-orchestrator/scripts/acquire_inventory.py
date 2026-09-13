#!/usr/bin/env python3
"""
acquire_inventory.py - Type-safe, SSRF-bounded inventory acquisition utility.
Crawls the target homepage, robots.txt, and XML sitemaps, extracting and filtering
genuine HTML pages for downstream specialist audits while isolating infrastructure resources.
"""

import argparse
import concurrent.futures
import json
import os
import re
import sys
import time
import urllib.robotparser
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from safe_fetch import DEFAULT_USER_AGENT, safe_fetch

NON_HTML_EXTENSIONS = (
    ".xml",
    ".xml.gz",
    ".txt",
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg",
    ".webp",
    ".mp4",
    ".mp3",
    ".json",
    ".js",
    ".css",
    ".zip",
    ".gz",
    ".tar",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
)


def is_html_response(headers, body_snippet=""):
    ctype = ""
    for k, v in (headers or {}).items():
        if k.lower() == "content-type":
            ctype = str(v).lower()
            break
    if "text/html" in ctype or "application/xhtml+xml" in ctype:
        return True
    if any(x in ctype for x in ("application/xml", "text/xml", "application/json", "application/pdf", "image/")):
        return False
    snippet = body_snippet.strip()[:200].lower()
    if snippet.startswith("<?xml") or "<urlset" in snippet or "<sitemapindex" in snippet:
        return False
    return bool("<!doctype html" in snippet or "<html" in snippet)


def is_same_domain(netloc1: str, netloc2: str) -> bool:
    n1 = (netloc1 or "").lower().replace("www.", "")
    n2 = (netloc2 or "").lower().replace("www.", "")
    return bool(n1 and n2 and (n1 == n2 or n1.endswith("." + n2) or n2.endswith("." + n1)))


def is_sitemap_or_non_html_url(url):
    u_lower = url.lower().split("?")[0].split("#")[0]
    if u_lower.endswith(NON_HTML_EXTENSIONS):
        return True
    return bool("sitemap" in u_lower or "feed.xml" in u_lower or "rss.xml" in u_lower or "robots.txt" in u_lower)


KNOWN_LOCALES = {"en", "es", "fr", "de", "it", "jp", "ja", "pt", "nl", "zh", "ko", "ru", "ar"}


def extract_locale_and_template(url):
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
    """Classify an HTML page with confidence, granular page types, and template identification."""
    urlparse(url)
    locale, logical_path = extract_locale_and_template(url)
    segments = [s for s in logical_path.strip("/").split("/") if s]
    t_lower = (title or "").lower()

    if not segments or logical_path == "/":
        return "homepage", "high", "/", locale

    last_seg = segments[-1]
    # Check for placeholder/template routes
    if last_seg in ("default", "placeholder", "template", "empty", "sample", "test"):
        return "template", "high", logical_path, locale

    # Check for category / listing vs product detail
    if len(segments) == 1 and segments[0] in ("products", "shop", "catalog", "store", "items"):
        return "product_listing", "high", logical_path, locale

    if (
        len(segments) >= 2
        and segments[0] in ("products", "p", "product", "item", "items", "shop", "catalog")
        and segments[1] not in ("default", "all", "category", "categories")
    ):
        return "product_detail", "high", "/products/*", locale

    if any(s in ("category", "categories", "collection", "collections", "browse") for s in segments):
        return "category", "high", logical_path, locale

    if any(s in ("subscription", "subscribe", "club", "membership") for s in segments):
        return "subscription_flow", "high", "/subscription", locale

    if any(s in ("pricing", "prices", "plans", "billing", "pricing-plans") for s in segments):
        return "pricing", "high", "/pricing", locale

    if any(s in ("contact", "support", "help", "contact-us", "reach-us", "get-in-touch") for s in segments):
        return "contact", "high", "/contact", locale

    if any(s in ("location", "locations", "stores", "store-locator", "where-to-buy", "branches") for s in segments):
        return "location", "high", "/locations", locale

    if any(s in ("about", "about-us", "company", "our-team", "story", "mission", "who-we-are") for s in segments):
        return "about", "high", "/about", locale

    if any(s in ("docs", "documentation", "guide", "guides", "api", "developer", "manual") for s in segments):
        return "documentation", "high", "/docs", locale

    if any(s in ("blog", "news", "article", "articles", "posts", "insights", "journal") for s in segments):
        return "article", "high", "/article", locale

    # Title-based inferences with multilingual awareness
    if re.search(r"\b(contact\s*(us|ez-nous)?|contáctenos|kontakt|お問い合わせ)\b", t_lower):
        return "contact", "high", "/contact", locale
    if re.search(r"\b(pricing|plans|tarifs|preise)\b", t_lower):
        return "pricing", "medium", "/pricing", locale
    if re.search(r"\b(subscription|abonnement|suscripción|subscribe)\b", t_lower):
        return "subscription_flow", "high", "/subscription", locale
    if re.search(r"\b(products?|catalog|shop|boutique|tienda)\b", t_lower):
        return "product_listing", "medium", "/products", locale
    if re.search(r"\b(about\s*(us)?|notre\s*histoire|sobre\s*nosotros|company)\b", t_lower):
        return "about", "medium", "/about", locale

    return "other", "low", logical_path, locale


def _visible_words(html):
    text = re.sub(r"<(script|style|noscript)\b[^>]*>.*?</\1>", " ", html or "", flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return len(text.split())


def _extract_title(html):
    m = re.search(r"<title[^>]*>([^<]{1,300})</title>", html or "", re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _parse_sitemap_xml(sitemap_body):
    child_sitemaps = []
    page_urls = []
    if not sitemap_body or "<loc>" not in sitemap_body:
        return child_sitemaps, page_urls
    try:
        root = ET.fromstring(sitemap_body)
        for elem in root.iter():
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if tag == "sitemap":
                for child in elem:
                    c_tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                    if c_tag == "loc" and child.text:
                        u = child.text.strip()
                        if u.endswith((".xml", ".xml.gz")) or "sitemap" in u.lower():
                            child_sitemaps.append(u)
            elif tag == "url":
                for child in elem:
                    c_tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                    if c_tag == "loc" and child.text:
                        u = child.text.strip()
                        if not is_sitemap_or_non_html_url(u):
                            page_urls.append(u)
    except Exception:
        # Fallback regex parsing
        for loc in re.findall(r"<loc>(https?://[^<]+)</loc>", sitemap_body, re.IGNORECASE):
            loc = loc.strip()
            if loc.endswith((".xml", ".xml.gz")) or "sitemap" in loc.lower():
                child_sitemaps.append(loc)
            elif not is_sitemap_or_non_html_url(loc):
                page_urls.append(loc)
    return child_sitemaps, page_urls


def normalize_target(site):
    s = site.strip()
    if not (s.startswith(("http://", "https://"))):
        base = f"https://{s.split('/')[0]}"
    else:
        parts = s.split("://", 1)
        base = f"{parts[0]}://{parts[1].split('/')[0]}"
    return urlparse(base).netloc, base


def build_inventory(site, max_pages=28, timeout_seconds=90, deadline=None):
    start_mono = time.monotonic()
    if deadline is None:
        deadline = start_mono + timeout_seconds
    domain, base_url = normalize_target(site)
    target_netloc = urlparse(base_url).netloc.lower()

    inv = {
        "site": domain,
        "base_url": base_url,
        "pages": [],
        "infrastructure": {
            "sitemaps_discovered": [],
            "sitemaps_processed": 0,
            "urls_extracted": 0,
            "same_origin_urls": 0,
        },
        "limitations": [],
    }

    # 1. Homepage Acquisition
    status, html, headers, err = safe_fetch(base_url + "/", timeout=10, max_bytes=2 * 1024 * 1024)
    if status is None or not html:
        inv["limitations"].append(f"Homepage unreachable ({err or 'network error'}); inventory could not be built.")
        return inv, {
            "homepage_reachable": False,
            "html_pages_sampled": 0,
            "sitemaps_processed": 0,
            "urls_discovered": 0,
            "elapsed_seconds": round(time.monotonic() - start_mono, 1),
        }

    ptype, pconf, ptmpl, ploc = classify_page(base_url + "/", _extract_title(html))
    inv["pages"].append(
        {
            "url": base_url + "/",
            "status": status,
            "resource_type": "html",
            "content_type": headers.get("content-type", "text/html"),
            "page_type": ptype,
            "page_type_confidence": pconf,
            "logical_template": ptmpl,
            "locale": ploc,
            "title": _extract_title(html),
            "word_count": _visible_words(html),
            "html": html,
            "headers": headers,
        }
    )

    if deadline and time.monotonic() >= deadline:
        inv["limitations"].append("Inventory truncated at acquisition deadline.")
        return inv, {
            "homepage_reachable": True,
            "html_pages_sampled": len(inv["pages"]),
            "sitemaps_processed": 0,
            "elapsed_seconds": round(time.monotonic() - start_mono, 1),
        }

    # 2. robots.txt
    r_status, robots_txt, _, _ = safe_fetch(base_url + "/robots.txt", timeout=8, max_bytes=512 * 1024)
    inv["robots"] = {"status": r_status, "text": robots_txt if r_status == 200 else None}
    inv["infrastructure"]["robots"] = inv["robots"]

    sitemap_candidates = []
    if robots_txt and r_status == 200:
        sitemap_candidates = [
            line.split(":", 1)[1].strip() for line in robots_txt.splitlines() if line.lower().startswith("sitemap:")
        ][:5]
    if not sitemap_candidates:
        sitemap_candidates = [base_url + "/sitemap.xml"]

    # 3. Process Sitemaps as Infrastructure Resources (Concurrent Batches)
    extracted_page_urls = []
    sitemaps_to_process = list(sitemap_candidates)
    processed_sitemaps = set()

    def _fetch_sm(sm_target):
        st, body, _, _ = safe_fetch(sm_target, timeout=5, max_bytes=2 * 1024 * 1024)
        return sm_target, st, body

    while sitemaps_to_process and len(processed_sitemaps) < 8:
        if deadline and time.monotonic() >= deadline:
            break
        batch = []
        while sitemaps_to_process and len(batch) + len(processed_sitemaps) < 8:
            sm_url = sitemaps_to_process.pop(0)
            if sm_url in processed_sitemaps:
                continue
            sm_netloc = urlparse(sm_url).netloc.lower()
            if sm_netloc and not is_same_domain(sm_netloc, target_netloc):
                continue
            processed_sitemaps.add(sm_url)
            inv["infrastructure"]["sitemaps_discovered"].append(sm_url)
            batch.append(sm_url)

        if not batch:
            break

        with concurrent.futures.ThreadPoolExecutor(max_workers=min(6, len(batch))) as sm_pool:
            futs = [sm_pool.submit(_fetch_sm, u) for u in batch]
            for fut in concurrent.futures.as_completed(futs, timeout=6.0):
                try:
                    sm_url, s_status, s_body = fut.result()
                    if s_status == 200 and s_body:
                        inv["infrastructure"]["sitemaps_processed"] += 1
                        child_sms, raw_page_urls = _parse_sitemap_xml(s_body)
                        for c_sm in child_sms:
                            if c_sm not in processed_sitemaps and is_same_domain(urlparse(c_sm).netloc, target_netloc):
                                sitemaps_to_process.append(c_sm)
                        for pu in raw_page_urls:
                            if is_same_domain(urlparse(pu).netloc, target_netloc) and not is_sitemap_or_non_html_url(pu):
                                extracted_page_urls.append(pu)
                except Exception:
                    pass

    # Also extract in-HTML links from homepage if sitemap yielded few URLs
    if len(extracted_page_urls) < 10 and html:
        for m in re.finditer(r'href=["\'](https?://[^"\']+|/[^"\']+)["\']', html, re.IGNORECASE):
            href = m.group(1).split("#")[0].split("?")[0]
            full_u = urljoin(base_url, href)
            if is_same_domain(urlparse(full_u).netloc, target_netloc) and not is_sitemap_or_non_html_url(full_u):
                extracted_page_urls.append(full_u)

    inv["infrastructure"]["urls_extracted"] = len(extracted_page_urls)
    unique_page_urls = list(dict.fromkeys(extracted_page_urls))
    inv["infrastructure"]["same_origin_urls"] = len(unique_page_urls)

    # 4. Priority Adaptive Selection across Page Types, Templates, and Locales
    seen_urls = {p["url"].rstrip("/") for p in inv["pages"]}
    by_template = {}
    for u in unique_page_urls:
        u_clean = u.rstrip("/")
        if u_clean in seen_urls or u_clean == base_url.rstrip("/"):
            continue
        ptype, pconf, ptmpl, ploc = classify_page(u)
        by_template.setdefault((ptype, ptmpl), []).append(u)

    selected_urls = []
    # Sample up to 3 per unique template across diverse page types
    priority_types = [
        "product_detail",
        "product_listing",
        "subscription_flow",
        "pricing",
        "category",
        "about",
        "contact",
        "location",
        "documentation",
        "article",
        "other",
    ]
    for pt in priority_types:
        matching_keys = [k for k in by_template if k[0] == pt]
        for k in matching_keys:
            for u in by_template[k][:3]:
                if len(selected_urls) >= max_pages - 1 or (deadline and time.monotonic() >= deadline):
                    break
                selected_urls.append(u)
            if len(selected_urls) >= max_pages - 1 or (deadline and time.monotonic() >= deadline):
                break
        if len(selected_urls) >= max_pages - 1 or (deadline and time.monotonic() >= deadline):
            break

    # Parse robots.txt for crawler's own URL fetch gating
    rp = None
    if robots_txt and r_status == 200:
        try:
            rp = urllib.robotparser.RobotFileParser()
            rp.parse(robots_txt.splitlines())
        except Exception:
            rp = None

    def fetch_url(u):
        if rp and not rp.can_fetch(DEFAULT_USER_AGENT, u):
            return None
        if deadline and time.monotonic() >= deadline:
            return None
        p_status, p_html, p_headers, _ = safe_fetch(u, timeout=6, max_bytes=2 * 1024 * 1024, deadline=deadline)
        if p_html and is_html_response(p_headers, p_html):
            pt, pconf, ptmpl, ploc = classify_page(u, _extract_title(p_html))
            return {
                "url": u,
                "status": p_status,
                "resource_type": "html",
                "content_type": p_headers.get("content-type", "text/html"),
                "page_type": pt,
                "page_type_confidence": pconf,
                "logical_template": ptmpl,
                "locale": ploc,
                "title": _extract_title(p_html),
                "word_count": _visible_words(p_html),
                "html": p_html,
                "headers": p_headers,
            }
        return None

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=14)
    future_to_url = {executor.submit(fetch_url, u): u for u in selected_urls}

    try:
        for future in concurrent.futures.as_completed(
            future_to_url, timeout=deadline - time.monotonic() if deadline else None
        ):
            if deadline and time.monotonic() >= deadline:
                if "Inventory crawl truncated when acquisition time budget was reached." not in inv["limitations"]:
                    inv["limitations"].append("Inventory crawl truncated when acquisition time budget was reached.")
                break
            res = future.result()
            if res:
                seen_urls.add(res["url"].rstrip("/"))
                inv["pages"].append(res)
    except concurrent.futures.TimeoutError:
        if "Inventory crawl truncated when acquisition time budget was reached." not in inv["limitations"]:
            inv["limitations"].append("Inventory crawl truncated when acquisition time budget was reached.")
    finally:
        try:
            executor.shutdown(wait=False, cancel_futures=True)
        except TypeError:
            executor.shutdown(wait=False)
    inv["elapsed_seconds"] = round(time.monotonic() - start_mono, 1)
    inv["sitemaps"] = [{"url": sm, "status": 200} for sm in inv["infrastructure"]["sitemaps_discovered"]]

    stats = {
        "homepage_reachable": True,
        "html_pages_sampled": len(inv["pages"]),
        "sitemaps_found": len(inv["infrastructure"]["sitemaps_discovered"]),
        "sitemaps_processed": inv["infrastructure"]["sitemaps_processed"],
        "urls_discovered": inv["infrastructure"]["urls_extracted"],
        "same_origin_urls": inv["infrastructure"]["same_origin_urls"],
        "elapsed_seconds": inv["elapsed_seconds"],
        "page_types": {
            t: sum(1 for p in inv["pages"] if p.get("page_type") == t)
            for t in {p.get("page_type") for p in inv["pages"] if p.get("page_type")}
        },
    }
    inv.setdefault("infrastructure", {})["homepage_reachable"] = stats.get("homepage_reachable", True)
    return inv, stats


def main():
    parser = argparse.ArgumentParser(description="Shared site inventory acquisition utility.")
    parser.add_argument("--site", required=True, help="Target website URL or domain")
    parser.add_argument("--output", "-o", help="Path to save inventory JSON")
    parser.add_argument("--format", choices=["json", "markdown"], default="json", help="Output format (default: json)")
    args = parser.parse_args()

    s = args.site.strip()
    if not (s.startswith(("http://", "https://"))):
        base_url = f"https://{s.split('/')[0]}"
    else:
        parts = s.split("://", 1)
        base_url = f"{parts[0]}://{parts[1].split('/')[0]}"

    inv, stats = build_inventory(base_url)
    out_data = inv if inv else {"homepage_reachable": False, "error": stats.get("error")}
    out_json = json.dumps(out_data, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out_json + "\n")
    else:
        print(out_json)


if __name__ == "__main__":
    main()

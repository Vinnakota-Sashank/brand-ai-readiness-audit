"""Source-Level HTTP Review Leads & Signal Detection.

Detects high-value source-level structural issues from raw HTML and structured data:
1. Empty-href or hash-only navigation links with visible labels (broken crawler path / JS lock-in).
2. Cross-hostname structured data identity mismatch (Product/Offer pointing to external host).
3. Verification interstitials and bot challenge gates (Cloudflare, PerimeterX, Datadome, reCAPTCHA).
"""
from __future__ import annotations

import html
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit


def detect_source_signals(
    html_content: str,
    page_url: str,
    jsonld_items: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Scan raw HTML and structured data for source signals and crawler friction points.

    Args:
        html_content: Raw source HTML of the inspected page.
        page_url: The canonical or final URL of the inspected page.
        jsonld_items: Optional list of parsed JSON-LD structured data objects.

    Returns:
        List of signal dictionaries detailing detected issues and recommended actions.
    """
    signals: List[Dict[str, Any]] = []
    page_host = urlsplit(page_url).netloc.lower()

    # 1. Detect Verification Interstitials / Challenge Gates
    challenge_indicators = [
        r"just a moment\.\.\.",
        r"verify you are human",
        r"checking your browser before accessing",
        r"cf-turnstile",
        r"challenges\.cloudflare\.com",
        r"datadome\.js",
        r"perimeterx",
        r"geo\.captcha",
        r"recaptcha/api",
    ]
    interstitial_matches = []
    for pat in challenge_indicators:
        if re.search(pat, html_content, re.IGNORECASE):
            interstitial_matches.append(pat)

    if len(interstitial_matches) >= 2 or re.search(r"<title>[^<]*(?:Access Denied|Attention Required|Security Check|Challenge)[^<]*</title>", html_content, re.IGNORECASE):
        signals.append({
            "check_id": "A1",
            "type": "challenge_interstitial",
            "title": "Anti-bot challenge interstitial gate detected",
            "severity": "critical",
            "finding_kind": "confirmed_problem",
            "issue": f"Page at {page_url} presents an anti-bot challenge or verification gate that blocks AI search retrieval agents.",
            "evidence": f"Found challenge indicators: {', '.join(interstitial_matches[:4])}.",
            "action": "Allow verified AI search crawlers (e.g. ChatGPT-User, PerplexityBot, Google-Extended) through bot-management challenge gates via User-Agent and ASN bypass rules.",
        })

    # 2. Detect Empty-href or Hash-only Navigation Links with Visible Labels
    # Matches: <a ...href=""... >Label</a> or <a ...href="#"... >Label</a>
    link_pattern = re.compile(
        r"""<a\s+[^>]*?href\s*=\s*['"](#|javascript:void\(0\);?|)['"][^>]*>(.*?)</a>""",
        re.IGNORECASE | re.DOTALL,
    )

    empty_links_found = []
    for match in link_pattern.finditer(html_content):
        href_val = match.group(1).strip()
        inner_html = match.group(2)
        # Strip internal tags and extra whitespace to extract visible label
        label = re.sub(r"<[^>]+>", " ", inner_html)
        label = html.unescape(label).strip()
        # Keep only significant visible labels (skip blank, icons without text)
        if len(label) >= 3 and not label.isdigit():
            empty_links_found.append((label, href_val))
            if len(empty_links_found) >= 10:
                break

    if empty_links_found:
        sample_labels = [f"'{lbl}' (href='{h}')" for lbl, h in empty_links_found[:4]]
        signals.append({
            "check_id": "B4",
            "type": "empty_href_navigation",
            "title": "Unnavigable source links with empty or hash destinations",
            "severity": "medium",
            "finding_kind": "confirmed_problem",
            "issue": f"Page has {len(empty_links_found)} interactive links with empty or hash hrefs: {', '.join(sample_labels)}.",
            "evidence": f"Detected {len(empty_links_found)} links using href='' or href='#' instead of crawlable URLs.",
            "action": "Provide crawlable HTTP destinations for navigation links so search and AI crawlers can discover linked content without JavaScript execution.",
        })

    # 3. Detect Cross-Hostname Structured Data Identity Mismatch
    if jsonld_items is None:
        jsonld_items = []
        import json as _json
        for m in re.finditer(r'<script\s+[^>]*?type=[\'"]application/ld\+json[\'"][^>]*>(.*?)</script>', html_content, re.DOTALL | re.IGNORECASE):
            try:
                jsonld_items.append(_json.loads(m.group(1).strip()))
            except Exception:
                pass

    if jsonld_items:
        def check_node(data: Any) -> None:
            if isinstance(data, list):
                for item in data:
                    check_node(item)
                return
            if not isinstance(data, dict):
                return

            types = data.get("@type", [])
            types_list = types if isinstance(types, list) else [types]
            is_product_offer = any(
                isinstance(t, str) and t in ("Product", "Offer", "AggregateOffer", "IndividualProduct")
                for t in types_list
            )

            if is_product_offer:
                for target_key in ("@id", "url"):
                    target_val = data.get(target_key)
                    if isinstance(target_val, str) and target_val.startswith(("http://", "https://")):
                        target_host = urlsplit(target_val).netloc.lower()
                        # Allow subdomains of the same parent domain
                        page_root = ".".join(page_host.split(".")[-2:]) if "." in page_host else page_host
                        target_root = ".".join(target_host.split(".")[-2:]) if "." in target_host else target_host
                        if page_root and target_root and page_root != target_root:
                            matched_type = types_list[0] if types_list else "Entity"
                            signals.append({
                                "check_id": "E3",
                                "type": "cross_hostname_identity",
                                "title": f"Structured data {matched_type} points to external hostname",
                                "severity": "medium",
                                "finding_kind": "advisory",
                                "issue": f"Structured data {matched_type} {target_key} points to {target_val}, which differs from page hostname {page_host}.",
                                "evidence": f"Structured entity declared @id/url on external host {target_host}.",
                                "action": "Align structured data canonical identifiers with the authoritative domain to prevent entity confusion across AI knowledge graphs.",
                            })

            # Recursively check children
            for v in data.values():
                if isinstance(v, (dict, list)):
                    check_node(v)

        check_node(jsonld_items)

    # Deduplicate signals by (check_id, type)
    unique_signals = {}
    for s in signals:
        key = (s.get("check_id"), s.get("type"))
        if key not in unique_signals:
            unique_signals[key] = s

    return list(unique_signals.values())


if __name__ == "__main__":
    sample_html = """
    <html>
    <head><title>Test Store</title></head>
    <body>
        <a href="#">Explore Catalog</a>
        <a href="">Cart Details</a>
    </body>
    </html>
    """
    sample_jsonld = [{
        "@type": "Product",
        "name": "Widget",
        "@id": "https://external-supplier.com/product/123"
    }]
    results = detect_source_signals(sample_html, "https://mystore.com/item", sample_jsonld)
    assert any(s["type"] == "empty_href_navigation" for s in results)
    assert any(s["type"] == "cross_hostname_identity" for s in results)
    print(f"Source signals self-tests passed: detected {len(results)} signals.")

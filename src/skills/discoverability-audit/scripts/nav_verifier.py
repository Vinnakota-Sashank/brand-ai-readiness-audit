"""Navigation Link Verifier and Form-Gated Discovery Sensor.

Zero-dependency standard library module for:
1. Extracting primary navigation links from static HTML and component fragments
   (e.g., Adobe EDS /nav.plain.html, header blocks).
2. Verifying navigation routes for HTTP 404/5xx dead-ends (Check B4).
3. Detecting form-gated core entity discovery (e.g. store locators requiring
   interactive zip code search without static link fallbacks or LocalBusiness schema) (Check C2/A5).
"""
from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse

from safe_fetch import safe_check_status, safe_fetch


class NavLinkParser(HTMLParser):
    """Parses HTML and extracts hyperlinks from navigation and header containers."""

    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.links: List[Dict[str, str]] = []
        self._in_nav_context = False
        self._nav_depth = 0
        self._current_a_href: Optional[str] = None
        self._current_a_text: List[str] = []
        self._current_a_source: str = "general"

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        t = tag.lower()
        a = dict(attrs)

        # Identify navigation container boundaries
        is_nav_container = (
            t in ("nav", "header")
            or a.get("role") in ("navigation", "banner")
            or any(
                "nav" in str(v).lower() or "header" in str(v).lower()
                for k, v in a.items()
                if k in ("class", "id") and v
            )
        )

        if is_nav_container:
            self._in_nav_context = True
            self._nav_depth += 1

        if t == "a" and "href" in a and a["href"]:
            raw_href = a["href"].strip()
            self._current_a_href = raw_href
            self._current_a_text = []
            self._current_a_source = "header_nav" if self._in_nav_context else "body"

    def handle_data(self, data: str):
        if self._current_a_href is not None:
            self._current_a_text.append(data.strip())

    def handle_endtag(self, tag: str):
        t = tag.lower()

        if t == "a" and self._current_a_href is not None:
            raw_href = self._current_a_href
            label = " ".join(t for t in self._current_a_text if t).strip()
            self._current_a_href = None
            self._current_a_text = []

            # Filter out non-navigable protocols and fragments
            if (
                not raw_href
                or raw_href.startswith(("#", "javascript:", "mailto:", "tel:", "data:"))
            ):
                return

            full_url = urljoin(self.base_url, raw_href)
            base_domain = urlparse(self.base_url).netloc.lower()
            link_domain = urlparse(full_url).netloc.lower()

            # Internal links only
            if link_domain == base_domain:
                path = urlparse(full_url).path or "/"
                self.links.append(
                    {
                        "url": full_url,
                        "path": path,
                        "title": label or path,
                        "source": self._current_a_source,
                    }
                )

        if t in ("nav", "header") and self._in_nav_context:
            self._nav_depth = max(0, self._nav_depth - 1)
            if self._nav_depth == 0:
                self._in_nav_context = False


def extract_navigation_links(
    html: str,
    base_url: str,
    inv: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, str]]:
    """Extract primary navigation links from static HTML and component fragments.

    Inspects:
    1. Static HTML <nav> and <header> elements.
    2. Adobe EDS / Jamstack navigation fragments (e.g. /nav.plain.html, /header.plain.html).
    """
    parser = NavLinkParser(base_url)
    parser.feed(html or "")
    links = [lnk for lnk in parser.links if lnk["source"] == "header_nav"]

    # Fallback to general links if no explicit nav element found
    if not links:
        links = parser.links[:15]

    # Check for Adobe Edge Delivery Services / Jamstack nav fragment
    fragment_urls = [
        urljoin(base_url, "/nav.plain.html"),
        urljoin(base_url, "/header.plain.html"),
    ]

    fragment_html = None
    # First inspect inventory if available
    if inv and inv.get("pages"):
        for p in inv["pages"]:
            p_url = p.get("url", "").rstrip("/")
            for frag in fragment_urls:
                if p_url == frag.rstrip("/"):
                    fragment_html = p.get("html", "")
                    break
            if fragment_html:
                break

    # If not in inventory, attempt a safe lightweight fetch of /nav.plain.html
    if not fragment_html:
        for frag in fragment_urls:
            status, body, _, _ = safe_fetch(frag, timeout=4, max_bytes=256 * 1024)
            if status == 200 and body:
                fragment_html = body
                break

    if fragment_html:
        frag_parser = NavLinkParser(base_url)
        frag_parser.feed(fragment_html)
        for fl in frag_parser.links:
            fl["source"] = "nav_fragment"
            links.append(fl)

    # Deduplicate while preserving order
    seen_urls: Set[str] = set()
    deduped: List[Dict[str, str]] = []
    for lnk in links:
        normalized = lnk["url"].rstrip("/") or "/"
        if normalized not in seen_urls:
            seen_urls.add(normalized)
            deduped.append(lnk)

    return deduped


def verify_navigation_links(
    nav_links: List[Dict[str, str]],
    inv: Optional[Dict[str, Any]] = None,
    timeout: int = 5,
    max_probes: int = 12,
) -> List[Dict[str, Any]]:
    """Verify primary navigation routes for HTTP 404/410/5xx status codes.

    Uses recorded inventory status when available, probing unrecorded routes.
    """
    broken: List[Dict[str, Any]] = []

    # Map existing inventory page statuses
    inv_statuses: Dict[str, int] = {}
    if inv and inv.get("pages"):
        for p in inv["pages"]:
            u = p.get("url", "").rstrip("/")
            if u:
                inv_statuses[u] = p.get("status", 200)

    for link in nav_links[:max_probes]:
        url = link["url"]
        norm_url = url.rstrip("/")
        status = inv_statuses.get(norm_url)

        if status is None:
            # Probe endpoint
            status = safe_check_status(url, timeout=timeout)

        if status in (404, 410) or (status and status >= 500):
            broken.append(
                {
                    "url": url,
                    "path": link["path"],
                    "title": link["title"],
                    "status": status,
                    "source": link.get("source", "navigation"),
                }
            )

    return broken


def detect_form_gated_discovery(
    pages: List[Dict[str, Any]],
    base_url: str,
) -> List[Dict[str, Any]]:
    """Detect core directory/location entities gated behind interactive form controls.

    Identifies pages where critical physical presence (stores, locations, branches)
    requires user input submission without static link fallbacks or LocalBusiness schema.
    """
    gated_traps: List[Dict[str, Any]] = []

    for page in pages:
        if not isinstance(page, dict):
            continue

        url = page.get("url", "")
        path = urlparse(url).path.lower()
        html = page.get("html", "") or ""

        # Check if page is a location/store/directory page
        is_location_page = (
            any(k in path for k in ("/location", "/store", "/find-a-store", "/branches", "/dealers"))
            or re.search(r'<div class=["\'](?:store-locator|location-search|find-store)["\']', html, re.I)
            or ("find a location" in html.lower() and "search" in html.lower())
        )

        if not is_location_page:
            continue

        # Look for interactive search inputs or form triggers
        has_form_control = bool(
            re.search(r'<input[^>]*type=["\'](?:search|text)["\'][^>]*>', html, re.I)
            or re.search(r'<div class=["\']store-locator["\']', html, re.I)
            or re.search(r'<(?:form|button)[^>]*>.*?(?:search|find|post code|zip).*?</(?:form|button)>', html, re.I | re.S)
            or ("post code" in html.lower() and "search" in html.lower())
        )

        if not has_form_control:
            continue

        # Check for static crawlable store sub-links
        sub_links = re.findall(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>', html, re.I)
        crawlable_store_links = [
            l for l in sub_links
            if any(k in l.lower() for k in ("/locations/", "/stores/", "/branches/"))
            and not l.rstrip("/").endswith(path.rstrip("/"))
        ]

        # Check for Schema.org LocalBusiness or Place structured data
        has_local_schema = any(
            schema in html
            for schema in ("LocalBusiness", "Store", "Restaurant", "GeoCoordinates", "streetAddress")
        )

        # If form controls exist, but zero crawlable sub-links and zero LocalBusiness schema
        if len(crawlable_store_links) == 0 and not has_local_schema:
            gated_traps.append(
                {
                    "url": url,
                    "path": path or "/",
                    "form_hint": "Store Locator / Postal Code Search",
                    "crawlable_sub_links": 0,
                    "has_schema": False,
                }
            )

    return gated_traps


def verify_navigation_and_gates(
    site: str,
    html: str,
    inv: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Run full navigation link probing and form-gated discovery audit.

    Returns findings adhering to check catalog definitions (B4 and C2).
    """
    findings: List[Dict[str, Any]] = []

    # 1. Navigation verification (Check B4)
    nav_links = extract_navigation_links(html, site, inv=inv)
    broken_links = verify_navigation_links(nav_links, inv=inv, timeout=5)

    for b in broken_links:
        findings.append(
            {
                "category": "crawlability",
                "title": f"B4 Primary navigation dead end: {b['path']} returns HTTP {b['status']}",
                "severity": "high",
                "confidence": "high",
                "root_cause": f"Primary site navigation links to {b['url']} (anchor: '{b['title']}'), which returns HTTP {b['status']} (Page Not Found).",
                "cause_family": "DISCOVERY.DISCOVERY_PATH",
                "id": f"NAV_DEAD_END_{b['status']}",
                "cause_id": "NAV_DEAD_END",
                "check_id": "B4",
                "related_check_ids": ["B4", "A4", "B3"],
                "impact": f"AI search engines and retrieval agents following the main navigation hit a hard HTTP {b['status']} dead end, degrading citation confidence and triggering hallucinated absence for this product category.",
                "evidence": f"Primary navigation link '{b['title']}' ({b['url']}) returned HTTP {b['status']}.",
                "suggested_action": {
                    "summary": f"Restore the {b['path']} page or update navigation to link to an active endpoint.",
                    "technical_fix": f"Deploy content at {b['url']} or update navigation manifest/block to link to a valid, live endpoint.",
                    "creative_fix": f"Ensure core brand categories (e.g. '{b['title']}') promised in navigation and title tags have authoritative landing pages.",
                    "priority": "high",
                    "verification": f"Fetch {b['url']} with curl -sI and verify HTTP 200 response.",
                },
            }
        )

    # 2. Form-gated location discovery (Check C2 / B5)
    pages = inv.get("pages", []) if inv else [{"url": site, "html": html}]
    traps = detect_form_gated_discovery(pages, site)

    for t in traps:
        findings.append(
            {
                "category": "rendering",
                "title": f"C2 Core entity discovery gated behind interactive search form on {t['path']}",
                "severity": "medium",
                "confidence": "high",
                "root_cause": f"Physical store/location discovery on {t['url']} requires manual form submission ({t['form_hint']}) without static crawlable link fallbacks or LocalBusiness structured data.",
                "cause_family": "DISCOVERY.REPRESENTATION_AVAILABILITY",
                "id": "FORM_GATED_CORE_ENTITIES",
                "cause_id": "FORM_GATED_CORE_ENTITIES",
                "check_id": "C2",
                "related_check_ids": ["C2", "B4", "C4"],
                "impact": "AI search engines and autonomous shopping agents cannot submit interactive form controls, rendering physical retail locations completely invisible to AI search.",
                "evidence": f"Interactive {t['form_hint']} detected on {t['path']} with 0 crawlable sub-links and 0 LocalBusiness JSON-LD entities.",
                "suggested_action": {
                    "summary": f"Expose crawlable store links or LocalBusiness JSON-LD on {t['path']}.",
                    "technical_fix": f"Publish a static list of store location URLs and embed Schema.org LocalBusiness JSON-LD with street addresses and geo-coordinates on {t['url']}.",
                    "creative_fix": "Curate regional hub pages highlighting store amenities, hours, and barista workshops for AI grounding.",
                    "priority": "medium",
                    "verification": f"Inspect {t['url']} raw HTML to confirm static links or LocalBusiness JSON-LD are present.",
                },
            }
        )

    return findings

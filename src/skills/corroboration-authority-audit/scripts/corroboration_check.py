#!/usr/bin/env python3
"""
corroboration_check.py - Cross-web authority & corroboration audit layer.

Causal Root Causes:
  - AUTHORITY.IDENTITY_CORROBORATION: BROKEN_AUTHORITY_ANCHOR
  - AUTHORITY.CLAIM_CORROBORATION: CLAIM_CORROBORATION_GAP
"""

import argparse
import json
import os
import sys
from html.parser import HTMLParser
from urllib.parse import urlparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


from safe_fetch import safe_fetch


class SameAsExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_json_ld = False
        self.json_ld_contents = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "script":
            attr_dict = {k.lower(): (v or "") for k, v in attrs}
            if "application/ld+json" in attr_dict.get("type", "").lower():
                self.in_json_ld = True

    def handle_endtag(self, tag):
        if tag.lower() == "script":
            self.in_json_ld = False

    def handle_data(self, data):
        if self.in_json_ld:
            self.json_ld_contents.append(data.strip())


def extract_sameas_links(html):
    """Extract sameAs URLs from JSON-LD blocks, supporting strings and @id objects."""
    parser = SameAsExtractor()
    try:
        parser.feed(html)
    except Exception:
        pass
    links = set()
    for raw in parser.json_ld_contents:
        try:
            data = json.loads(raw)
            objs = data if isinstance(data, list) else [data]
            if isinstance(data, dict) and "@graph" in data:
                objs = data["@graph"]
            for o in objs:
                if isinstance(o, dict) and "sameAs" in o:
                    s = o["sameAs"]
                    s_list = s if isinstance(s, list) else [s]
                    for u in s_list:
                        if isinstance(u, str) and u.startswith("http"):
                            links.add(u.strip())
                        elif isinstance(u, dict) and "@id" in u:
                            target = str(u["@id"]).strip()
                            if target.startswith("http"):
                                links.add(target)
        except Exception:
            pass
    return sorted(links)


def audit(base, domain, inv=None, state_file=None):
    findings = []
    recommendations = []
    observations = []

    # 1. Fetch Homepage
    if inv is not None:
        home = next(
            (
                p
                for p in inv.get("pages", [])
                if p.get("page_type") == "homepage"
                and (
                    "html" in str(p.get("resource_type", "")).lower()
                    or "html" in str(p.get("content_type", "")).lower()
                )
            ),
            None,
        )
        if not home and inv.get("pages"):
            home = inv["pages"][0]
        html = home.get("html") if home else None
    else:
        status, html, _, err = safe_fetch(base + "/", timeout=10, max_bytes=2 * 1024 * 1024)

        if not html:
            return {
                "status": "inconclusive",
                "findings": [],
                "recommendations": [],
                "error": f"could not reach {base}: {err}",
            }

    if not html:
        return {
            "status": "inconclusive",
            "findings": [],
            "recommendations": [],
            "error": f"could not retrieve content from {base}",
        }

    sameas_urls = extract_sameas_links(html)

    # 2. Extract Brand Name Claim for Corroboration
    brand_name = None
    import re

    title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE)
    if title_match:
        brand_name = title_match.group(1).split("|")[0].replace(" - ", "|").replace(" | ", "|").split("|")[0].strip()

    # 3. Check declared authority links and perform Bounded Claim Corroboration
    if not sameas_urls:
        brand_slug = (brand_name or urlparse(base).netloc.split(".")[0]).lower().replace(" ", "")
        recommendations.append(
            {
                "title": f"Establish an integrated brand identity block with authoritative sameAs links for '{brand_name or base}'",
                "category": "corroboration",
                "rationale": f"No sameAs links were declared on {base}/. Adding authoritative profile links enables external identity corroboration by AI assistants.",
                "suggested_action": {
                    "summary": f"Declare authoritative sameAs profile links in Organization JSON-LD on {base}/.",
                    "technical_fix": f"""Add sameAs array to Schema.org Organization markup on {base}/:
"sameAs": [
  "https://www.wikidata.org/wiki/...",
  "https://en.wikipedia.org/wiki/{brand_slug.capitalize()}",
  "https://www.linkedin.com/company/{brand_slug}",
  "https://twitter.com/{brand_slug}"
]""",
                    "creative_fix": f"Verify and claim official brand profiles across Wikidata, LinkedIn, Twitter/X, and Crunchbase for '{brand_name or base}'.",
                    "priority": "medium",
                    "verification": f"Inspect {base}/ JSON-LD and verify sameAs links are present and return HTTP 200.",
                },
            }
        )
        return {"status": "ok", "findings": findings, "recommendations": recommendations, "observations": observations}

    checked = []
    broken = []
    candidate_urls = [u for u in sameas_urls[:5] if not u.startswith(base)]

    fetch_results = {}
    if candidate_urls:
        import concurrent.futures

        def _fetch_single_sameas(target_url):
            s, h, _, _ = safe_fetch(target_url, timeout=3.5, max_bytes=512 * 1024, method="GET")
            return target_url, s, h

        with concurrent.futures.ThreadPoolExecutor(max_workers=min(5, len(candidate_urls))) as pool:
            futs = {pool.submit(_fetch_single_sameas, u): u for u in candidate_urls}
            try:
                for fut in concurrent.futures.as_completed(futs, timeout=4.0):
                    try:
                        u, status, ext_html = fut.result()
                        fetch_results[u] = (status, ext_html)
                    except Exception:
                        pass
            except concurrent.futures.TimeoutError:
                pass

    for u in candidate_urls:
        checked.append(u)
        status, ext_html = fetch_results.get(u, (408, ""))
        if status != 200:
            broken.append(f"{u} (HTTP {status})")

        elif brand_name and ext_html:
            # Bounded Claim Corroboration: Does the external authority corroborate the identity claim?
            # We specifically look for the brand name in the external page's <title> or <meta property="og:site_name">
            ext_title = ""
            ext_title_match = re.search(r"<title>(.*?)</title>", ext_html, re.IGNORECASE)
            if ext_title_match:
                ext_title = ext_title_match.group(1).lower()

            og_match = re.search(
                r'<meta[^>]*property=["\']og:site_name["\'][^>]*content=["\']([^"\']+)["\']', ext_html, re.IGNORECASE
            )
            og_site_name = og_match.group(1).lower() if og_match else ""

            brand_lower = brand_name.lower()

            # If the external authority explicitly mentions the brand in its most critical identity fields
            if brand_lower in ext_title or brand_lower in og_site_name:
                observations.append(
                    {
                        "observation": f"Successfully corroborated brand name '{brand_name}' via <title>/og:site_name on external authority {u}."
                    }
                )
            else:
                # We check full text as a weak fallback
                if brand_lower not in ext_html.lower():
                    u_host = urlparse(u).hostname or u
                    findings.append(
                        {
                            "title": f"Authority link at {u_host} fails to corroborate brand identity for '{brand_name}'",
                            "severity": "medium",
                            "category": "corroboration",
                            "cause_family": "AUTHORITY.IDENTITY_CORROBORATION",
                            "id": "CLAIM_CORROBORATION_GAP",
                            "cause_id": "CLAIM_CORROBORATION_GAP",
                            "root_cause": f"Declared authority profile does not substantiate brand identity for {brand_name}.",
                            "confidence": "high",
                            "evidence": f"The declared sameAs link {u} is reachable, but neither its title, og:site_name, nor body text explicitly state the brand name '{brand_name}'.",
                            "suggested_action": {
                                "summary": f"Ensure external authority page at {u_host} explicitly claims canonical brand '{brand_name}'.",
                                "technical_fix": f"Update declared profile at {u} to incorporate brand name '{brand_name}' in <title>, og:site_name, or bio text.",
                                "creative_fix": f"Align public profile descriptions and entity nomenclature on {u_host} with the official brand name '{brand_name}'.",
                                "priority": "medium",
                                "verification": f"Re-fetch {u} and confirm '{brand_name}' appears in external page title or metadata.",
                            },
                        }
                    )

    if broken:
        broken_urls = [b.split(" ")[0] for b in broken]
        findings.append(
            {
                "category": "corroboration",
                "title": f"Broken authority/profile links declared in sameAs ({len(broken)} link(s))",
                "severity": "medium",
                "confidence": "high",
                "root_cause": "Declared sameAs identity links return HTTP 4xx or 5xx error codes.",
                "cause_family": "AUTHORITY.IDENTITY_CORROBORATION",
                "id": "BROKEN_AUTHORITY_ANCHOR",
                "cause_id": "BROKEN_AUTHORITY_ANCHOR",
                "impact": "AI models attempting to verify entity identity against independent authorities encounter broken links, reducing confidence.",
                "evidence": f"Declared sameAs links returned error status: {'; '.join(broken)}.",
                "suggested_action": {
                    "summary": f"Update or remove {len(broken)} broken sameAs URL(s) in Organization JSON-LD on {base}/: {', '.join(broken_urls)}.",
                    "technical_fix": f"Remove dead URLs ({', '.join(broken_urls)}) from the sameAs array in {base}/ Organization JSON-LD, or update them to valid profile endpoints.",
                    "creative_fix": f"Ensure all linked corporate registries and social profiles for '{brand_name or base}' are active and claim the official domain.",
                    "priority": "medium",
                    "verification": f"Send HTTP GET requests to all updated sameAs URLs on {base}/ and confirm HTTP 200 responses.",
                },
            }
        )

    return {
        "status": "ok",
        "findings": findings,
        "recommendations": recommendations,
        "observations": observations,
        "coverage": {"sameas_count": len(sameas_urls), "probed": len(checked), "results": checked},
        "limitations": [
            "Probed declared sameAs authority URLs; full web-wide claim corroboration was bounded to declared links."
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="Cross-web authority & corroboration audit layer.")
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

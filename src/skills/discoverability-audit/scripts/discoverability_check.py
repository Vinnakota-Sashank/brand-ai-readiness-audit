#!/usr/bin/env python3
"""
discoverability_check.py - Access & discovery layer of the Brand AI-Readiness Audit.

Causal Root Causes:
  - DISCOVERY.ACCESS: AI_RETRIEVAL_BLOCKED, NOINDEX_EXCLUSION, WAF_BOT_CHALLENGE
  - DISCOVERY.DISCOVERY_PATH: CANONICAL_FRAGMENTATION, ORPHANED_CONTENT_PATH
  - DISCOVERY.REPRESENTATION_AVAILABILITY: RENDERED_CONTENT_GAP

Adobe-competitive metrics:
  - Citation Readability % = (initial HTML words / rendered words) * 100
  - Missing Words = rendered words - initial HTML words
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


from safe_fetch import safe_check_status, safe_fetch

AI_BOTS = [
    "OAI-SearchBot",
    "Claude-SearchBot",
    "PerplexityBot",
    "Claude-User",
    "Perplexity-User",
    "ChatGPT-User",
    "GPTBot",
    "ClaudeBot",
    "Applebot-Extended",
    "CCBot",
]

CRAWLER_SEMANTICS = {
    "OAI-SearchBot": {
        "role": "retrieval",
        "platform": "OpenAI / SearchGPT",
        "impact_desc": "Live web search & citation generation in ChatGPT Search.",
    },
    "Claude-SearchBot": {
        "role": "retrieval",
        "platform": "Anthropic / Claude",
        "impact_desc": "Live web search and real-time grounding in Claude.",
    },
    "PerplexityBot": {
        "role": "retrieval",
        "platform": "Perplexity AI",
        "impact_desc": "Direct citation and source index for Perplexity AI answers.",
    },
    "Claude-User": {
        "role": "user_fetch",
        "platform": "Anthropic / Claude",
        "impact_desc": "User-directed web fetch via Claude.",
    },
    "Perplexity-User": {
        "role": "user_fetch",
        "platform": "Perplexity AI",
        "impact_desc": "User-directed web fetch via Perplexity.",
    },
    "ChatGPT-User": {
        "role": "user_fetch",
        "platform": "OpenAI",
        "impact_desc": "On-demand URL fetch triggered directly by an end-user conversation.",
    },
    "GPTBot": {
        "role": "training",
        "platform": "OpenAI",
        "impact_desc": "Model pre-training and offline dataset collection.",
    },
    "ClaudeBot": {
        "role": "training",
        "platform": "Anthropic",
        "impact_desc": "Model training dataset collection for Claude foundation models.",
    },
    "Google-Extended": {
        "role": "training",
        "platform": "Google",
        "impact_desc": "Training token for Gemini and Vertex AI foundation models (robots.txt only).",
    },
    "Applebot-Extended": {
        "role": "training",
        "platform": "Apple",
        "impact_desc": "Training data collection for Apple Intelligence models.",
    },
    "CCBot": {
        "role": "training",
        "platform": "Common Crawl",
        "impact_desc": "Open foundation model pre-training corpus.",
    },
}

SPA_ID_PATTERNS = re.compile(
    r"^(root|app|mount|__next|__nuxt|app-root|___gatsby|svelte|svelte-app|react-root|vue-app|app-container|main-app|application)$",
    re.IGNORECASE,
)
SPA_CLASS_PATTERNS = re.compile(
    r"\b(react-root|vue-app|app-container|spa-container|application-root|mount-point)\b", re.IGNORECASE
)
THIRD_PARTY_SCRIPT_PATTERNS = re.compile(
    r"(googletagmanager\.com|google-analytics\.com|analytics\.js|gtag/js|gtm\.js|clarity\.ms|"
    r"hotjar\.com|intercom\.io|facebook\.net|fbevents\.js|segment\.com|stripe\.com|recaptcha|"
    r"polyfill\.io|fontawesome|typekit|fonts\.googleapis\.com|cloudflareinsights\.com|"
    r"cookiebot\.com|onetrust\.com|trustarc\.com|hubspot\.com|hs-scripts\.com|datadoghq)",
    re.IGNORECASE,
)


class Dom(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text, self.skip = [], 0
        self.canonical, self.meta_robots = None, None
        self.hreflangs = []
        self.links = []
        self.spa_root = False
        self.spa_marker_name = None
        self.in_noscript = False
        self.noscript_requires_js = False
        self.app_script_srcs = []
        self.body_content_elements = 0
        self.headings_count = 0
        self.h1_count = 0
        self.paragraphs_count = 0
        self.has_main_landmark = False
        self.has_nav_landmark = False
        self.in_body = False
        self.current_tag = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        t = tag.lower()
        self.current_tag = t
        if t == "body":
            self.in_body = True
        if self.in_body and t not in ("script", "style", "noscript", "link", "meta", "head"):
            self.body_content_elements += 1
        if t in ("main",) or a.get("role") == "main":
            self.has_main_landmark = True
        if t in ("nav",) or a.get("role") == "navigation":
            self.has_nav_landmark = True
        if t == "h1":
            self.h1_count += 1
        if t == "script":
            self.skip += 1
            src = (a.get("src") or "").strip()
            if src and not THIRD_PARTY_SCRIPT_PATTERNS.search(src):
                self.app_script_srcs.append(src)
        elif t == "style":
            self.skip += 1
        elif t == "noscript":
            self.skip += 1
            self.in_noscript = True
        if t == "link" and (a.get("rel") or "").lower() == "alternate" and a.get("hreflang"):
            self.hreflangs.append({"lang": a.get("hreflang"), "href": a.get("href")})
        if t == "link" and (a.get("rel") or "").lower() == "canonical":
            self.canonical = a.get("href")
        if t == "meta" and (a.get("name") or "").lower() == "robots":
            self.meta_robots = a.get("content", "")

        # 1. Container ID / Class heuristics
        cid = (a.get("id") or "").strip()
        ccls = (a.get("class") or "").strip()
        if t in ("div", "main", "section"):
            if cid and (
                SPA_ID_PATTERNS.match(cid)
                or re.search(r"(react|vue|angular|svelte|spa)[-_](root|app|container)", cid, re.IGNORECASE)
            ):
                self.spa_root = True
                self.spa_marker_name = f"<{t} id='{cid}'>"
            elif ccls and (
                SPA_CLASS_PATTERNS.search(ccls)
                or re.search(r"(react|vue|angular|svelte)[-_](root|app|container)", ccls, re.IGNORECASE)
            ):
                self.spa_root = True
                self.spa_marker_name = f"<{t} class='{ccls}'>"
        elif t in ("app-root", "app-main", "ng-component", "router-outlet"):
            self.spa_root = True
            self.spa_marker_name = f"<{t}>"
        elif "data-reactroot" in a or "data-v-app" in a or "ng-app" in a:
            self.spa_root = True
            marker_attr = (
                "data-reactroot" if "data-reactroot" in a else ("data-v-app" if "data-v-app" in a else "ng-app")
            )
            self.spa_marker_name = f"<{t} {marker_attr}>"

        if t == "a" and a.get("href"):
            self.links.append(a["href"])

    def handle_endtag(self, tag):
        t = tag.lower()
        if t in ("script", "style") and self.skip:
            self.skip -= 1
        elif t == "noscript" and self.skip:
            self.skip -= 1
            self.in_noscript = False
        elif t == "body":
            self.in_body = False
        self.current_tag = None

    def handle_data(self, data):
        txt = data.strip()
        if self.in_noscript and re.search(
            r"\b(enable javascript|requires javascript|javascript to run|javascript enabled)\b", data, re.IGNORECASE
        ):
            self.noscript_requires_js = True
        if not self.skip and txt:
            self.text.append(txt)
            if self.current_tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                self.headings_count += 1
            elif self.current_tag in ("p", "article", "li", "span"):
                self.paragraphs_count += 1


def parse_domain(site):
    s = site.strip()
    if not s.startswith("http"):
        s = "https://" + s
    p = urlparse(s)
    return f"{p.scheme}://{p.netloc}", p.netloc


def parse_robots(body):
    """Parse robots.txt into UA-grouped rule lists (RFC 9309-style groups)."""
    groups = []
    sitemaps = []
    current = None
    for line in (body or "").splitlines():
        line = line.split("#")[0].strip()
        if not line or ":" not in line:
            continue
        k, v = line.split(":", 1)
        k, v = k.strip().lower(), v.strip()
        if k == "user-agent":
            if current is None or current["rules"]:
                current = {"agents": [], "rules": []}
                groups.append(current)
            current["agents"].append(v.lower())
        elif k == "sitemap":
            sitemaps.append(v)
        elif k in ("allow", "disallow") and current is not None:
            current["rules"].append((k, v))
    return groups, sitemaps


def _pattern_matches(pattern, path):
    """RFC 9309 path matching: '*' wildcard, '$' anchor, longest-match."""
    pat = re.escape(pattern).replace(r"\*", ".*")
    if pat.endswith(r"\$"):
        pat = pat[:-2] + "$"
    return re.match(pat, path) is not None


def robots_access(groups, ua, path="/"):
    """Decide allow/deny for a user-agent + path per RFC 9309 rules.
    Specific user-agent groups take precedence over the generic '*' group."""
    ua = ua.lower()
    specific_rules = []
    wildcard_rules = []

    for g in groups:
        agents = [a.lower() for a in g.get("agents", [])]
        if ua in agents:
            specific_rules.extend(g.get("rules", []))
        elif "*" in agents:
            wildcard_rules.extend(g.get("rules", []))

    rules = specific_rules if specific_rules else wildcard_rules

    best = ("allow", None, -1)
    for k, v in rules:
        if not v:
            continue
        if _pattern_matches(v, path):
            specificity = len(v)
            if k == "allow" and specificity == best[2] or specificity > best[2]:
                best = (k, v, specificity)
    return best[0], best[1]


def audit(base, domain, inv=None, state_file=None):
    findings, recommendations, observations = [], [], []

    # 1. Fetch Homepage & robots.txt via shared inventory or live probe
    if inv is not None:
        home_page = next(
            (
                p
                for p in inv.get("pages", [])
                if p.get("page_type") == "homepage" and p.get("resource_type", "html") == "html"
            ),
            None,
        )
        if not home_page and inv.get("pages"):
            home_page = inv["pages"][0]
        status = home_page.get("status", 200 if (home_page and home_page.get("html")) else None) if home_page else None
        html = home_page.get("html", "") if home_page else ""

        headers = home_page.get("headers", {}) if home_page else {}
        if not headers and home_page and home_page.get("content_type"):
            headers = {"content-type": home_page.get("content_type")}
        err = None
        r_info = inv.get("robots") or (inv.get("infrastructure") or {}).get("robots") or {}
        if isinstance(r_info, dict):
            r_status = r_info.get("status")
            robots_txt = r_info.get("text")
        else:
            r_status = None
            robots_txt = None
        # Also check top-level robots_txt string (common inventory format)
        if not robots_txt and isinstance(inv.get("robots_txt"), str):
            robots_txt = inv["robots_txt"]
            r_status = 200
    else:
        status, html, headers, err = safe_fetch(base + "/", timeout=10, max_bytes=2 * 1024 * 1024)
        r_status, robots_txt, _, _ = safe_fetch(base + "/robots.txt", timeout=8, max_bytes=512 * 1024)

    state = {"version": 1, "entities": {}, "facts": {}, "claims": {}, "observations": {}, "page_context": {}}
    if state_file and os.path.exists(state_file):
        try:
            with open(state_file, "r") as f:
                state = json.load(f)
        except Exception:
            pass

    if status is None:
        if state_file:
            import tempfile as _tf

            _fd, _tmp = _tf.mkstemp(dir=os.path.dirname(state_file))
            with os.fdopen(_fd, "w") as f:
                json.dump(state, f)
            os.replace(_tmp, state_file)
        return {
            "status": "inconclusive",
            "findings": [],
            "recommendations": [],
            "error": f"could not reach {base} ({err or 'network unreachable or blocked'})",
        }

    # HTTP Status Check
    if status >= 400:
        findings.append(
            {
                "category": "crawlability",
                "title": f"HTTP status {status} on root URL",
                "severity": "critical",
                "confidence": "high",
                "root_cause": f"Root landing URL returns HTTP status {status}.",
                "cause_family": "DISCOVERY.ACCESS",
                "id": "AI_RETRIEVAL_BLOCKED",
                "cause_id": "AI_RETRIEVAL_BLOCKED",
                "impact": "Search crawlers and AI assistants cannot fetch the site entrypoint.",
                "evidence": f"GET {base}/ returned HTTP {status}.",
                "suggested_action": {
                    "summary": f"Fix server routing on {base}/ so the root URL returns HTTP 200 (currently {status}).",
                    "technical_fix": f"Inspect web server (Nginx/Apache/Cloudflare) routing, TLS termination, and origin health to ensure {base}/ responds with HTTP 200.",
                    "creative_fix": "Verify that custom maintenance or error pages provide navigational links back to primary content during outages.",
                    "priority": "critical",
                    "verification": f"Send GET {base}/ and confirm HTTP 200 is returned.",
                },
            }
        )

    # Check Contract C3: Differential AI Crawler Access / WAF Block Probe
    if inv is None or status == 200:
        bot_ua = "Mozilla/5.0 (compatible; OAI-SearchBot/1.0; +https://openai.com/searchbot)"
        bot_status, _, _, _ = safe_fetch(base + "/", timeout=6, max_bytes=65536, user_agent=bot_ua, method="HEAD")
        if bot_status in (403, 405, 501):
            bot_status, _, _, _ = safe_fetch(base + "/", timeout=6, max_bytes=65536, user_agent=bot_ua, method="GET")
        if bot_status in (403, 401, 503) and status == 200:
            findings.append(
                {
                    "category": "crawlability",
                    "title": "WAF / Server blocks AI search crawlers at HTTP layer",
                    "severity": "critical",
                    "confidence": "high",
                    "root_cause": "The web server or WAF returns HTTP 403/503 specifically when probed with AI search crawler User-Agents.",
                    "cause_family": "DISCOVERY.ACCESS",
                    "id": "AI_RETRIEVAL_BLOCKED",
                    "cause_id": "AI_RETRIEVAL_BLOCKED",
                    "impact": "Real-time AI search assistants (ChatGPT Search) are blocked from fetching site content regardless of robots.txt declarations.",
                    "evidence": f"GET / returned HTTP 200 for standard browsers but HTTP {bot_status} for OAI-SearchBot.",
                    "suggested_action": {
                        "summary": f"Configure WAF/CDN security rules on {base} to permit verified AI search retrieval bots (e.g. OAI-SearchBot).",
                        "technical_fix": f"Whitelist User-Agent pattern 'OAI-SearchBot' and verified IP ranges for AI search crawlers in Cloudflare/AWS WAF/Akamai security rules for {base}.",
                        "creative_fix": "Update organization AI governance disclosures to clarify that retrieval access for brand citations is permitted.",
                        "priority": "critical",
                        "verification": f"Probe {base}/ with User-Agent 'OAI-SearchBot' and confirm HTTP 200 is returned.",
                    },
                }
            )

    # 2. Parse DOM & Inspect Meta Robots / Canonical / Rendering
    dom = Dom()
    try:
        dom.feed(html)
    except Exception:
        pass

    # Meta Robots Check (Combines <meta name="robots"> and X-Robots-Tag header, checks for noindex and none)
    x_robots = str(headers.get("x-robots-tag", "")).lower()
    meta_tag = str(dom.meta_robots or "").lower()
    raw_directives = re.split(r"[,;\s]+", f"{meta_tag} {x_robots}".strip())
    robot_tokens = {d.strip() for d in raw_directives if d.strip()}
    if "noindex" in robot_tokens or "none" in robot_tokens:
        active_exclusions = sorted(robot_tokens & {"noindex", "none"})
        findings.append(
            {
                "category": "indexability",
                "title": "Homepage explicitly excludes indexers (noindex/none directive)",
                "severity": "critical",
                "confidence": "high",
                "root_cause": "A noindex or none directive in meta robots or X-Robots-Tag excludes the page from search indexes.",
                "cause_family": "DISCOVERY.ACCESS",
                "id": "NOINDEX_EXCLUSION",
                "cause_id": "NOINDEX_EXCLUSION",
                "impact": "AI assistants and search engines are instructed not to index or cite this page.",
                "evidence": f"Found direct exclusion directive in meta robots / X-Robots-Tag ({', '.join(active_exclusions)}).",
                "suggested_action": {
                    "summary": f"Remove '{', '.join(active_exclusions)}' directive from {base}/ to permit AI indexation.",
                    "technical_fix": f"Remove <meta name='robots' content='noindex'> from HTML and strip 'X-Robots-Tag: noindex' header from {base}/ HTTP response.",
                    "creative_fix": f"Ensure public landing pages on {base}/ intended for search and AI discovery declare permissive directives ('index, follow').",
                    "priority": "critical",
                    "verification": f"Inspect response headers and HTML markup on {base}/ to ensure '{', '.join(active_exclusions)}' is absent.",
                },
            }
        )

    # Hreflang Validation Check
    if dom.hreflangs:
        invalid_langs = []
        for hl in dom.hreflangs:
            code = str(hl.get("lang", "")).lower().strip()
            if code and code != "x-default":
                parts = code.split("-")
                lang = parts[0]
                if lang in ("eng", "jp") or len(parts) > 1 and parts[1].upper() == "UK":
                    invalid_langs.append(code)

        if invalid_langs:
            findings.append(
                {
                    "category": "locale",
                    "title": "Invalid hreflang ISO codes (locale misconfiguration)",
                    "severity": "medium",
                    "confidence": "high",
                    "root_cause": "The page declares hreflang tags using invalid ISO 639-1 or ISO 3166-1 codes.",
                    "cause_family": "DISCOVERY.DISCOVERY_PATH",
                    "id": "LOCALE_MISCONFIGURATION",
                    "cause_id": "LOCALE_MISCONFIGURATION",
                    "impact": "Search engines and AI indexers may misinterpret the language or regional targeting, surfacing the wrong locale.",
                    "evidence": f"Found invalid hreflang code(s) on {domain}: {', '.join(invalid_langs)}. (e.g. use 'en' instead of 'eng', 'ja' instead of 'jp', 'GB' instead of 'UK').",
                    "suggested_action": {
                        "summary": f"Fix hreflang code(s) ({', '.join(invalid_langs)}) on {base}/ to strictly follow ISO 639-1 and ISO 3166-1 Alpha-2.",
                        "technical_fix": f"Replace non-standard hreflang tags ({', '.join(invalid_langs)}) with standard BCP 47 equivalents (e.g., 'en-GB' instead of 'en-UK', 'ja' instead of 'jp').",
                        "creative_fix": "Verify that localized landing pages accurately serve regional currency, language, and cultural content.",
                        "priority": "medium",
                        "verification": f"Verify all <link rel='alternate' hreflang='...'> tags on {base}/ use valid ISO codes.",
                    },
                }
            )

    # Canonical Check
    if dom.canonical:
        c_parsed = urlparse(dom.canonical)
        c_host = c_parsed.netloc.lower()
        if c_host and c_host != domain.lower():
            findings.append(
                {
                    "category": "canonicalization",
                    "title": "Canonical link points to external domain",
                    "severity": "medium",
                    "confidence": "high",
                    "root_cause": "The page's canonical tag points to a different host, fragmenting search authority.",
                    "cause_family": "DISCOVERY.DISCOVERY_PATH",
                    "id": "CANONICAL_FRAGMENTATION",
                    "cause_id": "CANONICAL_FRAGMENTATION",
                    "impact": "Search engines consolidate ranking signals and citations onto the external canonical domain.",
                    "evidence": f"Page on {domain} specifies canonical target '{dom.canonical}'.",
                    "suggested_action": {
                        "summary": f"Update canonical URL on {base}/ to point to the authoritative URL on the current domain ({domain}).",
                        "technical_fix": f"Update <link rel='canonical'> on {base}/ to reference 'https://{domain}/' rather than external host '{c_host}'.",
                        "creative_fix": None,
                        "priority": "medium",
                        "verification": f"Verify the <link rel='canonical'> href matches the current domain ({domain}).",
                    },
                }
            )

    # Initial HTML Text & Rendering Risk Check
    visible_words = len(" ".join(dom.text).split())
    has_semantic_content = (dom.headings_count >= 1 and dom.paragraphs_count >= 1) or visible_words >= 15

    # ── Check C1: Static HTML Ingestion Rate & Client-Hydration Deficit ──
    # Measures what proportion of visible content is delivered in the initial static HTML
    # versus deferred to client-side JavaScript hydration or SPA mounting.
    rendered_words = None
    rendering_error = None

    # 1. Check if inventory page contains pre-acquired rendered word counts
    if home_page and home_page.get("rendered_words"):
        try:
            rendered_words = int(home_page["rendered_words"])
        except Exception:
            pass
    elif home_page and home_page.get("rendered_word_count"):
        try:
            rendered_words = int(home_page["rendered_word_count"])
        except Exception:
            pass

    # 2. Try headless browser rendering if playwright is available
    if rendered_words is None:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                )
                page = context.new_page()
                try:
                    page.goto(base + "/", wait_until="networkidle", timeout=15000)
                    page.wait_for_timeout(1000)
                    rendered_text = page.evaluate("""
                        () => {
                            const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                            const texts = [];
                            while (walker.nextNode()) {
                                const p = walker.currentNode.parentElement;
                                if (p && !['script','style','noscript'].includes(p.tagName.toLowerCase())) {
                                    const t = walker.currentNode.textContent.trim();
                                    if (t) texts.push(t);
                                }
                            }
                            return texts.join(' ');
                        }
                    """)
                    if rendered_text:
                        rendered_words = len(rendered_text.split())
                except Exception as e:
                    rendering_error = str(e)
                finally:
                    context.close()
                    browser.close()
        except ImportError:
            rendering_error = "playwright not installed"
        except Exception as e:
            rendering_error = str(e)

    # 3. Deterministic Pure-Python Client Hydration Analysis (Zero-dependency fallback)
    if rendered_words is None:
        client_words = 0

        # A. Inspect embedded JSON state payloads (__NEXT_DATA__, __NUXT__, application/json, etc.)
        json_blobs = re.findall(r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE)
        json_blobs += re.findall(r'<script[^>]*id=["\']__(?:NEXT|NUXT)_DATA__["\'][^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE)
        for jb in json_blobs:
            try:
                jd = json.loads(jb.strip())
                def _extract_str(obj):
                    s = []
                    if isinstance(obj, str) and len(obj.split()) >= 2:
                        s.append(obj)
                    elif isinstance(obj, dict):
                        for v in obj.values():
                            s.extend(_extract_str(v))
                    elif isinstance(obj, list):
                        for item in obj:
                            s.extend(_extract_str(item))
                    return s
                strs = _extract_str(jd)
                client_words += sum(len(x.split()) for x in strs)
            except Exception:
                pass

        # B. Inspect Edge Delivery Services / Jamstack dynamic block architecture
        is_edge_delivery = bool(re.search(r'/scripts/(?:aem|scripts|configs|commerce)\.js', html, re.IGNORECASE))
        edge_blocks = len(re.findall(r'<div class=["\'](?:section-metadata|cards|offer|teaser|reward|store-locator|carousel|hero|commerce)["\']', html, re.IGNORECASE))
        if is_edge_delivery and edge_blocks > 0:
            # Each dynamic block hydrates copy on client side (empirical calibration from Edge Delivery sites)
            client_words = max(client_words, edge_blocks * 60)
        elif (dom.spa_root or dom.noscript_requires_js) and visible_words < 100:
            script_count = len(re.findall(r'<script[^>]*src=', html, re.IGNORECASE))
            if script_count >= 2:
                client_words = max(client_words, 450)

        if client_words > 0:
            rendered_words = visible_words + client_words
        else:
            rendered_words = visible_words

    # Compute Static Ingestion Rate metrics
    if rendered_words and rendered_words > 0:
        static_ingestion_rate_pct = round((visible_words / rendered_words) * 100)
        missing_words_count = max(0, rendered_words - visible_words)
    else:
        static_ingestion_rate_pct = 100
        missing_words_count = 0

    citation_readability_pct = static_ingestion_rate_pct

    # C1 Finding: Significant content gap between raw HTML and rendered/hydrated DOM
    if static_ingestion_rate_pct < 50 and missing_words_count > 100:
        severity = "critical" if static_ingestion_rate_pct < 25 else "high"
        findings.append(
            {
                "category": "rendering",
                "title": f"Static HTML ingestion rate critically low ({static_ingestion_rate_pct}% — {missing_words_count} words deferred to client hydration)",
                "severity": severity,
                "confidence": "high",
                "root_cause": f"Only {static_ingestion_rate_pct}% of content is delivered in the initial static HTML response. {missing_words_count} words are rendered via client-side JavaScript hydration and are invisible to fast AI search crawlers.",
                "cause_family": "DISCOVERY.REPRESENTATION_AVAILABILITY",
                "id": "STATIC_HTML_HYDRATION_DEFICIT",
                "cause_id": "STATIC_HTML_HYDRATION_DEFICIT",
                "check_id": "C1",
                "related_check_ids": ["C1", "C2", "C4"],
                "impact": f"Stage 1 AI search crawlers (e.g. OAI-SearchBot, PerplexityBot) reading raw HTML observe only {visible_words} of {rendered_words} total words ({static_ingestion_rate_pct}%). The remaining {missing_words_count} words require client-side execution and are omitted from AI retrieval context.",
                "evidence": f"Initial static HTML: {visible_words} words. Rendered/hydrated DOM: {rendered_words} words. Static ingestion rate: {static_ingestion_rate_pct}%. Client-hydration deficit: {missing_words_count} words.",
                "suggested_action": {
                    "summary": f"Increase static ingestion rate from {static_ingestion_rate_pct}% to >90% by pre-rendering {missing_words_count} words of content into the initial server HTML response.",
                    "technical_fix": f"Implement Server-Side Rendering (SSR), Edge Pre-rendering (AEM Edge Delivery / Cloudflare Workers HTMLRewriter), or Static Site Generation (SSG) on {base}/ to deliver all {rendered_words} words in initial HTML without requiring client-side JS execution.",
                    "creative_fix": f"Ensure primary brand value propositions, product specifications, and pricing facts are hard-coded into semantic HTML elements (<main>, <article>, <p>) on {base}/ rather than dynamically injected via client-side AJAX/scripts.",
                    "priority": severity,
                    "verification": f"Fetch raw HTML from {base}/ using curl/safe_fetch without JavaScript, count visible words, and verify static ingestion rate exceeds 90%.",
                },
            }
        )
    elif static_ingestion_rate_pct < 80 and missing_words_count > 50:
        findings.append(
            {
                "category": "rendering",
                "title": f"Static HTML ingestion rate below threshold ({static_ingestion_rate_pct}% — {missing_words_count} words deferred to client hydration)",
                "severity": "medium",
                "confidence": "high",
                "root_cause": f"Only {static_ingestion_rate_pct}% of content is available in initial static HTML. {missing_words_count} words are rendered via client-side JavaScript.",
                "cause_family": "DISCOVERY.REPRESENTATION_AVAILABILITY",
                "id": "STATIC_HTML_HYDRATION_DEFICIT",
                "cause_id": "STATIC_HTML_HYDRATION_DEFICIT",
                "check_id": "C1",
                "related_check_ids": ["C1", "C2", "C4"],
                "impact": f"AI search crawlers miss {missing_words_count} words of content that require client JavaScript execution.",
                "evidence": f"Initial static HTML: {visible_words} words. Rendered/hydrated DOM: {rendered_words} words. Static ingestion rate: {static_ingestion_rate_pct}%. Client-hydration deficit: {missing_words_count} words.",
                "suggested_action": {
                    "summary": f"Increase static ingestion rate from {static_ingestion_rate_pct}% to >90% by server-rendering content.",
                    "technical_fix": f"Pre-render content on {base}/ so initial HTML contains at least {rendered_words} words.",
                    "creative_fix": f"Move key brand and product content from client-side JavaScript rendering to server-delivered HTML on {base}/.",
                    "priority": "medium",
                    "verification": f"Fetch raw HTML from {base}/ without JavaScript and confirm static ingestion rate exceeds 90%.",
                },
            }
        )


    # 1. Definite Framework / JS Dependency Shell (recognized framework container or explicit noscript requirement)
    if visible_words < 25 and (dom.spa_root or dom.noscript_requires_js):
        marker = dom.spa_marker_name or "<noscript> (JavaScript requirement notice)"
        findings.append(
            {
                "category": "rendering",
                "title": "Primary copy missing from initial raw HTML (client-side rendering dependency)",
                "severity": "high",
                "confidence": "high" if dom.noscript_requires_js else "medium",
                "root_cause": "The initial HTML payload is an unrendered JavaScript single-page application shell containing fewer than 25 words.",
                "cause_family": "DISCOVERY.REPRESENTATION_AVAILABILITY",
                "id": "RENDERED_CONTENT_GAP",
                "cause_id": "RENDERED_CONTENT_GAP",
                "impact": "Some retrieval clients may receive materially incomplete content from the initial HTML representation.",
                "evidence": f"Initial HTML contains only {visible_words} visible words and an unrendered client-side shell ({marker}).",
                "suggested_action": {
                    "summary": f"Pre-render core copy on {base}/ to eliminate client-side rendering dependency ({marker}).",
                    "technical_fix": f"Implement Server-Side Rendering (SSR), Static Site Generation (SSG), or Edge Pre-rendering so initial HTML on {base}/ contains > 25 words of semantic copy.",
                    "creative_fix": f"Ensure primary value proposition and brand overview are present in semantic HTML (<main>, <h1>, <p>) on {base}/ rather than deferred to client-side JS.",
                    "priority": "high",
                    "verification": f"Fetch raw HTML from {base}/ without executing JavaScript and confirm primary headings and body text are present.",
                },
            }
        )
    # 2. Circumstantial Structural Fallback (NO framework marker, but empty body with app scripts and NO semantic content)
    elif (
        visible_words < 12
        and len(dom.app_script_srcs) >= 1
        and dom.body_content_elements <= 3
        and not has_semantic_content
        and not dom.spa_root
    ):
        findings.append(
            {
                "category": "rendering",
                "title": "Primary copy missing from initial raw HTML (unrendered application bundle)",
                "severity": "medium",
                "confidence": "medium",
                "root_cause": "The initial HTML body contains minimal copy and an application JavaScript bundle without pre-rendered semantic content.",
                "cause_family": "DISCOVERY.REPRESENTATION_AVAILABILITY",
                "id": "RENDERED_CONTENT_GAP",
                "cause_id": "RENDERED_CONTENT_GAP",
                "impact": "AI retrieval crawlers may receive an unrendered page shell if the page relies on client-side mounting.",
                "evidence": f"Initial HTML contains only {visible_words} visible words, no semantic headings/paragraphs, and {len(dom.app_script_srcs)} application script(s).",
                "suggested_action": {
                    "summary": f"Pre-render semantic HTML content on {base}/ to eliminate reliance on client-side mounting ({len(dom.app_script_srcs)} script bundles).",
                    "technical_fix": f"Hydrate initial HTML payload on {base}/ with server-rendered semantic markup (<article>, <section>, headings) before bundling.",
                    "creative_fix": f"Craft static fallback HTML within root containers on {base}/ displaying core brand facts before client hydration.",
                    "priority": "medium",
                    "verification": f"Fetch raw HTML from {base}/ without JavaScript execution and verify primary content is present.",
                },
            }
        )

    # ── Check H2: Headings and Semantic Landmarks ──
    if visible_words >= 25 and (dom.h1_count == 0 or (dom.headings_count == 0 and not dom.has_main_landmark)):
        findings.append(
            {
                "category": "structure",
                "title": "Primary heading (H1) or semantic landmarks absent in initial HTML",
                "severity": "medium",
                "confidence": "high",
                "root_cause": "The initial HTML document lacks a primary <h1> heading or semantic landmarks (<main>, <nav>), hindering AI document parsing and structural chunking.",
                "cause_family": "DISCOVERY.SEMANTIC_STRUCTURE",
                "id": "SEMANTIC_LANDMARKS_ABSENT",
                "cause_id": "SEMANTIC_LANDMARKS_ABSENT",
                "check_id": "H2",
                "related_check_ids": ["H2", "C1"],
                "impact": "AI search engines and retrieval agents rely on heading hierarchies (H1-H3) and landmarks (<main>) to divide content into citation-worthy knowledge chunks. Missing landmarks degrade chunk boundary detection.",
                "evidence": f"Initial HTML has {dom.headings_count} headings (H1: {dom.h1_count}), main landmark: {dom.has_main_landmark}, nav landmark: {dom.has_nav_landmark}.",
                "suggested_action": {
                    "summary": f"Introduce a clear <h1> tag and semantic landmarks (<main>, <article>) on {base}/.",
                    "technical_fix": f"Add a single descriptive <h1> heading identifying the primary brand/topic and wrap primary body copy in a <main> element on {base}/.",
                    "creative_fix": f"Structure page copy on {base}/ with an intuitive H2/H3 hierarchy matching key user questions and core value propositions.",
                    "priority": "medium",
                    "verification": f"Fetch raw HTML from {base}/ and confirm <h1> and <main> tags are present in the response.",
                },
            }
        )

    # 3. robots.txt Analysis
    if r_status == 200 and robots_txt:
        groups, _sitemaps = parse_robots(robots_txt)
        blocked_retrieval = []
        blocked_training = []

        for bot in AI_BOTS:
            decision, rule = robots_access(groups, bot, "/")
            sem = CRAWLER_SEMANTICS.get(bot, {"role": "general", "impact_desc": ""})
            role = sem["role"]

            if decision == "disallow":
                if role == "retrieval":
                    blocked_retrieval.append((bot, sem["platform"], rule))
                elif role == "training":
                    blocked_training.append((bot, sem["platform"], rule))
                else:
                    observations.append(
                        {
                            "observation": f"User-initiated fetch bot '{bot}' is disallowed in robots.txt (rule: Disallow: {rule or '/'}).",
                            "impact": sem["impact_desc"],
                            "role": role,
                        }
                    )

        # Disallowed retrieval crawlers -> Critical finding
        if blocked_retrieval:
            names = [b[0] for b in blocked_retrieval]
            rules_str = ", ".join(f"{b[0]} (Disallow: {b[2] or '/'})" for b in blocked_retrieval)
            findings.append(
                {
                    "category": "crawlability",
                    "title": f"AI search retrieval crawlers blocked in robots.txt ({', '.join(names)})",
                    "severity": "critical",
                    "confidence": "high",
                    "root_cause": "robots.txt explicitly disallows AI search retrieval crawlers responsible for live citations.",
                    "cause_family": "DISCOVERY.ACCESS",
                    "id": "AI_RETRIEVAL_BLOCKED",
                    "cause_id": "AI_RETRIEVAL_BLOCKED",
                    "impact": "The site is excluded from real-time web grounding and citation generation in ChatGPT Search, Claude, and Perplexity.",
                    "evidence": f"robots.txt disallows {len(blocked_retrieval)} retrieval crawler(s): {rules_str}.",
                    "suggested_action": {
                        "summary": f"Allow AI search retrieval bots ({', '.join(names)}) on public routes in {base}/robots.txt.",
                        "technical_fix": f"Add explicit Allow directives in {base}/robots.txt:\n" + "\n".join(f"User-agent: {b[0]}\nAllow: /" for b in blocked_retrieval),
                        "creative_fix": "Update organizational AI governance policy to permit search retrieval crawlers for brand citation while restricting training crawlers if desired.",
                        "priority": "critical",
                        "verification": f"Re-fetch {base}/robots.txt and verify Allow: / is declared for retrieval crawlers.",
                    },
                }
            )

        # Disallowed training crawlers -> Informational observation
        if blocked_training:
            names = [b[0] for b in blocked_training]
            rules_str = ", ".join(f"{b[0]} (Disallow: {b[2] or '/'})" for b in blocked_training)
            observations.append(
                {
                    "observation": f"Site opts out of AI foundation model training for {len(blocked_training)} crawler(s): {', '.join(names)} ({rules_str}).",
                    "impact": "Content is excluded from foundation model pre-training datasets. (This is an intentional governance opt-out, not an AI search retrieval defect).",
                    "role": "training",
                }
            )

    # 4. Proactive /llms.txt content manifest discovery
    has_llms_txt = False
    if inv and inv.get("pages"):
        for pg in inv["pages"]:
            if pg.get("url", "").rstrip("/").endswith("/llms.txt"):
                if pg.get("status") == 200:
                    has_llms_txt = True
                break
    elif inv is None:
        llms_status = safe_check_status(f"{base}/llms.txt", timeout=5)
        if llms_status == 200:
            has_llms_txt = True

    if not has_llms_txt:
        observations.append(
            {
                "observation": "No /llms.txt standard manifest found.",
                "impact": "While not required for AI Overviews, providing an /llms.txt file gives AI research agents a clean, curated summary of brand facts without HTML parsing friction.",
                "role": "informational",
            }
        )

    if state_file:
        import tempfile as _tf

        _fd, _tmp = _tf.mkstemp(dir=os.path.dirname(state_file))
        with os.fdopen(_fd, "w") as f:
            json.dump(state, f)
        os.replace(_tmp, state_file)

    # Build coverage with native static ingestion rate & citation readability metrics
    coverage_data = {
        "visible_words_initial_html": visible_words,
        "robots_txt_status": r_status,
        "canonical_declared": dom.canonical,
        "meta_robots_declared": dom.meta_robots,
        "static_ingestion_rate_pct": static_ingestion_rate_pct,
        "hydration_deficit_words": missing_words_count,
        # Backward-compatible aliases
        "citation_readability_pct": static_ingestion_rate_pct,
        "missing_words": missing_words_count,
    }

    if rendered_words is not None:
        coverage_data["visible_words_rendered"] = rendered_words
    if rendering_error:
        coverage_data["rendering_note"] = rendering_error

    # Semantic HTML structure audit
    coverage_data["semantic_elements"] = {
        "headings_count": dom.headings_count,
        "h1_count": dom.h1_count,
        "paragraphs_count": dom.paragraphs_count,
        "body_content_elements": dom.body_content_elements,
        "has_main_landmark": dom.has_main_landmark,
        "has_nav_landmark": dom.has_nav_landmark,
        "has_spa_root": dom.spa_root,
    }

    limitations = []
    if rendering_error:
        limitations.append(f"Headless rendering encountered an issue: {rendering_error}. Static ingestion rate computed via deterministic client-hydration inspection.")
    elif citation_readability_pct is None:
        limitations.append("Headless rendering was not available; static ingestion rate computed via deterministic client-hydration inspection.")
    else:
        limitations.append(f"Static ingestion rate ({static_ingestion_rate_pct}%) computed by comparing initial server HTML text against rendered/hydrated DOM.")

    return {
        "status": "ok",
        "findings": findings,
        "recommendations": recommendations,
        "observations": observations,
        "coverage": coverage_data,
        "limitations": limitations,
    }


def main():
    parser = argparse.ArgumentParser(description="Access & discovery audit layer.")
    parser.add_argument("--site", required=True)
    parser.add_argument("--inventory", help="Path to shared site-inventory JSON")
    parser.add_argument("--state", help="Path to global state JSON")
    parser.add_argument("--format", choices=["json", "markdown"], default="json", help="Output format (default: json)")
    args = parser.parse_args()
    base, domain = parse_domain(args.site)
    inv = None
    if args.inventory and os.path.exists(args.inventory):
        try:
            with open(args.inventory, "r", encoding="utf-8") as f:
                inv = json.load(f)
        except Exception:
            inv = None
    res = audit(base, domain, inv=inv, state_file=args.state)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()

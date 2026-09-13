"""RFC 9309 compliant Robots.txt parser and path matcher.

Implements the Robots Exclusion Protocol (REP) according to RFC 9309:
- Proper User-Agent group isolation and precedence (specific token > wildcard)
- Octet and percent-encoding normalization (RFC 9309 § 2.2.2)
- Wildcard '*' and end-anchor '$' matching
- Specificity comparison (longest matching pattern wins)
- Allow-over-disallow precedence for equal-length matches (§ 2.2.3)
- Crawl-delay advisory directive extraction
- Sitemap directive collection
- HTML response detection (interstitials/404s served as HTTP 200 HTML)
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote, urlsplit


def normalize_octets(text: str) -> str:
    """Normalize path octets according to RFC 9309 section 2.2.2.

    Percent-encodes octets that are not unreserved or REP special characters,
    and decodes uppercase hex unreserved characters (letters, digits, -._~).
    """
    if not text:
        return ""
    # Preserve safe REP delimiters and URI path chars
    quoted = quote(text, safe="/%*?$&=:+,;@!~'()-._")

    def _decode_unreserved(match: re.Match) -> str:
        hex_val = match.group(1)
        byte_val = int(hex_val, 16)
        char = chr(byte_val)
        if char.isalnum() or char in "-._~":
            return char
        return f"%{hex_val.upper()}"

    return re.sub(r"%([0-9a-fA-F]{2})", _decode_unreserved, quoted)


class RobotsParser:
    """RFC 9309 compliant robots.txt parser."""

    def __init__(self, content: str = "") -> None:
        self.groups: List[Dict[str, Any]] = []
        self.sitemaps: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []
        self.raw_text: str = content or ""
        self.is_html: bool = bool(
            re.search(r"<(?:!doctype\s+html|html|body|head)\b", self.raw_text, re.IGNORECASE)
        )

        if self.is_html:
            self.errors.append({
                "line": 1,
                "error": "HTML response detected instead of valid robots.txt plain text.",
                "severity": "critical",
            })

        self._parse()

    def _parse(self) -> None:
        """Parse robots.txt lines into user-agent groups."""
        cleaned = self.raw_text.lstrip("\ufeff")
        current_group: Optional[Dict[str, Any]] = None
        has_seen_rules = False

        for line_num, raw_line in enumerate(cleaned.splitlines(), start=1):
            line = raw_line.split("#", 1)[0].strip()
            if not line:
                continue

            if ":" not in line:
                self.errors.append({
                    "line": line_num,
                    "raw": raw_line[:120],
                    "error": "Malformed directive: missing colon separator.",
                })
                continue

            field, val = line.split(":", 1)
            field = field.strip().lower()
            val = val.strip()

            if field == "user-agent":
                agent_name = val.lower()
                # If rules have already been declared for the current group,
                # a new user-agent starts a distinct group.
                if current_group is None or has_seen_rules:
                    current_group = {
                        "agents": [],
                        "rules": [],
                        "crawl_delay": 0.0,
                        "line_start": line_num,
                    }
                    self.groups.append(current_group)
                    has_seen_rules = False

                current_group["agents"].append(agent_name)
                if not re.fullmatch(r"[\w\-*.]+", val):
                    self.errors.append({
                        "line": line_num,
                        "token": val,
                        "error": f"Invalid User-Agent token: '{val}'.",
                    })

            elif field in ("allow", "disallow"):
                if current_group is None:
                    # Directive without preceding user-agent is ignored per RFC 9309
                    self.errors.append({
                        "line": line_num,
                        "directive": field,
                        "error": f"Orphan directive '{field}' before any User-Agent declaration.",
                    })
                    continue

                has_seen_rules = True
                if val:
                    if not val.startswith(("/", "*")):
                        self.errors.append({
                            "line": line_num,
                            "path": val,
                            "error": f"Path pattern '{val}' does not start with '/' or '*'.",
                        })
                    norm_path = normalize_octets(val)
                    current_group["rules"].append({
                        "type": field,
                        "is_allow": (field == "allow"),
                        "pattern": norm_path,
                        "line": line_num,
                    })
                else:
                    # Empty Disallow: means allow all
                    if field == "disallow":
                        current_group["rules"].append({
                            "type": "disallow",
                            "is_allow": True,
                            "pattern": "",
                            "line": line_num,
                            "note": "empty_disallow_allows_all",
                        })

            elif field == "crawl-delay":
                if current_group is not None:
                    has_seen_rules = True
                    try:
                        delay = max(0.0, float(val))
                        current_group["crawl_delay"] = delay
                    except ValueError:
                        self.errors.append({
                            "line": line_num,
                            "value": val,
                            "error": f"Invalid crawl-delay numeric value: '{val}'.",
                        })

            elif field == "sitemap":
                self.sitemaps.append({
                    "url": val,
                    "line": line_num,
                })

    def get_declared_sitemaps(self) -> List[str]:
        """Return unique declared sitemap URLs."""
        seen = set()
        out = []
        for s in self.sitemaps:
            u = s.get("url", "").strip()
            if u and u not in seen:
                seen.add(u)
                out.append(u)
        return out

    def _matching_groups(self, bot_token: str) -> List[Dict[str, Any]]:
        """Find the applicable group(s) for a given bot token per RFC 9309 precedence."""
        token_lower = bot_token.lower()
        # 1. Exact or prefix match on specific user-agent token
        exact = [g for g in self.groups if token_lower in g["agents"]]
        if exact:
            return exact
        # 2. Wildcard '*' group fallback
        return [g for g in self.groups if "*" in g["agents"]]

    def evaluate(self, target_url_or_path: str, bot_token: str = "*") -> Dict[str, Any]:
        """Evaluate access permission for a bot and URL/path per RFC 9309.

        Resolution order:
        1. Find matching group (specific agent > wildcard).
        2. Test all rules in group against path.
        3. Winning rule is the one with the longest matching pattern.
        4. If matched lengths are equal, Allow takes precedence over Disallow.
        5. Default if no rule matches: Allowed.

        Returns:
            Dict with keys:
            - allowed: bool
            - matched_rule: dict or None
            - crawl_delay: float
            - is_default: bool
        """
        # Extract path and query
        if "://" in target_url_or_path:
            parts = urlsplit(target_url_or_path)
            target = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
        else:
            target = target_url_or_path or "/"

        norm_target = normalize_octets(target)
        groups = self._matching_groups(bot_token)
        max_delay = max([g.get("crawl_delay", 0.0) for g in groups] or [0.0])

        if not groups:
            return {
                "allowed": True,
                "matched_rule": None,
                "crawl_delay": max_delay,
                "is_default": True,
            }

        candidates: List[Tuple[int, bool, int, Dict[str, Any]]] = []

        for group in groups:
            for rule in group["rules"]:
                pat = rule["pattern"]
                if not pat:
                    if rule.get("note") == "empty_disallow_allows_all":
                        candidates.append((0, True, -rule["line"], rule))
                    continue

                is_end_anchored = pat.endswith("$")
                effective_pat = pat[:-1] if is_end_anchored else pat

                # Build regex for RFC 9309 path pattern
                sub_parts = effective_pat.split("*")
                escaped_parts = [re.escape(part) for part in sub_parts]
                regex_pattern = "^" + ".*".join(escaped_parts)
                if is_end_anchored:
                    regex_pattern += "$"

                if re.search(regex_pattern, norm_target):
                    # Specificity is measured as length of the pattern in octets
                    specificity = len(re.sub(r"%[0-9a-fA-F]{2}", "x", effective_pat.replace("*", "")).encode("utf-8"))
                    # Tuple: (specificity, is_allow, -line_number) for sorting
                    # max() picks highest specificity; if equal, True (allow) > False (disallow);
                    # if still equal, earlier line (-line) is higher
                    candidates.append((specificity, rule["is_allow"], -rule["line"], rule))

        if not candidates:
            return {
                "allowed": True,
                "matched_rule": None,
                "crawl_delay": max_delay,
                "is_default": True,
            }

        winning = max(candidates, key=lambda c: (c[0], c[1], c[2]))[3]
        return {
            "allowed": winning["is_allow"],
            "matched_rule": winning,
            "crawl_delay": max_delay,
            "is_default": False,
        }


if __name__ == "__main__":
    sample = """
    User-agent: Googlebot
    Disallow: /private/
    Allow: /private/public-file.html
    Crawl-delay: 2.5

    User-agent: *
    Disallow: /
    Sitemap: https://example.com/sitemap.xml
    """
    parser = RobotsParser(sample)
    assert parser.get_declared_sitemaps() == ["https://example.com/sitemap.xml"]
    
    # Test Googlebot matching
    res1 = parser.evaluate("/private/secret.html", "Googlebot")
    assert not res1["allowed"], "Should be disallowed"
    assert res1["crawl_delay"] == 2.5

    res2 = parser.evaluate("/private/public-file.html", "Googlebot")
    assert res2["allowed"], "Allow rule has higher specificity"

    # Test wildcard fallback
    res3 = parser.evaluate("/anything", "OtherBot")
    assert not res3["allowed"], "Wildcard disallows root"

    print("RobotsParser self-tests passed successfully!")

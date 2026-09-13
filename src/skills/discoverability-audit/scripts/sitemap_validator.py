"""Sitemap Protocol and XML Standards Validator.

Validates sitemaps against standard sitemaps.org 0.9 schema:
- Gzip decompression (magic bytes \x1f\x8b or .gz extensions)
- XXE / DTD entity construct protection
- XML namespace validation ('http://www.sitemaps.org/schemas/sitemap/0.9')
- Root tag inspection ('urlset' vs 'sitemapindex')
- Protocol limit enforcement (max 50,000 URLs, max 50 MB uncompressed)
- ISO 8601 lastmod date format validation
- Absolute URL canonical location validation
"""
from __future__ import annotations

import gzip
import io
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit

SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
MAX_ENTRIES = 50000
MAX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024  # 50 MB
ISO_8601_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2}))?$")


def validate_sitemap_data(
    raw_data: bytes | str,
    sitemap_url: str = "",
) -> Dict[str, Any]:
    """Validate sitemap payload against XML standards and REP limits.

    Args:
        raw_data: Raw byte payload or text content of the sitemap.
        sitemap_url: Source URL of the sitemap.

    Returns:
        Structured validation results dict.
    """
    errors: List[str] = []
    warnings: List[str] = []
    sample_urls: List[str] = []
    is_gzip = False

    if isinstance(raw_data, str):
        data = raw_data.encode("utf-8")
    else:
        data = bytes(raw_data)

    # 1. Check Gzip compression
    if data.startswith(b"\x1f\x8b"):
        is_gzip = True
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(data)) as gz:
                data = gz.read(MAX_UNCOMPRESSED_BYTES + 1024)
        except Exception as exc:
            return {
                "valid": False,
                "url": sitemap_url,
                "kind": None,
                "entry_count": 0,
                "gzip": True,
                "size_bytes": len(raw_data),
                "errors": [f"Failed to decompress gzip sitemap: {exc}"],
                "warnings": warnings,
                "sample_urls": [],
            }

    size_bytes = len(data)
    if size_bytes > MAX_UNCOMPRESSED_BYTES:
        errors.append(f"Uncompressed size exceeds 50 MB protocol limit ({size_bytes} bytes).")

    # 2. XXE / DTD Injection Defense
    if re.search(br"<!\s*(DOCTYPE|ENTITY)", data, re.IGNORECASE):
        errors.append("Prohibited DTD/entity construct detected in XML (potential XXE vector).")
        return {
            "valid": False,
            "url": sitemap_url,
            "kind": None,
            "entry_count": 0,
            "gzip": is_gzip,
            "size_bytes": size_bytes,
            "errors": errors,
            "warnings": warnings,
            "sample_urls": [],
        }

    # 3. XML Parsing
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        return {
            "valid": False,
            "url": sitemap_url,
            "kind": None,
            "entry_count": 0,
            "gzip": is_gzip,
            "size_bytes": size_bytes,
            "errors": [f"XML parsing error: {exc}"],
            "warnings": warnings,
            "sample_urls": [],
        }

    # 4. Namespace and Root Element Validation
    root_tag = root.tag
    if not (root_tag.startswith(SITEMAP_NS) or root_tag in ("urlset", "sitemapindex")):
        errors.append(
            f"Invalid root XML namespace or tag: '{root_tag}'. "
            f"Expected '{SITEMAP_NS}urlset' or '{SITEMAP_NS}sitemapindex'."
        )

    # Determine kind
    clean_tag = root_tag.split("}")[-1] if "}" in root_tag else root_tag
    if clean_tag not in ("urlset", "sitemapindex"):
        errors.append(f"Unrecognized root tag '{clean_tag}'. Expected 'urlset' or 'sitemapindex'.")
        kind = None
    else:
        kind = clean_tag

    # 5. Entry Validation
    entry_tag = "url" if kind == "urlset" else "sitemap"
    entries = root.findall(f"{SITEMAP_NS}{entry_tag}") if SITEMAP_NS in root_tag else root.findall(entry_tag)
    entry_count = len(entries)

    if entry_count > MAX_ENTRIES:
        errors.append(f"Entry count ({entry_count}) exceeds protocol maximum of 50,000 URLs per sitemap file.")

    has_lastmod = False
    invalid_locs = 0
    invalid_lastmods = 0

    for idx, node in enumerate(entries):
        # Check <loc>
        loc_elem = node.find(f"{SITEMAP_NS}loc") if SITEMAP_NS in root_tag else node.find("loc")
        loc_val = (loc_elem.text or "").strip() if loc_elem is not None else ""
        if not loc_val:
            invalid_locs += 1
        else:
            p = urlsplit(loc_val)
            if p.scheme not in ("http", "https") or not p.netloc:
                invalid_locs += 1
            elif len(sample_urls) < 5:
                sample_urls.append(loc_val)

        # Check <lastmod>
        lastmod_elem = node.find(f"{SITEMAP_NS}lastmod") if SITEMAP_NS in root_tag else node.find("lastmod")
        if lastmod_elem is not None and lastmod_elem.text:
            has_lastmod = True
            mod_text = lastmod_elem.text.strip()
            if not ISO_8601_REGEX.match(mod_text):
                invalid_lastmods += 1

    if invalid_locs > 0:
        errors.append(f"Found {invalid_locs} entries with missing or non-absolute URL in <loc> tags.")

    if invalid_lastmods > 0:
        warnings.append(f"Found {invalid_lastmods} entries with invalid ISO 8601 dates in <lastmod> tags.")

    if not has_lastmod and entry_count > 0:
        warnings.append("Sitemap entries omit <lastmod> timestamps; AI crawlers cannot determine content freshness.")

    is_valid = (len(errors) == 0)

    return {
        "valid": is_valid,
        "url": sitemap_url,
        "kind": kind,
        "entry_count": entry_count,
        "gzip": is_gzip,
        "size_bytes": size_bytes,
        "has_lastmod": has_lastmod,
        "sample_urls": sample_urls,
        "errors": errors,
        "warnings": warnings,
    }


if __name__ == "__main__":
    valid_sample = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url>
            <loc>https://example.com/page1</loc>
            <lastmod>2026-03-01T12:00:00Z</lastmod>
        </url>
        <url>
            <loc>https://example.com/page2</loc>
        </url>
    </urlset>
    """
    res = validate_sitemap_data(valid_sample, "https://example.com/sitemap.xml")
    assert res["valid"], f"Expected valid sitemap, got errors: {res['errors']}"
    assert res["kind"] == "urlset"
    assert res["entry_count"] == 2
    assert len(res["sample_urls"]) == 2
    print("Sitemap validator self-test passed successfully!")

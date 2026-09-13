"""Unit tests for nav_verifier: navigation route probing and form-gated discovery."""
from unittest.mock import patch
import pytest

from nav_verifier import (
    extract_navigation_links,
    verify_navigation_links,
    detect_form_gated_discovery,
    verify_navigation_and_gates,
)


def test_extract_navigation_links_from_nav_element():
    html = """
    <html>
      <body>
        <nav>
          <ul>
            <li><a href="/products">Products</a></li>
            <li><a href="/about-us">About Us</a></li>
            <li><a href="https://external.com">External</a></li>
            <li><a href="#section">Anchor</a></li>
          </ul>
        </nav>
      </body>
    </html>
    """
    links = extract_navigation_links(html, "https://example.com")
    paths = [l["path"] for l in links]
    assert "/products" in paths
    assert "/about-us" in paths
    # External and anchors filtered out
    assert not any("external.com" in l["url"] for l in links)
    assert not any("#section" in l["url"] for l in links)


def test_extract_navigation_links_from_eds_fragment():
    homepage_html = "<html><body><main><h1>Welcome</h1></main></body></html>"
    inv = {
        "pages": [
            {
                "url": "https://example.com/nav.plain.html",
                "html": "<div><ul><li><a href='/tea'>Tea</a></li><li><a href='/coffee'>Coffee</a></li></ul></div>",
                "status": 200,
            }
        ]
    }
    links = extract_navigation_links(homepage_html, "https://example.com", inv=inv)
    paths = [l["path"] for l in links]
    assert "/tea" in paths
    assert "/coffee" in paths


def test_verify_navigation_links_detects_404():
    nav_links = [
        {"url": "https://example.com/coffee", "path": "/coffee", "title": "Coffee"},
        {"url": "https://example.com/tea", "path": "/tea", "title": "Tea"},
    ]
    inv = {
        "pages": [
            {"url": "https://example.com/coffee", "status": 200},
            {"url": "https://example.com/tea", "status": 404},
        ]
    }
    broken = verify_navigation_links(nav_links, inv=inv)
    assert len(broken) == 1
    assert broken[0]["path"] == "/tea"
    assert broken[0]["status"] == 404


def test_detect_form_gated_discovery_flags_store_locator():
    pages = [
        {
            "url": "https://example.com/locations",
            "html": """
            <html><body>
              <h3>Our Locations</h3>
              <div class="store-locator">
                <div>Try a roast near you!</div>
                <div>Find A Location</div>
                <div>Post Code</div>
                <div>Search</div>
              </div>
            </body></html>
            """,
        }
    ]
    traps = detect_form_gated_discovery(pages, "https://example.com")
    assert len(traps) == 1
    assert traps[0]["path"] == "/locations"
    assert traps[0]["has_schema"] is False


def test_detect_form_gated_discovery_passes_with_schema():
    pages = [
        {
            "url": "https://example.com/locations",
            "html": """
            <html>
              <head>
                <script type="application/ld+json">
                {
                  "@context": "https://schema.org",
                  "@type": "LocalBusiness",
                  "name": "Example Cafe",
                  "address": {"streetAddress": "123 Main St"}
                }
                </script>
              </head>
              <body>
                <div class="store-locator">Search</div>
              </body>
            </html>
            """,
        }
    ]
    traps = detect_form_gated_discovery(pages, "https://example.com")
    assert len(traps) == 0


def test_verify_navigation_and_gates_integration():
    homepage = "<html><body><nav><a href='/dead-end'>Dead Link</a></nav></body></html>"
    inv = {
        "pages": [
            {"url": "https://example.com/dead-end", "status": 404},
            {
                "url": "https://example.com/stores",
                "html": "<div class='store-locator'>Find a store by zip <input type='text'></div>",
            },
        ]
    }
    findings = verify_navigation_and_gates("https://example.com", homepage, inv=inv)
    check_ids = [f["check_id"] for f in findings]
    assert "B4" in check_ids
    assert "C2" in check_ids

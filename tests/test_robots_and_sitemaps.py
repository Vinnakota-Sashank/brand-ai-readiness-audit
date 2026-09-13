"""Tests for RFC 9309 RobotsParser, SitemapValidator, and Source Signals."""
import gzip
import pytest
from robots_parser import RobotsParser, normalize_octets
from sitemap_validator import validate_sitemap_data
from source_signals import detect_source_signals


class TestRobotsParserRFC9309:
    def test_longest_match_specificity(self):
        txt = """
        User-agent: Googlebot
        Disallow: /shop/
        Allow: /shop/special/deal.html
        """
        parser = RobotsParser(txt)
        # More specific Allow should win over Disallow
        res = parser.evaluate("/shop/special/deal.html", "Googlebot")
        assert res["allowed"] is True
        # Less specific Disallow should apply to other files
        res2 = parser.evaluate("/shop/other.html", "Googlebot")
        assert res2["allowed"] is False

    def test_equal_length_allow_precedence(self):
        # RFC 9309 § 2.2.3: if Allow and Disallow have equal length, Allow wins
        txt = """
        User-agent: *
        Disallow: /page
        Allow: /page
        """
        parser = RobotsParser(txt)
        res = parser.evaluate("/page", "AnyBot")
        assert res["allowed"] is True

    def test_user_agent_group_precedence(self):
        # Specific user-agent takes strict precedence over wildcard
        txt = """
        User-agent: *
        Disallow: /

        User-agent: Claude-SearchBot
        Allow: /
        """
        parser = RobotsParser(txt)
        res_claude = parser.evaluate("/article", "Claude-SearchBot")
        assert res_claude["allowed"] is True

        res_other = parser.evaluate("/article", "OtherBot")
        assert res_other["allowed"] is False

    def test_html_in_robots_detected(self):
        html_robots = "<!DOCTYPE html><html><body>404 Not Found</body></html>"
        parser = RobotsParser(html_robots)
        assert parser.is_html is True
        assert len(parser.errors) > 0

    def test_crawl_delay_and_sitemaps(self):
        txt = """
        User-agent: PerplexityBot
        Crawl-delay: 3.5
        Disallow: /private/
        Sitemap: https://example.com/sitemap.xml
        Sitemap: https://example.com/sitemap2.xml
        """
        parser = RobotsParser(txt)
        res = parser.evaluate("/public", "PerplexityBot")
        assert res["crawl_delay"] == 3.5
        assert parser.get_declared_sitemaps() == [
            "https://example.com/sitemap.xml",
            "https://example.com/sitemap2.xml",
        ]


class TestSitemapValidator:
    def test_valid_urlset_sitemap(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url>
                <loc>https://example.com/page-1</loc>
                <lastmod>2026-01-15T10:00:00Z</lastmod>
            </url>
        </urlset>
        """
        res = validate_sitemap_data(xml, "https://example.com/sitemap.xml")
        assert res["valid"] is True
        assert res["kind"] == "urlset"
        assert res["entry_count"] == 1
        assert res["has_lastmod"] is True

    def test_valid_gzip_sitemap(self):
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://example.com/page</loc></url>
        </urlset>
        """
        gz_data = gzip.compress(xml)
        res = validate_sitemap_data(gz_data, "https://example.com/sitemap.xml.gz")
        assert res["valid"] is True
        assert res["gzip"] is True
        assert res["entry_count"] == 1

    def test_dtd_entity_rejected_xxe_protection(self):
        evil_xml = """<?xml version="1.0"?>
        <!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>&xxe;</loc></url>
        </urlset>
        """
        res = validate_sitemap_data(evil_xml, "https://example.com/sitemap.xml")
        assert res["valid"] is False
        assert any("DTD" in err for err in res["errors"])

    def test_invalid_lastmod_warned(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url>
                <loc>https://example.com/page</loc>
                <lastmod>Yesterday at 5pm</lastmod>
            </url>
        </urlset>
        """
        res = validate_sitemap_data(xml, "https://example.com/sitemap.xml")
        assert len(res["warnings"]) > 0


class TestSourceSignals:
    def test_detect_empty_href_links(self):
        html_doc = """
        <html><body>
            <a href="#">Read Customer Reviews</a>
            <a href="">Order Online Now</a>
            <a href="https://example.com/valid">Valid Link</a>
        </body></html>
        """
        signals = detect_source_signals(html_doc, "https://example.com/")
        empty_sig = [s for s in signals if s["type"] == "empty_href_navigation"]
        assert len(empty_sig) == 1
        assert "Customer Reviews" in empty_sig[0]["issue"]

    def test_detect_cross_hostname_identity(self):
        html_doc = "<html><body><h1>Product</h1></body></html>"
        jsonld = [{
            "@type": "Product",
            "name": "Super Widget",
            "@id": "https://external-store.com/item/123",
        }]
        signals = detect_source_signals(html_doc, "https://mystore.com/item/123", jsonld_items=jsonld)
        cross_sig = [s for s in signals if s["type"] == "cross_hostname_identity"]
        assert len(cross_sig) == 1
        assert "external-store.com" in cross_sig[0]["issue"]

    def test_detect_challenge_interstitial(self):
        html_doc = """
        <html>
        <head><title>Just a moment... Attention Required</title></head>
        <body>
            <p>Please verify you are human to continue.</p>
            <script src="https://challenges.cloudflare.com/turnstile/v0/api.js"></script>
        </body>
        </html>
        """
        signals = detect_source_signals(html_doc, "https://example.com/")
        challenge_sig = [s for s in signals if s["type"] == "challenge_interstitial"]
        assert len(challenge_sig) == 1

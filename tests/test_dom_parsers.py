import sys
import unittest

sys.path.insert(0, "src/skills/discoverability-audit/scripts")
import discoverability_check

sys.path.insert(0, "src/skills/entity-content-audit/scripts")
import entity_content_check

sys.path.insert(0, "src/skills/fact-consistency-audit/scripts")
import fact_consistency_check

sys.path.insert(0, "src/skills/geo-content-audit/scripts")
import geo_content_check


class TestDOMParsers(unittest.TestCase):
    def test_discoverability_canonical_extraction(self):
        html = '<html><head><link rel="canonical" href="https://example.com/page"/></head></html>'
        parser = discoverability_check.Dom()
        parser.feed(html)
        self.assertEqual(parser.canonical, "https://example.com/page")

    def test_discoverability_meta_robots_noindex(self):
        html = '<html><head><meta name="robots" content="noindex, follow"/></head></html>'
        parser = discoverability_check.Dom()
        parser.feed(html)
        self.assertIn("noindex", parser.meta_robots)

    def test_entity_json_ld_single_and_graph(self):
        html = """<html><head>
        <script type="application/ld+json">{"@context": "https://schema.org", "@type": "Organization", "name": "Org1"}</script>
        <script type="application/ld+json">{"@context": "https://schema.org", "@graph": [{"@type": "Product", "name": "Prod1"}]}</script>
        </head></html>"""
        parser = entity_content_check.EntityDOMParser()
        parser.feed(html)
        entities = entity_content_check.parse_json_ld(parser.json_ld_contents)
        names = [e.get("name") for e in entities]
        self.assertIn("Org1", names)
        self.assertIn("Prod1", names)

    def test_entity_malformed_json_ld_recovery(self):
        html = """<html><head>
        <script type="application/ld+json">{ invalid json @#$ }</script>
        <script type="application/ld+json">{"@context": "https://schema.org", "@type": "Organization", "name": "ValidOrg"}</script>
        </head></html>"""
        parser = entity_content_check.EntityDOMParser()
        parser.feed(html)
        entities = entity_content_check.parse_json_ld(parser.json_ld_contents)
        self.assertEqual(len(entities), 1)
        self.assertEqual(entities[0]["name"], "ValidOrg")

    def test_freshness_headings_and_context(self):
        html = "<html><body><h2>Product Plan</h2><p>Price: $99/mo</p></body></html>"
        parser = fact_consistency_check.FreshnessAnalyzer()
        parser.feed(html)
        self.assertTrue(len(parser.headings) > 0)
        self.assertEqual(parser.headings[0][1], "Product Plan")

    def test_geo_dom_parser_structure(self):
        html = "<html><body><h1>Title</h1><table><tr><td>Data</td></tr></table><ul><li>Item 1</li></ul></body></html>"
        parser = geo_content_check.GEODOMParser()
        parser.feed(html)
        self.assertEqual(parser.tables, 1)
        self.assertEqual(parser.lists, 1)
        self.assertIn("Title", parser.headings)


if __name__ == "__main__":
    unittest.main()

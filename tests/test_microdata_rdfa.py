import os
import sys
import unittest

SCRIPT_DIR = os.path.join(os.path.dirname(__file__), "..", "src", "skills", "entity-content-audit", "scripts")
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from entity_content_check import extract_microdata_and_rdfa, parse_json_ld


class TestMicrodataRDFaExtraction(unittest.TestCase):
    def test_extract_product_microdata(self):
        html = """
        <div itemscope itemtype="https://schema.org/Product">
            <h1 itemprop="name">Enterprise Cloud Suite</h1>
            <span itemprop="sku">ECS-100</span>
            <p itemprop="description">Scalable enterprise cloud platform.</p>
        </div>
        """
        entities = extract_microdata_and_rdfa(html)
        self.assertEqual(len(entities), 1)
        prod = entities[0]
        self.assertEqual(prod.get("@type"), "Product")
        self.assertEqual(prod.get("name"), "Enterprise Cloud Suite")
        self.assertEqual(prod.get("sku"), "ECS-100")
        self.assertEqual(prod.get("description"), "Scalable enterprise cloud platform.")

    def test_extract_organization_rdfa(self):
        html = """
        <div vocab="https://schema.org/" typeof="Organization">
            <span property="name">Acme Corporation</span>
            <a property="url" href="https://acme.com">Website</a>
        </div>
        """
        entities = extract_microdata_and_rdfa(html)
        self.assertEqual(len(entities), 1)
        org = entities[0]
        self.assertEqual(org.get("@type"), "Organization")
        self.assertEqual(org.get("name"), "Acme Corporation")

    def test_unified_parse_json_ld_with_microdata_fallback(self):
        json_ld_list = []  # No JSON-LD on page
        html = """
        <div itemscope itemtype="https://schema.org/Product">
            <h1 itemprop="name">Widget Pro</h1>
            <span itemprop="sku">WP-001</span>
        </div>
        """
        parsed = parse_json_ld(json_ld_list, raw_html=html)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["name"], "Widget Pro")


if __name__ == "__main__":
    unittest.main()

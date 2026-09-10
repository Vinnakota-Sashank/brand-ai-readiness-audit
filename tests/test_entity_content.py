import json
import os
import subprocess
import tempfile
import unittest


class TestEntityContentAudit(unittest.TestCase):
    def setUp(self):
        self.script_path = "src/skills/entity-content-audit/scripts/entity_content_check.py"
        self.test_inv = os.path.join(tempfile.gettempdir(), "test_entity_inv.json")
        self.test_state = os.path.join(tempfile.gettempdir(), "test_entity_state.json")

    def test_missing_product_answerability(self):
        inv_data = {
            "site": "https://testbrand.com",
            "pages": [
                {
                    "url": "https://testbrand.com/",
                    "status": 200,
                    "content_type": "text/html",
                    "page_type": "homepage",
                    "html": "<html><head><title>TestBrand</title></head><body><h1>TestBrand</h1></body></html>",
                },
                {
                    "url": "https://testbrand.com/products/suite",
                    "status": 200,
                    "content_type": "text/html",
                    "page_type": "product",
                    "html": """<!DOCTYPE html><html><head><title>Product</title><script type="application/ld+json">{"@context": "https://schema.org", "@type": "Product", "name": "AI Suite"}</script></head><body><h1>AI Suite</h1></body></html>""",
                },
            ],
            "robots_txt": "",
            "sitemaps": [],
        }
        with open(self.test_inv, "w") as f:
            json.dump(inv_data, f)
        with open(self.test_state, "w") as f:
            json.dump(
                {"version": 1, "entities": {}, "facts": {}, "claims": {}, "observations": {}, "page_context": {}}, f
            )

        res = subprocess.run(
            [
                "python3",
                self.script_path,
                "--site",
                "https://testbrand.com",
                "--inventory",
                self.test_inv,
                "--state",
                self.test_state,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertEqual(data["status"], "ok")
        cause_ids = [f.get("cause_id") for f in data.get("findings", [])]
        self.assertIn("ATTRIBUTE_INCOMPLETENESS", cause_ids)

    def test_valid_organization_schema(self):
        inv_data = {
            "site": "https://testbrand.com",
            "pages": [
                {
                    "url": "https://testbrand.com/",
                    "status": 200,
                    "content_type": "text/html",
                    "page_type": "homepage",
                    "html": """<!DOCTYPE html><html><head><title>With Schema</title><script type="application/ld+json">{"@context": "https://schema.org", "@type": "Organization", "name": "TestBrand", "url": "https://testbrand.com"}</script></head><body><h1>With Schema</h1><p>Price starts at $49/mo.</p></body></html>""",
                }
            ],
            "robots_txt": "",
            "sitemaps": [],
        }
        with open(self.test_inv, "w") as f:
            json.dump(inv_data, f)
        with open(self.test_state, "w") as f:
            json.dump(
                {"version": 1, "entities": {}, "facts": {}, "claims": {}, "observations": {}, "page_context": {}}, f
            )

        res = subprocess.run(
            [
                "python3",
                self.script_path,
                "--site",
                "https://testbrand.com",
                "--inventory",
                self.test_inv,
                "--state",
                self.test_state,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertEqual(data["status"], "ok")


if __name__ == "__main__":
    unittest.main()

import json
import os
import subprocess
import tempfile
import unittest


class TestEngagementDeep(unittest.TestCase):
    def setUp(self):
        self.script = "skills/engagement-context-audit/scripts/engagement_check.py"
        self.test_inv = os.path.join(tempfile.gettempdir(), "test_eng_inv.json")
        self.test_state = os.path.join(tempfile.gettempdir(), "test_eng_state.json")

    def test_engagement_audit_execution(self):
        inv_data = {
            "site": "https://testbrand.com",
            "pages": [
                {
                    "url": "https://testbrand.com/pricing",
                    "status": 200,
                    "content_type": "text/html",
                    "page_type": "pricing",
                    "html": '<html><body><h1>Pricing Plans</h1><p>Plans start at $49/mo.</p><a href="/signup">Sign Up</a></body></html>',
                }
            ],
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
                self.script,
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
        out = json.loads(res.stdout)
        self.assertEqual(out["status"], "ok")

    def test_product_detail_scent_anchoring(self):
        inv_data = {
            "site": "https://testbrand.com",
            "pages": [
                {
                    "url": "https://testbrand.com/products/pro",
                    "status": 200,
                    "content_type": "text/html",
                    "page_type": "product_detail",
                    "html": '<html><body><h1>Enterprise Pro Suite</h1><p>Details about enterprise pro suite.</p><a href="/checkout">Buy Now</a></body></html>',
                }
            ],
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
                self.script,
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
        out = json.loads(res.stdout)
        self.assertEqual(out["status"], "ok")

    def test_empty_pages_engagement_handling(self):
        inv_data = {"site": "https://testbrand.com", "pages": []}
        with open(self.test_inv, "w") as f:
            json.dump(inv_data, f)
        res = subprocess.run(
            ["python3", self.script, "--site", "https://testbrand.com", "--inventory", self.test_inv],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)

    def test_recommendation_on_missing_heading_scent(self):
        inv_data = {
            "site": "https://testbrand.com",
            "pages": [
                {
                    "url": "https://testbrand.com/",
                    "status": 200,
                    "content_type": "text/html",
                    "page_type": "homepage",
                    "html": "<html><body><p>No headings anywhere on this page.</p></body></html>",
                }
            ],
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
                self.script,
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
        out = json.loads(res.stdout)
        recs = [r.get("title") for r in out.get("recommendations", [])]
        self.assertTrue(any("h1" in r.lower() or "heading" in r.lower() for r in recs))

    def test_state_population_by_engagement(self):
        inv_data = {
            "site": "https://testbrand.com",
            "pages": [
                {
                    "url": "https://testbrand.com/",
                    "status": 200,
                    "content_type": "text/html",
                    "page_type": "homepage",
                    "html": "<html><body><h1>TestBrand Official</h1><p>Contact: support@testbrand.com</p></body></html>",
                }
            ],
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
                self.script,
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


if __name__ == "__main__":
    unittest.main()

import json
import os
import subprocess
import tempfile
import unittest


class TestFactConsistencyAudit(unittest.TestCase):
    def setUp(self):
        self.script_path = "skills/fact-consistency-audit/scripts/fact_consistency_check.py"
        self.test_inv = os.path.join(tempfile.gettempdir(), "test_fact_inv.json")
        self.test_state = os.path.join(tempfile.gettempdir(), "test_fact_state.json")

    def test_price_contradiction_detection(self):
        inv_data = {
            "site": "https://testbrand.com",
            "pages": [
                {
                    "url": "https://testbrand.com/",
                    "status": 200,
                    "content_type": "text/html",
                    "page_type": "homepage",
                    "html": "<html><body><h2>Cloud Pro Suite</h2><p>Price: $10/mo</p></body></html>",
                },
                {
                    "url": "https://testbrand.com/pricing",
                    "status": 200,
                    "content_type": "text/html",
                    "page_type": "pricing",
                    "html": "<html><body><h2>Cloud Pro Suite</h2><p>Price: $50/mo</p></body></html>",
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
        self.assertIn("FIRST_PARTY_FACT_CONFLICT", cause_ids)


if __name__ == "__main__":
    unittest.main()

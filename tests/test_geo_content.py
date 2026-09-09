import json
import os
import subprocess
import tempfile
import unittest


class TestGeoContentAudit(unittest.TestCase):
    def setUp(self):
        self.script_path = "skills/geo-content-audit/scripts/geo_content_check.py"
        self.test_inv = os.path.join(tempfile.gettempdir(), "test_geo_inv.json")
        self.test_state = os.path.join(tempfile.gettempdir(), "test_geo_state.json")

    def test_geo_scoring(self):
        inv_data = {
            "site": "https://testbrand.com",
            "pages": [
                {
                    "url": "https://testbrand.com/",
                    "status": 200,
                    "content_type": "text/html",
                    "page_type": "homepage",
                    "html": "<html><body><h1>TestBrand</h1><p>TestBrand accelerates workflow by 45% because our distributed cache eliminates disk I/O latency. Therefore, response times drop below 10ms.</p></body></html>",
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

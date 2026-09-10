import json
import os
import subprocess
import tempfile
import unittest


class TestDiscoverabilityAudit(unittest.TestCase):
    def setUp(self):
        self.script_path = "src/skills/discoverability-audit/scripts/discoverability_check.py"
        self.test_inv = os.path.join(tempfile.gettempdir(), "test_disc_inv.json")

    def test_robots_txt_searchbot_blocking(self):
        inv_data = {
            "site": "https://testbrand.com",
            "pages": [
                {
                    "url": "https://testbrand.com/",
                    "status": 200,
                    "content_type": "text/html",
                    "page_type": "homepage",
                    "html": "<html><head><title>Test</title><link rel='canonical' href='https://testbrand.com/'/></head><body><h1>Test</h1></body></html>",
                }
            ],
            "robots_txt": "User-agent: OAI-SearchBot\nDisallow: /\n",
            "sitemaps": [],
        }
        with open(self.test_inv, "w") as f:
            json.dump(inv_data, f)

        res = subprocess.run(
            ["python3", self.script_path, "--site", "https://testbrand.com", "--inventory", self.test_inv],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertEqual(data["status"], "ok")
        cause_ids = [f.get("cause_id") for f in data.get("findings", [])]
        self.assertIn("AI_RETRIEVAL_BLOCKED", cause_ids)

    def test_clean_site_passes(self):
        inv_data = {
            "site": "https://testbrand.com",
            "pages": [
                {
                    "url": "https://testbrand.com/",
                    "status": 200,
                    "content_type": "text/html",
                    "page_type": "homepage",
                    "html": "<html><head><title>Test</title><link rel='canonical' href='https://testbrand.com/'/></head><body><h1>Test</h1></body></html>",
                }
            ],
            "robots_txt": "User-agent: *\nAllow: /\n",
            "sitemaps": [],
        }
        with open(self.test_inv, "w") as f:
            json.dump(inv_data, f)

        res = subprocess.run(
            ["python3", self.script_path, "--site", "https://testbrand.com", "--inventory", self.test_inv],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertEqual(data["status"], "ok")


if __name__ == "__main__":
    unittest.main()

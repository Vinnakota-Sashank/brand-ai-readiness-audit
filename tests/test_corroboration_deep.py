import json
import os
import subprocess
import tempfile
import unittest


class TestCorroborationDeep(unittest.TestCase):
    def setUp(self):
        self.script = "skills/corroboration-authority-audit/scripts/corroboration_check.py"
        self.test_inv = os.path.join(tempfile.gettempdir(), "test_corrob_inv.json")
        self.test_state = os.path.join(tempfile.gettempdir(), "test_corrob_state.json")

    def test_corroboration_with_valid_sameas(self):
        inv_data = {
            "site": "https://testbrand.com",
            "pages": [
                {
                    "url": "https://testbrand.com/",
                    "status": 200,
                    "content_type": "text/html",
                    "page_type": "homepage",
                    "html": """<!DOCTYPE html><html><head><script type="application/ld+json">{"@context": "https://schema.org", "@type": "Organization", "name": "TestBrand", "sameAs": ["https://twitter.com/testbrand", "https://linkedin.com/company/testbrand"]}</script></head><body><h1>TestBrand</h1></body></html>""",
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

    def test_corroboration_missing_sameas_emits_recommendation(self):
        inv_data = {
            "site": "https://testbrand.com",
            "pages": [
                {
                    "url": "https://testbrand.com/",
                    "status": 200,
                    "content_type": "text/html",
                    "page_type": "homepage",
                    "html": """<!DOCTYPE html><html><head><title>TestBrand</title></head><body><h1>TestBrand</h1></body></html>""",
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
        # Should emit recommendation to add sameAs profiles
        recs = [r.get("title") for r in out.get("recommendations", [])]
        self.assertTrue(any("sameAs" in r or "profile" in r.lower() for r in recs))

    def test_broken_sameas_link_detection(self):
        # sameAs with invalid non-existent domain should flag broken anchor
        inv_data = {
            "site": "https://testbrand.com",
            "pages": [
                {
                    "url": "https://testbrand.com/",
                    "status": 200,
                    "content_type": "text/html",
                    "page_type": "homepage",
                    "html": """<!DOCTYPE html><html><head><script type="application/ld+json">{"@context": "https://schema.org", "@type": "Organization", "name": "TestBrand", "sameAs": ["https://invalid-non-existent-domain-test-12345.org"]}</script></head><body><h1>TestBrand</h1></body></html>""",
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
        cause_ids = [f.get("cause_id") for f in out.get("findings", [])]
        self.assertIn("BROKEN_AUTHORITY_ANCHOR", cause_ids)

    def test_ssrf_attempt_in_sameas_blocked(self):
        # sameAs pointing to 127.0.0.1 must be safely blocked
        inv_data = {
            "site": "https://testbrand.com",
            "pages": [
                {
                    "url": "https://testbrand.com/",
                    "status": 200,
                    "content_type": "text/html",
                    "page_type": "homepage",
                    "html": """<!DOCTYPE html><html><head><script type="application/ld+json">{"@context": "https://schema.org", "@type": "Organization", "name": "TestBrand", "sameAs": ["http://127.0.0.1:8080/admin"]}</script></head><body><h1>TestBrand</h1></body></html>""",
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
        # 127.0.0.1 is blocked by safe_fetch so treated as broken anchor
        cause_ids = [f.get("cause_id") for f in out.get("findings", [])]
        self.assertIn("BROKEN_AUTHORITY_ANCHOR", cause_ids)

    def test_corroboration_empty_inventory(self):
        res = subprocess.run(
            [
                "python3",
                self.script,
                "--site",
                "https://testbrand.com",
                "--inventory",
                os.path.join(tempfile.gettempdir(), "non_existent.json"),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)


if __name__ == "__main__":
    unittest.main()

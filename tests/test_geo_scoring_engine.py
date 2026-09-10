import json
import os
import subprocess
import tempfile
import unittest


class TestGeoScoringEngine(unittest.TestCase):
    def setUp(self):
        self.script_path = "src/skills/geo-content-audit/scripts/geo_content_check.py"
        self.test_inv = os.path.join(tempfile.gettempdir(), "test_geo_unit_inv.json")
        self.test_state = os.path.join(tempfile.gettempdir(), "test_geo_unit_state.json")

    def test_causal_conjunction_detection(self):
        # A pricing page with deep causal explanations should not flag missing mechanisms
        inv_data = {
            "site": "https://testbrand.com",
            "pages": [
                {
                    "url": "https://testbrand.com/pricing",
                    "status": 200,
                    "content_type": "text/html",
                    "page_type": "pricing",
                    "html": "<html><body><h1>Pricing</h1><p>Our distributed cache improves efficiency because network bottlenecks are eliminated. Therefore, query latency drops by 40%.</p></body></html>",
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
        out = json.loads(res.stdout)
        cause_ids = [f.get("cause_id") for f in out.get("findings", [])]
        self.assertNotIn("MISSING_IN_DEPTH_MECHANISMS", cause_ids)

    def test_vague_text_flags_shallow_mechanisms(self):
        # A pricing page with shallow text without because/therefore should flag MISSING_IN_DEPTH_MECHANISMS
        inv_data = {
            "site": "https://testbrand.com",
            "pages": [
                {
                    "url": "https://testbrand.com/pricing",
                    "status": 200,
                    "content_type": "text/html",
                    "page_type": "pricing",
                    "html": "<html><body><h1>Pricing</h1><p>We provide the best world-class solutions for all businesses.</p></body></html>",
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
        out = json.loads(res.stdout)
        cause_ids = [f.get("cause_id") for f in out.get("findings", [])]
        self.assertIn("MISSING_IN_DEPTH_MECHANISMS", cause_ids)

    def test_statistical_density_detection(self):
        # Text with numbers and percentages satisfies specific evidence criteria
        inv_data = {
            "site": "https://testbrand.com",
            "pages": [
                {
                    "url": "https://testbrand.com/pricing",
                    "status": 200,
                    "content_type": "text/html",
                    "page_type": "pricing",
                    "html": "<html><body><h1>Pricing</h1><p>Our platform costs $49/mo, handles 10 million events daily, and reduces latency by 50% because of parallel processing. Therefore uptime exceeds 99.9%.</p></body></html>",
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
        out = json.loads(res.stdout)
        self.assertEqual(out["status"], "ok")

    def test_content_depth_insufficient_flags_thin_page(self):
        # A page with 50 words should trigger CONTENT_DEPTH_INSUFFICIENT
        thin_text = "Our platform provides exceptional services for growing businesses across multiple domains. " * 5
        inv_data = {
            "site": "https://testbrand.com",
            "pages": [
                {
                    "url": "https://testbrand.com/article",
                    "status": 200,
                    "content_type": "text/html",
                    "page_type": "article",
                    "html": f"<html><body><h1>Article</h1><p>{thin_text}</p></body></html>",
                }
            ],
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
        out = json.loads(res.stdout)
        cause_ids = [f.get("cause_id") for f in out.get("findings", [])]
        self.assertIn("CONTENT_DEPTH_INSUFFICIENT", cause_ids)

    def test_pronoun_density_recommendation_emitted(self):
        # A page with >3% ambiguous pronouns should emit PROACTIVE.GEO.PRONOUN_DENSITY.001
        pronoun_heavy = "It is clear that this system delivers what they need. This enables it to operate because it is fast. " * 20
        inv_data = {
            "site": "https://testbrand.com",
            "pages": [
                {
                    "url": "https://testbrand.com/article",
                    "status": 200,
                    "content_type": "text/html",
                    "page_type": "article",
                    "html": f"<html><body><h1>Title</h1><p>{pronoun_heavy}</p></body></html>",
                }
            ],
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
        out = json.loads(res.stdout)
        rec_ids = [r.get("id") for r in out.get("recommendations", [])]
        self.assertIn("PROACTIVE.GEO.PRONOUN_DENSITY.001", rec_ids)

    def test_passage_chunk_length_recommendation_emitted(self):
        # A page with oversized paragraphs (>250 words) should emit PROACTIVE.GEO.PASSAGE_CHUNK_LENGTH.001
        long_para = "Comprehensive architectural analysis indicates that systems scaling across distributed environments require structured fault tolerance. " * 25
        inv_data = {
            "site": "https://testbrand.com",
            "pages": [
                {
                    "url": "https://testbrand.com/article",
                    "status": 200,
                    "content_type": "text/html",
                    "page_type": "article",
                    "html": f"<html><body><h1>Title</h1><p>{long_para}</p><p>{long_para}</p></body></html>",
                }
            ],
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
        out = json.loads(res.stdout)
        rec_ids = [r.get("id") for r in out.get("recommendations", [])]
        self.assertIn("PROACTIVE.GEO.PASSAGE_CHUNK_LENGTH.001", rec_ids)


if __name__ == "__main__":
    unittest.main()

import json
import os
import subprocess
import sys
import tempfile
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SKILLS_DIR = os.path.join(PROJECT_ROOT, "skills")


class TestSpecialistSensors(unittest.TestCase):
    def setUp(self):
        self.synthetic_inv = {
            "site": "https://testbrand.com",
            "pages": [
                {
                    "url": "https://testbrand.com/",
                    "status": 200,
                    "content_type": "text/html",
                    "page_type": "homepage",
                    "html": """<!DOCTYPE html>
                    <html>
                    <head>
                        <title>TestBrand Enterprise AI</title>
                        <meta name="description" content="TestBrand provides AI optimization.">
                        <link rel="canonical" href="https://testbrand.com/">
                        <script type="application/ld+json">
                        {
                            "@context": "https://schema.org",
                            "@type": "Organization",
                            "name": "TestBrand",
                            "url": "https://testbrand.com",
                            "sameAs": ["https://wikidata.org/wiki/Q12345", "https://linkedin.com/company/testbrand"]
                        }
                        </script>
                    </head>
                    <body>
                        <h1>TestBrand Enterprise AI</h1>
                        <p>Accelerate workflows by 85% because automated indexing eliminates manual steps.</p>
                        <a href="/demo" class="cta-btn">Request Demo</a>
                    </body>
                    </html>""",
                },
                {
                    "url": "https://testbrand.com/pricing",
                    "status": 200,
                    "content_type": "text/html",
                    "page_type": "pricing",
                    "html": """<!DOCTYPE html>
                    <html>
                    <head><title>Pricing - TestBrand</title></head>
                    <body>
                        <h2>Starter Plan</h2>
                        <p>Our starter tier is priced at $49/mo because of scalable cloud architecture.</p>
                        <table>
                            <tr><th>Plan</th><th>Price</th></tr>
                            <tr><td>Starter</td><td>$49/mo</td></tr>
                        </table>
                        <a href="/signup">Sign Up</a>
                    </body>
                    </html>""",
                },
            ],
            "robots_txt": "User-agent: *\nAllow: /\nUser-agent: GPTBot\nDisallow: /\n",
            "sitemaps": ["https://testbrand.com/sitemap.xml"],
        }
        self.temp_dir = tempfile.gettempdir()
        self.inv_path = os.path.join(self.temp_dir, "test_sensors_inv.json")
        with open(self.inv_path, "w", encoding="utf-8") as f:
            json.dump(self.synthetic_inv, f)

    def tearDown(self):
        if os.path.exists(self.inv_path):
            os.remove(self.inv_path)

    def test_all_six_specialists_execute_standalone(self):
        specialists = [
            ("discoverability-audit", "discoverability_check.py"),
            ("entity-content-audit", "entity_content_check.py"),
            ("fact-consistency-audit", "fact_consistency_check.py"),
            ("corroboration-authority-audit", "corroboration_check.py"),
            ("geo-content-audit", "geo_content_check.py"),
            ("engagement-context-audit", "engagement_check.py"),
        ]

        for sname, sfile in specialists:
            script_path = os.path.join(SKILLS_DIR, sname, "scripts", sfile)
            self.assertTrue(os.path.exists(script_path), f"Script missing: {script_path}")

            cmd = [
                sys.executable,
                script_path,
                "--site",
                "https://testbrand.com",
                "--inventory",
                self.inv_path,
                "--format",
                "json",
            ]
            proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, f"{sname} failed with stderr: {proc.stderr}")

            out = json.loads(proc.stdout)
            self.assertIn("status", out, f"{sname} missing 'status' key")
            self.assertIn("findings", out, f"{sname} missing 'findings' key")
            self.assertIn("recommendations", out, f"{sname} missing 'recommendations' key")
            self.assertEqual(out["status"], "ok")


if __name__ == "__main__":
    unittest.main()

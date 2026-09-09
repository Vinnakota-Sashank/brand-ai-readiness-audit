import os
import sys
import unittest

SCRIPT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../skills/geo-content-audit/scripts"))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from geo_content_check import GEODOMParser, audit


class TestGEOPrincetonVectors(unittest.TestCase):
    def test_outbound_authority_citations(self):
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>Research Paper on AI Retrieval</title></head>
        <body>
            <h1>Understanding LLM Retrieval Dynamics</h1>
            <p>According to research published on <a href="https://doi.org/10.1145/123456">ACM Digital Library</a> and detailed on <a href="https://arxiv.org/abs/2311.09735">arXiv</a>, citing authoritative primary sources increases generative engine visibility by 115% because models prioritize verified evidence.</p>
        </body>
        </html>
        """
        parser = GEODOMParser(base_domain="example.com")
        parser.feed(html)
        self.assertEqual(len(parser.outbound_citations), 2)
        self.assertTrue(any("doi.org" in c for c in parser.outbound_citations))
        self.assertTrue(any("arxiv.org" in c for c in parser.outbound_citations))

    def test_causal_mechanisms_and_statistics(self):
        # Page with causal depth and statistics
        good_html = """
        <!DOCTYPE html>
        <html>
        <head><title>High Performance Cloud Infrastructure</title></head>
        <body>
            <h1>Architecture Overview</h1>
            <p>Our distributed caching engine improves throughput by 85% because it eliminates redundant database roundtrips, therefore reducing latency from 120ms to 18ms. This mechanism allows high-concurrency workloads to scale smoothly.</p>
        </body>
        </html>
        """
        inv = {
            "site": "https://example.com",
            "pages": [{"url": "https://example.com/article", "status": 200, "page_type": "article", "html": good_html}],
        }
        res = audit("https://example.com", "example.com", inv)
        # Should not flag MISSING_IN_DEPTH_MECHANISMS
        finding_ids = [f["cause_id"] for f in res.get("findings", [])]
        self.assertNotIn("MISSING_IN_DEPTH_MECHANISMS", finding_ids)

    def test_missing_causal_depth_flagged(self):
        # Shallow marketing copy with no causal conjunctions
        shallow_html = """
        <!DOCTYPE html>
        <html>
        <head><title>Best Solutions Ever</title></head>
        <body>
            <h1>We Are The Best</h1>
            <p>Welcome to our world-class enterprise platform. We deliver premium value and unmatched customer satisfaction for your business operations across the globe.</p>
        </body>
        </html>
        """
        inv = {
            "site": "https://example.com",
            "pages": [
                {"url": "https://example.com/pricing", "status": 200, "page_type": "pricing", "html": shallow_html}
            ],
        }
        res = audit("https://example.com", "example.com", inv)
        finding_ids = [f["cause_id"] for f in res.get("findings", [])]
        self.assertIn("MISSING_IN_DEPTH_MECHANISMS", finding_ids)

    def test_author_credentials_detection(self):
        html_with_author = """
        <!DOCTYPE html>
        <html>
        <head><title>Cardiovascular Study</title></head>
        <body>
            <h1>Lipid Optimization Guide</h1>
            <p class="author">Written by Dr. Sarah Jenkins, MD, PhD</p>
            <p>Maintaining optimal LDL cholesterol reduces arterial plaque accumulation because low apolipoprotein B concentrations prevent endothelial infiltration, resulting in 40% lower cardiovascular events.</p>
        </body>
        </html>
        """
        inv = {
            "site": "https://example.com",
            "pages": [
                {"url": "https://example.com/article", "status": 200, "page_type": "article", "html": html_with_author}
            ],
        }
        res = audit("https://example.com", "example.com", inv)
        rec_ids = [r["id"] for r in res.get("recommendations", [])]
        # Should NOT recommend adding author credentials since they are present
        self.assertNotIn("PROACTIVE.GEO.AUTHOR_CREDENTIALS.001", rec_ids)


if __name__ == "__main__":
    unittest.main()

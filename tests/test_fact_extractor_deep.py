import sys
import unittest

sys.path.insert(0, "src/skills/engagement-context-audit/scripts")
import fact_extractor


class TestFactExtractorDeep(unittest.TestCase):
    def test_email_extraction(self):
        html = "<div>Contact support at support@brandcorp.com or sales at sales@brandcorp.org for inquiries.</div>"
        emails = [m.group(0) for m in fact_extractor.EMAIL_PATTERN.finditer(html)]
        self.assertIn("support@brandcorp.com", emails)
        self.assertIn("sales@brandcorp.org", emails)

    def test_phone_extraction(self):
        text = "Call +1 (555) 123-4567 or international 415-555-0199."
        phones = [m.group(0) for m in fact_extractor.PHONE_PATTERN.finditer(text)]
        self.assertTrue(len(phones) >= 1)

    def test_price_pattern_matching(self):
        text = "Starter: $49/mo, Enterprise: €199/mo, India: ₹1,499."
        matches = [m.group(0) for m in fact_extractor.PRICE_PATTERN.finditer(text)]
        self.assertTrue(len(matches) >= 3)

    def test_currency_and_interval(self):
        self.assertEqual(fact_extractor.extract_currency("$49"), "USD")
        self.assertEqual(fact_extractor.extract_currency("€99"), "EUR")
        self.assertEqual(fact_extractor.extract_currency("£50"), "GBP")
        self.assertEqual(fact_extractor.extract_currency("₹999"), "INR")
        self.assertEqual(fact_extractor.extract_interval("Billed monthly"), "month")
        self.assertEqual(fact_extractor.extract_interval("Billed annually"), "year")

    def test_freshness_analyzer_dom(self):
        html = "<html><head><title>Test Page</title></head><body><h1>Main Heading</h1><p>Body text</p></body></html>"
        analyzer = fact_extractor.FreshnessAnalyzer()
        analyzer.feed(html)
        self.assertIn("Main Heading", analyzer.headings[0][1])


if __name__ == "__main__":
    unittest.main()

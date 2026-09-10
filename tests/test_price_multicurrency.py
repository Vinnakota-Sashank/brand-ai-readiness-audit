import os
import sys
import unittest

SCRIPT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../src/skills/fact-consistency-audit/scripts"))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from fact_consistency_check import extract_currency, extract_interval, extract_scoped_facts, normalize_price_str


class TestMultiCurrencyAndIntervals(unittest.TestCase):
    def test_currency_extraction(self):
        self.assertEqual(extract_currency("$49.99"), "USD")
        self.assertEqual(extract_currency("USD 100"), "USD")
        self.assertEqual(extract_currency("€1.499,00"), "EUR")
        self.assertEqual(extract_currency("49,99 EUR"), "EUR")
        self.assertEqual(extract_currency("£25.50"), "GBP")
        self.assertEqual(extract_currency("GBP 500"), "GBP")
        self.assertEqual(extract_currency("₹4,999"), "INR")
        self.assertEqual(extract_currency("Rs. 1500"), "INR")
        self.assertEqual(extract_currency("INR 2500"), "INR")
        self.assertEqual(extract_currency("¥15,000"), "JPY")
        self.assertEqual(extract_currency("R$ 199,00"), "BRL")
        self.assertEqual(extract_currency("AED 350"), "AED")
        self.assertEqual(extract_currency("CAD 89.00"), "CAD")
        self.assertEqual(extract_currency("AUD 120.00"), "AUD")

    def test_interval_extraction(self):
        self.assertEqual(extract_interval("Starting at $49/mo"), "month")
        self.assertEqual(extract_interval("$99 per month"), "month")
        self.assertEqual(extract_interval("$15 per user/mo"), "month")
        self.assertEqual(extract_interval("Billed monthly at $29"), "month")
        self.assertEqual(extract_interval("$499/yr"), "year")
        self.assertEqual(extract_interval("$499 per year"), "year")
        self.assertEqual(extract_interval("Billed annually at $399"), "year")
        self.assertEqual(extract_interval("$25/wk"), "week")
        self.assertEqual(extract_interval("$5 per day"), "day")
        self.assertEqual(extract_interval("One-time lifetime payment of $299"), "one_time")

    def test_normalize_price_str(self):
        self.assertEqual(normalize_price_str("$49.99"), "49.99")
        self.assertEqual(normalize_price_str("1,250.50"), "1250.50")
        self.assertEqual(normalize_price_str("1.499,00"), "1499.00")
        self.assertEqual(normalize_price_str("49,99"), "49.99")
        self.assertEqual(normalize_price_str("₹5,499"), "5499.00")
        self.assertEqual(normalize_price_str("15000"), "15000.00")

    def test_extract_scoped_facts_multicurrency(self):
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>Enterprise Pricing</title></head>
        <body>
            <h2>Pro Plan</h2>
            <p>Our Pro Plan starts at €1.499,00 / month for up to 10 team members.</p>
            <h2>Starter Plan</h2>
            <p>Starter Plan is available for ₹4,999 / mo in India.</p>
        </body>
        </html>
        """
        facts = extract_scoped_facts(html, "https://example.com/pricing")
        scoped_prices = facts.get("scoped_prices", [])
        self.assertTrue(len(scoped_prices) >= 2)

        currencies = {sp["currency"] for sp in scoped_prices}
        self.assertIn("EUR", currencies)
        self.assertIn("INR", currencies)


if __name__ == "__main__":
    unittest.main()

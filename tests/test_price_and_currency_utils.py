import sys
import unittest

sys.path.insert(0, "skills/fact-consistency-audit/scripts")
import fact_consistency_check


class TestPriceAndCurrencyUtils(unittest.TestCase):
    def test_currency_symbol_extraction(self):
        test_cases = [
            ("$49.99", "USD"),
            ("€120", "EUR"),
            ("£85.50", "GBP"),
            ("₹1,499", "INR"),
            ("USD 99", "USD"),
            ("EUR 45", "EUR"),
            ("INR 500", "INR"),
        ]
        for raw, expected in test_cases:
            self.assertEqual(fact_consistency_check.extract_currency(raw), expected, f"Failed on {raw}")

    def test_price_string_normalization(self):
        self.assertEqual(fact_consistency_check.normalize_price_str("49", "USD"), "49.00")
        self.assertEqual(fact_consistency_check.normalize_price_str("1,299.50", "USD"), "1299.50")
        self.assertEqual(fact_consistency_check.normalize_price_str("0", "USD"), "0.00")
        self.assertIsNone(fact_consistency_check.normalize_price_str("invalid", "USD"))

    def test_interval_extraction(self):
        self.assertEqual(fact_consistency_check.extract_interval("Only $49/mo for pro plan"), "month")
        self.assertEqual(fact_consistency_check.extract_interval("Billed annually at $490/yr"), "year")
        self.assertEqual(fact_consistency_check.extract_interval("One time purchase of $299"), "one_time")

    def test_utility_heading_filtering(self):
        # Utility headings must NOT be treated as product entity names
        self.assertFalse(fact_consistency_check.is_valid_product_entity("Pricing"))
        self.assertFalse(fact_consistency_check.is_valid_product_entity("About Us"))
        self.assertFalse(fact_consistency_check.is_valid_product_entity("Privacy Policy"))
        self.assertFalse(fact_consistency_check.is_valid_product_entity("Frequently Asked Questions"))

        # Genuine product names should pass
        self.assertTrue(fact_consistency_check.is_valid_product_entity("Enterprise Cloud Suite Pro"))

    def test_phone_number_extraction(self):
        text = "Call our sales team at +1 (800) 555-0199 or support at 415-555-2671."
        matches = list(fact_consistency_check.PHONE_PATTERN.finditer(text))
        self.assertTrue(len(matches) >= 1)


if __name__ == "__main__":
    unittest.main()

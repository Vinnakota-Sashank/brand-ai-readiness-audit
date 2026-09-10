import os
import sys
import unittest

script_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../src/skills/audit-orchestrator/scripts"))
sys.path.insert(0, script_dir)

import safe_fetch


class TestSafeFetchSecurity(unittest.TestCase):
    def test_block_ipv4_mapped_ipv6(self):
        status, _, _, err = safe_fetch.safe_fetch("http://[::ffff:127.0.0.1]/")
        self.assertIsNone(status)
        self.assertIn("blocked network", err)

        status, _, _, err = safe_fetch.safe_fetch("http://[::ffff:10.0.0.1]/")
        self.assertIsNone(status)
        self.assertIn("blocked network", err)

        status, _, _, err = safe_fetch.safe_fetch("http://127.0.0.1/")
        self.assertIsNone(status)
        self.assertIn("blocked network", err)


if __name__ == "__main__":
    unittest.main()

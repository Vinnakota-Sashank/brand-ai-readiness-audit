import sys
import unittest

sys.path.insert(0, "skills/audit-orchestrator/scripts")
import safe_fetch


class TestSafeFetchUnit(unittest.TestCase):
    def test_blocked_private_ipv4(self):
        private_ips = ["10.0.0.1", "10.255.255.255", "172.16.0.1", "172.31.255.255", "192.168.0.1", "192.168.1.254"]
        for ip in private_ips:
            safe, reason, _ = safe_fetch._is_safe_host(ip)
            self.assertFalse(safe, f"IP {ip} should be blocked")
            self.assertIn("blocked network", reason)

    def test_blocked_loopback_and_metadata(self):
        targets = ["127.0.0.1", "127.0.0.2", "localhost", "169.254.169.254", "169.254.0.1", "::1"]
        for t in targets:
            safe, _reason, _ = safe_fetch._is_safe_host(t)
            self.assertFalse(safe, f"Target {t} should be blocked")

    def test_blocked_ipv4_mapped_ipv6(self):
        mapped = ["::ffff:127.0.0.1", "::ffff:169.254.169.254", "::ffff:10.0.0.1", "::ffff:192.168.1.1"]
        for ip in mapped:
            safe, _reason, _ = safe_fetch._is_safe_host(ip)
            self.assertFalse(safe, f"Mapped IP {ip} should be blocked")

    def test_malformed_hostnames(self):
        malformed = ["", " ", "invalid host with spaces", "target\nnewline", "target\r\n"]
        for h in malformed:
            safe, _reason, _ = safe_fetch._is_safe_host(h)
            self.assertFalse(safe, f"Malformed host '{h}' should fail safety check")

    def test_disallowed_protocols(self):
        url = "file:///etc/passwd"
        status, _content, _, err = safe_fetch.safe_fetch(url)
        self.assertIn(status, [0, None])
        self.assertIn("Disallowed scheme", err)

    def test_safe_public_resolution(self):
        safe, _reason, safe_ips = safe_fetch._is_safe_host("8.8.8.8")
        self.assertTrue(safe)
        self.assertTrue(len(safe_ips) > 0)


if __name__ == "__main__":
    unittest.main()

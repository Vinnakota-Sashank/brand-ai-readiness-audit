import json
import subprocess
import unittest


class TestSchemaEdgeCases(unittest.TestCase):
    def setUp(self):
        self.val_script = "src/skills/audit-orchestrator/scripts/validate_report.py"

    def test_reject_extra_root_properties(self):
        # additionalProperties: false at root level
        bad_report = {
            "site": "https://example.com",
            "audited_at": "2026-09-01T12:00:00Z",
            "audit_status": "complete",
            "summary": {"total_findings": 0, "critical": 0, "high": 0, "medium": 0, "low": 0},
            "findings": [],
            "proactive_actions": [],
            "unexpected_root_field": "illegal",
        }
        res = subprocess.run(
            ["python3", self.val_script, "-"], input=json.dumps(bad_report), check=False, capture_output=True, text=True
        )
        self.assertNotEqual(res.returncode, 0)

    def test_reject_negative_summary_counts(self):
        bad_report = {
            "site": "https://example.com",
            "audited_at": "2026-09-01T12:00:00Z",
            "audit_status": "complete",
            "summary": {"total_findings": -1, "critical": 0, "high": 0, "medium": 0, "low": 0},
            "findings": [],
        }
        res = subprocess.run(
            ["python3", self.val_script, "-"], input=json.dumps(bad_report), check=False, capture_output=True, text=True
        )
        self.assertNotEqual(res.returncode, 0)

    def test_reject_invalid_date_format(self):
        bad_report = {
            "site": "https://example.com",
            "audited_at": "yesterday at 3pm",  # Not ISO date-time
            "audit_status": "complete",
            "summary": {"total_findings": 0, "critical": 0, "high": 0, "medium": 0, "low": 0},
            "findings": [],
        }
        res = subprocess.run(
            ["python3", self.val_script, "-"], input=json.dumps(bad_report), check=False, capture_output=True, text=True
        )
        self.assertNotEqual(res.returncode, 0)

    def test_accept_null_creative_fix(self):
        # technical_fix can be string and creative_fix can be null or string
        valid_report = {
            "site": "https://example.com",
            "audited_at": "2026-09-01T12:00:00Z",
            "audit_status": "complete",
            "summary": {"total_findings": 1, "critical": 0, "high": 1, "medium": 0, "low": 0},
            "findings": [
                {
                    "id": "f-1",
                    "title": "Robots Block",
                    "severity": "high",
                    "category": "discoverability",
                    "root_cause": "Blocked in robots.txt",
                    "evidence": {
                        "summary": "Blocked",
                        "scope": "robots.txt",
                        "sources": [
                            {"url": "https://example.com/robots.txt", "type": "robots_txt", "observation": "Blocked"}
                        ],
                    },
                    "suggested_action": {
                        "summary": "Fix",
                        "priority": "high",
                        "technical_fix": "Add Allow: /",
                        "creative_fix": None,
                        "verification": "Verify",
                    },
                }
            ],
            "proactive_actions": [],
        }
        res = subprocess.run(
            ["python3", self.val_script, "-"],
            input=json.dumps(valid_report),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)

    def test_reject_unquoted_or_malformed_json_input(self):
        malformed_json = "{ site: 'example.com', unquoted_key: 123 }"
        res = subprocess.run(
            ["python3", self.val_script, "-"], input=malformed_json, check=False, capture_output=True, text=True
        )
        self.assertNotEqual(res.returncode, 0)


if __name__ == "__main__":
    unittest.main()

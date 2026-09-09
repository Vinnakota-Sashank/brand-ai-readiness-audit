"""Unit tests for evidence-gated report assembly, deduplication, and priority ranking."""
import unittest
import json
from pathlib import Path
from assemble_report import assemble, verify_evidence, sort_tasks, plan, validate_report

ROOT = Path(__file__).resolve().parents[1]
CHECKS = json.loads((ROOT / "skills/audit-orchestrator/references/checks.json").read_text(encoding="utf-8"))


class TestAssembleReport(unittest.TestCase):
    def setUp(self):
        self.site = "https://example.com"
        self.sample_record = {
            "artifact": "homepage_html",
            "url": "https://example.com",
            "text": "<html><head><title>Example</title></head><body><h1>Example Domain</h1><p>Our organic cold-pressed oil is Rs 850 for 500ml.</p></body></html>",
            "status": 200,
        }
        self.records = [self.sample_record]
        self.coverage = {
            "observed": ["A1", "A2", "N1", "N2", "EC1"],
            "blocked": [],
            "not_applicable": [],
        }

    def test_valid_candidate_assembled_successfully(self):
        """A grounded candidate finding with an exact quote must pass evidence gating and produce a valid report."""
        candidate = {
            "check_id": "A1",
            "actual_band": "S4",
            "finding_kind": "confirmed_problem",
            "collection_complete_for_scope": True,
            "scope": "https://example.com/robots.txt",
            "severity_reason": "Effective retrieval block",
            "difficulty": 2,
            "difficulty_reason": "Update robots.txt to allow AI search bots",
            "evidence_refs": [
                {
                    "artifact": "homepage_html",
                    "locator": "text",
                    "quote": "Example Domain",
                }
            ],
            "suggested_action": {
                "summary": "Allow AI search bots in robots.txt",
                "priority": "critical",
            },
        }
        report = assemble(self.site, [candidate], self.records, CHECKS, self.coverage)
        self.assertEqual(report["site"], self.site)
        self.assertEqual(len(report["findings"]), 1)
        self.assertEqual(report["findings"][0]["severity"], "critical")
        self.assertEqual(report["findings"][0]["priority_index"], 5 * 4 + (6 - 2))  # 20 + 4 = 24
        self.assertEqual(len(report["dropped_findings"]), 0)

    def test_fabricated_quote_rejected_by_evidence_gate(self):
        """A candidate with a quote not present in the artifact must be dropped."""
        candidate = {
            "check_id": "A1",
            "actual_band": "S4",
            "finding_kind": "confirmed_problem",
            "collection_complete_for_scope": True,
            "scope": "https://example.com/robots.txt",
            "severity_reason": "Fabricated finding",
            "difficulty": 2,
            "difficulty_reason": "Fix",
            "evidence_refs": [
                {
                    "artifact": "homepage_html",
                    "locator": "text",
                    "quote": "This text definitely does not exist in the HTML at all.",
                }
            ],
        }
        report = assemble(self.site, [candidate], self.records, CHECKS, self.coverage)
        self.assertEqual(len(report["findings"]), 0)
        self.assertEqual(len(report["dropped_findings"]), 1)
        self.assertIn("Quote not found", report["dropped_findings"][0]["reason"])

    def test_cause_scoped_deduplication(self):
        """Candidates with identical root cause and scope must be merged into one finding."""
        c1 = {
            "check_id": "A1",
            "actual_band": "S4",
            "finding_kind": "confirmed_problem",
            "collection_complete_for_scope": True,
            "scope": "https://example.com",
            "root_cause_key": "robots_ai_crawl_block",
            "root_cause_reason": "Robots file disallows all automated user-agents",
            "severity_reason": "Retrieval block",
            "difficulty": 2,
            "difficulty_reason": "Edit robots.txt",
            "evidence_refs": [{"artifact": "homepage_html", "locator": "text", "quote": "Example"}],
        }
        c2 = {
            "check_id": "A2",
            "actual_band": "S4",
            "finding_kind": "confirmed_problem",
            "collection_complete_for_scope": True,
            "scope": "https://example.com",
            "root_cause_key": "robots_ai_crawl_block",
            "root_cause_reason": "Robots file disallows all automated user-agents",
            "severity_reason": "Retrieval block",
            "difficulty": 2,
            "difficulty_reason": "Edit robots.txt",
            "evidence_refs": [{"artifact": "homepage_html", "locator": "text", "quote": "Domain"}],
        }
        report = assemble(self.site, [c1, c2], self.records, CHECKS, self.coverage)
        self.assertEqual(len(report["findings"]), 1)
        self.assertIn("A1", report["findings"][0]["related_check_ids"])
        self.assertIn("A2", report["findings"][0]["related_check_ids"])

    def test_priority_ranking_formula(self):
        """Priority index must follow 5 * severity + (6 - difficulty)."""
        item = {"actual_band": "S3", "difficulty": 1, "finding_kind": "confirmed_problem"}
        planned = plan(item, {"title": "Test Finding"})
        self.assertEqual(planned["priority_index"], 5 * 3 + (6 - 1))  # 15 + 5 = 20

    def test_dependency_sorting_no_cycles(self):
        """Dependent tasks must be sorted after their prerequisites."""
        task_a = {
            "id": "task_a",
            "actual_band": "S4",
            "queue": "confirmed",
            "depends_on": [],
            "scope": "global",
        }
        task_b = {
            "id": "task_b",
            "actual_band": "S3",
            "queue": "confirmed",
            "depends_on": ["task_a"],
            "scope": "global",
        }
        sorted_tasks = sort_tasks([task_b, task_a])
        self.assertEqual([t["id"] for t in sorted_tasks], ["task_a", "task_b"])

    def test_dependency_cycle_detection(self):
        """Cyclic dependencies must raise a ValueError."""
        task_a = {"id": "task_a", "actual_band": "S4", "queue": "confirmed", "depends_on": ["task_b"], "scope": "g"}
        task_b = {"id": "task_b", "actual_band": "S3", "queue": "confirmed", "depends_on": ["task_a"], "scope": "g"}
        with self.assertRaises(ValueError):
            sort_tasks([task_a, task_b])


if __name__ == "__main__":
    unittest.main()

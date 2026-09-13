"""Tests for EvidenceRegistry and evidence provenance."""
import hashlib
import json
import pytest
from evidence import EvidenceRegistry, hash_value, redact_sensitive


def test_evidence_hash_deterministic():
    data1 = {"b": 2, "a": 1}
    data2 = {"a": 1, "b": 2}
    assert hash_value(data1) == hash_value(data2)


def test_evidence_redaction():
    url = "https://example.com/api?token=secret123&user=admin"
    redacted = redact_sensitive(url)
    assert "secret123" not in redacted
    assert "[REDACTED]" in redacted
    assert "user=admin" in redacted


def test_evidence_deduplication_and_occurrences():
    registry = EvidenceRegistry()
    eid1 = registry.add(
        value="Disallow: /checkout",
        page_id="https://example.com/robots.txt",
        channel="robots",
        locator="line 12",
        context="A1",
    )
    eid2 = registry.add(
        value="Disallow: /checkout",
        page_id="https://example.com/other-robots.txt",
        channel="robots",
        locator="line 5",
        context="A1",
    )
    assert eid1 == eid2
    item = registry.get(eid1)
    assert item is not None
    assert len(item["occurrences"]) == 2
    assert item["occurrences"][0]["page_id"] == "https://example.com/robots.txt"
    assert item["occurrences"][1]["page_id"] == "https://example.com/other-robots.txt"


def test_evidence_total_sha256():
    registry = EvidenceRegistry()
    assert registry.total_sha256() == hashlib.sha256(b"").hexdigest()
    registry.add("Evidence 1", page_id="https://example.com")
    h1 = registry.total_sha256()
    assert len(h1) == 64
    registry.add("Evidence 2", page_id="https://example.com")
    h2 = registry.total_sha256()
    assert h1 != h2

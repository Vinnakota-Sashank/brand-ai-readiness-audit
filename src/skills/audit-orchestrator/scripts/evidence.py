"""Evidence Integrity and Provenance Layer.

Provides cryptographic hashing, deduplication, sensitive data redaction,
and occurrence tracking for audit evidence across all specialist sensors.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, List, Optional


def hash_value(value: Any) -> str:
    """Compute deterministic SHA-256 hex digest for any JSON-serializable value or bytes."""
    if isinstance(value, bytes):
        raw = value
    elif isinstance(value, str):
        raw = value.encode("utf-8")
    else:
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def redact_sensitive(value: Any) -> Any:
    """Redact sensitive query params and tokens from strings or nested collections."""
    if isinstance(value, dict):
        return {k: redact_sensitive(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_sensitive(v) for v in value]
    if isinstance(value, str):
        # Redact common secrets in query strings or auth headers
        pattern = r"([?&](?:access_token|token|secret|password|signature|session|api[_-]?key)=)[^&#\s]*"
        return re.sub(pattern, r"\1[REDACTED]", value, flags=re.IGNORECASE)
    return value


class EvidenceRegistry:
    """Central registry tracking evidence items with SHA-256 provenance and occurrence chains."""

    def __init__(self) -> None:
        self.items: Dict[str, Dict[str, Any]] = {}
        self._key_to_id: Dict[str, str] = {}
        self._id_counter: int = 0

    def add(
        self,
        value: Any,
        page_id: str = "",
        channel: str = "http",
        locator: str = "",
        capture_hash: str = "",
        context: str = "",
        kind: str = "text",
    ) -> str:
        """Register an evidence item or append an occurrence if already registered.

        Args:
            value: The evidence payload (text, dict, list, observation).
            page_id: URL or identifier of the page where evidence was observed.
            channel: Observation channel ('http', 'source_body', 'headers', 'jsonld', 'robots', etc.).
            locator: CSS selector, XPath, JSON path, or line reference.
            capture_hash: Optional SHA-256 of the raw network capture/document.
            context: Context label or surrounding text snippet.
            kind: Content kind ('text', 'structured_data', 'header', 'status_code', 'directive').

        Returns:
            Unique evidence ID (e.g. 'E000001').
        """
        # Group similar body channels for conservative deduplication
        channel_group = "body" if channel in {"source_body", "rendered_body"} else channel
        dedup_key = hash_value([value, kind, context, channel_group])

        occurrence = {
            "page_id": page_id,
            "channel": channel,
            "locator": locator,
            "capture_sha256": capture_hash,
            "context": context,
        }

        if dedup_key in self._key_to_id:
            eid = self._key_to_id[dedup_key]
            if occurrence not in self.items[eid]["occurrences"]:
                self.items[eid]["occurrences"].append(occurrence)
            return eid

        self._id_counter += 1
        eid = f"E{self._id_counter:06d}"
        self._key_to_id[dedup_key] = eid

        displayed = redact_sensitive(value)
        entry: Dict[str, Any] = {
            "id": eid,
            "value": displayed,
            "kind": kind,
            "sha256": hash_value(displayed),
            "occurrences": [occurrence],
        }
        if displayed != value:
            entry["redaction"] = "Sensitive query values or tokens withheld; original sanitized."

        self.items[eid] = entry
        return eid

    def get(self, evidence_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve evidence entry by ID."""
        return self.items.get(evidence_id)

    def total_sha256(self) -> str:
        """Compute an overall aggregate SHA-256 fingerprint of all registered evidence."""
        if not self.items:
            return hashlib.sha256(b"").hexdigest()
        serialized = json.dumps(self.items, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize all registry items to a dictionary."""
        return {
            "total_items": len(self.items),
            "evidence_sha256": self.total_sha256(),
            "items": self.items,
        }


if __name__ == "__main__":
    registry = EvidenceRegistry()
    eid1 = registry.add("Sample robots.txt Disallow: /admin", page_id="https://example.com", channel="robots")
    eid2 = registry.add("Sample robots.txt Disallow: /admin", page_id="https://example.com/other", channel="robots")
    assert eid1 == eid2, "Identical evidence should deduplicate"
    assert len(registry.items[eid1]["occurrences"]) == 2, "Should track multiple occurrences"
    print(f"Self-test passed: {eid1}, aggregate hash: {registry.total_sha256()[:16]}...")

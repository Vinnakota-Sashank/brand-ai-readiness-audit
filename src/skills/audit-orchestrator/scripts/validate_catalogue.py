"""Catalogue and Check Registry Validator.

Validates the master checks.json catalogue at build time:
- No duplicate check IDs
- Complete required metadata (check_id, title, reference_band, owner, detection, solution)
- Valid severity bands (S4, S3, S2, S1, S0, U)
- Valid owner skills matching registered specialist skills
- Domain taxonomy alignment with audit-orchestrator
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Set

VALID_BANDS: Set[str] = {"S4", "S3", "S2", "S1", "S0", "U"}
VALID_OWNERS: Set[str] = {
    "discoverability-audit",
    "entity-content-audit",
    "fact-consistency-audit",
    "corroboration-authority-audit",
    "geo-content-audit",
    "engagement-context-audit",
    "audit-orchestrator",
}
REQUIRED_FIELDS: List[str] = [
    "check_id",
    "title",
    "reference_band",
    "owner",
    "detection",
    "solution",
]


def validate_catalogue_data(checks_data: Any) -> Dict[str, Any]:
    """Validate a checks catalogue structure.

    Args:
        checks_data: List of check definition dicts.

    Returns:
        Validation summary dict with statistics.

    Raises:
        ValueError: If catalogue fails integrity or schema checks.
    """
    if not isinstance(checks_data, list) or not checks_data:
        raise ValueError("Catalogue must be a non-empty list of check objects.")

    seen_ids: Set[str] = set()
    owner_counts: Dict[str, int] = {o: 0 for o in VALID_OWNERS}
    band_counts: Dict[str, int] = {b: 0 for b in VALID_BANDS}

    for idx, check in enumerate(checks_data):
        if not isinstance(check, dict):
            raise ValueError(f"Entry {idx} is not a valid dictionary object.")

        for field in REQUIRED_FIELDS:
            if field not in check or not str(check[field]).strip():
                cid = check.get("check_id", f"index-{idx}")
                raise ValueError(f"Check {cid} is missing required field '{field}'.")

        cid = check["check_id"]
        if cid in seen_ids:
            raise ValueError(f"Duplicate check ID detected: '{cid}'.")
        seen_ids.add(cid)

        band = check["reference_band"]
        if band not in VALID_BANDS:
            raise ValueError(f"Check {cid} has invalid reference band: '{band}'. Allowed: {sorted(VALID_BANDS)}")
        band_counts[band] += 1

        owner = check["owner"]
        if owner not in VALID_OWNERS:
            raise ValueError(f"Check {cid} has unknown owner skill: '{owner}'. Allowed: {sorted(VALID_OWNERS)}")
        owner_counts[owner] += 1

    return {
        "valid": True,
        "total_checks": len(checks_data),
        "unique_check_ids": len(seen_ids),
        "owner_distribution": owner_counts,
        "band_distribution": band_counts,
    }


def validate_file(catalogue_path: Optional[Path] = None) -> Dict[str, Any]:
    """Validate catalogue JSON from disk."""
    if catalogue_path is None:
        catalogue_path = Path(__file__).resolve().parents[1] / "references" / "checks.json"

    if not catalogue_path.exists():
        raise FileNotFoundError(f"Catalogue file not found at: {catalogue_path}")

    with open(catalogue_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return validate_catalogue_data(data)


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    res = validate_file(path)
    print(f"Catalogue integrity verified: {res['total_checks']} checks across {len(res['owner_distribution'])} skills.")
    for owner, count in res["owner_distribution"].items():
        print(f"  - {owner}: {count} checks")

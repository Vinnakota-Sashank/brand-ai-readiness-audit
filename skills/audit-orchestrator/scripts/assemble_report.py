"""Evidence-gated report assembly for the unified marketplace."""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

LABELS = {"S4": "critical", "S3": "high", "S2": "medium", "S1": "low"}
DEFAULT_CATEGORY = {
    "discoverability-audit": "discoverability",
    "entity-content-audit": "entity_content",
    "fact-consistency-audit": "fact_consistency",
    "corroboration-authority-audit": "corroboration",
    "geo-content-audit": "geo_content",
    "engagement-context-audit": "engagement",
}


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def plan(item, check):
    """Normalize a candidate finding with difficulty and priority ranking."""
    item.setdefault("depends_on", [])
    item.setdefault("related_check_ids", [])
    item.setdefault("root_cause_key", item.get("check_id"))
    item.setdefault("root_cause_reason", f"Observed failure for check {item.get('check_id')}")
    item.setdefault("queue", "confirmed" if item.get("finding_kind") == "confirmed_problem" else "advisory")
    item.setdefault("remedy_readiness", "ready" if item.get("difficulty") else "needs_context")
    if item.get("difficulty") and item["remedy_readiness"] == "ready":
        band_val = int(item["actual_band"][1]) if item.get("actual_band", "").startswith("S") else 1
        item["priority_index"] = 5 * band_val + (6 - item["difficulty"])
    item.setdefault("title", check.get("title", item.get("check_id", "Finding")))
    return item


def validate_schema(value, schema, path="$"):
    """Strict implementation of Draft-07 keywords used by our report schema."""
    known = {
        "$schema", "$id", "title", "description", "type", "required", "properties", "items", "enum",
        "minimum", "maximum", "minLength", "minItems", "additionalProperties", "format",
    }
    unknown = set(schema) - known
    if unknown:
        raise ValueError(f"Unsupported schema keywords: {unknown}")
    typ = schema.get("type")
    types = {
        "object": dict, "array": list, "string": str, "integer": int,
        "number": (int, float), "boolean": bool, "null": type(None),
    }
    if typ:
        if isinstance(typ, list):
            valid_types = tuple(types[t] for t in typ)
            if not isinstance(value, valid_types):
                raise ValueError(f"{path}: expected one of {typ}")
        elif not isinstance(value, types[typ]) or (typ in ("integer", "number") and isinstance(value, bool)):
            raise ValueError(f"{path}: expected {typ}")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"{path}: invalid enum value {value}")
    for k, op in [
        ("minimum", lambda a, b: a >= b),
        ("maximum", lambda a, b: a <= b),
        ("minLength", lambda a, b: len(a) >= b),
        ("minItems", lambda a, b: len(a) >= b),
    ]:
        if k in schema and not op(value, schema[k]):
            raise ValueError(f"{path}: violates {k}")
    if schema.get("format") == "date-time":
        try:
            if datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is None:
                raise ValueError()
        except ValueError:
            raise ValueError(f"{path}: timezone-aware timestamp required")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                raise ValueError(f"{path}: missing required property '{key}'")
        for key, v in value.items():
            if key in schema.get("properties", {}):
                validate_schema(v, schema["properties"][key], path + "." + key)
            elif schema.get("additionalProperties") is False:
                raise ValueError(f"{path}: unexpected property '{key}'")
    if isinstance(value, list) and "items" in schema:
        for i, v in enumerate(value):
            validate_schema(v, schema["items"], path + f"[{i}]")


def verify_evidence(item, artifacts):
    """Verify that cited quotes exist in collected artifacts at cited locators."""
    refs = item.get("evidence_refs", [])
    if not refs:
        raise ValueError("Missing evidence references")
    for ref in refs:
        artifact = artifacts.get(ref.get("artifact"))
        if artifact is None:
            raise ValueError(f"Evidence artifact not found: {ref.get('artifact')}")
        quote = ref.get("quote")
        if not isinstance(quote, str) or not quote or not ref.get("locator"):
            raise ValueError("Exact quote and locator required")
        locator = ref["locator"]
        if locator in ("response body", "response"):
            locator = "text"
        if not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*(?:\[\d+\])?(?:\.[A-Za-z_][A-Za-z_0-9]*(?:\[\d+\])?)*", locator):
            raise ValueError("Unsupported evidence locator grammar")
        selected = artifact
        try:
            for part in locator.split("."):
                m = re.fullmatch(r"([A-Za-z_][A-Za-z_0-9]*)(?:\[(\d+)\])?", part)
                selected = selected[m[1]]
                if m[2] is not None:
                    selected = selected[int(m[2])]
        except (KeyError, TypeError, IndexError):
            raise ValueError("Evidence locator does not resolve")
        haystack = selected if isinstance(selected, str) else json.dumps(selected, ensure_ascii=False)
        if quote not in haystack and json.dumps(quote, ensure_ascii=False)[1:-1] not in haystack:
            if not (locator == "source.canonicals" and all(q in haystack for q in quote.split(" | "))):
                raise ValueError("Quote not found at cited locator")
    if item.get("finding_kind") == "confirmed_problem" and not item.get("collection_complete_for_scope"):
        raise ValueError("Confirmed problem lacks complete evidence for its narrow scope")
    if not item.get("severity_reason") or not item.get("scope"):
        raise ValueError("Scope and activated severity reason required")


def sort_tasks(items):
    """Topologically sort findings by dependency and queue order."""
    queues = {"confirmed": 0, "advisory": 1, "investigation": 2}

    def key(item):
        band = item.get("actual_band", "S1")
        severity = int(band[1]) if band.startswith("S") and band[1:].isdigit() else 1
        d = item.get("difficulty")
        return (
            queues.get(item.get("queue", "confirmed"), 0),
            -severity,
            d if d is not None else 0,
            -len(set(item.get("affected_urls", [item.get("scope", "")]))),
            item.get("id", ""),
        )

    pending = {i["id"]: i for i in items}
    done, output = set(), []
    for item in items:
        for dep in item.get("depends_on", []):
            if dep not in pending:
                raise ValueError("Unknown prerequisite: " + dep)
            if queues.get(pending[dep].get("queue", "confirmed"), 0) > queues.get(item.get("queue", "confirmed"), 0):
                raise ValueError("Unresolved cross-queue prerequisite; move dependent to investigation")
    while pending:
        available = [i for i in pending.values() if set(i.get("depends_on", [])) <= done]
        if not available:
            raise ValueError("Dependency cycle")
        first = min(available, key=key)
        output.append(first)
        done.add(first["id"])
        del pending[first["id"]]
    return output


def assemble(site, candidates, records, checks, coverage=None, browser=None):
    """Assemble verified candidates into a schema-valid Draft-07 audit report."""
    artifacts = {a["artifact"]: a for a in records}
    if browser:
        artifacts.update({a["artifact"]: a for a in browser.get("captures", [])})
    catalogue = {c["check_id"]: c for c in checks}
    observations, dropped, merged = [], [], {}

    for index, raw_item in enumerate(candidates):
        try:
            item = dict(raw_item)
            check = catalogue.get(item.get("check_id"))
            if not check:
                raise ValueError(f"Unknown check_id: {item.get('check_id')}")
            if item.get("actual_band") not in ("S4", "S3", "S2", "S1", "S0", "U"):
                raise ValueError("Invalid actual band")
            if item.get("finding_kind") not in ("confirmed_problem", "advisory", "investigation", "informational_observation"):
                raise ValueError("Unknown finding kind")
            if item["finding_kind"] == "confirmed_problem" and item["actual_band"] in ("S0", "U"):
                raise ValueError("Unassessable/no-change item cannot be a confirmed problem")

            verify_evidence(item, artifacts)
            item = plan(item, check)

            if item["finding_kind"] == "informational_observation" or item["actual_band"] == "S0":
                observations.append(item)
                continue

            ids = sorted(set(item.get("related_check_ids", []) + [item["check_id"]]))
            evidence_key = tuple(sorted((e["artifact"], e["locator"]) for e in item.get("evidence_refs", [])))
            cause = item.get("root_cause_key")
            dedup = (item.get("scope"), item.get("finding_kind"), cause or evidence_key)

            item["related_check_ids"] = ids
            item["id"] = item.get("id") or "F-" + hashlib.sha256(repr(dedup).encode()).hexdigest()[:12]

            if dedup in merged:
                prev = merged[dedup]
                prev["related_check_ids"] = sorted(set(prev["related_check_ids"] + ids))
                prev["evidence_refs"] += [e for e in item.get("evidence_refs", []) if e not in prev["evidence_refs"]]
                curr_band = int(item["actual_band"][1]) if item["actual_band"].startswith("S") else 1
                prev_band = int(prev["actual_band"][1]) if prev["actual_band"].startswith("S") else 1
                if curr_band > prev_band:
                    prev["actual_band"] = item["actual_band"]
                prev["depends_on"] = sorted(set(prev["depends_on"] + item.get("depends_on", [])))
            else:
                merged[dedup] = item
        except (ValueError, KeyError, TypeError) as exc:
            dropped.append(dict(candidate_index=index, check_id=raw_item.get("check_id"), reason=str(exc)))

    sorted_findings = sort_tasks(list(merged.values()))
    schema_findings = []

    for item in sorted_findings:
        band = item.get("actual_band", "S1")
        sev = LABELS.get(band, "low")
        owner_skill = catalogue.get(item["check_id"], {}).get("owner", "discoverability-audit")
        category = DEFAULT_CATEGORY.get(owner_skill, "discoverability")

        sources = []
        for e in item.get("evidence_refs", []):
            art = artifacts.get(e.get("artifact"), {})
            sources.append({
                "url": art.get("url", item.get("scope", site)),
                "type": "html" if "html" in e.get("artifact", "") else "http",
                "observation": f"{e.get('artifact')} at {e.get('locator')}: {e.get('quote', '')[:300]}",
            })

        evidence_obj = {
            "summary": item.get("severity_reason") or f"Issue detected for {item['check_id']}",
            "scope": item.get("scope", site),
            "sources": sources if sources else [{"url": site, "type": "html", "observation": "Direct sensor observation"}],
        }

        sugg_action = item.get("suggested_action", {})
        if isinstance(sugg_action, str):
            sugg_action = {"summary": sugg_action}

        scope = item.get("scope") or site
        check_obj = catalogue.get(item.get("check_id"), {})
        check_title = check_obj.get("title") or item.get("title") or item.get("check_id")
        solution_guide = check_obj.get("solution") or ""

        # Construct dynamic, evidence-grounded dual-track recommendations
        action_summary = sugg_action.get("summary")
        if not action_summary or action_summary.startswith("Remediate check"):
            action_summary = f"Remediate {check_title} for {scope}." + (f" Guidance: {solution_guide}" if solution_guide else "")

        tech_fix = sugg_action.get("technical_fix")
        if not tech_fix or tech_fix.startswith("Update site configuration"):
            tech_fix = f"Implement technical remediation for {check_title} on {scope}. {solution_guide}".strip()

        creative_fix = sugg_action.get("creative_fix")
        if not creative_fix and (check_obj.get("benefit_area") in ("E", "B") or check_obj.get("solution_level") == "E"):
            creative_fix = f"Align on-page copy and content hierarchy on {scope} to reinforce entity clarity and user journey continuity."

        verification = sugg_action.get("verification")
        if not verification or "sensor to confirm resolution" in verification:
            verification = f"Re-evaluate {scope} using {owner_skill} to confirm {check_title} is resolved without regression."

        action_obj = {
            "summary": action_summary,
            "priority": sugg_action.get("priority", sev),
            "technical_fix": tech_fix,
            "creative_fix": creative_fix,
            "verification": verification,
        }

        finding = {
            "id": item["id"],
            "title": item.get("title", f"Finding {item['check_id']}"),
            "severity": sev,
            "category": category,
            "root_cause": item.get("root_cause_reason") or f"Identified root cause for {item['check_id']}",
            "evidence": evidence_obj,
            "suggested_action": action_obj,
            "actual_band": item.get("actual_band", band),
            "priority_index": item.get("priority_index"),
            "related_check_ids": item.get("related_check_ids", [item["check_id"]]),
            "finding_kind": item.get("finding_kind", "confirmed_problem"),
            "queue": item.get("queue", "confirmed"),
            "difficulty": item.get("difficulty"),
            "difficulty_reason": item.get("difficulty_reason"),
        }
        schema_findings.append(finding)

    summary = {
        "total_findings": len(schema_findings),
        "critical": sum(1 for f in schema_findings if f["severity"] == "critical"),
        "high": sum(1 for f in schema_findings if f["severity"] == "high"),
        "medium": sum(1 for f in schema_findings if f["severity"] == "medium"),
        "low": sum(1 for f in schema_findings if f["severity"] == "low"),
    }

    report = {
        "site": site,
        "audited_at": now(),
        "audit_status": "complete",
        "summary": summary,
        "findings": schema_findings,
        "observations": observations,
        "dropped_findings": dropped,
        "coverage": coverage or {"observed": [], "blocked": [], "not_applicable": []},
        "limitations": [
            "An empty findings array is not a pass.",
            "No citation, traffic or conversion uplift is measured.",
            "Recommendations only; no changes were applied to the website."
        ],
    }

    validate_report(report)
    return report


def validate_report(report):
    """Validate report structure against Draft-07 schema gate."""
    schema_path = Path(__file__).resolve().parents[1] / "references/report-schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validate_schema(report, schema)
    if report["summary"]["total_findings"] != len(report["findings"]):
        raise ValueError("Summary total does not equal findings length")
    for sev in ("critical", "high", "medium", "low"):
        if report["summary"].get(sev, 0) != sum(1 for f in report["findings"] if f["severity"] == sev):
            raise ValueError(f"Incorrect severity count for {sev}")
    if len({f["id"] for f in report["findings"]}) != len(report["findings"]):
        raise ValueError("Duplicate finding ID detected")
    return True


if __name__ == "__main__":
    import sys
    validate_report(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")))
    print("Report schema and counts valid")

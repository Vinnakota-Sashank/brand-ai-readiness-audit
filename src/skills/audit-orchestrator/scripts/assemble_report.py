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

# ── 10-Category GEO Scoring Taxonomy (Adobe / Glippy aligned) ──
# Maps each check_id prefix or exact ID to one of the 10 GEO categories.
GEO_CATEGORY_MAP = {
    # 1. Structured Data & Schema
    "structured_data_schema": {
        "name": "Structured Data & Schema",
        "check_ids": ["E1", "E2", "E3", "E4", "E5", "E6", "E7", "N11",
                       "EC6", "SA6", "PP5", "BN4", "ED6", "ME4", "BC6"],
        "weight": 1.2,
        "description": "JSON-LD presence, Schema.org validity, type coverage, and markup correctness",
    },
    # 2. Semantic HTML
    "semantic_html": {
        "name": "Semantic HTML",
        "check_ids": ["H2", "J1", "BN8", "SA8", "SC6", "ED8", "ME7"],
        "weight": 0.9,
        "description": "Heading hierarchy, semantic elements, content-to-markup ratio",
    },
    # 3. Accessibility for Agents
    "accessibility_agents": {
        "name": "Accessibility for Agents",
        "check_ids": ["F1", "F2", "F3", "F4", "F5"],
        "weight": 0.8,
        "description": "Alt text, lang attributes, ARIA landmarks, descriptive link text",
    },
    # 4. Internal Linking
    "internal_linking": {
        "name": "Internal Linking",
        "check_ids": ["D2", "J2", "B4"],
        "weight": 0.8,
        "description": "Sitemap coverage, navigation structure, breadcrumbs, orphan pages",
    },
    # 5. Meta & Discoverability
    "meta_discoverability": {
        "name": "Meta & Discoverability",
        "check_ids": ["A1", "A2", "A3", "A4", "A5", "B1", "B2", "B3", "B5"],
        "weight": 1.3,
        "description": "Robots.txt, canonical URLs, meta robots, redirects, crawler access",
    },
    # 6. Machine Readability
    "machine_readability": {
        "name": "Machine Readability",
        "check_ids": ["C1", "C2", "C3", "C4", "C5"],
        "weight": 1.5,
        "description": "Raw vs. rendered content gap, SSR detection, JS dependency, citation readability",
    },
    # 7. Entity & Authority
    "entity_authority": {
        "name": "Entity & Authority",
        "check_ids": ["BC1", "BC2", "BC3", "BC4", "BC5", "BC7", "BC8",
                       "N15", "PP7", "SA2", "PROFILE_DATA_MISMATCH",
                       "UNDECLARED_PROFILE_FOUND", "SC5"],
        "weight": 1.0,
        "description": "Organization identity, brand consistency, author credentials, authority signals",
    },
    # 8. Citability & Answer-Readiness
    "citability_answer_readiness": {
        "name": "Citability & Answer-Readiness",
        "check_ids": ["N1", "N2", "N3", "N4", "N5", "N6", "N7", "N8",
                       "N9", "N10", "N12", "N13", "N14",
                       "EC5", "PP1", "PP3", "BN1", "BN3", "BN5", "BN6",
                       "BN7", "SC4", "ED1", "ED4", "ME6",
                       "SA1", "SA3", "SA4"],
        "weight": 1.1,
        "description": "Self-contained answers, FAQ coverage, content depth, causal explanations, fluency",
    },
    # 9. Performance & Crawlability
    "performance_crawlability": {
        "name": "Performance & Crawlability",
        "check_ids": ["H1", "H3", "I1", "I2", "J9", "J10"],
        "weight": 0.7,
        "description": "Page latency, DOM size, render-blocking scripts, deep link stability",
    },
    # 10. Agent Interactivity
    "agent_interactivity": {
        "name": "Agent Interactivity",
        "check_ids": ["G1", "G2"],
        "weight": 0.7,
        "description": "llms.txt manifest, WebMCP compliance, declarative API endpoints",
    },
}


def compute_geo_scores(findings, coverage_data=None):
    """Compute per-category GEO scores (0-100) and overall grade.

    Scoring logic:
    - Start at 100 for each category.
    - Deduct points based on finding severity:
      critical=-40, high=-25, medium=-15, low=-5
    - Bonus for coverage: +10 if category checks were explicitly observed.
    - Citation readability directly affects Machine Readability score.
    """
    SEVERITY_DEDUCTION = {"critical": 40, "high": 25, "medium": 15, "low": 5}
    GRADE_THRESHOLDS = [
        (90, "A"), (80, "B"), (70, "C"), (60, "D"), (50, "E"), (0, "F")
    ]

    # Build reverse map: check_id -> category_key
    check_to_category = {}
    for cat_key, cat_info in GEO_CATEGORY_MAP.items():
        for cid in cat_info["check_ids"]:
            check_to_category[cid] = cat_key

    # Initialize scores
    scores = {}
    for cat_key, cat_info in GEO_CATEGORY_MAP.items():
        scores[cat_key] = {
            "name": cat_info["name"],
            "score": 100,
            "grade": "A",
            "finding_count": 0,
            "deductions": [],
            "weight": cat_info["weight"],
        }

    # Apply deductions from findings
    for f in findings:
        related_ids = f.get("related_check_ids", [])
        severity = f.get("severity", "low")
        deduction = SEVERITY_DEDUCTION.get(severity, 5)
        matched_categories = set()

        for cid in related_ids:
            cat_key = check_to_category.get(cid)
            if cat_key and cat_key not in matched_categories:
                matched_categories.add(cat_key)
                scores[cat_key]["score"] = max(0, scores[cat_key]["score"] - deduction)
                scores[cat_key]["finding_count"] += 1
                scores[cat_key]["deductions"].append(
                    f"-{deduction} ({severity}: {f.get('title', cid)[:60]})"
                )

        # If no category matched, try to match by finding ID pattern
        if not matched_categories:
            fid = f.get("id", "")
            if "CITATION_READABILITY" in fid:
                cat_key = "machine_readability"
                scores[cat_key]["score"] = max(0, scores[cat_key]["score"] - deduction)
                scores[cat_key]["finding_count"] += 1
                scores[cat_key]["deductions"].append(
                    f"-{deduction} ({severity}: {f.get('title', fid)[:60]})"
                )

    # Apply citation readability directly to Machine Readability score
    if coverage_data:
        cit_pct = coverage_data.get("citation_readability_pct")
        if cit_pct is not None:
            # Scale: 100% readability = no extra deduction, 0% = full penalty
            cr_penalty = max(0, int((100 - cit_pct) * 0.5))
            if cr_penalty > 0:
                scores["machine_readability"]["score"] = max(
                    0, scores["machine_readability"]["score"] - cr_penalty
                )
                scores["machine_readability"]["deductions"].append(
                    f"-{cr_penalty} (citation readability: {cit_pct}%)"
                )

    # Compute grades
    for cat_key in scores:
        score = scores[cat_key]["score"]
        for threshold, grade in GRADE_THRESHOLDS:
            if score >= threshold:
                scores[cat_key]["grade"] = grade
                break

    # Compute weighted overall score
    total_weight = sum(s["weight"] for s in scores.values())
    weighted_sum = sum(s["score"] * s["weight"] for s in scores.values())
    overall_score = round(weighted_sum / total_weight) if total_weight > 0 else 0
    overall_grade = "F"
    for threshold, grade in GRADE_THRESHOLDS:
        if overall_score >= threshold:
            overall_grade = grade
            break

    return {
        "overall_score": overall_score,
        "overall_grade": overall_grade,
        "categories": {
            k: {
                "name": v["name"],
                "score": v["score"],
                "grade": v["grade"],
                "finding_count": v["finding_count"],
            }
            for k, v in scores.items()
        },
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


def assemble(site, candidates, records, checks, coverage=None, browser=None,
             discoverability_coverage=None):
    """Assemble verified candidates into a schema-valid Draft-07 audit report.

    Args:
        discoverability_coverage: Coverage data from the discoverability specialist,
            including citation_readability_pct and missing_words.
    """
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

    # Add Citation Readability metrics to summary (Adobe-competitive)
    if discoverability_coverage:
        cit_pct = discoverability_coverage.get("citation_readability_pct")
        if cit_pct is not None:
            summary["citation_readability_pct"] = cit_pct
            summary["citation_readability_missing_words"] = discoverability_coverage.get("missing_words", 0)
            summary["visible_words_initial_html"] = discoverability_coverage.get("visible_words_initial_html", 0)
            summary["visible_words_rendered"] = discoverability_coverage.get("visible_words_rendered", 0)

    # Compute GEO Category Scores
    geo_scores = compute_geo_scores(schema_findings, discoverability_coverage)

    report = {
        "site": site,
        "audited_at": now(),
        "audit_status": "complete",
        "summary": summary,
        "geo_scores": geo_scores,
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

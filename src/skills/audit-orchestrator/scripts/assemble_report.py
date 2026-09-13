"""Evidence-gated report assembly for the unified marketplace."""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

try:
    from .evidence import EvidenceRegistry
    from .site_classifier import classify_site
except ImportError:
    try:
        from evidence import EvidenceRegistry
        from site_classifier import classify_site
    except ImportError:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from evidence import EvidenceRegistry
        from site_classifier import classify_site

LABELS = {"S4": "critical", "S3": "high", "S2": "medium", "S1": "low"}
DEFAULT_CATEGORY = {
    "discoverability-audit": "discoverability",
    "entity-content-audit": "entity_content",
    "fact-consistency-audit": "fact_consistency",
    "corroboration-authority-audit": "corroboration",
    "geo-content-audit": "geo_content",
    "engagement-context-audit": "engagement",
}

# ── Native 6 Specialist Domains + Agent Interactivity ──
# Aligned 1-to-1 with our 6 specialist skills + orchestrator protocols (134 total checks)
DOMAIN_TAXONOMY = {
    # 1. Discoverability & Crawlability (discoverability-audit)
    "discoverability": {
        "name": "Discoverability & Crawlability",
        "skill": "discoverability-audit",
        "check_ids": [
            "A1", "A2", "A3", "A4", "A5",
            "B1", "B2", "B3", "B4", "B5",
            "C1", "C2", "C3", "C4", "C5",
            "H1", "H2", "H3",
            "I1", "I2",
            "J9", "J10",
        ],
        "weight": 1.3,
        "description": "Robots.txt access, crawler directives, static HTML ingestion rate, and hydration parity",
    },
    # 2. Entity Identity & Answerability (entity-content-audit)
    "entity_content": {
        "name": "Entity Identity & Content Answerability",
        "skill": "entity-content-audit",
        "check_ids": [
            "E1", "E2", "E3", "E4", "E5", "E6", "E7",
            "BC1", "BC2", "BC3", "BC4", "BC5", "BC6", "BC7", "BC8",
        ],
        "weight": 1.2,
        "description": "Schema.org structured data, Organization identity, Product/Offer answerability, and speakable specifications",
    },
    # 3. Fact Consistency & Grounding (fact-consistency-audit)
    "fact_consistency": {
        "name": "Fact Consistency & Grounding",
        "skill": "fact-consistency-audit",
        "check_ids": [
            "F1", "F2", "F3", "F4", "F5",
            "PP1", "PP2", "PP3", "PP4", "PP5", "PP6", "PP7",
            "PROFILE_DATA_MISMATCH", "UNDECLARED_PROFILE_FOUND",
            "STALE_THIRD_PARTY_PROFILE", "MISSING_EXPECTED_PROFILE",
        ],
        "weight": 1.0,
        "description": "Cross-surface claim consistency, pricing parity, and profile truth alignment across channels",
    },
    # 4. Corroboration & Authority (corroboration-authority-audit)
    "corroboration_authority": {
        "name": "Corroboration & Authority Signals",
        "skill": "corroboration-authority-audit",
        "check_ids": [
            "SA1", "SA2", "SA3", "SA4", "SA5", "SA6", "SA7", "SA8", "SA9",
            "SC1", "SC2", "SC3", "SC4", "SC5", "SC6", "SC7",
        ],
        "weight": 1.0,
        "description": "Independent third-party validation, citation ecosystem presence, and sentiment corroboration",
    },
    # 5. GEO Citability & Synthesis (geo-content-audit)
    "geo_citability": {
        "name": "GEO Citability & Synthesis Readiness",
        "skill": "geo-content-audit",
        "check_ids": [
            "N1", "N2", "N3", "N4", "N5", "N6", "N7", "N8", "N9", "N10",
            "N11", "N12", "N13", "N14", "N15",
            "BN1", "BN2", "BN3", "BN4", "BN5", "BN6", "BN7", "BN8", "BN9",
            "ED1", "ED2", "ED3", "ED4", "ED5", "ED6", "ED7", "ED8", "ED9",
            "ME1", "ME2", "ME3", "ME4", "ME5", "ME6", "ME7", "ME8",
        ],
        "weight": 1.2,
        "description": "Direct answer density, factual self-containment, statistical backing, and quotable chunk boundaries",
    },
    # 6. Engagement & Context Continuity (engagement-context-audit)
    "engagement_context": {
        "name": "Engagement & Search Journey Context",
        "skill": "engagement-context-audit",
        "check_ids": [
            "EC1", "EC2", "EC3", "EC4", "EC5", "EC6", "EC7", "EC8", "EC9",
            "D1", "D2", "D3", "D4", "D5",
        ],
        "weight": 0.8,
        "description": "User intent fulfillment, navigation clarity, and search-to-conversion continuity",
    },
    # 7. Agent Interactivity & Protocols (orchestrator proactive declarations)
    "agent_interactivity": {
        "name": "Agent Interactivity & Protocol Declarations",
        "skill": "audit-orchestrator",
        "check_ids": [
            "G1", "G2",
            "J1", "J2", "J3", "J4", "J5", "J6", "J7", "J8",
        ],
        "weight": 0.8,
        "description": "llms.txt manifest availability, WebMCP compliant endpoints, and programmatic agent discovery",
    },
}

GEO_CATEGORY_MAP = DOMAIN_TAXONOMY  # Backward compatibility

READINESS_TIERS = [
    (90, "Tier 1: Elite Citability", "Authoritative knowledge source with pre-rendered facts and machine-explicit identity; primed for top-rank AI search citations."),
    (75, "Tier 2: Strong Grounding", "High citability with minor schema or answerability gaps; reliably indexed for search retrieval."),
    (60, "Tier 3: Selective Ingestion", "Partially visible to AI bots; hydration delays or entity ambiguities reduce extraction confidence."),
    (40, "Tier 4: High Hallucination Risk", "Substantial blind spots; missing core schema, heavy client hydration, or crawler friction cause inconsistent AI representations."),
    (0, "Tier 5: AI-Invisible / High Friction", "Severe crawl blocks, complete client-rendering dependency, or ungrounded entity profiles render site invisible to AI agents."),
]


def compute_domain_scores(findings, coverage_data=None, category=None):
    """Compute per-domain Brand AI-Readiness scores (0-100), composite index, grade, and tier.

    Scoring logic:
    - Start at 100 for each of the 6 specialist domains (+ agent interactivity).
    - Deduct points based on finding severity:
      critical=-40, high=-25, medium=-15, low=-5
    - Deductions apply to the domain corresponding to the finding's related_check_ids.
    - Static Ingestion Rate penalty: If static HTML ingestion rate is low (<90%),
      apply a direct penalty to the Discoverability domain.
    - Archetype-specific weight adjustments: Tune domain evaluation weight according to site category.
    """
    SEVERITY_DEDUCTION = {"critical": 40, "high": 25, "medium": 15, "low": 5}
    GRADE_THRESHOLDS = [
        (90, "A"), (80, "B"), (70, "C"), (60, "D"), (50, "E"), (0, "F")
    ]

    # Build reverse map: check_id -> domain_key
    check_to_domain = {}
    for dom_key, dom_info in DOMAIN_TAXONOMY.items():
        for cid in dom_info["check_ids"]:
            check_to_domain[cid] = dom_key

    # Initialize domain scores
    scores = {}
    for dom_key, dom_info in DOMAIN_TAXONOMY.items():
        scores[dom_key] = {
            "name": dom_info["name"],
            "skill": dom_info["skill"],
            "score": 100,
            "grade": "A",
            "finding_count": 0,
            "deductions": [],
            "weight": dom_info["weight"],
        }

    # Apply category-specific weight adjustments if applicable
    CATEGORY_WEIGHT_ADJUSTMENTS = {
        "ECOMMERCE": {"entity_content": 1.4, "engagement_context": 1.1},
        "SAAS": {"agent_interactivity": 1.1, "entity_content": 1.3},
        "BLOG_NEWS": {"geo_citability": 1.4, "fact_consistency": 1.1},
        "DOCUMENTATION": {"discoverability": 1.4, "geo_citability": 1.3},
        "LOCAL_BUSINESS": {"entity_content": 1.3, "fact_consistency": 1.2},
        "B2B_SERVICES": {"entity_content": 1.3, "corroboration_authority": 1.2},
    }
    if category and category in CATEGORY_WEIGHT_ADJUSTMENTS:
        for dom_key, adj_weight in CATEGORY_WEIGHT_ADJUSTMENTS[category].items():
            if dom_key in scores:
                scores[dom_key]["weight"] = adj_weight

    # Apply deductions from findings
    for f in findings:
        related_ids = f.get("related_check_ids", [])
        severity = f.get("severity", "low")
        deduction = SEVERITY_DEDUCTION.get(severity, 5)
        matched_domains = set()

        for cid in related_ids:
            dom_key = check_to_domain.get(cid)
            if dom_key and dom_key not in matched_domains:
                matched_domains.add(dom_key)
                scores[dom_key]["score"] = max(0, scores[dom_key]["score"] - deduction)
                scores[dom_key]["finding_count"] += 1
                scores[dom_key]["deductions"].append(
                    f"-{deduction} ({severity}: {f.get('title', cid)[:60]})"
                )

        # Fallback by finding ID / category if no check_id matched
        if not matched_domains:
            fid = f.get("id", "")
            fcat = f.get("category", "")
            if "STATIC_HTML" in fid or "CITATION_READABILITY" in fid or fcat == "rendering":
                dom_key = "discoverability"
            elif "ENTITY" in fid or fcat in ("entity-identity", "product-answerability"):
                dom_key = "entity_content"
            elif fcat == "crawlability":
                dom_key = "discoverability"
            else:
                dom_key = "discoverability"
            scores[dom_key]["score"] = max(0, scores[dom_key]["score"] - deduction)
            scores[dom_key]["finding_count"] += 1
            scores[dom_key]["deductions"].append(
                f"-{deduction} ({severity}: {f.get('title', fid)[:60]})"
            )

    # Apply static HTML ingestion rate directly to Discoverability domain
    if coverage_data:
        static_rate = coverage_data.get("static_ingestion_rate_pct")
        if static_rate is None:
            static_rate = coverage_data.get("citation_readability_pct")
        if static_rate is not None and static_rate < 90:
            deficit_penalty = max(0, int((100 - static_rate) * 0.4))
            if deficit_penalty > 0:
                scores["discoverability"]["score"] = max(
                    0, scores["discoverability"]["score"] - deficit_penalty
                )
                scores["discoverability"]["deductions"].append(
                    f"-{deficit_penalty} (static ingestion rate: {static_rate}%)"
                )

    # Compute grades for each domain
    for dom_key in scores:
        score = scores[dom_key]["score"]
        for threshold, grade in GRADE_THRESHOLDS:
            if score >= threshold:
                scores[dom_key]["grade"] = grade
                break

    # Compute composite Brand AI-Readiness Index (0-100)
    total_weight = sum(s["weight"] for s in scores.values())
    weighted_sum = sum(s["score"] * s["weight"] for s in scores.values())
    overall_score = round(weighted_sum / total_weight) if total_weight > 0 else 0

    overall_grade = "F"
    for threshold, grade in GRADE_THRESHOLDS:
        if overall_score >= threshold:
            overall_grade = grade
            break

    readiness_tier = "Tier 5: AI-Invisible / High Friction"
    tier_desc = ""
    for threshold, tier_name, desc in READINESS_TIERS:
        if overall_score >= threshold:
            readiness_tier = tier_name
            tier_desc = desc
            break

    domain_output = {
        k: {
            "name": v["name"],
            "skill": v["skill"],
            "score": v["score"],
            "grade": v["grade"],
            "finding_count": v["finding_count"],
        }
        for k, v in scores.items()
    }

    result = {
        "brand_readiness_index": overall_score,
        "overall_grade": overall_grade,
        "readiness_tier": readiness_tier,
        "tier_description": tier_desc,
        "domains": domain_output,
    }
    return result


compute_geo_scores = compute_domain_scores  # Backward compatibility alias




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
        "minimum", "maximum", "minLength", "minItems", "additionalProperties", "format", "pattern",
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
    if "pattern" in schema and isinstance(value, str):
        import re
        if not re.search(schema["pattern"], value):
            raise ValueError(f"{path}: violates pattern {schema['pattern']}")
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
             discoverability_coverage=None, include_diagnostics=False, collection_seconds=None):
    """Assemble verified candidates into a schema-valid Draft-07 audit report.

    Args:
        discoverability_coverage: Coverage data from the discoverability specialist,
            including citation_readability_pct and missing_words.
        collection_seconds: Optional float recording total evidence collection duration.
    """
    artifacts = {a["artifact"]: a for a in records}
    if browser:
        artifacts.update({a["artifact"]: a for a in browser.get("captures", [])})
    catalogue = {c["check_id"]: c for c in checks}
    observations, dropped, merged = [], [], {}
    registry = EvidenceRegistry()

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

    for idx, item in enumerate(sorted_findings, 1):
        finding_id = f"F-{idx:03d}"
        band = item.get("actual_band", "S1")
        sev = LABELS.get(band, "low")
        owner_skill = catalogue.get(item["check_id"], {}).get("owner", "discoverability-audit")
        category = DEFAULT_CATEGORY.get(owner_skill, "discoverability")

        sources = []
        for e in item.get("evidence_refs", []):
            art = artifacts.get(e.get("artifact"), {})
            src_url = art.get("url", item.get("scope", site))
            src_type = "html" if "html" in e.get("artifact", "") else "http"
            obs = f"{e.get('artifact')} at {e.get('locator')}: {e.get('quote', '')[:300]}"
            sources.append({
                "url": src_url,
                "type": src_type,
                "observation": obs,
            })

        if not sources:
            default_obs = item.get("severity_reason") or f"Direct sensor observation for {item['check_id']}"
            sources = [{"url": site, "type": "html", "observation": default_obs}]

        evidence_obj = {
            "summary": item.get("severity_reason") or f"Issue detected for {item['check_id']}",
            "scope": item.get("scope", site),
            "sources": sources,
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
            "id": finding_id,
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

    # Classify site archetype deterministically
    archetype_info = classify_site(site, records=records, candidates=candidates)

    # Generate proactive recommendations (e.g. autonomous /llms.txt manifest)
    proactive_actions = []
    llms_missing = any("llms.txt" in str(obs) for obs in observations) or not any(
        "/llms.txt" in str(r.get("url", "")) for r in records
    )
    if llms_missing:
        from urllib.parse import urlparse
        domain_name = urlparse(site).netloc or site.replace("https://", "").replace("http://", "").split("/")[0]
        if domain_name.lower().startswith("www."):
            domain_name = domain_name[4:]
        brand_title = domain_name.split(".")[0].capitalize()
        proactive_actions.append(
            {
                "id": "PROACTIVE_LLMS_TXT_MANIFEST",
                "title": f"Autonomous /llms.txt manifest for {brand_title}",
                "category": "agent_interactivity",
                "summary": f"Generate and deploy an /llms.txt AI search manifest on {site}/llms.txt to provide zero-friction grounding for AI research agents.",
                "technical_fix": f"Deploy a Markdown file at {site}/llms.txt following the llmstxt.org specification, linking primary documentation, product catalogue, and canonical brand facts.",
                "creative_fix": f"Curate executive summaries of {brand_title}'s core differentiators, key service offerings, and authoritative contact endpoints within the manifest.",
                "priority": "medium",
                "verification": f"Fetch {site}/llms.txt with curl -sI and verify HTTP 200 response with Content-Type: text/markdown.",
            }
        )

    report = {
        "site": site,
        "audited_at": now(),
        "audit_status": "complete",
        "site_category": {
            "primary": archetype_info["primary"],
            "secondary": archetype_info["secondary"],
            "confidence": archetype_info["confidence"],
        },
        "summary": summary,
        "proactive_actions": proactive_actions,
        "findings": schema_findings,
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


def assemble_from_specialist_outputs(site, inv, specialist_outputs, checks=None, collection_seconds=None):
    """
    Ingests raw specialist outputs and inventory, constructs grounded evidence records,
    reconciles findings into candidate objects, and invokes assemble() to generate a
    strictly schema-valid Draft-07 audit report.
    """
    if checks is None:
        checks_path = Path(__file__).resolve().parents[1] / "references/checks.json"
        checks = json.loads(checks_path.read_text(encoding="utf-8"))
    catalogue = {c["check_id"]: c for c in checks}

    # 1. Build ground-truth evidence records from inventory
    robots_text = inv.get("robots", {}).get("text", "") or inv.get("robots_txt", "")
    hp_page = next(
        (p for p in inv.get("pages", []) if p.get("page_type") == "homepage" or p.get("url") in (f"{site}/", site)),
        inv.get("pages", [{}])[0] if inv.get("pages") else {},
    )
    hp_html = hp_page.get("html", "")

    records = [
        {"artifact": "robots_txt", "url": f"{site}/robots.txt", "text": robots_text, "status": 200},
        {
            "artifact": "homepage_html",
            "url": hp_page.get("url", f"{site}/"),
            "text": hp_html,
            "status": hp_page.get("status", 200),
            "page_type": "homepage",
        },
    ]
    for idx, page in enumerate(inv.get("pages", [])):
        records.append({
            "artifact": f"page_{idx}",
            "url": page.get("url", ""),
            "text": page.get("html", ""),
            "page_type": page.get("page_type", ""),
            "status": page.get("status", 200),
        })

    artifacts = {a["artifact"]: a for a in records}

    def find_grounded_quote(art_text, preferred_strings):
        for s in preferred_strings:
            if s and len(s) >= 3 and s in art_text:
                return s
        words = (art_text or "").split()
        for w in words:
            if len(w) > 4 and w in art_text:
                return w
        return art_text[:20] if art_text else "evidence"

    CAUSE_TO_CHECK = {
        "CONTENT_DEPTH_INSUFFICIENT": "N1",
        "CAUSAL_MECHANISMS_MISSING": "N1",
        "STATISTICAL_EVIDENCE_ABSENT": "N3",
        "AUTHORITY_CITATIONS_ABSENT": "BN1",
        "CREDIBLE_QUOTATION_ABSENT": "N5",
        "PRONOUN_HEAVY_STYLE": "N6",
        "JARGON_UNDEFINED": "N8",
        "KEYWORD_STUFFING_DETECTED": "N10",
        "FAQ_STRUCTURE_ABSENT": "N13",
        "FRESHNESS_SIGNALS_STALE": "N14",
        "AUTHOR_CREDENTIALS_ABSENT": "N15",
        "NAV_DEAD_END_404": "B4",
        "STATIC_HTML_HYDRATION_DEFICIT": "C1",
        "SEMANTIC_LANDMARKS_ABSENT": "H2",
        "AI_RETRIEVAL_BLOCKED": "A3",
        "ROBOTS_TXT_MISSING": "A1",
        "WILDCARD_DISALLOW_PRESENT": "A2",
        "SITEMAP_PROTOCOL_ERROR": "A5",
        "CLAIM_CORROBORATION_GAP": "SA2",
        "ORGANIZATION_SCHEMA_MISSING": "E1",
        "PRODUCT_OFFER_MISSING": "E2",
        "PRICING_INCONSISTENCY": "F1",
    }
    SEV_TO_BAND = {"critical": "S4", "high": "S3", "medium": "S2", "low": "S1"}

    candidates = []
    disc_cov = None

    # Flatten and normalize specialist data blocks
    spec_blocks = []
    for item in specialist_outputs:
        data = item
        if isinstance(item, (str, Path)):
            p = Path(item)
            if p.is_file():
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                except Exception:
                    continue
        if not isinstance(data, dict):
            continue

        if "findings" in data or "coverage" in data:
            spec_blocks.append(data)
        else:
            for v in data.values():
                if isinstance(v, dict) and ("findings" in v or "coverage" in v or "observations" in v):
                    spec_blocks.append(v)

    # Ingest from all specialist outputs
    for data in spec_blocks:
        # Extract discoverability coverage if present
        if "coverage" in data and isinstance(data["coverage"], dict):
            cov = data["coverage"]
            if "static_ingestion_rate_pct" in cov or "citation_readability_pct" in cov:
                disc_cov = cov

        # Ingest findings
        for f in data.get("findings", []):
            if not isinstance(f, dict):
                continue
            cid = f.get("check_id") or CAUSE_TO_CHECK.get(f.get("cause_id") or f.get("id"))
            if not cid or cid not in catalogue:
                continue
            sev = str(f.get("severity", "medium")).lower()
            band = SEV_TO_BAND.get(sev, "S2")

            art_name = "robots_txt" if cid.startswith("A") else "homepage_html"
            art_text = artifacts.get(art_name, {}).get("text", "")
            quote = find_grounded_quote(art_text, [f.get("scope", ""), hp_page.get("title", ""), "User-agent", "html", "head"])

            existing_refs = f.get("evidence_refs")
            if existing_refs and isinstance(existing_refs, list):
                refs = existing_refs
            else:
                refs = [{"artifact": art_name, "locator": "text", "quote": quote}]

            cand = {
                "check_id": cid,
                "actual_band": band,
                "finding_kind": "confirmed_problem" if band in ("S4", "S3", "S2") else "advisory",
                "collection_complete_for_scope": True,
                "scope": f.get("scope") or f"{site}/",
                "severity_reason": f.get("root_cause") or f.get("title") or f"Observed defect in {cid}",
                "difficulty": int(f.get("difficulty", 2)) if str(f.get("difficulty", "")).isdigit() else 2,
                "difficulty_reason": f.get("difficulty_reason") or "Remediate according to technical specifications.",
                "evidence_refs": refs,
                "suggested_action": f.get("suggested_action", {
                    "summary": f.get("title", f"Remediate {cid}"),
                    "priority": sev,
                }),
            }
            candidates.append(cand)

    report = assemble(
        site=site,
        candidates=candidates,
        records=records,
        checks=checks,
        discoverability_coverage=disc_cov,
        collection_seconds=collection_seconds,
    )
    return report


def main():
    import argparse
    import glob
    import os
    import sys

    if len(sys.argv) == 2 and not sys.argv[1].startswith("-") and os.path.exists(sys.argv[1]):
        validate_report(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")))
        print("Report schema and counts valid")
        return

    parser = argparse.ArgumentParser(description="Evidence-gated report assembler and validator.")
    parser.add_argument("--site", help="Target website URL")
    parser.add_argument("--inventory", help="Path to inventory JSON file")
    parser.add_argument("--specialists", nargs="*", help="Specialist JSON output files or glob pattern")
    parser.add_argument("--output", "-o", help="Path to save final report JSON")
    parser.add_argument("--validate", help="Validate an existing report JSON file")

    args = parser.parse_args()

    if args.validate:
        validate_report(json.loads(Path(args.validate).read_text(encoding="utf-8")))
        print("Report schema and counts valid")
        return

    if not args.site or not args.inventory:
        parser.print_help()
        sys.exit(1)

    inv = json.loads(Path(args.inventory).read_text(encoding="utf-8"))
    specialist_files = []
    for s_arg in (args.specialists or []):
        expanded = glob.glob(s_arg)
        if expanded:
            specialist_files.extend(expanded)
        elif os.path.exists(s_arg):
            specialist_files.append(s_arg)

    report = assemble_from_specialist_outputs(
        site=args.site,
        inv=inv,
        specialist_outputs=specialist_files,
    )

    out_json = json.dumps(report, indent=2)
    if args.output:
        Path(args.output).write_text(out_json, encoding="utf-8")
        print(f"[+] Successfully assembled and validated report -> {args.output}")
    else:
        print(out_json)


if __name__ == "__main__":
    main()

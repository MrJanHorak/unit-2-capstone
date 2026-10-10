"""Analyse real transcripts/logs and check answers against independent teaching facts."""
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import ROOT

MONTHLY_REVENUE = {"2025-10": 120000, "2025-11": 57000, "2025-12": 68000,
                   "2026-01": 260000, "2026-02": 85000, "2026-03": 66000,
                   "2026-04": 275000, "2026-05": 15000, "2026-06": 10000}
Q4_REGIONS = {"North America": 180000, "EMEA": 45000, "APAC": 12000, "LATAM": 8000}
DEPARTMENT_SCORES = {"Engineering": 4.325, "Customer Experience": 11 / 3,
                     "Sales": 12.2 / 3, "Security": 4.55, "Product": 4.05}


def has_patterns(text, patterns):
    return all(re.search(pattern, text, re.I | re.S) for pattern in patterns)


def document_facts(result, scenario):
    # Match required facts independently of the model-reviewer's opinion.
    patterns = {
        1: [r"\b16\b", r"MFA|Multi.Factor", r"AES.?256", r"TLS\s*1\.3", r"SMS"],
        2: [r"two|\b2\b", r"peer|approv", r"parameter", r"SAST|Static Application"],
        3: [r"acknowledge|de.escalation", r"investigat|cross.reference", r"250",
            r"closure|survey", r"Jira|escalation"],
    }
    return bool(has_patterns(result.get("answer", ""), patterns[scenario]))


def numeric_mapping(agent, expected, column_hint):
    columns = agent.get("columns", [])
    position = next((i for i, name in enumerate(columns) if column_hint in name.lower()), None)
    if position is None:
        # SQLite can name AVG(...) directly; aliases are optional.
        return False
    actual = {str(row[0]): row[position] for row in agent.get("rows", [])}
    return set(actual) == set(expected) and all(isinstance(actual[key], (int, float)) and
        math.isclose(actual[key], value, abs_tol=0.005) for key, value in expected.items())


def verify_scenario(result, scenario):
    checks = {"released_after_validation": result["status"] == "accepted"}
    agent = result.get("agents", {}).get("quantitative", {})
    if scenario <= 3:
        checks["required_document_facts"] = document_facts(result, scenario)
    elif scenario in (4, 8):
        checks["exact_monthly_revenue"] = numeric_mapping(agent, MONTHLY_REVENUE, "revenue")
    elif scenario == 5:
        values = [value for row in agent.get("rows", []) for value in row if isinstance(value, (int, float))]
        checks["snapshot_churn_four_of_twelve"] = any(math.isclose(value, 1/3, abs_tol=0.0001)
            or math.isclose(value, 100/3, abs_tol=0.005) for value in values)
    elif scenario == 6:
        checks["exact_q4_regional_revenue"] = numeric_mapping(agent, Q4_REGIONS, "revenue")
    elif scenario == 7:
        checks["department_satisfaction"] = numeric_mapping(agent, DEPARTMENT_SCORES, "satisfaction")
        checks["missing_benchmark_acknowledged"] = bool(has_patterns(result["answer"],
            [r"industry", r"not|cannot|no |missing|absen|unavail"]))
    elif scenario in (9, 10):
        expected = 180000 if scenario == 9 else 52
        checks["reference_scope_and_value"] = agent.get("rows") in ([[expected]], [(expected,)])
        if scenario == 10:
            checks["follow_up_resolves_region_and_quarter"] = has_patterns(
                result.get("standalone_query", ""), [r"North America", r"Q4", r"2025"]) is True
    elif scenario == 11:
        checks["unsupported_topic_refused"] = result["answer"] == "I cannot find this information in the provided documents."
    return {"scenario": scenario, "query_id": result["tokenomics"]["query_id"],
            "query": result["query"], "checks": {k: bool(v) for k, v in checks.items()},
            "passed": all(checks.values())}


def build_report():
    evidence = ROOT / "docs/evidence"
    runs = json.loads((evidence / "live_queries.json").read_text(encoding="utf-8"))
    pairs = json.loads((evidence / "optimisation.json").read_text(encoding="utf-8"))
    logs = [json.loads(line) for line in (ROOT / "tokenomics_log.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    current = [record for record in logs if record.get("schema_version") == 2]
    experiment = []
    totals = {label: {"input_tokens": 0, "output_tokens": 0, "thinking_tokens": 0}
              for label in ("baseline", "optimised")}
    for i, pair in enumerate(pairs, 1):
        row = {"query": pair["query"]}
        for label in totals:
            result = pair[label]
            row[label] = {"query_id": result["tokenomics"]["query_id"], "status": result["status"],
                          "required_facts_present": document_facts(result, i)}
            for field in totals[label]:
                totals[label][field] += result["tokenomics"][field]
        experiment.append(row)
    baseline, optimised = totals["baseline"], totals["optimised"]
    base_total, opt_total = sum(baseline.values()), sum(optimised.values())
    return {"live_checks": [verify_scenario(result, i) for i, result in enumerate(runs, 1)],
            "legacy_stage_records_preserved": len(logs) - len(current),
            "version_2_query_records": len(current),
            "known_paid_tier_estimate_usd": sum(record["estimated_cost_usd"] or 0 for record in current),
            "unknown_cost_records": sum(record["estimated_cost_usd"] is None for record in current),
            "experiment": experiment, "experiment_totals": totals,
            "input_token_reduction_percent": (1 - optimised["input_tokens"] / baseline["input_tokens"]) * 100 if baseline["input_tokens"] else None,
            "total_token_reduction_percent": (1 - opt_total / base_total) * 100 if base_total else None,
            "quality_preserved_on_tested_queries": len(pairs) == 3 and all(
                row[label]["status"] == "accepted" and row[label]["required_facts_present"]
                for row in experiment for label in totals)}


if __name__ == "__main__":
    report = build_report()
    (ROOT / "docs/evidence/report.json").write_text(json.dumps(report, indent=2), encoding="utf-8", newline="\n")
    passed = sum(row["passed"] for row in report["live_checks"])
    print(f"Independent live checks: {passed}/{len(report['live_checks'])}")
    for row in report["live_checks"]:
        if not row["passed"]:
            print(f"Scenario {row['scenario']} failed: {row['checks']}")
    print(f"Paired quality preserved: {report['quality_preserved_on_tested_queries']}")
    print(f"Input token reduction: {report['input_token_reduction_percent']:.2f}%")
    print(f"Total token reduction: {report['total_token_reduction_percent']:.2f}%")
    print(f"Saved full report: {ROOT / 'docs/evidence/report.json'}")
    raise SystemExit(int(not all(row["passed"] for row in report["live_checks"])
                        or not report["quality_preserved_on_tested_queries"]))

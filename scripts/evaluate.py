"""Explicit live submission runs and an A/B retrieval-budget experiment."""
import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agents.manager import Session
from config import ROOT, Settings

QUERIES = [
    "What is our company's security policy?",
    "Explain the code review process",
    "How do we handle customer complaints?",
    "Show me monthly revenue trends",
    "What is our customer churn rate?",
    "Compare Q4 2025 revenue across regions",
    "How does our employee satisfaction compare to industry standards and what policies might impact this?",
    "Analyse our sales performance and recommend policy changes based on our customer success strategies",
    "What was North America's Q4 2025 revenue?",
    "How many units did that region sell in that quarter?",
    "What is our policy for bringing pet dragons to work?",
]


def save(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True, help="Acknowledges real Gemini API calls")
    parser.add_argument("--optimisation", action="store_true")
    parser.add_argument("--only", type=int, nargs="+", help="Rerun selected 1-based scenario numbers")
    args = parser.parse_args()
    settings = Settings.from_environment()
    report = []
    if args.optimisation:
        output = ROOT / "docs/evidence/optimisation.json"
        # Same model, prompts, reviewer and questions; vary ONLY retrieval budget.
        for query in QUERIES[:3]:
            pair = {"query": query}
            for label, variant in (("baseline", replace(settings, top_k=5, context_words=1500)),
                                   ("optimised", settings)):
                result = Session(variant).run(query)
                pair[label] = result
                print(f"{label}: {result['status']} | {query}", flush=True)
            report.append(pair)
            save(output, report)
    else:
        output = ROOT / "docs/evidence/live_queries.json"
        if args.only:
            if any(i < 1 or i > len(QUERIES) for i in args.only):
                parser.error("Scenario numbers must be between 1 and 11")
            report = json.loads(output.read_text(encoding="utf-8"))
            if 10 in args.only and 9 not in args.only:
                args.only.append(9)  # Rebuild the reference pair's session context.
        session = Session(settings)
        for i, query in enumerate(QUERIES, 1):
            if args.only and i not in args.only:
                continue
            # Only the final reference pair shares history. Independent scenarios
            # should not pay for irrelevant earlier conversation context.
            if i != 10:
                session.reset()
            result = session.run(query)
            if args.only:
                report[i-1] = result
            else:
                report.append(result)
            save(output, report)
            print(f"{i}: {result['route']} / {result['status']} | {query}", flush=True)
            if result.get("warnings"):
                print("; ".join(result["warnings"]), flush=True)
    # Failure remains visible and causes a nonzero exit, never fake passing evidence.
    results = ([p[label] for p in report for label in ("baseline", "optimised")]
               if args.optimisation else report)
    return int(any(result["status"] != "accepted" for result in results))


if __name__ == "__main__":
    raise SystemExit(main())

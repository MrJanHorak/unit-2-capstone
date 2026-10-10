"""Interactive CLI and scriptable single-query mode; only release verified answers."""
import argparse
import json
from agents.manager import Session


def display(result):
    print(f"\nRoute: {result['route']} | Status: {result['status']}\n{result['answer']}")
    for warning in result.get("warnings", []):
        print(f"Validation: {warning}")
    for name, agent in result["agents"].items():
        if name == "qualitative":
            for i, chunk in enumerate(agent["chunks"], 1):
                print(f"Source {i}: {chunk['source']} (chunk {chunk['chunk']})")
        elif agent["validation"] == "PASSED":
            print(f"SQL used: {agent['sql']}")
    usage = result["tokenomics"]
    cost = usage["estimated_cost_usd"]
    cost_text = f"${cost:.6f}" if cost is not None else "unknown"
    print(f"Tokens: {usage['input_tokens']} input / {usage['output_tokens']} output / "
          f"{usage['thinking_tokens']} thinking; paid-tier estimate {cost_text}\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", help="Run one query, then exit")
    parser.add_argument("--json", action="store_true", help="Output a public JSON result")
    args = parser.parse_args()
    session = Session()
    if args.query:
        result = session.run(args.query)
        if args.json:
            # Raw rejected candidates stay in evaluation artifacts, not public CLI output.
            public = {k: v for k, v in result.items() if k not in {"agents", "synthesis_candidate"}}
            print(json.dumps(public, ensure_ascii=False, indent=2))
        else:
            display(result)
        return 0 if result["status"] == "accepted" else 1
    print("Spoonful Enterprise RAG (Gemini)\nType exit to quit, /reset to clear session history.")
    while True:
        try:
            query = input("Ask a question: ").strip()
            if query.lower() in {"exit", "quit"}:
                break
            if query == "/reset":
                session.reset()
                print("Conversation history cleared.")
            elif query:
                try:
                    display(session.run(query))
                except ValueError as exc:
                    print(exc)
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

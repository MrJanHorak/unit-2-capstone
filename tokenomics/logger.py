"""Append one query record containing every generation and review call."""
import json
import os
from datetime import datetime, timezone
from uuid import uuid4

# Standard pricing checked 2026-10-09; USD per million tokens, paid-tier equivalent.
PRICES = {"gemini-3.5-flash-lite": (0.30, 2.50)}


class Ledger:
    def __init__(self, query, settings):
        self.query, self.settings = query, settings
        self.calls = []
        self.query_id = str(uuid4())

    def record(self, stage, usage, seconds=0):
        def count(name):
            return max(0, int(getattr(usage, name, 0) or 0))
        incoming, outgoing = count("prompt_token_count"), count("candidates_token_count")
        thinking = count("thoughts_token_count")
        rates = PRICES.get(self.settings.model)
        if os.getenv("INPUT_USD_PER_MILLION") and os.getenv("OUTPUT_USD_PER_MILLION"):
            rates = (float(os.environ["INPUT_USD_PER_MILLION"]), float(os.environ["OUTPUT_USD_PER_MILLION"]))
        cost = ((incoming * rates[0] + (outgoing + thinking) * rates[1]) / 1_000_000
                if rates and usage is not None else None)
        self.calls.append({"stage": stage, "input_tokens": incoming, "output_tokens": outgoing,
                           "thinking_tokens": thinking, "usage_available": usage is not None,
                           "estimated_cost_usd": cost, "duration_seconds": round(seconds, 3)})

    def failed(self, stage, error):
        # Missing provider usage is unknown, not proof of a free failed request.
        self.calls.append({"stage": stage, "error": error, "usage_available": False,
                           "input_tokens": 0, "output_tokens": 0, "thinking_tokens": 0,
                           "estimated_cost_usd": None})

    def finish(self, route, status):
        costs = [c["estimated_cost_usd"] for c in self.calls]
        total = sum(costs) if all(c is not None for c in costs) else None
        entry = {"schema_version": 2, "timestamp": datetime.now(timezone.utc).isoformat(),
                 "query_id": self.query_id, "query": self.query, "model": self.settings.model,
                 "route": route, "status": status, "calls": self.calls,
                 "input_tokens": sum(c["input_tokens"] for c in self.calls),
                 "output_tokens": sum(c["output_tokens"] for c in self.calls),
                 "thinking_tokens": sum(c["thinking_tokens"] for c in self.calls),
                 "estimated_cost_usd": total,
                 "cost_per_1000_queries_usd": total * 1000 if total is not None else None,
                 "pricing_basis": "paid-tier equivalent; free-tier billing may be zero"}
        self.settings.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.settings.log_path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry

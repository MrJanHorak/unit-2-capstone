"""Scripted model responses and temporary datasets for deterministic offline tests."""
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from config import Settings
from setup_db import create_database

CHUNKS = [{"content": "Production code requires two approving peer reviews.",
           "source": "security_policy.txt", "chunk": 0}]


class ScriptedModel:
    def __init__(self, responses, ledger=None):
        self.responses, self.ledger, self.calls = responses, ledger, []

    def generate(self, stage, prompt, **kwargs):
        self.calls.append((stage, prompt, kwargs))
        response = self.responses[stage]
        if self.ledger:
            self.ledger.record(stage, SimpleNamespace(prompt_token_count=10, candidates_token_count=5))
        if isinstance(response, Exception):
            raise response
        return response


def good_review():
    return {"supported": True, "issues": []}


def routing_plan(route, query):
    return {"route": route, "standalone_query": query,
            "document_question": query, "data_question": query}


class TemporaryProject:
    def __enter__(self):
        self.temp = TemporaryDirectory()
        root = Path(self.temp.name)
        self.settings = replace(Settings(), database=root / "test.sqlite", log_path=root / "usage.jsonl")
        create_database(self.settings.database)
        return self

    def __exit__(self, *args):
        self.temp.cleanup()

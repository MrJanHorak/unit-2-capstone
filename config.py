"""Central settings; paths work even when launched outside the project folder."""
import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load_environment():
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    model: str = "gemini-3.5-flash-lite"
    database: Path = ROOT / "data/database.sqlite"
    documents: Path = ROOT / "data/documents"
    index: Path = ROOT / "data/index"
    log_path: Path = ROOT / "tokenomics_log.jsonl"
    embedding_model: str = "all-MiniLM-L6-v2"
    collection: str = "enterprise-docs"
    top_k: int = 2
    context_words: int = 700
    history_turns: int = 4
    max_rows: int = 50
    sql_steps: int = 100_000

    @classmethod
    def from_environment(cls):
        load_environment()
        return cls(model=os.getenv("GEMINI_MODEL", cls.model))

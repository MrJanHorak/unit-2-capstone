"""Real SQLite safety, chunk boundaries, and token-cost accounting regressions."""
import json
import sqlite3
import unittest
from dataclasses import replace
from types import SimpleNamespace
from ingest import chunk_document
from safe_sql import clean_sql_output, execute_select, validate_sql
from setup_db import create_database
from tests.helpers import TemporaryProject
from tokenomics.logger import Ledger


class SQLTests(unittest.TestCase):
    def test_writes_attach_pragma_and_stacked_statements_rejected(self):
        with TemporaryProject() as project:
            before = project.settings.database.read_bytes()
            for sql in ("DELETE FROM sales", "DROP TABLE sales", "ATTACH DATABASE ':memory:' AS x",
                        "PRAGMA writable_schema=ON", "SELECT 1; DELETE FROM sales", "SELECT 1; SELECT 2",
                        "SELECT load_extension('bad')", "SELECT sql FROM sqlite_master"):
                with self.subTest(sql=sql), self.assertRaises((ValueError, sqlite3.Error)):
                    execute_select(sql, project.settings)
            self.assertEqual(project.settings.database.read_bytes(), before)

    def test_read_does_not_block_keyword_inside_literal(self):
        with TemporaryProject() as project:
            self.assertEqual(execute_select("SELECT 'updated' AS label", project.settings)["rows"], [("updated",)])

    def test_churn_has_float_denominator(self):
        with TemporaryProject() as project:
            rows = execute_select("SELECT 100.0 * SUM(churn_date IS NOT NULL) / COUNT(*) FROM customers", project.settings)["rows"]
            self.assertAlmostEqual(rows[0][0], 100 / 3)

    def test_row_limit_and_progress_limit(self):
        with TemporaryProject() as project:
            limited = replace(project.settings, max_rows=2)
            result = execute_select("SELECT * FROM sales", limited)
            self.assertTrue(result["truncated"])
            self.assertEqual(len(result["rows"]), 2)
            with self.assertRaises(sqlite3.Error):
                execute_select("SELECT SUM(a.revenue * b.revenue * c.revenue) FROM sales a, sales b, sales c",
                               replace(project.settings, sql_steps=1000))

    def test_setup_does_not_replace_existing_database(self):
        with TemporaryProject() as project:
            original = project.settings.database.read_bytes()
            with self.assertRaises(FileExistsError):
                create_database(project.settings.database)
            self.assertEqual(project.settings.database.read_bytes(), original)

    def test_fence_cleaning_preserves_backtick_identifier(self):
        self.assertEqual(clean_sql_output("```sql\nSELECT `region` FROM sales;\n```"), "SELECT `region` FROM sales;")
        self.assertFalse(validate_sql("SELECTED something")["valid"])


class ChunkTests(unittest.TestCase):
    def test_overlap_and_final_word_preserved(self):
        words = [str(i) for i in range(1050)]
        chunks = [c.split() for c in chunk_document(" ".join(words))]
        self.assertEqual([len(c) for c in chunks], [500, 500, 150])
        self.assertEqual(chunks[0][-50:], chunks[1][:50])
        self.assertEqual(chunks[-1][-1], "1049")

    def test_exact_chunk_does_not_duplicate_overlap(self):
        self.assertEqual(len(chunk_document("x " * 500)), 1)
        self.assertEqual(chunk_document(""), [])

    def test_bad_chunk_parameters(self):
        for size, overlap in ((0, 0), (2, 2), (5, -1)):
            with self.assertRaises(ValueError):
                chunk_document("some text", size, overlap)


class TokenomicsTests(unittest.TestCase):
    def test_thinking_tokens_and_query_totals(self):
        with TemporaryProject() as project:
            ledger = Ledger("Test", project.settings)
            ledger.record("answer", SimpleNamespace(prompt_token_count=1000, candidates_token_count=100, thoughts_token_count=20))
            ledger.record("review", SimpleNamespace(prompt_token_count=1000, candidates_token_count=80))
            record = ledger.finish("qualitative", "accepted")
            self.assertAlmostEqual(record["estimated_cost_usd"], 0.0011)
            self.assertEqual(record["thinking_tokens"], 20)
            self.assertEqual(json.loads(project.settings.log_path.read_text())["input_tokens"], 2000)

    def test_missing_usage_or_unknown_model_cost_is_unknown(self):
        with TemporaryProject() as project:
            ledger = Ledger("Test", replace(project.settings, model="unknown-model"))
            ledger.record("answer", SimpleNamespace(prompt_token_count=5))
            self.assertIsNone(ledger.finish("qualitative", "accepted")["estimated_cost_usd"])
            ledger = Ledger("Test", project.settings)
            ledger.record("answer", None)
            self.assertIsNone(ledger.finish("qualitative", "accepted")["estimated_cost_usd"])

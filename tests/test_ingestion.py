"""Real Chroma integration, with a local deterministic embedder and no API calls."""
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from config import Settings
from ingest import ingest
from retrieval import collection_for, retrieve


class LocalEmbeddings:
    def encode(self, texts):
        # Deterministic vectors suffice to exercise persistence, not semantic quality.
        class Vectors(list):
            def tolist(self):
                return list(self)
        return Vectors([[float("security" in text), 1.0, float(len(text) % 7)] for text in texts])


class IngestionIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import chromadb
        except ImportError:
            raise unittest.SkipTest("Install requirements.txt to run real Chroma integration tests")

    def test_repeat_ingestion_shrink_and_remove_file(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            docs = root / "documents"
            docs.mkdir()
            file = docs / "policy.txt"
            file.write_text("security " * 1000, encoding="utf-8")
            other = docs / "other.md"
            other.write_text("Other policy", encoding="utf-8")
            settings = replace(Settings(), index=root / "index", documents=docs, context_words=10)
            with patch("ingest.embedding_model", return_value=LocalEmbeddings()), patch(
                    "retrieval.embedding_model", return_value=LocalEmbeddings()):
                self.assertEqual(ingest(settings=settings), 4)
                self.assertEqual(ingest(settings=settings), 4)
                with collection_for(settings) as collection:
                    self.assertEqual(collection.count(), 4)
                chunks = retrieve("security", settings)
                self.assertLessEqual(sum(len(c["content"].split()) for c in chunks), 10)
                file.write_text("security update", encoding="utf-8")
                other.unlink()
                self.assertEqual(ingest(settings=settings), 1)
                with collection_for(settings) as collection:
                    self.assertEqual(collection.count(), 1)
                    self.assertEqual(collection.get()["documents"], ["security update"])

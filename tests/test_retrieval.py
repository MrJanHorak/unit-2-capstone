"""Reranking regression for a fact hidden in a broad security-policy document."""
import unittest
from retrieval import rank_candidates


class RetrievalTests(unittest.TestCase):
    def test_precise_code_review_terms_beat_broad_semantic_document(self):
        candidates = [
            {"content": "Customer service ticket escalation", "distance": 0.66},
            {"content": "Engineering onboarding environment", "distance": 0.78},
            {"content": "Production code requires two approving peer reviews", "distance": 0.79},
        ]
        ranked = rank_candidates("Explain the code review process", candidates)
        self.assertIn("two approving peer reviews", ranked[0]["content"])

    def test_empty_query_terms_do_not_divide_by_zero(self):
        self.assertEqual(len(rank_candidates("What is our", [{"content": "policy", "distance": 0.5}])), 1)

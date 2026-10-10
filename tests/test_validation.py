"""Failure cases where citation presence and SQL success are insufficient evidence."""
import unittest
from tests.helpers import CHUNKS, ScriptedModel
from validation.validator import REFUSAL, validate_qualitative, validate_quantitative


class ValidatorTests(unittest.TestCase):
    def test_source_10_does_not_match_source_1(self):
        self.assertTrue(validate_qualitative("Two reviews. [Source 10]", CHUNKS)["flag"])

    def test_missing_citation_flagged(self):
        self.assertTrue(validate_qualitative("Two reviews required.", CHUNKS)["flag"])

    def test_exact_refusal_allowed(self):
        self.assertFalse(validate_qualitative(REFUSAL, [])["flag"])

    def test_cannot_find_phrase_is_not_a_validation_bypass(self):
        self.assertTrue(validate_qualitative("I cannot find it, but policy allows anything.", CHUNKS)["flag"])

    def test_irrelevant_context_is_flagged_by_reviewer(self):
        model = ScriptedModel({"qualitative-review": {"supported": False, "issues": ["Review policy does not establish salary"]}})
        result = validate_qualitative("Salary is $200000. [Source 1]", CHUNKS, query="Salary?", llm=model)
        self.assertTrue(result["flag"])

    def test_refusal_when_evidence_has_answer_is_rejected(self):
        model = ScriptedModel({"qualitative-review": {"supported": False, "issues": ["Two reviews is in the evidence"]}})
        self.assertTrue(validate_qualitative(REFUSAL, CHUNKS, query="Code review?", llm=model)["flag"])

    def test_malformed_reviewer_cannot_release_answer(self):
        model = ScriptedModel({"qualitative-review": {"supported": "yes", "issues": []}})
        with self.assertRaises(ValueError):
            validate_qualitative("Two reviews. [Source 1]", CHUNKS, llm=model)

    def test_sql_error_and_block_have_distinct_flags(self):
        self.assertTrue(validate_quantitative("", "DELETE", "FAILED")["sql_blocked"])
        self.assertTrue(validate_quantitative("", "SELECT bad", "ERROR")["execution_error"])

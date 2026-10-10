"""Unit coverage for routing, grounding, SQL interpretation, and failed validation."""
import json
import unittest
from agents import manager, qualitative, quantitative
from tests.helpers import CHUNKS, ScriptedModel, TemporaryProject, good_review, routing_plan
from validation.validator import REFUSAL


class ManagerTests(unittest.TestCase):
    def test_all_routes_are_validated(self):
        for route in manager.ROUTES:
            with self.subTest(route=route):
                model = ScriptedModel({"manager-classifier": routing_plan(route, "Question?")})
                self.assertEqual(manager.classify("Question?", [], model), routing_plan(route, "Question?"))

    def test_invalid_route_cannot_silently_default(self):
        model = ScriptedModel({"manager-classifier": {"route": "maybe", "standalone_query": "Question?"}})
        with self.assertRaises(ValueError):
            manager.classify("Question?", [], model)

    def test_classifier_receives_session_context(self):
        history = [{"query": "Q4 2025 sales?", "answer": "North America led."}]
        model = ScriptedModel({"manager-classifier": routing_plan("quantitative", "North America Q4 2025 sales?")})
        manager.classify("What about that region?", history, model)
        self.assertEqual(json.loads(model.calls[0][1])["history"], history)

    def test_missing_task_plan_is_rejected(self):
        model = ScriptedModel({"manager-classifier": {"route": "both", "standalone_query": "Question?"}})
        with self.assertRaises(ValueError):
            manager.classify("Question?", [], model)


class QualitativeTests(unittest.TestCase):
    def test_prompt_preserves_source_provenance(self):
        prompt = json.loads(qualitative.build_prompt("Explain code review", CHUNKS))
        self.assertEqual(prompt["sources"][0]["label"], "Source 1")
        self.assertEqual(prompt["sources"][0]["file"], "security_policy.txt")

    def test_second_reviewer_catches_plausible_but_false_citation(self):
        with TemporaryProject() as project:
            model = ScriptedModel({"qualitative-answer": "One review suffices. [Source 1]",
                                   "qualitative-review": {"supported": False, "issues": ["Evidence requires two reviews"]}})
            result = qualitative.run("Code review?", model, project.settings, lambda q, s: CHUNKS)
            self.assertTrue(result["check"]["flag"])
            self.assertEqual([c[0] for c in model.calls], ["qualitative-answer", "qualitative-review"])

    def test_no_evidence_refuses_without_model_call(self):
        with TemporaryProject() as project:
            model = ScriptedModel({})
            result = qualitative.run("Missing policy?", model, project.settings, lambda q, s: [])
            self.assertEqual(result["answer"], REFUSAL)
            self.assertFalse(model.calls)


class QuantitativeTests(unittest.TestCase):
    def test_exact_q4_results_and_interpretation_review(self):
        with TemporaryProject() as project:
            model = ScriptedModel({"quantitative-sql": "SELECT SUM(revenue) AS revenue FROM sales WHERE date >= '2025-10-01' AND date < '2026-01-01'",
                                   "quantitative-answer": "Q4 2025 revenue is $245,000. [SQL result]",
                                   "quantitative-review": good_review()})
            result = quantitative.run("Q4 2025 revenue?", model, project.settings)
            self.assertEqual(result["rows"], [(245000.0,)])
            self.assertFalse(result["check"]["flag"])

    def test_non_select_blocked_before_interpretation(self):
        with TemporaryProject() as project:
            model = ScriptedModel({"quantitative-sql": "DELETE FROM sales"})
            result = quantitative.run("Delete sales", model, project.settings)
            self.assertEqual(result["validation"], "FAILED")
            self.assertEqual(len(model.calls), 1)

    def test_execution_failure_is_not_an_answer(self):
        with TemporaryProject() as project:
            model = ScriptedModel({"quantitative-sql": "SELECT imaginary_column FROM sales",
                                   "quantitative-sql-repair": "SELECT still_imaginary FROM sales"})
            result = quantitative.run("Revenue?", model, project.settings)
            self.assertEqual(result["validation"], "ERROR")
            self.assertTrue(result["check"]["flag"])

    def test_wrong_number_flagged_after_successful_sql(self):
        with TemporaryProject() as project:
            model = ScriptedModel({"quantitative-sql": "SELECT COUNT(*) FROM customers",
                                   "quantitative-answer": "There are 99 customers. [SQL result]",
                                   "quantitative-review": {"supported": False, "issues": ["Actual count is 12"]}})
            self.assertTrue(quantitative.run("Customer count?", model, project.settings)["check"]["flag"])

    def test_schema_repair_is_bounded_and_revalidated(self):
        with TemporaryProject() as project:
            model = ScriptedModel({"quantitative-sql": "SELECT satisfsaction_score FROM employees",
                                   "quantitative-sql-repair": "DELETE FROM employees"})
            result = quantitative.run("Employee satisfaction?", model, project.settings)
            self.assertEqual(result["validation"], "FAILED")
            self.assertEqual(len(model.calls), 2)

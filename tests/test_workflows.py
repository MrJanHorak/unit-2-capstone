"""Offline integration tests: real SQLite + real orchestrator, scripted API only."""
import json
import unittest
from dataclasses import replace
from agents.manager import Session
from tests.helpers import CHUNKS, ScriptedModel, TemporaryProject, good_review, routing_plan


def responses(route="both"):
    plan = routing_plan(route, "Reviews and customer count?")
    if route == "both":
        plan.update(document_question="Code review requirements?", data_question="Customer count?")
    return {"manager-classifier": plan,
            "qualitative-answer": "Two peer reviews are required. [Source 1]",
            "qualitative-review": good_review(), "quantitative-sql": "SELECT COUNT(*) AS customers FROM customers",
            "quantitative-answer": "There are 12 customers. [SQL result]", "quantitative-review": good_review(),
            "manager-synthesis": "Two reviews are required [Source 1]; there are 12 customers [SQL result].",
            "synthesis-review": good_review()}


class WorkflowTests(unittest.TestCase):
    def make_session(self, project, script):
        self.models = []
        def factory(settings, ledger):
            model = ScriptedModel(script, ledger)
            self.models.append(model)
            return model
        return Session(project.settings, factory, lambda q, s: CHUNKS)

    def test_both_workflow_combines_raw_evidence_and_logs_all_stages(self):
        with TemporaryProject() as project:
            session = self.make_session(project, responses())
            result = session.run("Reviews and customer count?")
            self.assertEqual(result["status"], "accepted")
            self.assertEqual(len(result["tokenomics"]["calls"]), 8)
            record = json.loads(project.settings.log_path.read_text())
            self.assertEqual(record["input_tokens"], 80)
            self.assertIn("12 customers", result["answer"])
            quant_prompt = next(prompt for stage, prompt, config in self.models[0].calls if stage == "quantitative-sql")
            self.assertEqual(json.loads(quant_prompt)["question"], "Customer count?")

    def test_follow_up_receives_history_reset_clears_it(self):
        with TemporaryProject() as project:
            session = self.make_session(project, responses("quantitative"))
            session.run("Customer count?")
            session.run("What about that population?")
            history = json.loads(self.models[-1].calls[0][1])["history"]
            self.assertEqual(len(history), 1)
            session.reset()
            self.assertFalse(session.history)

    def test_failed_agent_answer_never_reaches_final_or_history(self):
        with TemporaryProject() as project:
            script = responses("qualitative")
            script["qualitative-answer"] = "SECRET_UNSUPPORTED_CLAIM [Source 1]"
            script["qualitative-review"] = {"supported": False, "issues": ["Unsupported"]}
            session = self.make_session(project, script)
            result = session.run("Reviews?")
            self.assertEqual(result["status"], "flagged")
            self.assertNotIn("SECRET_UNSUPPORTED_CLAIM", result["answer"])
            self.assertFalse(session.history)

    def test_failed_final_synthesis_is_withheld(self):
        with TemporaryProject() as project:
            script = responses()
            script["synthesis-review"] = {"supported": False, "issues": ["Invented causal relationship"]}
            result = self.make_session(project, script).run("Mixed question?")
            self.assertEqual(result["status"], "flagged")
            self.assertIn("synthesis_candidate", result)

    def test_reviewer_failure_is_logged_and_withheld(self):
        with TemporaryProject() as project:
            script = responses("qualitative")
            script["qualitative-review"] = RuntimeError("Review unavailable")
            session = self.make_session(project, script)
            result = session.run("Reviews?")
            self.assertEqual(result["status"], "error")
            self.assertEqual(len(result["tokenomics"]["calls"]), 3)
            self.assertFalse(session.history)

    def test_history_is_bounded(self):
        with TemporaryProject() as project:
            session = self.make_session(project, responses("qualitative"))
            session.settings = replace(project.settings, history_turns=2)
            for query in ("A?", "B?", "C?"):
                session.run(query)
            self.assertEqual(len(session.history), 2)

    def test_empty_query_is_rejected_without_api_or_log(self):
        with TemporaryProject() as project:
            session = self.make_session(project, responses())
            with self.assertRaises(ValueError):
                session.run("   ")
            self.assertFalse(project.settings.log_path.exists())

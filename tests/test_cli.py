"""Ensure internal rejected candidates cannot escape through public CLI JSON."""
import contextlib
import io
import json
import unittest
from unittest.mock import Mock, patch
import main


class CLITests(unittest.TestCase):
    def test_public_json_withholds_internal_candidates(self):
        session = Mock()
        session.run.return_value = {"status": "flagged", "answer": "Candidate withheld.",
                                    "agents": {"qualitative": {"answer": "UNVERIFIED_SECRET"}},
                                    "synthesis_candidate": "UNVERIFIED_SECRET"}
        output = io.StringIO()
        with patch("main.Session", return_value=session), patch("sys.argv", ["main.py", "--query", "Policy?", "--json"]), contextlib.redirect_stdout(output):
            self.assertEqual(main.main(), 1)
        public = json.loads(output.getvalue())
        self.assertNotIn("agents", public)
        self.assertNotIn("synthesis_candidate", public)
        self.assertNotIn("UNVERIFIED_SECRET", output.getvalue())

    def test_reset_and_eof_do_not_make_api_queries(self):
        session = Mock()
        with patch("main.Session", return_value=session), patch("sys.argv", ["main.py"]), patch(
                "builtins.input", side_effect=["", "/reset", EOFError()]), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main.main(), 0)
        session.reset.assert_called_once()
        session.run.assert_not_called()

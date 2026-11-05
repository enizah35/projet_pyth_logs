"""Vérifier le raccordement du main sans livrer P1 ou P3 à leur place."""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType
import unittest
from unittest.mock import Mock, patch

import main
from tests.p2_helpers import make_record


class MainTests(unittest.TestCase):
    def test_connects_p1_to_real_p2_then_p3_in_one_pass(self) -> None:
        paths = [Path("first.jsonl"), Path("second.jsonl")]
        blacklist = frozenset({"192.168.1.66"})
        seen = []

        def source():
            for line in ("\n", "invalid", "first", "second"):
                seen.append(line)
                yield line

        records = {
            "invalid": None,
            "first": make_record(level=" warning ", ip="192.168.1.66"),
            "second": make_record(level=" info "),
        }
        ingestion = ModuleType("logengine.ingestion")
        ingestion.read_sources = Mock(return_value=source())
        parsing = ModuleType("logengine.parsing")
        parsing.parse_line = Mock(side_effect=records.__getitem__)
        analysis = ModuleType("logengine.analysis")

        def analyze(checked, *, blacklist, threshold):
            self.assertEqual(seen, [])
            self.assertIsInstance(blacklist, frozenset)
            self.assertEqual(threshold, 3)
            output = list(checked)
            self.assertEqual([r["level"] for r in output], ["WARNING", "INFO"])
            self.assertEqual(output[0]["alerts"][0]["type"], "blacklist")
            self.assertEqual(output[1]["alerts"], [])
            return {"total": len(output)}

        analysis.analyze = Mock(side_effect=analyze)
        with patch.dict("sys.modules", {
            "logengine.ingestion": ingestion,
            "logengine.parsing": parsing,
            "logengine.analysis": analysis,
        }):
            result = main.run_project(paths, blacklist, 3)

        self.assertEqual(result, {"total": 2})
        ingestion.read_sources.assert_called_once_with(paths)
        self.assertEqual(parsing.parse_line.call_count, 3)
        analysis.analyze.assert_called_once()

    def test_cli_displays_p3_summary_and_exports_real_audit(self) -> None:
        record = make_record()
        summary = {"total": 1, "ips": {"192.168.1.20", "192.168.1.10"},
                   "timestamp": record["timestamp"]}
        with TemporaryDirectory() as directory:
            root = Path(directory)
            blacklist = root / "blacklist.txt"
            blacklist.write_text(" 192.168.1.66 \n\n192.168.1.66\n", encoding="utf-8")
            audit = root / "output" / "audit.json"
            stdout = StringIO()
            with patch.object(main, "run_project", return_value=summary) as run:
                with redirect_stdout(stdout):
                    result = main.main([
                        "one.jsonl", "two.jsonl", "--blacklist", str(blacklist),
                        "--threshold", "4", "--audit", str(audit),
                    ])
            run.assert_called_once_with(
                [Path("one.jsonl"), Path("two.jsonl")],
                frozenset({"192.168.1.66"}), 4,
            )
            displayed = json.loads(stdout.getvalue().split("\nAudit : ")[0])
            self.assertEqual(displayed["ips"], ["192.168.1.10", "192.168.1.20"])
            self.assertEqual(displayed["timestamp"], record["timestamp"].isoformat())
            scope = json.loads(audit.read_text(encoding="utf-8"))
            self.assertEqual(scope["locals"]["blacklist"], "frozenset")
            self.assertEqual(scope["locals"]["summary"], "dict")
            self.assertEqual(result, 0)

    def test_reports_missing_team_module_but_keeps_other_import_errors_visible(self) -> None:
        for name in ("logengine.ingestion", "logengine.parsing", "logengine.analysis"):
            with self.subTest(name=name):
                stderr = StringIO()
                with patch.object(main, "run_project", side_effect=ModuleNotFoundError(name=name)):
                    with redirect_stderr(stderr), self.assertRaises(SystemExit) as error:
                        main.main([])
                self.assertEqual(error.exception.code, 2)
                self.assertIn(name, stderr.getvalue())
                self.assertIn("--demo-p2", stderr.getvalue())

        with patch.object(main, "run_project", side_effect=ModuleNotFoundError(name="other_dependency")):
            with self.assertRaises(ModuleNotFoundError):
                main.main([])

    def test_invalid_threshold_stops_before_processing(self) -> None:
        for threshold in ("0", "-2", "abc"):
            with self.subTest(threshold=threshold):
                with patch.object(main, "run_project") as run:
                    with redirect_stderr(StringIO()), self.assertRaises(SystemExit) as error:
                        main.main(["--threshold", threshold])
                self.assertEqual(error.exception.code, 2)
                run.assert_not_called()


if __name__ == "__main__":
    unittest.main()

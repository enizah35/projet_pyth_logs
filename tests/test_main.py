"""Tests du point d'entrée : raccordement des trois parties."""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
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
        read_sources = Mock(return_value=source())
        parse_line = Mock(side_effect=records.__getitem__)

        def analyze(checked, *, blacklist, threshold):
            self.assertEqual(seen, [])
            self.assertIsInstance(blacklist, frozenset)
            self.assertEqual(threshold, 3)
            output = list(checked)
            self.assertEqual([r["level"] for r in output], ["WARNING", "INFO"])
            self.assertEqual(output[0]["alerts"][0]["type"], "blacklist")
            self.assertEqual(output[1]["alerts"], [])
            return {"total": len(output)}

        fake_analyze = Mock(side_effect=analyze)
        # On remplace les fonctions de P1 et P3 par des versions de test.
        with patch.object(main, "read_sources", read_sources),                 patch.object(main, "parse_line", parse_line),                 patch.object(main, "analyze", fake_analyze):
            result = main.run_project(paths, blacklist, 3)

        self.assertEqual(result, {"total": 2})
        read_sources.assert_called_once_with(paths)
        self.assertEqual(parse_line.call_count, 3)
        fake_analyze.assert_called_once()

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

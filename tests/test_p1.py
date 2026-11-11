"""Tests P1 : lecture, parsing, générateur et mode --details."""

import argparse
from contextlib import redirect_stdout
from datetime import datetime
from io import StringIO
import itertools
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import main
from logengine.ingestion import read_lines, read_sources
from logengine.parsing import parse_line, parse_line_details
from scripts.generate_logs import (
    generate_records, main as generate_main, size_in_bytes, write_logs,
)

ROOT = Path(__file__).resolve().parents[1]


class IngestionTests(unittest.TestCase):
    def test_order_empty_utf8_and_final_line(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory) / str(i) for i in range(3)]
            for path, content in zip(paths, ("été\nfin", "", "suite\n")):
                path.write_text(content, encoding="utf-8")
            self.assertEqual(
                list(read_sources(paths)), ["été\n", "fin", "suite\n"]
            )

    def test_lazy_open_and_close(self):
        source = StringIO("a\nb\n")
        with patch("builtins.open", return_value=source) as opened:
            lines = read_lines("unused")
            opened.assert_not_called()
            self.assertEqual(next(lines), "a\n")
            self.assertFalse(source.closed)
            lines.close()
            self.assertTrue(source.closed)

    def test_multisource_is_lazy_and_closes_delegate(self):
        first, second = StringIO("a\n"), StringIO("b\n")
        with patch("builtins.open", side_effect=[first, second]) as opened:
            lines = read_sources(["first", "second"])
            self.assertEqual(next(lines), "a\n")
            self.assertEqual(opened.call_count, 1)
            self.assertEqual(next(lines), "b\n")
            self.assertTrue(first.closed)
            lines.close()
            self.assertTrue(second.closed)

    def test_missing_file_and_invalid_utf8(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "logs"
            lines = read_lines(path)
            with self.assertRaises(FileNotFoundError):
                next(lines)
            path.write_bytes(b"\xff\n")
            with self.assertRaises(UnicodeDecodeError):
                list(read_lines(path))

    def test_read_failure_closes_file(self):
        class BrokenSource(StringIO):
            def __next__(self):
                raise OSError("lecture interrompue")

        source = BrokenSource()
        with patch("builtins.open", return_value=source):
            with self.assertRaises(OSError):
                next(read_lines("unused"))
        self.assertTrue(source.closed)


class ParsingTests(unittest.TestCase):
    def setUp(self):
        self.record = next(generate_records())

    def test_types_preservation_and_payloads(self):
        for payload in ({"event": "request"}, "message", {}):
            with self.subTest(payload=payload):
                self.record.update(
                    level=" warning ", payload=payload, extra=42
                )
                result = parse_line(json.dumps(self.record))
                self.assertIsInstance(result["timestamp"], datetime)
                self.assertIsInstance(result["connection"], tuple)
                self.assertEqual(result["level"], " warning ")
                self.assertEqual(result["payload"], payload)
                self.assertEqual(result["extra"], 42)
        self.record["level"] = "CUSTOM"
        self.assertIsNotNone(parse_line(json.dumps(self.record)))

    def test_blank_is_silent(self):
        with self.assertNoLogs("logengine.parsing", level="WARNING"):
            self.assertIsNone(parse_line(" \n\t"))

    def test_no_undocumented_business_validation(self):
        self.record.update(timestamp="2026-11-05T10:00:00+02:00",
                           ip="IP fictive", user_id="", level="CUSTOM",
                           connection=["autre IP", -1, "protocole fictif"])
        result = parse_line(json.dumps(self.record))
        self.assertIsNotNone(result)
        self.assertIsNotNone(result["timestamp"].tzinfo)

    def test_missing_fields(self):
        for field in self.record:
            record = self.record.copy()
            del record[field]
            with self.subTest(field=field):
                with self.assertLogs("logengine.parsing"):
                    self.assertIsNone(parse_line(json.dumps(record)))

    def test_incorrect_types_and_values(self):
        invalid = {
            "timestamp": [None, 123, "2026-02-30T12:00:00"],
            "level": [None, 2], "ip": [[], 4], "user_id": [False, {}],
            "connection": [None, {}, [], ["ip", 443], ["ip", 443, "p", 0],
                           ["ip", True, "p"], ["ip", "443", "p"],
                           ["ip", 443.0, "p"], [0, 443, "p"], ["ip", 443, 0]],
            "payload": [None, [], 1, True],
        }
        for field, values in invalid.items():
            for value in values:
                record = dict(self.record, **{field: value})
                with self.subTest(field=field, value=value):
                    with self.assertLogs("logengine.parsing"):
                        self.assertIsNone(parse_line(json.dumps(record)))
        for line in ('{"timestamp":', "[]", "null", '"texte"'):
            with self.subTest(line=line), self.assertLogs("logengine.parsing"):
                self.assertIsNone(parse_line(line))

    def test_demo_and_continuation_after_error(self):
        with self.assertLogs("logengine.parsing") as logs:
            records = [record for line in read_lines(ROOT / "data/demo.jsonl")
                       if (record := parse_line(line)) is not None]
        self.assertEqual(len(records), 10)
        self.assertEqual(len(logs.output), 1)
        valid = json.dumps(self.record)
        with self.assertLogs("logengine.parsing"):
            self.assertEqual(sum(parse_line(line) is not None
                                 for line in (valid, "{", valid)), 2)


class GenerationTests(unittest.TestCase):
    def test_cli_and_overwrite_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "generated.jsonl"
            args = ["--output", str(path), "--size-gb", "0.000001"]
            with redirect_stdout(StringIO()):
                self.assertEqual(generate_main(args), 0)
            with patch("sys.stderr", new_callable=StringIO):
                with self.assertRaises(SystemExit) as error:
                    generate_main(args)
            self.assertEqual(error.exception.code, 1)

    def test_seed_population_and_chronology(self):
        records = list(itertools.islice(generate_records(7), 100))
        same = list(itertools.islice(generate_records(7), 100))
        different = list(itertools.islice(generate_records(8), 100))
        self.assertEqual(records, same)
        self.assertNotEqual(records, different)
        self.assertLessEqual(len({r["ip"] for r in records}), 32)
        dates = [r["timestamp"] for r in records]
        self.assertEqual(dates, sorted(dates))
        self.assertTrue(all(
            parse_line(json.dumps(record)) is not None for record in records
        ))

    def test_byte_target_reproducibility_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory) / str(i) for i in range(2)]
            for path in paths:
                written = write_logs(path, 4000, seed=3)
                self.assertEqual(written, path.stat().st_size)
                self.assertGreaterEqual(written, 4000)
                content = path.read_bytes()
                self.assertTrue(content.endswith(b"\n"))
                last_size = len(content.splitlines(True)[-1])
                self.assertLess(written - 4000, last_size)
                for line in content.decode("utf-8").splitlines():
                    self.assertIsNotNone(parse_line(line))
            self.assertEqual(paths[0].read_bytes(), paths[1].read_bytes())
            with self.assertRaises(FileExistsError):
                write_logs(paths[0], 1)

    def test_sizes(self):
        self.assertEqual(size_in_bytes("10"), 10_000_000_000)
        self.assertEqual(size_in_bytes("0.0000000001"), 1)
        for value in ("0", "-1", "nan", "inf", "abc"):
            with self.subTest(value=value):
                with self.assertRaises(argparse.ArgumentTypeError):
                    size_in_bytes(value)
        for value in (0, -1, True, 1.5):
            with self.assertRaises(ValueError):
                write_logs("unused", value)


class CliTests(unittest.TestCase):
    def test_details_fixture_and_summary(self):
        output = StringIO()
        with redirect_stdout(output):
            code = main.main([str(ROOT / "data/test_p1.jsonl"), "--details"])
        self.assertEqual(code, 0)
        text = output.getvalue()
        for expected in (
            "Ligne 1 : événement valide",
            "Ligne 2 : ligne vide ignorée",
            "Ligne 3 : rejetée — JSON malformé",
            "Ligne 4 : rejetée — champ manquant : timestamp",
            "Ligne 5 : événement valide",
            "Lignes lues : 5", "Événements valides : 2",
            "Lignes rejetées : 2", "Lignes vides ignorées : 1",
        ):
            self.assertIn(expected, text)

    def test_multisource_numbering_and_single_parse(self):
        output = StringIO()
        with redirect_stdout(output):
            with patch("main.parse_line_details", wraps=parse_line_details) as parse:
                result = main.main([
                    str(ROOT / "data/test_p1.jsonl"),
                    str(ROOT / "data/test_p1.jsonl"), "--details",
                ])
        self.assertEqual(result, 0)
        self.assertEqual(parse.call_count, 8)  # Les blancs ne sont pas parsés.
        self.assertIn("Ligne 10 : événement valide", output.getvalue())
        self.assertIn("Événements valides : 4", output.getvalue())
        self.assertIn("Lignes rejetées : 4", output.getvalue())
        self.assertIn("Lignes vides ignorées : 2", output.getvalue())

    def test_help(self):
        with redirect_stdout(StringIO()):
            with self.assertRaises(SystemExit) as error:
                main.parse_args(["--help"])
        self.assertEqual(error.exception.code, 0)

    def test_empty_input_blacklist_and_bad_encoding(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "logs"
            path.write_text("", encoding="utf-8")
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(main.main([str(path)]), 0)
            self.assertIn("Événements valides : 0", output.getvalue())
            path.write_text("\n ip \n ip\n\n", encoding="utf-8")
            self.assertEqual(main.load_blacklist(path), frozenset(("ip",)))
            path.write_bytes(b"\xff")
            with self.assertLogs(level="ERROR"):
                self.assertEqual(main.main([str(path)]), 1)

    def test_args_and_invalid_threshold(self):
        args = main.parse_args(["b", "a"])
        self.assertEqual(args.paths, [Path("b"), Path("a")])
        self.assertEqual(args.threshold, 3)
        for value in ("0", "-1", "abc"):
            with patch("sys.stderr", new_callable=StringIO):
                with self.assertRaises(SystemExit) as error:
                    main.parse_args(["a", "--threshold", value])
            self.assertEqual(error.exception.code, 2)

    def test_blacklist_demo_measure_and_error(self):
        self.assertEqual(main.load_blacklist(ROOT / "data/blacklist.txt"),
                         frozenset(("192.168.1.66", "192.168.1.99")))
        output = StringIO()
        with redirect_stdout(output), self.assertLogs("logengine.parsing"):
            code = main.main([str(ROOT / "data/demo.jsonl"), "--measure"])
        self.assertEqual(code, 0)
        self.assertIn("Événements valides : 10", output.getvalue())
        self.assertIn("Pic allocations Python", output.getvalue())
        with tempfile.TemporaryDirectory() as directory:
            with self.assertLogs(level="ERROR"):
                missing = str(Path(directory) / "absent")
                self.assertEqual(main.main([missing]), 1)


if __name__ == "__main__":
    unittest.main()

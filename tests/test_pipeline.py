"""Comportements de normalisation, routage et traitement à la demande."""

from copy import deepcopy
import unittest
from unittest.mock import Mock, call

from logengine.pipeline import (
    build_pipeline,
    normalize_record,
    normalize_records,
    route_value,
)
from tests.p2_helpers import make_record


class NormalizationTests(unittest.TestCase):
    def test_cleans_fields_without_changing_the_input(self) -> None:
        record = make_record(
            level=" warning ",
            ip=" 192.168.1.20 ",
            user_id=" bob ",
            connection=(" 192.168.1.20 ", 443, " https "),
            payload=" Health check OK ",
        )
        before = deepcopy(record)
        result = normalize_record(record)

        self.assertEqual(record, before)
        self.assertEqual(result["level"], "WARNING")
        self.assertEqual(result["ip"], "192.168.1.20")
        self.assertEqual(result["user_id"], "bob")
        self.assertEqual(result["connection"], ("192.168.1.20", 443, "HTTPS"))
        self.assertEqual(result["payload"], "Health check OK")
        self.assertIn("[WARNING] user=bob", result["message"])

    def test_preserves_structured_payload_and_datetime(self) -> None:
        record = make_record()
        result = normalize_record(record)
        self.assertEqual(result["payload"], record["payload"])
        self.assertEqual(result["timestamp"], record["timestamp"])
        self.assertEqual(result["payload_description"]["kind"], "event")
        self.assertEqual(
            result["connection_description"]["kind"], "connection"
        )

    def test_unknown_level_is_skipped_and_processing_continues(self) -> None:
        records = [make_record(level="debug"), make_record(level=" error ")]
        result = list(normalize_records(records))
        self.assertEqual([record["level"] for record in result], ["ERROR"])

    def test_empty_stream_is_valid(self) -> None:
        self.assertEqual(list(normalize_records(iter(()))), [])


class RoutingTests(unittest.TestCase):
    def test_supported_formats(self) -> None:
        cases = (
            ("message", "text", "message"),
            (
                {"event": "login", "status": "failure", "path": "/"},
                "event",
                "login : failure",
            ),
            ({"level": "ERROR", "code": 403}, "event", "ERROR code 403"),
            ({"other": 1}, "event", "événement structuré"),
            (
                ("192.168.1.20", 443, "HTTPS"),
                "connection",
                "HTTPS 192.168.1.20:443",
            ),
        )
        for value, kind, summary in cases:
            with self.subTest(value=value):
                self.assertEqual(
                    route_value(value),
                    {"kind": kind, "value": value, "summary": summary},
                )

    def test_dict_pattern_checks_value_types(self) -> None:
        # Un code qui n'est pas un entier ne correspond pas au motif
        # {"level": ..., "code": int()} : on retombe sur le cas dict().
        result = route_value({"level": "ERROR", "code": "403"})
        self.assertEqual(result["summary"], "événement structuré")

    def test_unsupported_format_uses_fallback(self) -> None:
        values = (None, 123, ("incomplete",), ["192.168.1.20", 443, "HTTPS"])
        for value in values:
            with self.subTest(value=value):
                self.assertEqual(route_value(value)["kind"], "unknown")


class PipelineTests(unittest.TestCase):
    def test_blanks_and_invalid_entries_do_not_stop_the_stream(self) -> None:
        parser = Mock(
            side_effect=[make_record(level=" warning "), None, make_record()]
        )
        lines = iter(["\n", "first", " \t ", "invalid", "last"])
        result = list(build_pipeline(lines, parser=parser))
        self.assertEqual(
            [record["level"] for record in result], ["WARNING", "INFO"]
        )
        self.assertEqual(
            parser.call_args_list,
            [call("first"), call("invalid"), call("last")],
        )

    def test_requests_only_the_next_record(self) -> None:
        seen = []

        def source():
            for line in ("first", "second"):
                seen.append(line)
                yield line

        parser = Mock(side_effect=lambda line: make_record())
        result = build_pipeline(source(), parser=parser)
        self.assertEqual(seen, [])
        parser.assert_not_called()
        next(result)
        self.assertEqual(seen, ["first"])
        self.assertEqual(parser.call_count, 1)
        next(result)
        self.assertEqual(seen, ["first", "second"])

    def test_parser_bug_is_not_silently_hidden(self) -> None:
        parser = Mock(side_effect=RuntimeError("bug du parseur"))
        with self.assertRaisesRegex(RuntimeError, "bug du parseur"):
            next(build_pipeline(["line"], parser=parser))

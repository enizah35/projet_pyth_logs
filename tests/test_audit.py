"""Audit de la portée choisie, sans export de valeurs ni lecture des flux."""

import json
from pathlib import Path
import tempfile
import unittest

from logengine.audit import export_audit


class AuditTests(unittest.TestCase):
    def test_exports_names_and_types_not_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested/audit.json"
            export_audit(path, {"secret": "do-not-export-this"}, {"count": 3})
            text = path.read_text(encoding="utf-8")
            report = json.loads(text)
        self.assertEqual(
            report,
            {"globals": {"secret": "str"}, "locals": {"count": "int"}},
        )
        self.assertNotIn("do-not-export-this", text)

    def test_does_not_consume_a_generator(self) -> None:
        seen = []

        def source():
            seen.append("consumed")
            yield "event"

        records = source()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.json"
            export_audit(path, {}, {"records": records})
            report = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(seen, [])
        self.assertEqual(report["locals"]["records"], "generator")

    def test_caller_can_select_its_scope_with_globals_and_locals(self) -> None:
        local_counter = 10
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.json"
            export_audit(path, globals(), locals())
            report = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(report["locals"]["local_counter"], "int")
        self.assertIn("AuditTests", report["globals"])

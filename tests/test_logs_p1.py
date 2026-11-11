"""Tests P2 : pipeline sur le fichier de logs de P1."""

from datetime import datetime
import json
import os
import unittest

from logengine.pipeline import build_pipeline
from logengine.rules import apply_security_rules, rule_blacklist, rule_critical


TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_PATH = os.path.join(TESTS_DIR, "..", "data", "logs_test_p1.jsonl")


def read_lines(path: str):
    """Lire le fichier ligne par ligne, sans le charger en entier."""
    with open(path, "r", encoding="utf-8") as source:
        for line in source:
            yield line


def simple_parser(line: str) -> dict | None:
    """Parseur minimal réservé à ce test, en attendant parse_line de P1.

    Il respecte le contrat : date en datetime, connexion en tuple et
    None pour une ligne qui n'est pas du JSON.
    """
    try:
        record = json.loads(line)
    except json.JSONDecodeError:
        return None
    record["timestamp"] = datetime.fromisoformat(record["timestamp"])
    record["connection"] = tuple(record["connection"])
    return record


def run_chain(*rules) -> list[dict]:
    """Lancer lecture, pipeline et règles sur le fichier de P1.

    Le fichier ne contient que dix lignes : on peut garder le résultat
    dans une liste pour le vérifier.
    """
    records = build_pipeline(read_lines(LOGS_PATH), parser=simple_parser)
    checked = apply_security_rules(
        *rules, records=records, blacklist=frozenset({"192.168.1.66"})
    )
    return list(checked)


class LogsP1Tests(unittest.TestCase):
    def test_ten_events_are_kept(self) -> None:
        self.assertEqual(len(run_chain()), 10)

    def test_levels_are_counted_as_expected(self) -> None:
        counts = {}
        for record in run_chain():
            level = record["level"]
            counts[level] = counts.get(level, 0) + 1
        self.assertEqual(
            counts, {"INFO": 4, "WARNING": 3, "ERROR": 2, "CRITICAL": 1}
        )

    def test_connections_are_tuples(self) -> None:
        for record in run_chain():
            self.assertIsInstance(record["connection"], tuple)
            self.assertEqual(
                record["connection_description"]["kind"], "connection"
            )

    def test_raw_text_payload_is_recognized(self) -> None:
        # Seul david envoie une chaîne brute : "Service unavailable".
        texts = []
        for record in run_chain():
            if record["payload_description"]["kind"] == "text":
                texts.append(record["user_id"])
        self.assertEqual(texts, ["david"])

    def test_no_ip_of_this_file_is_blacklisted(self) -> None:
        for record in run_chain(rule_blacklist):
            self.assertEqual(record["alerts"], [])

    def test_critical_rule_finds_the_admin_event(self) -> None:
        users = []
        for record in run_chain(rule_blacklist, rule_critical):
            for alert in record["alerts"]:
                users.append((alert["type"], alert["user_id"]))
        self.assertEqual(users, [("critical", "admin")])


if __name__ == "__main__":
    unittest.main()

"""Tests P2 : règles de sécurité et moteur."""

import unittest

from logengine.rules import apply_security_rules, rule_blacklist, rule_critical
from tests.p2_helpers import make_record


class SecurityRuleTests(unittest.TestCase):
    def test_blacklist_alert_has_the_shared_fields(self) -> None:
        record = make_record(ip="203.0.113.7", user_id="another_user")
        alert = rule_blacklist(record, blacklist=frozenset({"203.0.113.7"}))
        self.assertEqual(
            alert,
            {
                "type": "blacklist",
                "timestamp": "2026-11-05T10:00:01",
                "ip": "203.0.113.7",
                "user_id": "another_user",
                "message": "IP présente dans la blacklist",
            },
        )

    def test_allowed_ip_has_no_alert(self) -> None:
        self.assertIsNone(rule_blacklist(make_record(), blacklist=frozenset()))

    def test_missing_blacklist_is_a_configuration_error(self) -> None:
        with self.assertRaises(KeyError):
            rule_blacklist(make_record())

    def test_critical_rule_is_independent(self) -> None:
        alert = rule_critical(make_record(level="CRITICAL"))
        self.assertEqual(alert["type"], "critical")
        self.assertIsNone(rule_critical(make_record(level="ERROR")))

    def test_without_rules_events_are_preserved(self) -> None:
        record = make_record()
        result = list(apply_security_rules(records=[record]))
        self.assertEqual(result, [{**record, "alerts": []}])
        self.assertNotIn("alerts", record)

    def test_normal_events_are_not_lost(self) -> None:
        records = [
            make_record(ip="192.168.1.20"),
            make_record(ip="192.168.1.66"),
        ]
        result = list(
            apply_security_rules(
                rule_blacklist,
                records=records,
                blacklist=frozenset({"192.168.1.66"}),
            )
        )
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["alerts"], [])
        self.assertEqual(len(result[1]["alerts"]), 1)

    def test_multiple_rules_receive_configuration(self) -> None:
        def custom_rule(record, **config):
            if record["user_id"] == config["user_to_flag"]:
                return {"type": "custom"}
            return None

        result = list(
            apply_security_rules(
                rule_blacklist,
                rule_critical,
                custom_rule,
                records=[make_record(level="CRITICAL")],
                blacklist=frozenset({"192.168.1.20"}),
                user_to_flag="bob",
            )
        )
        self.assertEqual(
            [alert["type"] for alert in result[0]["alerts"]],
            ["blacklist", "critical", "custom"],
        )

    def test_keeps_existing_alerts_without_mutating_them(self) -> None:
        old_alerts = [{"type": "previous"}]
        record = make_record(level="CRITICAL", alerts=old_alerts)
        result = next(apply_security_rules(rule_critical, records=[record]))
        self.assertEqual(
            [alert["type"] for alert in result["alerts"]],
            ["previous", "critical"],
        )
        self.assertEqual(old_alerts, [{"type": "previous"}])

    def test_rule_engine_is_lazy(self) -> None:
        seen = []

        def source():
            for i in range(3):
                seen.append(i)
                yield make_record()

        result = apply_security_rules(records=source())
        self.assertEqual(seen, [])
        next(result)
        self.assertEqual(seen, [0])

    def test_rule_errors_are_not_swallowed(self) -> None:
        def broken_rule(record, **config):
            raise RuntimeError("bug de règle")

        with self.assertRaisesRegex(RuntimeError, "bug de règle"):
            next(apply_security_rules(broken_rule, records=[make_record()]))

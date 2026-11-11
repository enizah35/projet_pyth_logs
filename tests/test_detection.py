"""Tests P3 : détection de force brute."""

from datetime import datetime, timedelta
import unittest

from logengine.detection import BruteForceDetector, is_login_attempt

START = datetime(2026, 11, 5, 10, 0, 0)


def make_event(
    second: int,
    status: str = "failure",
    ip: str = "10.0.0.1",
    user_id: str = "user",
    event: str = "login",
) -> dict:
    """Fabriquer un événement minimal conforme au contrat commun."""
    return {
        "timestamp": START + timedelta(seconds=second),
        "level": "WARNING",
        "ip": ip,
        "user_id": user_id,
        "connection": (ip, 22, "TCP"),
        "payload": {"event": event, "status": status},
        "alerts": [],
    }


def run(detector: BruteForceDetector, events: list[dict]) -> list[dict]:
    """Passer les événements au détecteur et garder les alertes émises."""
    alerts = []
    for event in events:
        alert = detector.process(event)
        if alert is not None:
            alerts.append(alert)
    return alerts


class TestBruteForceDetector(unittest.TestCase):

    def test_below_threshold_gives_no_alert(self) -> None:
        detector = BruteForceDetector(3)
        events = [make_event(0), make_event(1)]
        self.assertEqual(run(detector, events), [])

    def test_threshold_gives_one_alert_in_common_format(self) -> None:
        detector = BruteForceDetector(3)
        alerts = run(detector, [make_event(s) for s in range(3)])
        self.assertEqual(len(alerts), 1)
        self.assertEqual(
            alerts[0],
            {
                "type": "brute_force",
                "timestamp": "2026-11-05T10:00:02",
                "ip": "10.0.0.1",
                "user_id": "user",
                "message": "3 échecs de connexion consécutifs",
            },
        )

    def test_no_second_alert_before_a_success(self) -> None:
        detector = BruteForceDetector(3)
        alerts = run(detector, [make_event(s) for s in range(6)])
        self.assertEqual(len(alerts), 1)

    def test_success_resets_the_series(self) -> None:
        detector = BruteForceDetector(3)
        events = [
            make_event(0),
            make_event(1),
            make_event(2, status="success"),
            make_event(3),
            make_event(4),
        ]
        self.assertEqual(run(detector, events), [])

    def test_new_alert_possible_after_success(self) -> None:
        detector = BruteForceDetector(2)
        events = [
            make_event(0),
            make_event(1),
            make_event(2, status="success"),
            make_event(3),
            make_event(4),
        ]
        self.assertEqual(len(run(detector, events)), 2)

    def test_interleaved_activity_does_not_reset(self) -> None:
        detector = BruteForceDetector(3)
        events = [
            make_event(0),
            make_event(1, user_id="other", status="success"),
            make_event(2, event="request"),
            make_event(3),
            make_event(4, ip="10.0.0.2"),
            make_event(5),
        ]
        alerts = run(detector, events)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["timestamp"], "2026-11-05T10:00:05")

    def test_two_users_behind_same_ip_are_independent(self) -> None:
        detector = BruteForceDetector(2)
        events = [
            make_event(0, user_id="a"),
            make_event(1, user_id="b"),
            make_event(2, user_id="a"),
        ]
        alerts = run(detector, events)
        self.assertEqual([alert["user_id"] for alert in alerts], ["a"])

    def test_request_failure_is_not_a_login_failure(self) -> None:
        detector = BruteForceDetector(1)
        event = make_event(0, event="request")
        self.assertFalse(is_login_attempt(event))
        self.assertIsNone(detector.process(event))

    def test_text_payload_is_ignored(self) -> None:
        detector = BruteForceDetector(1)
        event = make_event(0)
        event["payload"] = "Health check OK"
        self.assertFalse(is_login_attempt(event))
        self.assertIsNone(detector.process(event))

    def test_unknown_status_is_reported_and_ignored(self) -> None:
        detector = BruteForceDetector(2)
        with self.assertLogs("logengine.detection", level="WARNING"):
            alert = detector.process(make_event(0, status="timeout"))
        self.assertIsNone(alert)
        # Le statut inconnu n'a ni allongé ni remis à zéro la série.
        events = [make_event(1), make_event(2)]
        self.assertEqual(len(run(detector, events)), 1)

    def test_series_continues_across_two_files(self) -> None:
        # Un seul détecteur par lancement : l'état passe d'un fichier
        # à l'autre.
        detector = BruteForceDetector(3)
        first_file = [make_event(0), make_event(1)]
        second_file = [make_event(2)]
        self.assertEqual(run(detector, first_file), [])
        self.assertEqual(len(run(detector, second_file)), 1)

    def test_invalid_threshold_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            BruteForceDetector(0)


if __name__ == "__main__":
    unittest.main()

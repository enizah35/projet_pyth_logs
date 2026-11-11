import unittest
 
from logengine.analysis import analyze
from tests.sample_records import BLACKLIST, RECORDS
 
 
class TestAnalyze(unittest.TestCase):
    """Vérifie le bilan produit par analyze() sur les 10 événements."""
 
    def setUp(self) -> None:
        self.summary = analyze(iter(RECORDS), blacklist=BLACKLIST, threshold=3)
 
    def test_total(self) -> None:
        self.assertEqual(self.summary["total"], 10)
 
    def test_by_level(self) -> None:
        expected = {"INFO": 4, "WARNING": 3, "ERROR": 2, "CRITICAL": 1}
        self.assertEqual(self.summary["by_level"], expected)
 
    def test_by_user(self) -> None:
        expected = {"alice": 3, "bob": 5, "carol": 1, "service": 1}
        self.assertEqual(self.summary["by_user"], expected)
 
    def test_active_ips(self) -> None:
        expected = {
            "192.168.1.10",
            "192.168.1.20",
            "192.168.1.30",
            "192.168.1.66",
        }
        self.assertEqual(self.summary["active_ips"], expected)
 
    def test_error_ips(self) -> None:
        expected = {"192.168.1.10", "192.168.1.20", "192.168.1.66"}
        self.assertEqual(self.summary["error_ips"], expected)
 
    def test_ip_sets(self) -> None:
        ip_sets = self.summary["ip_sets"]
        self.assertEqual(
            ip_sets["union"],
            {
                "192.168.1.10",
                "192.168.1.20",
                "192.168.1.30",
                "192.168.1.66",
                "192.168.1.99",
            },
        )
        self.assertEqual(ip_sets["intersection"], {"192.168.1.66"})
        self.assertEqual(
            ip_sets["active_only"],
            {"192.168.1.10", "192.168.1.20", "192.168.1.30"},
        )
        self.assertEqual(ip_sets["blacklist_only"], {"192.168.1.99"})
        self.assertEqual(
            ip_sets["symmetric_difference"],
            {"192.168.1.10", "192.168.1.20", "192.168.1.30", "192.168.1.99"},
        )
 
    def test_alerts_by_type(self) -> None:
        self.assertEqual(
            self.summary["alerts_by_type"],
            {"blacklist": 1, "brute_force": 1},
        )
 
    def test_alert_samples(self) -> None:
        samples = self.summary["alert_samples"]
        found = {(a["type"], a["ip"], a["user_id"]) for a in samples}
        self.assertEqual(
            found,
            {
                ("blacklist", "192.168.1.66", "carol"),
                ("brute_force", "192.168.1.20", "bob"),
            },
        )
 
    def test_samples_are_capped_but_all_alerts_counted(self) -> None:
        flagged = RECORDS[5]
        stream = (flagged for _ in range(25))
        summary = analyze(stream, blacklist=BLACKLIST, threshold=3)
        self.assertEqual(summary["alerts_by_type"]["blacklist"], 25)
        self.assertEqual(len(summary["alert_samples"]), 20)
 
    def test_empty_stream(self) -> None:
        summary = analyze(iter([]), blacklist=BLACKLIST, threshold=3)
        self.assertEqual(summary["total"], 0)
        self.assertEqual(summary["ip_sets"]["blacklist_only"], BLACKLIST)
        self.assertEqual(summary["ip_sets"]["intersection"], set())
        self.assertEqual(
            summary["alerts_by_type"], {"blacklist": 0, "brute_force": 0}
        )
        self.assertEqual(summary["alert_samples"], [])
 
 
if __name__ == "__main__":
    unittest.main()
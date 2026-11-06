import unittest

from logengine.analysis import analyze
from tests.sample_records import BLACKLIST, RECORDS


class TestAnalyze(unittest.TestCase):
    """Vérifie le bilan produit par analyze() sur les 10 événements."""

    def setUp(self) -> None:
        # iter() simule un vrai flux : il ne peut être parcouru qu'une fois.
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
        # IP des événements de niveau ERROR ou CRITICAL.
        expected = {"192.168.1.10", "192.168.1.20", "192.168.1.66"}
        self.assertEqual(self.summary["error_ips"], expected)

    def test_empty_stream(self) -> None:
        # Un flux vide doit donner un bilan valide, sans erreur.
        summary = analyze(iter([]), blacklist=BLACKLIST, threshold=3)
        self.assertEqual(summary["total"], 0)


if __name__ == "__main__":
    unittest.main()
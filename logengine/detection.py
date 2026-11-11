#P3 : détection bruteforce

from collections import defaultdict
import logging

LOGGER = logging.getLogger(__name__)

LOGIN_EVENT = "login"
SUCCESS = "success"
FAILURE = "failure"


def is_login_attempt(record: dict) -> bool:
    """Dire si l'événement est une tentative de connexion structurée."""
    payload = record["payload"]
    return isinstance(payload, dict) and payload.get("event") == LOGIN_EVENT


class BruteForceDetector:
    """Compter les échecs consécutifs de chaque couple (ip, user_id)."""

    def __init__(self, threshold: int) -> None:
        if threshold < 1:
            raise ValueError("le seuil doit être strictement positif")
        self.threshold = threshold
        self._failures: defaultdict[tuple[str, str], int] = defaultdict(int)

    def process(self, record: dict) -> dict | None:
        """Mettre à jour l'état ; renvoyer une alerte ou None.

        L'appelant ne transmet que des tentatives de connexion
        (voir is_login_attempt), mais la méthode reste sûre sinon.
        """
        if not is_login_attempt(record):
            return None

        key = (record["ip"], record["user_id"])
        status = record["payload"].get("status")

        for known_status in (SUCCESS, FAILURE):
            if status != known_status:
                continue
            if known_status == SUCCESS:
                self._failures.pop(key, None)
                return None
            self._failures[key] += 1
            break
        else:
            LOGGER.warning(
                "Connexion ignorée par le détecteur : statut inconnu %r",
                status,
            )
            return None

        if self._failures[key] == self.threshold:
            return self._make_alert(record)
        return None

    def _make_alert(self, record: dict) -> dict:
        """Construire l'alerte au format commun (guide, page 5)."""
        return {
            "type": "brute_force",
            "timestamp": record["timestamp"].isoformat(),
            "ip": record["ip"],
            "user_id": record["user_id"],
            "message": f"{self.threshold} échecs de connexion consécutifs",
        }
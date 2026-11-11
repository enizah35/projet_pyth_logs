"""P3 : détection des attaques par force brute.

Une alerte est levée quand un couple (ip, user_id) atteint le seuil
d'échecs consécutifs ; une connexion réussie remet son compteur à zéro.
"""

from collections import defaultdict
import logging

LOGGER = logging.getLogger(__name__)

LOGIN_EVENT = "login"
SUCCESS = "success"
FAILURE = "failure"


def is_login_attempt(record: dict) -> bool:
    """Indiquer si l'événement est une tentative de connexion."""
    payload = record["payload"]
    return isinstance(payload, dict) and payload.get("event") == LOGIN_EVENT


class BruteForceDetector:
    """Compter les échecs consécutifs de chaque couple (ip, user_id)."""

    def __init__(self, threshold: int) -> None:
        """Préparer un compteur d'échecs vide pour le seuil donné."""
        if threshold < 1:
            raise ValueError("le seuil doit être strictement positif")
        self.threshold = threshold
        self._failures: defaultdict[tuple[str, str], int] = defaultdict(int)

    def process(self, record: dict) -> dict | None:
        """Mettre à jour le compteur ; renvoyer une alerte ou None."""
        if not is_login_attempt(record):
            return None

        key = (record["ip"], record["user_id"])
        status = record["payload"].get("status")

        # break : statut reconnu ; else : aucun break, statut inconnu
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

        # Une seule alerte par série : au moment exact du seuil
        if self._failures[key] == self.threshold:
            return self._make_alert(record)
        return None

    def _make_alert(self, record: dict) -> dict:
        """Construire l'alerte au format commun aux règles de P2."""
        return {
            "type": "brute_force",
            "timestamp": record["timestamp"].isoformat(),
            "ip": record["ip"],
            "user_id": record["user_id"],
            "message": f"{self.threshold} échecs de connexion consécutifs",
        }
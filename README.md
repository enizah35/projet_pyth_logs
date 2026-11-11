# Moteur d'analyse de logs en flux

Outil en ligne de commande qui lit des fichiers de logs JSON Lines, nettoie
les événements, applique des règles de sécurité et affiche un bilan :
activité par niveau et par utilisateur, IP en erreur, comparaison avec une
blacklist et détection des attaques par force brute.

Les logs sont traités en flux, un événement à la fois : un fichier de 10 Go
est analysé avec moins de 20 Mo de mémoire.

Projet ING3 en trinôme · Python 3.10 ou supérieur · bibliothèque standard
uniquement.

## Démarrage rapide

Sous PowerShell, depuis la racine du projet :

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py data/demo.jsonl --blacklist data/blacklist.txt --threshold 3
```

`requirements.txt` est vide : `pip freeze` ne renvoie aucune dépendance, le
projet n'utilise que la bibliothèque standard.

Sans argument, `python main.py` utilise `data/demo.jsonl` et
`data/blacklist.txt`.

## Exemple de résultat

Sur le jeu de démonstration (extrait du bilan JSON) :

```text
WARNING : Ligne rejetée : JSON malformé (Expecting value) ; extrait='{"timestamp":\n'
{
  "total": 10,
  "by_level": {"INFO": 4, "WARNING": 3, "ERROR": 2, "CRITICAL": 1},
  "by_user": {"alice": 3, "bob": 5, "carol": 1, "service": 1},
  "error_ips": ["192.168.1.10", "192.168.1.20", "192.168.1.66"],
  "ip_sets": {"intersection": ["192.168.1.66"], "blacklist_only": ["192.168.1.99"], ...},
  "alerts_by_type": {"blacklist": 1, "brute_force": 1},
  "alert_samples": [
    {"type": "brute_force", "user_id": "bob", "message": "3 échecs de connexion consécutifs", ...},
    {"type": "blacklist", "user_id": "carol", "message": "IP présente dans la blacklist", ...}
  ]
}
Audit : output\audit.json
Événements valides : 10
```

La ligne JSON cassée est signalée sans arrêter la lecture ; la ligne vide est
ignorée sans avertissement.

## Fonctionnement

```text
fichiers ──► lignes ──► dictionnaires ──► nettoyage ──► règles ──► analyse ──► bilan
          read_sources    parse_line    build_pipeline  apply_     analyze
              (P1)           (P1)            (P2)       security_   (P3)
                                                        rules (P2)
```

Chaque étape renvoie un itérateur : un événement traverse toute la chaîne
avant que la ligne suivante soit lue. Seuls des compteurs, des ensembles d'IP
et 20 exemples d'alertes sont conservés.

| Module | Rôle | Partie |
|---|---|---|
| `logengine/ingestion.py` | Lecture ligne par ligne d'un ou plusieurs fichiers | P1 |
| `logengine/parsing.py` | Ligne JSON → dictionnaire typé, ou `None` si invalide | P1 |
| `logengine/pipeline.py` | Filtrage, normalisation, reconnaissance des formats | P2 |
| `logengine/rules.py` | Règles de sécurité et moteur qui les applique | P2 |
| `logengine/audit.py` | Export des noms et types des variables d'une portée | P2 |
| `logengine/analysis.py` | Compteurs, ensembles d'IP, bilan | P3 |
| `logengine/detection.py` | Détection de force brute | P3 |
| `main.py` | Point d'entrée en ligne de commande | commun |
| `scripts/generate_logs.py` | Génération d'un gros fichier de test | P1 |

## Correspondance avec l'énoncé

| Exigence | Où la trouver |
|---|---|
| Générateur `yield` ligne par ligne | `ingestion.read_lines` |
| `yield from` sur plusieurs fichiers | `ingestion.read_sources` |
| Ligne parsée en dictionnaire, types variés | `parsing.parse_line` |
| Tuple immuable `(IP, port, protocole)` | champ `connection`, créé par `parse_line` |
| `filter()` + `lambda`, `filter(None, ...)` | `pipeline.build_pipeline` |
| `map()` de normalisation, f-strings | `pipeline.normalize_record`, `normalize_records` |
| `match-case` : chaîne brute, dictionnaire, tuple | `pipeline.route_value` |
| `set` des IP en erreur | `analysis.analyze` (`error_ips`) |
| `frozenset` et opérations `\|`, `&`, `-`, `^` | `main.load_blacklist`, `analysis.compare_with_blacklist` |
| `defaultdict` pour les compteurs | `analysis.analyze`, `detection.BruteForceDetector` |
| `while`, `for`, `break`, `continue`, `else` de boucle | `analysis.analyze`, `detection.BruteForceDetector.process` |
| `apply_security_rules(*args, **kwargs)`, fonctions en argument | `rules.apply_security_rules` |
| Audit avec `globals()` et `locals()` | `audit.export_audit`, appelé dans `main.py` |
| Traitement sans charger le fichier en RAM | essai sur 10 Go, voir plus bas |

Le lien entre ces notions et les supports de cours est détaillé dans
[docs/LIEN_AVEC_LES_COURS.md](docs/LIEN_AVEC_LES_COURS.md).

## Options de la commande

```powershell
.\.venv\Scripts\python.exe main.py [fichiers ...] [options]
```

| Option | Rôle | Défaut |
|---|---|---|
| `fichiers` | Un ou plusieurs fichiers JSONL, lus dans l'ordre donné | `data/demo.jsonl` |
| `--blacklist` | Fichier contenant une IP par ligne | `data/blacklist.txt` |
| `--threshold` | Échecs consécutifs déclenchant une alerte de force brute | `3` |
| `--audit` | Destination de l'audit des variables | `output/audit.json` |
| `--details` | Afficher la décision du parseur ligne par ligne, sans règles ni analyse | désactivé |
| `--measure` | Afficher durée, débit et pic d'allocations Python (ralentit le parcours) | désactivé |
| `--demo-p2` | Lancer la démonstration du pipeline et des règles, sans fichier | désactivé |

Codes de sortie : `0` si le parcours est terminé, même avec des lignes
rejetées ; `1` pour une erreur de fichier ou d'encodage ; `2` pour une erreur
d'arguments.

## Format des logs

Un objet JSON par ligne, par exemple :

```json
{"timestamp":"2026-11-05T10:00:01","level":"WARNING","ip":"192.168.1.20","user_id":"bob","connection":["192.168.1.20",443,"HTTPS"],"payload":{"event":"login","status":"failure"}}
```

| Champ | Contenu | Type après parsing |
|---|---|---|
| `timestamp` | Date ISO de l'événement | `datetime` |
| `level` | INFO, WARNING, ERROR ou CRITICAL | `str`, normalisé par P2 |
| `ip` | Adresse IP source | `str` |
| `user_id` | Identifiant utilisateur | `str` |
| `connection` | IP, port, protocole | `tuple[str, int, str]` |
| `payload` | Événement structuré ou message brut | `dict` ou `str` |

Les six champs sont obligatoires. Une ligne mal formée, un champ manquant ou
un mauvais type donnent un avertissement et la ligne est ignorée. Les espaces
et minuscules du niveau (`" warning "`) sont corrigés par la normalisation ;
un niveau inconnu est ensuite écarté.

Une tentative de connexion est un payload `{"event": "login", "status":
"success" | "failure"}`. La détection compte les échecs consécutifs par couple
`(ip, user_id)` ; une connexion réussie remet le compteur à zéro.

## Données de test

| Fichier | Contenu |
|---|---|
| `data/demo.jsonl` | 10 événements valides, une ligne JSON cassée et une ligne vide |
| `data/blacklist.txt` | 2 IP de test, dont une présente dans `demo.jsonl` |
| `data/test_p1.jsonl` | 5 lignes pour le mode `--details` : 2 valides, 2 rejetées, 1 vide |
| `data/logs_test_p1.jsonl` | 10 événements avec connexions SSH et payload texte |

Toutes les données sont fictives.

## Démonstrations

Pipeline et règles P2 sur trois événements, avec une puis deux règles :

```powershell
.\.venv\Scripts\python.exe main.py --demo-p2
```

Décision du parseur ligne par ligne :

```powershell
.\.venv\Scripts\python.exe main.py data/test_p1.jsonl --details
```

Résultat attendu : 5 lignes lues, 2 événements valides, 2 lignes rejetées et
1 ligne vide ignorée.

## Essai sur 10 Go

Générer le fichier (environ 17 minutes, 10 Go d'espace disque libre requis),
puis l'analyser :

```powershell
.\.venv\Scripts\python.exe scripts/generate_logs.py --output data/generated/logs_10go.jsonl --size-gb 10 --seed 0
.\.venv\Scripts\python.exe main.py data/generated/logs_10go.jsonl
```

Pour un premier essai rapide, utiliser `--size-gb 0.01` (10 Mo). Le
générateur refuse d'écraser un fichier existant. Le dossier
`data/generated/` est ignoré par Git.

Résultats mesurés sur la chaîne complète :

| Mesure | Valeur |
|---|---|
| Taille du fichier | 10 000 000 021 octets |
| Événements traités | 55 983 446 |
| Durée | 1 164 s, soit environ 48 000 événements/s |
| Pic de mémoire du processus | 19,5 Mo |

La mémoire reste stable car aucun événement n'est conservé. Elle grandirait
seulement avec le nombre d'IP et d'utilisateurs distincts.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

75 tests couvrent la lecture, le parsing, le pipeline, les règles, l'audit,
l'analyse, la détection et le raccordement dans `main.py`.

## Documentation

- [Partie P2 du rapport](docs/rapport_P2.md) : pipeline, règles, audit et mesures.
- [Analyse de P1](docs/ANALYSE_P1.md) ([PDF](docs/ANALYSE_P1.pdf)) et
  [bilan de P1](docs/BILAN_P1.md) : lecture, parsing et génération.
- [Lien avec les cours](docs/LIEN_AVEC_LES_COURS.md) : notions utilisées et
  supports correspondants.
- [Guide d'équipe](docs/GUIDE_EQUIPE.md) : contrat de données, répartition et
  résultats de référence.

## Équipe

- **P1** : lecture, parsing, ligne de commande et génération des données.
- **P2** : nettoyage, pipeline fonctionnel, règles de sécurité et audit.
- **P3** : statistiques, détection de force brute et rapport.

Dépôt : <https://github.com/enizah35/projet_pyth_logs>. Chaque partie est
développée sur sa branche, puis fusionnée dans `main` par pull request.

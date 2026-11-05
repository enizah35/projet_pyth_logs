# Projet Python : guide de réalisation pour trois personnes

Objectif de remise retenu : jeudi 12 novembre 2026. Ce guide propose des choix techniques communs ; ils ne constituent pas des consignes supplémentaires de l'enseignant.

Source : `ÉNONCÉ DU PROJET FINAL.pdf`, pages 1 à 4. Le dossier contenait seulement ce PDF avant l'ajout de ce guide et des données d'exemple. Vérifiez aussi votre espace de cours : si l'enseignant y fournit un format ou des données, adaptez le lecteur à ces données.

## 1. Le produit à construire

Un outil en ligne de commande qui lit des fichiers de logs, nettoie les événements, applique des règles de sécurité et affiche un bilan : activité, erreurs, adresses IP et alertes de connexions suspectes.

Un log est un événement enregistré par une application. Vos exemples peuvent être entièrement fictifs. Le projet doit démontrer le traitement de fichiers volumineux ou d'un flux simulé ; vous n'avez pas besoin d'un accès à un véritable serveur pour démarrer.

Commande cible à implémenter, qui ne fonctionne pas encore à ce stade :

```powershell
python main.py data/demo.jsonl --blacklist data/blacklist.txt --threshold 3
```

Produit attendu : des scripts Python organisés en package, un point d'entrée `main.py`, des données de démonstration, des dépendances reproductibles et un rapport synthétique PDF ou notebook. Les graphiques sont facultatifs pour la première version.

## 2. D'où viennent les logs et quel est leur format ?

### Choix de départ : des données synthétiques

Commencez avec le fichier `data/demo.jsonl` fourni avec ce guide. Il contient des événements fictifs ; aucune collecte réelle n'a été effectuée. Vous pourrez ensuite générer un grand fichier du même format. Un jeu externe n'est utile que si vous avez du temps pour adapter son format au vôtre.

Le format proposé est JSON Lines : un objet JSON complet par ligne, sans tableau englobant et sans virgule entre les lignes. L'extension `.jsonl` décrit ce choix. Le PDF n'impose pas cette extension.

Exemple d'une seule ligne, ici répartie sur plusieurs lignes uniquement pour expliquer les champs :

```json
{
  "timestamp": "2026-11-05T10:00:01",
  "level": "WARNING",
  "ip": "192.168.1.20",
  "user_id": "bob",
  "connection": ["192.168.1.20", 443, "HTTPS"],
  "payload": {"event": "login", "status": "failure"}
}
```

| Champ | Signification | Type dans le programme |
|---|---|---|
| `timestamp` | Moment où l'événement s'est produit | `datetime`, après parsing |
| `level` | Gravité : INFO, WARNING, ERROR, CRITICAL | `str` normalisée |
| `ip` | Adresse IP source | `str` |
| `user_id` | Identifiant utilisateur | `str` |
| `connection` | IP, port, protocole | `tuple[str, int, str]` |
| `payload` | Contenu : événement structuré ou message brut | `dict` ou `str` |

JSON représente la connexion par un tableau ; le parseur Python le transforme en tuple, comme demandé dans le sujet. Les dictionnaires des logs restent des dictionnaires.

Pour reconnaître un échec de connexion, utilisez explicitement `payload.event == "login"` et `payload.status == "failure"`. Une erreur quelconque n'est pas forcément une tentative de connexion.

### Contenu du jeu d'exemple

Les dix événements valides sont classés par date. Il y a aussi une ligne JSON cassée et une ligne vide à ignorer sans interrompre le programme. Un niveau contient des espaces et des minuscules pour vérifier la normalisation.

- Alice se connecte et consulte une page ; une de ses requêtes échoue ensuite.
- Bob échoue trois fois depuis la même IP, réussit, puis échoue une nouvelle fois.
- Carol émet un événement depuis une IP blacklistée.
- Un service envoie un message texte brut.

La blacklist contient une IP présente dans les logs et une autre absente. Une IP blacklistée signifie ici « figurant dans notre fichier de test », pas une menace réelle.

## 3. Contrat commun à fixer ensemble avant de coder

Consacrez environ une heure à cette partie. Ensuite, chacun travaille sur ses propres fichiers.

### Chemin des données

```text
fichiers -> lignes -> dictionnaires -> nettoyage -> règles -> analyse -> bilan
```

- Les étapes produisent ou consomment des itérateurs : on demande un événement à la fois.
- Aucun `read()`, `readlines()` ou `list(tous_les_logs)` pour charger le fichier entier.
- On peut conserver les compteurs, les IP uniques et l'état de détection ; leur taille dépend des IP/utilisateurs distincts, pas seulement du nombre de lignes.
- L'analyse consomme le flux une seule fois : on ne réutilise pas ensuite un générateur déjà épuisé.
- Les fonctions sont annotées et les erreurs attendues sont traitées précisément.

### Interfaces proposées

Ces noms servent de contrat d'équipe. Vous pouvez les changer ensemble au premier jour, puis les conserver.

```python
# Personne 1
read_lines(path) -> Iterator[str]
read_sources(paths) -> Iterator[str]
parse_line(line: str) -> dict | None

# Personne 2
build_pipeline(lines) -> Iterator[dict]
route_value(value) -> dict
apply_security_rules(*rules, records, **config) -> Iterator[dict]
export_audit(path, global_scope, local_scope) -> None

# Personne 3
analyze(records, blacklist, threshold) -> dict
```

`build_pipeline` appelle le parseur de la personne 1, filtre les résultats invalides puis normalise les événements. `apply_security_rules` reçoit les fonctions de règles en arguments positionnels, le flux via `records=` et la configuration via les arguments nommés.

Une règle prend `record, **config` et retourne une alerte sous forme de dictionnaire ou `None`. Le moteur conserve tous les événements, même ceux qui ne déclenchent aucune alerte, et ajoute un champ `alerts` contenant les alertes de cet événement. Ainsi, l'analyse compte aussi l'activité normale. N'accumulez pas toutes les alertes de tous les événements dans une liste globale.

Branchement cible :

```python
lines = read_sources(paths)
records = build_pipeline(lines)
checked = apply_security_rules(
    rule_blacklist,
    records=records,
    blacklist=blacklist,
)
summary = analyze(checked, blacklist=blacklist, threshold=3)
```

### Décisions sur la détection

- Seuil paramétrable, égal à 3 pour la démonstration.
- Compter les échecs consécutifs par couple `(ip, user_id)`.
- L'activité d'un autre utilisateur ne remet pas le compteur à zéro.
- Une connexion réussie du même couple remet son compteur à zéro ; une requête ordinaire ne le modifie pas.
- Déclencher une seule alerte quand une série atteint le seuil, puis attendre une réussite avant de pouvoir en déclencher une nouvelle pour ce couple.
- Traiter les fichiers dans l'ordre fourni. Pour cette semaine, les données sont supposées chronologiques dans cet ordre ; aucun tri global du fichier n'est nécessaire.

## 4. Répartition et ordre de travail de chacun

### Personne 1 — Lecture, parsing et exécution

Responsabilité : module 1, mise en place du dépôt et raccordement final dans le terminal.

**Par où commencer :** ouvrir `data/demo.jsonl`, comprendre chaque champ, puis écrire une fonction qui renvoie les lignes avec `yield`.

1. Créer l'environnement virtuel, le package `logengine/` avec son `__init__.py`, le dossier de tests et le `.gitignore` pour exclure `.venv/`, les caches et les gros fichiers générés.
2. Écrire la lecture d'un fichier avec `with open(..., encoding="utf-8")`, une boucle et `yield`.
3. Écrire la lecture de plusieurs fichiers avec `yield from`. Fermer correctement les fichiers et signaler un chemin absent clairement.
4. Écrire le parseur : décoder JSON, vérifier que l'objet est un dictionnaire et contrôler les champs et types attendus. Convertir la date et la connexion en tuple. Retourner `None` et signaler la ligne si elle est invalide ; ne pas cacher les bugs avec un `except Exception` général.
5. Ne pas rejeter un niveau juste parce qu'il contient des espaces ou des minuscules : la personne 2 le normalise. Une valeur hors des quatre niveaux autorisés sera rejetée après cette normalisation.
6. Créer une première version de `main.py` qui affiche le nombre d'événements valides. Utiliser `argparse` pour les fichiers, la blacklist et le seuil.
7. Dès que les autres fonctions sont disponibles, brancher la chaîne complète et afficher le bilan. Charger la blacklist en `frozenset` avant de consommer les logs.
8. Ajouter `scripts/generate_logs.py` avec `--output` et `--size-gb` pour produire `data/generated/logs_10go.jsonl` ligne par ligne. Le groupe exige désormais un fichier de **10 Go**, soit au moins **10 000 000 000 octets** UTF-8, dernière ligne JSON complète. Vérifier la taille sur disque ; ne pas construire une énorme liste en mémoire. Les données doivent être variées et reproductibles. Le dossier `data/generated/` doit être ignoré par Git : partager le script et la commande, jamais le fichier de 10 Go.
9. Écrire les instructions d'installation et d'exécution du README. Générer `requirements.txt` depuis l'environnement virtuel avec `python -m pip freeze`.

**Fichiers possédés :** `logengine/ingestion.py`, `logengine/parsing.py`, `main.py`, `scripts/generate_logs.py`, `README.md`, `.gitignore`, `requirements.txt`, tests associés.

**Vérification personnelle :** le fichier d'exemple donne dix dictionnaires ; le JSON cassé et la ligne vide ne provoquent pas de crash. Deux fichiers sont lus successivement. Une date ou une structure invalide est signalée.

**À transmettre aux autres dès le début :** un exemple exact de dictionnaire retourné, les noms des champs et le comportement du parseur en cas d'erreur.

### Personne 2 — Nettoyage, règles et audit

Responsabilité : modules 2 et 4. Le filtrage et la normalisation étant courts, ils sont regroupés avec le moteur de règles.

**Par où commencer :** fabriquer à la main deux ou trois dictionnaires conformes au contrat et travailler dessus ; inutile d'attendre le lecteur de fichiers.

1. Écrire la normalisation : retirer les espaces superflus, passer le niveau en majuscules, normaliser le protocole et produire un message lisible avec une f-string.
2. Construire la chaîne avec `filter()` et une `lambda` pour les lignes utiles, `map(parse_line, ...)`, `filter(None, ...)`, puis `map()` pour la normalisation. Après normalisation, filtrer les niveaux inconnus. Tout cela doit rester paresseux : les données sont traitées à la demande.
3. Écrire `route_value` avec `match-case` pour distinguer une chaîne brute, un dictionnaire d'événement et un tuple de connexion. L'utiliser pour construire une description cohérente du contenu et des métadonnées ; vérifier concrètement les trois branches et le cas non reconnu.
4. Écrire une règle simple : si l'IP figure dans la blacklist, retourner une alerte `blacklist`. Sinon, retourner `None`.
5. Écrire le moteur `apply_security_rules(*rules, records, **config)` : parcourir les événements, appeler chaque fonction de règle avec la configuration et renvoyer les événements enrichis avec `yield`. Il doit fonctionner avec zéro, une ou plusieurs règles.
6. Prévoir une seconde règle simple pour démontrer la modularité, par exemple une règle signalant un niveau `CRITICAL`. L'activer dans un scénario distinct pour conserver les résultats de référence du jeu de base.
7. Écrire l'audit JSON : exporter noms et types des variables à partir de dictionnaires de portée passés en paramètres. Appeler `globals()` et `locals()` à l'endroit que l'on souhaite auditer, par exemple dans `main.py`, puis passer leurs résultats à l'exporteur.
8. Ne pas sérialiser directement tous les objets : un générateur ou un module n'est pas directement exportable en JSON. Une liste de noms et types suffit au rapport de portée ; éviter d'écrire des valeurs sensibles.
9. Rédiger le passage du rapport expliquant `map`, `filter`, `lambda`, `match-case`, fonctions passées en argument, `*args`, `**kwargs`, `globals()` et `locals()`.

**Fichiers possédés :** `logengine/pipeline.py`, `logengine/rules.py`, `logengine/audit.py`, tests associés.

**Vérification personnelle :** `" warning "` devient `"WARNING"`, les valeurs invalides sont filtrées, les trois formats sont reconnus, une IP blacklistée produit une alerte, les événements normaux restent présents et le fichier d'audit est lisible.

**À transmettre à la personne 3 :** structure exacte d'une alerte et du champ `alerts`. À la personne 1 : fonctions à appeler et paramètres de configuration.

### Personne 3 — Statistiques, force brute et rapport

Responsabilité : module 3 et assemblage du rapport. Chaque personne fournit le texte sur son propre code ; la personne 3 ne rédige pas seule tout le dossier.

**Par où commencer :** créer une petite liste de dictionnaires de test avec trois échecs puis une réussite et écrire les compteurs. Cette petite liste de test ne remet pas en cause le traitement en flux des vrais fichiers.

1. Compter les événements par niveau et utilisateur avec `defaultdict(int)`.
2. Conserver les IP actives dans un `set`, et celles ayant produit `ERROR` ou `CRITICAL` dans un autre `set`. Pour ce projet, c'est la définition commune d'une « IP en erreur ».
3. Calculer et expliquer les opérations avec la blacklist : union `|`, intersection `&`, différence `-` et différence symétrique `^`. Montrer aussi les IP blacklistées non rencontrées.
4. Écrire le détecteur de force brute avec un état par couple `(ip, user_id)`. Appliquer précisément les règles de remise à zéro et de déclenchement définies plus haut. Le détecteur doit aussi pouvoir être appelé directement par les tests.
5. Utiliser `for`, `while`, `break`, `continue` et un `else` de boucle dans un parcours utile, sans lire le fichier une seconde fois ni conserver son historique complet. Par exemple : parcourir le flux avec `while`/`next` ; dans chaque événement de connexion, utiliser un `for` sur les états de résultat reconnus (`success`, `failure`), `break` après traitement et `else` si aucun n'est reconnu ; utiliser `continue` pour les événements sans connexion. Expliquer que le `else` du `for` s'exécute si aucun `break` n'a été rencontré.
6. Rassembler statistiques et détection dans un seul passage. Compter les alertes par type et n'en conserver qu'un petit échantillon, par exemple vingt, pour l'affichage final. Le total doit inclure aussi les alertes non conservées dans cet échantillon.
7. Construire le dictionnaire de bilan destiné à `main.py` : total, compteurs par niveau/utilisateur, ensembles d'IP, opérations de blacklist, nombre d'alertes et échantillon.
8. Tester les cas importants : moins que le seuil, seuil atteint, réussite qui réinitialise, utilisateurs intercalés, deux utilisateurs derrière la même IP, plusieurs fichiers et aucun événement.
9. Rassembler le rapport avec les contributions des deux autres : problème, architecture, jeu de données, démonstration, notions Python, essais mémoire et limites.

**Fichiers possédés :** `logengine/analysis.py`, `logengine/detection.py`, rapport final et tests associés.

**Vérification personnelle :** trois échecs de Bob donnent une alerte ; sa réussite réinitialise la série ; le nouvel échec ne produit pas de seconde alerte. L'erreur de requête d'Alice n'est pas comptée comme un échec de connexion.

**À transmettre à la personne 1 :** forme exacte du bilan retourné et exemples d'affichage.

## 5. Structure cible du dépôt

Seuls ce guide et les deux fichiers de données sont fournis à ce stade ; les autres fichiers sont à réaliser par l'équipe.

```text
Projet1/
  main.py
  README.md
  requirements.txt
  .gitignore
  logengine/
    __init__.py
    ingestion.py
    parsing.py
    pipeline.py
    rules.py
    audit.py
    analysis.py
    detection.py
  data/
    demo.jsonl
    blacklist.txt
  scripts/
    generate_logs.py
  tests/
    test_ingestion.py
    test_parsing.py
    test_pipeline.py
    test_rules.py
    test_audit.py
    test_analysis.py
    test_detection.py
    test_integration.py
  docs/
    GUIDE_EQUIPE.md
    rapport.ipynb OU rapport.pdf
```

Bibliothèque standard suffisante pour le moteur : `json`, `datetime`, `argparse`, `collections`, `ipaddress` si vous validez les IP, et `unittest` pour les tests. Les outils de rédaction du rapport peuvent avoir leurs propres dépendances à déclarer. Ne pas utiliser pandas pour charger l'ensemble des logs.

## 6. Résultats attendus du jeu fourni

Configuration de référence : seuil 3, règle blacklist activée, règle CRITICAL supplémentaire désactivée.

| Résultat | Valeur attendue |
|---|---|
| Événements valides | 10 |
| Niveaux | INFO : 4 ; WARNING : 3 ; ERROR : 2 ; CRITICAL : 1 |
| Par utilisateur | alice : 3 ; bob : 5 ; carol : 1 ; service : 1 |
| IP actives | .10, .20, .30, .66, toutes sous `192.168.1` |
| IP en ERROR ou CRITICAL | .10, .20, .66 |
| IP actives et blacklistées | .66 |
| IP actives hors blacklist | .10, .20, .30 |
| IP blacklistées absentes | .99 |
| Union IP actives / blacklist | .10, .20, .30, .66, .99 |
| Différence symétrique | .10, .20, .30, .99 |
| Alertes blacklist | 1, sur .66 |
| Alertes force brute | 1, sur bob / .20 au troisième échec |

La ligne malformée et la ligne vide ne font pas partie des dix événements. Si vous ajoutez des compteurs de rejet, distinguez une ligne malformée d'une ligne vide ignorée.

## 7. Planning du 5 au 12 novembre

| Date | Personne 1 | Personne 2 | Personne 3 | Résultat commun |
|---|---|---|---|---|
| Jeu. 5 | Dépôt, environnement, lecteur | Normalisation sur dictionnaires de test | Compteurs sur dictionnaires de test | Contrat de données et interfaces convenus |
| Ven. 6 | Parsing, lecture multisource, premier main | Pipeline paresseux et match-case | Ensembles et première détection | Lire le fichier, le nettoyer et afficher des statistiques ensemble |
| Sam. 7 | Arguments CLI, erreurs de fichiers | Moteur de règles, blacklist | Détection complète et essais de seuil | Démonstration des deux types d'alerte de bout en bout |
| Dim. 8 | Générer le fichier de 10 Go | Audit et règles additionnelles | Tests des cas limites | Fichier de 10 Go disponible localement |
| Lun. 9 | Intégration du main | Vérification du branchement et de l'audit | Validation des résultats de référence | Commande complète stable avec le jeu fourni |
| Mar. 10 | Traitement complet des 10 Go et mesures | Corrections et rédaction de sa partie | Tests d'intégration et trame du rapport | Traitement complet des 10 Go documenté |
| Mer. 11 | README, requirements, installation neuve | Relecture technique du code et du rapport | Assemblage et export du rapport | Dépôt prêt à être rendu |
| Jeu. 12 | Démo commune | Démo commune | Démo commune | Vérification finale et remise |

La première intégration a lieu dès le 6, pas à la fin. Chacun peut commencer immédiatement avec un petit itérateur de données conforme au contrat. Si une fonction manque encore, utiliser temporairement un exemple manuel hors de sa version finale, puis le remplacer au raccordement.

## 8. Vérifications avant de rendre

### Fonctionnement

- [ ] Une commande exécute toute la chaîne sur le jeu fourni.
- [ ] Les résultats correspondent au tableau de référence.
- [ ] Plusieurs fichiers fonctionnent ; une série d'échecs peut continuer entre deux fichiers.
- [ ] Une ligne vide ou malformée n'arrête pas la lecture des lignes suivantes.
- [ ] Un fichier absent produit un message compréhensible.
- [ ] Un fichier vide produit un bilan vide sans division par zéro.
- [ ] Les cas de remise à zéro et d'utilisateurs intercalés sont vérifiés.
- [ ] L'audit est exporté et décrit la portée que vous avez choisie.

### Respect du sujet

- [ ] `yield`, `yield from`, dictionnaires, tuples et types de données variés.
- [ ] `filter`, `lambda`, `map`, `match-case`.
- [ ] `set`, `frozenset`, `|`, `&`, `-`, `^`, `defaultdict`.
- [ ] `for`, `while`, `break`, `continue` et `else` de boucle, avec un rôle expliqué.
- [ ] Fonctions passées en argument, `*args`, `**kwargs`, `globals`, `locals`.
- [ ] Package Python, Python 3.10+, typage, PEP8 et exceptions adaptées.
- [ ] Environnement isolé, fichier de dépendances, `main.py`, données de test et rapport.

### Mémoire et reproductibilité

- [ ] Après le petit jeu, générer puis traiter entièrement un fichier de **10 Go minimum** (10 000 000 000 octets, dernière ligne JSON complète), avec une population fixe d'utilisateurs/IP pour comparer le coût du volume. Cette taille est une exigence ajoutée par le groupe, pas une précision de l'énoncé fourni.
- [ ] Vérifier sa taille réelle sur disque, le nombre d'événements traités, la durée et le débit. Le générateur comme le moteur doivent travailler progressivement, sans charger le fichier en mémoire. Prévoir l'espace disque nécessaire.
- [ ] Conserver ce fichier dans `data/generated/`, ignoré par Git. Versionner seulement le générateur, la commande et les résultats des mesures.
- [ ] Consigner temps et pic mémoire, par exemple avec `time.perf_counter()` et `tracemalloc`, sans prétendre que ce dernier mesure toute la RAM du processus.
- [ ] Vérifier l'absence d'accumulation de tous les logs et de toutes les alertes.
- [ ] Expliquer la limite : ensembles et états augmentent si le nombre d'IP ou d'utilisateurs distincts augmente.
- [ ] Réinstaller depuis le dépôt dans un nouvel environnement et refaire la commande de démonstration.
- [ ] Exécuter les tests, par exemple `python -m unittest discover -s tests` si vous retenez `unittest`.

## 9. Organisation du rapport et de la démonstration

Rapport court : objectif, format des logs, schéma de traitement, répartition de l'équipe, exemples de sortie, notions Python utilisées, vérifications fonctionnelles, mesures mémoire et limites. Chaque membre fournit une explication de sa partie et ses résultats d'essai.

Démonstration conseillée : montrer un log, lancer la commande sur le jeu d'exemple, expliquer le bilan et les deux alertes, montrer l'audit, puis présenter l'essai sur gros fichier. Chacun explique son code et le raccordement avec les deux autres.

Priorité si le temps manque : un chemin complet et fiable, toutes les notions imposées, des tests ciblés et le rapport. Garder les fonctionnalités supplémentaires pour après cette base.

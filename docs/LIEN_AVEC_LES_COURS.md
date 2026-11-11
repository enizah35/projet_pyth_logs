# Construire et expliquer le projet à partir des cours

## Choix pour le projet

Le moteur utilise des fonctions courtes, des dictionnaires, des tuples et des
itérateurs. Les traitements restent progressifs, comme les exemples de
générateurs du cours sur les fonctions. Chaque membre doit pouvoir expliquer
les instructions de sa partie et suivre un événement de l'entrée à la sortie.

L'énoncé du projet reste la référence pour les livrables et les notions
obligatoires. Les exercices des supports sont des exemples pédagogiques :
ils ne deviennent pas des fonctionnalités supplémentaires à développer.

## Correspondance avec les supports

Les numéros ci-dessous désignent les diapositives dans l'ordre du fichier ou
les pages du PDF.

| Support | Repères | Application dans le projet |
|---|---|---|
| `python introduction.pptx` | 9–16 : pip, environnements, scripts ; 17–22 : variables et types | `.venv`, `requirements.txt`, scripts `.py`, types simples et `type()` pour l'audit |
| `Les conditions et les boucles - Caplogy.pptx` | 18–22 : `match-case` ; 24–31 : boucles, `break`, `continue`, `else` | `route_value` (P2) ; détection de force brute (P3) |
| `Les listes, tuples, ensembles et les dictionnaires.pdf` | 24–28 : tuples ; 32–43 : ensembles ; 45–64 : dictionnaires, `defaultdict`, JSON | Connexion en tuple (P1), niveaux et blacklist en `frozenset` (P2), événements en dictionnaires, compteurs et opérations d'ensembles (P3) |
| `Bibliothèques, fichiers et visualisation de données (1).pptx` | 5–8 : modules ; 23–33 : fichiers et encodage ; 36–38 : exceptions et gros fichiers | Imports, `with open`, UTF-8, lecture progressive (P1), écriture de l'audit (P2) et erreurs de fichiers |
| `Les Fonctions en Python (2).pptx` | 4–17 : fonctions, `*args`, `**kwargs` ; 18–26 : `lambda`, `map`, `filter` ; 27–32 : générateurs ; 33–40 : portées, `globals()`, `locals()` ; 41–43 : imports | Pipeline, moteur de règles et audit (P2) ; lecture avec `yield` et `yield from` (P1) |
| `PROGRAMMATION ORIENTÉE OBJET EN PYTHON (2).pptx` | 5 : procédural et POO ; 10–20 : objets, classes, méthodes, constructeur | Détecteur de force brute `BruteForceDetector` (P3) et classes de tests |

## Suivre le programme dans l'ordre

1. `main.py` récupère les chemins et le seuil, puis charge la blacklist en
   `frozenset`.
2. P1 fournit `read_sources(paths)` : les lignes arrivent à la demande, avec
   `yield` et `yield from`.
3. P2 appelle le parseur P1 et construit les étapes suivantes :

   ```python
   nonempty_lines = filter(lambda line: line.strip() != "", lines)
   parsed_records = map(parser, nonempty_lines)
   valid_records = filter(None, parsed_records)
   return normalize_records(valid_records)
   ```

   `lambda` décrit ici le test « la ligne contient autre chose que des espaces ».
   `map` reçoit une fonction sans l'appeler immédiatement. `filter(None, ...)`
   retire les `None` produits par le parseur pour les lignes invalides.
4. `normalize_record` copie le dictionnaire, nettoie les chaînes et reconstruit
   le tuple de connexion. `route_value` distingue les structures par `match-case`, avec des motifs
   de classe, de dictionnaire et de séquence.
5. `apply_security_rules` parcourt les fonctions reçues dans `*rules` et leur
   transmet la configuration avec `**config`. Il ajoute les alertes au seul
   événement courant, puis le transmet avec `yield`.
6. P3 consomme le flux une seule fois dans `analyze` : compteurs avec
   `defaultdict`, ensembles d'IP, détection de force brute et bilan.
7. Le main transmet `globals()` et `locals()` à `export_audit`. L'audit parcourt
   ces dictionnaires avec `for name, value in scope.items()` et écrit les noms
   des types dans un fichier JSON.

L'audit n'exporte pas les valeurs des variables. `type(value).__name__` permet
d'obtenir un nom comme `str`, `dict` ou `generator`, sans parcourir le générateur.

## Écriture retenue pour faciliter la lecture

- Employer `if`/`else` pour les choix et des boucles explicites pour construire
  la blacklist et le rapport d'audit.
- Copier un événement avec `record.copy()`, puis affecter ses champs avec
  `record["champ"] = valeur`. La copie est superficielle : les objets imbriqués
  restent partagés ; les fonctions actuelles ne les modifient pas.
- Conserver `map`, `filter`, `lambda`, `match-case`, `yield` et `yield from` :
  ces notions figurent dans les cours et sont demandées par l'énoncé.
- Garder les noms et signatures du contrat d'équipe pour raccorder les modules.
- Utiliser une classe seulement quand elle regroupe un état et des
  comportements, comme le détecteur de P3. Les logs restent des dictionnaires
  et les règles des fonctions.

Une petite liste de dictionnaires de démonstration est adaptée aux tests.
Pour les vrais fichiers, ne pas convertir le flux complet en liste, ni utiliser
`read()` ou `readlines()` sur tout le fichier. La blacklist est conservée
en mémoire ; les compteurs P3 dépendent du nombre d'IP et d'utilisateurs
distincts, pas du nombre de lignes.

## Compléments pratiques à savoir expliquer

Ces éléments servent au lancement, aux mesures ou aux vérifications. Ils ne
sont pas présentés comme des chapitres étudiés en détail dans les supports.

| Élément | Rôle dans le projet |
|---|---|
| `argparse` | Transformer les arguments du terminal en chemins et paramètres ; fournir `--help` |
| `Path` de `pathlib` | Représenter les chemins dans le main et le lecteur P1 |
| `os.path` / `os.makedirs` | Construire un chemin et créer le dossier de l'audit (P2) |
| Annotations `dict`, `str`, `int`, `X \| None` | Documenter entrées et sorties, conformément au critère de typage du sujet ; elles ne valident pas les données à l'exécution |
| `Iterable`, `Iterator`, `Callable` de `collections.abc` | Annoter un objet parcourable, un flux fourni élément par élément et une fonction reçue en argument (parseur, règle) |
| `logging` | Signaler les lignes rejetées par le parseur P1 et les erreurs de fichier |
| `json.dump` / `json.dumps` | Écrire l'audit / convertir le bilan en texte JSON |
| `json_value` dans le main | Convertir les ensembles en listes et les dates en chaînes pour afficher le bilan |
| `time.perf_counter` / `tracemalloc` | Mesurer la durée et les allocations Python avec `--measure` |
| `unittest` | Vérifier automatiquement chaque partie |

Dans le moteur de règles, `*rules` rassemble les fonctions positionnelles dans
un tuple, et `**config` rassemble les paramètres nommés dans un dictionnaire.
Le paramètre `records`, placé après `*rules`, doit être donné par son nom.

Deux précisions utiles lors de la lecture du support sur les fonctions :
`filter(None, ...)` conserve les valeurs considérées vraies, et une `lambda`
peut être passée directement en argument sans être affectée à une variable.

## Essayer le projet

- Chaîne complète : `python main.py data/demo.jsonl --blacklist data/blacklist.txt --threshold 3`.
- Démonstration P2 seule : `python main.py --demo-p2`.
- Diagnostic du parseur : `python main.py data/test_p1.jsonl --details`.
- Tests : `python -m unittest discover -s tests -v`.

Les graphiques des cours peuvent illustrer les compteurs du bilan dans le
rapport. Le moteur n'a besoin d'aucune bibliothèque externe et ne charge pas
les logs dans un DataFrame.

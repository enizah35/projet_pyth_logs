# Construire et expliquer le projet à partir des cours

## Choix pour le projet

Le moteur utilise des fonctions courtes, des dictionnaires, des tuples et des
itérateurs. Les traitements restent progressifs, comme les exemples de
générateurs du cours sur les fonctions. Chaque membre doit pouvoir expliquer
les instructions de sa partie et suivre un événement de l'entrée à la sortie.

L'énoncé du projet reste la référence pour les livrables et les notions
obligatoires. Les exercices des supports sont des exemples pédagogiques :
ils ne deviennent pas des fonctionnalités supplémentaires à développer.

## Correspondance avec les six supports

Les numéros ci-dessous désignent les diapositives dans l'ordre du fichier ou
les pages du PDF.

| Support | Repères | Application dans le projet |
|---|---|---|
| `python introduction.pptx` | 9–16 : pip, environnements, scripts ; 17–22 : variables et types | `.venv`, `requirements.txt`, scripts `.py`, types simples et `type()` pour l'audit |
| `Les conditions et les boucles - Caplogy.pptx` | 18–22 : `match-case` ; 24–31 : boucles, `break`, `continue`, `else` | Routage P2 dans `route_value` ; contrôle des échecs de connexion à réaliser par P3 |
| `Les listes, tuples, ensembles et les dictionnaires.pdf` | 24–28 : tuples ; 32–43 : ensembles ; 45–64 : dictionnaires, `defaultdict`, JSON | Connexion en tuple, blacklist en `frozenset`, événements en dictionnaires ; compteurs et opérations d'ensembles à réaliser par P3 |
| `Bibliothèques, fichiers et visualisation de données.pptx` | 5–8 : modules ; 24–28 : fichiers ; 36–38 : exceptions, encodage, gros fichiers | Imports, `with open`, UTF-8, lecture progressive et traitement des erreurs de fichiers |
| `Les Fonctions en Python (1).pptx` | 4–17 : fonctions, arguments et retours ; 18–26 : `lambda`, `map`, `filter` ; 27–32 : générateurs ; 33–40 : portées et fonctions en argument ; 41–43 : imports | Pipeline, règles configurables et audit ; lecture P1 avec `yield` et `yield from` |
| `PROGRAMMATION ORIENTÉE OBJET EN PYTHON (1).pptx` | 5 : procédural et POO ; 10–20 : objets, classes, méthodes, constructeur | Repères pour comprendre les objets Python et les classes de tests ; aucune classe métier nécessaire dans la base actuelle |

## Suivre le programme dans l'ordre

1. `main.py` récupère les chemins et le seuil, puis charge la blacklist.
2. P1 fournit `read_sources(paths)` : les lignes arrivent à la demande.
3. P2 appelle le parseur P1 et construit les étapes suivantes :

   ```python
   nonempty_lines = filter(lambda line: bool(line.strip()), lines)
   parsed_records = map(parser, nonempty_lines)
   valid_records = filter(None, parsed_records)
   yield from normalize_records(valid_records)
   ```

   `lambda` décrit ici le test « la ligne contient autre chose que des espaces ».
   `map` reçoit une fonction sans l'appeler immédiatement. `filter(None, ...)`
   retire notamment les `None` produits par le parseur pour les lignes invalides.
4. `normalize_record` copie le dictionnaire, nettoie les chaînes et reconstruit
   le tuple de connexion. `route_value` distingue les structures par `match-case`.
5. `apply_security_rules` parcourt les fonctions reçues dans `*rules` et leur
   transmet la configuration avec `**config`. Il ajoute les alertes au seul
   événement courant, puis le transmet avec `yield`.
6. P3 fournira `analyze` pour consommer le flux une fois et produire le bilan.
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
- Garder les noms et signatures du contrat d'équipe pour raccorder les branches.
- Ajouter une classe seulement si elle regroupe un état et des comportements
  utiles. L'énoncé demande des logs en dictionnaires et des règles en fonctions.

Une petite liste de dictionnaires de démonstration est adaptée aux tests.
Pour les vrais fichiers, ne pas convertir le flux complet en liste, ni utiliser
`read()` ou `readlines()` sur tout le fichier. La blacklist seule est conservée
en mémoire ; les compteurs P3 dépendront du nombre d'IP et d'utilisateurs distincts.

## Compléments pratiques à savoir expliquer

Ces éléments servent au lancement, au typage ou aux vérifications. Le tableau
des cours ci-dessus ne les présente pas comme des chapitres étudiés en détail.

| Élément | Rôle dans cette base |
|---|---|
| `argparse` | Transformer les arguments du terminal en chemins et paramètres ; fournir `--help` |
| `Path` de `pathlib` | Construire les chemins et créer le dossier d'audit |
| Annotations `dict`, `str`, `Iterator[dict]`, `Callable`, `X \| None` | Documenter entrées et sorties, conformément au critère de typage du sujet ; elles ne valident pas les données à l'exécution |
| `Iterable` / `Iterator` | Un objet parcourable / un objet qui fournit ses éléments progressivement |
| `Callable` | Une fonction, comme le parseur ou une règle, reçue en argument |
| `logging` | Signaler un niveau inconnu sans interrompre les événements suivants |
| `json.dump` / `json.dumps` | Écrire l'audit / convertir le bilan en texte JSON |
| `json_value` dans le main | Convertir les ensembles en listes et les dates en chaînes pour afficher le bilan |
| `unittest` et ses outils de simulation | Vérifier le code ; simuler P1 et P3 tant que leurs modules manquent |

Dans `build_pipeline(lines, *, parser=None)`, l'étoile impose de donner le
parseur par son nom : `parser=parse_line`. Dans le moteur de règles, `*rules`
rassemble les fonctions positionnelles dans un tuple, et `**config` rassemble
les paramètres nommés dans un dictionnaire.

Deux précisions utiles lors de la lecture du support sur les fonctions :
`filter(None, ...)` conserve les valeurs considérées vraies, et une `lambda`
peut être passée directement en argument sans être affectée à une variable.

## Ce qui reste à réaliser et à vérifier

- **P1** : lecture, parsing et génération des données, selon le contrat fourni.
- **P3** : `defaultdict`, opérations `|`, `&`, `-`, `^`, détection avec les boucles
  et clauses demandées, puis rapport final.
- **Équipe** : vérifier les dix événements du jeu commun, les deux types
  d'alertes et le traitement volumineux après intégration réelle des modules.

Les graphiques des cours peuvent illustrer les compteurs du bilan dans le
rapport. Le moteur actuel n'a besoin d'aucune bibliothèque externe et ne
charge pas les logs dans un DataFrame.

Pour essayer la partie disponible : `python main.py --demo-p2`.
Pour vérifier les comportements : `python -m unittest discover -s tests -v`.

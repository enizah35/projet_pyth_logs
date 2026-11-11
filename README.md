# Projet Python : analyse de logs en flux

Projet ING3 en trinôme, Python 3.10 ou supérieur. Le contrat de données et la
répartition figurent dans [le guide d'équipe](docs/GUIDE_EQUIPE.md).

Le [lien avec les cours](docs/LIEN_AVEC_LES_COURS.md) relie chaque notion aux
supports fournis et aux modules du projet. La base privilégie les fonctions,
les types simples et les étapes explicites, tout en conservant les notions
imposées par l'énoncé.

## Répartition

- P1 : lecture, parsing, CLI, environnement et génération du fichier de 10 Go.
- P2 : nettoyage, pipeline fonctionnel, règles de sécurité et audit.
- P3 : statistiques, détection de force brute et assemblage du rapport.

## Données communes

`data/demo.jsonl` contient dix événements valides, une ligne JSON malformée et
une ligne vide. `data/blacklist.txt` contient deux IP de test.

Le fichier de 10 Go sera généré dans `data/generated/`, exclu de Git.
Seuls le générateur, sa commande et les mesures doivent être partagés.

## Installation sous PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Le moteur démarre avec la bibliothèque standard de Python, sans dépendance
externe. Chaque personne utilise son propre environnement virtuel.

## Lancer le projet

Depuis la racine du projet :

```powershell
.\.venv\Scripts\python.exe main.py data/demo.jsonl --blacklist data/blacklist.txt --threshold 3
.\.venv\Scripts\python.exe main.py data/fichier1.jsonl data/fichier2.jsonl --threshold 3
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

`main.py` raccorde les fonctions des trois parties :

```text
read_sources(paths) -> build_pipeline(lines, parser=parse_line)
                   -> apply_security_rules(...) -> analyze(...)
```

Sans argument, `python main.py` utilise le jeu de démonstration et la blacklist
du dépôt. `python main.py --help` présente les options.

Résultat sur le jeu de démonstration : **10 événements valides**, une alerte
blacklist, une alerte de force brute, un avertissement pour le JSON cassé et
aucun pour la ligne vide. Le bilan est affiché en JSON, les ensembles d'IP
étant convertis en listes. Les fichiers sont parcourus dans l'ordre fourni,
sans tri ni chargement global. La blacklist est chargée avant le parcours en
`frozenset`. `--threshold` doit être un entier positif.

L'audit des variables est écrit dans `output/audit.json` ; `--audit chemin.json`
change sa destination. La règle CRITICAL facultative reste désactivée dans la
chaîne complète.

Codes de sortie : 0 pour un parcours terminé, même avec des lignes rejetées ;
1 pour une erreur de fichier ou d'encodage ; 2 pour une erreur d'arguments.

## Démonstration P2

```powershell
.\.venv\Scripts\python.exe main.py --demo-p2
```

La démonstration traite trois dictionnaires manuels dans deux scénarios :
la règle de blacklist seule (trois événements, une alerte), puis les règles
blacklist et CRITICAL ensemble (trois événements, deux alertes). L'audit JSON
est écrit dans `output/p2/audit.json`. Ce mode n'effectue pas la détection de
force brute.

Les modules P2 sont `logengine/pipeline.py`, `logengine/rules.py` et
`logengine/audit.py`. Leur fonctionnement est expliqué dans
[la partie P2 du rapport](docs/rapport_P2.md).

## Diagnostic du parseur

Le récapitulatif du travail P1 est disponible en
[PDF (7 pages)](docs/ANALYSE_P1.pdf) et en
[Markdown](docs/ANALYSE_P1.md).

Pour visualiser chaque décision du parseur sur cinq lignes :

```powershell
.\.venv\Scripts\python.exe main.py data/test_p1.jsonl --details
```

Résultat attendu : 5 lignes lues, 2 événements valides, 2 lignes rejetées et
1 ligne vide ignorée. L'affichage indique le numéro de chaque ligne et la
cause d'un rejet. La numérotation est globale et continue entre les fichiers.
Ce mode n'applique ni les règles ni l'analyse. Le réserver aux petits
fichiers : ne pas afficher des millions de résultats pendant l'essai volumineux.

Les outils de bibliothèque standard répondent à des besoins précis : `json`
décode le texte, `datetime` convertit la date, `argparse` récupère les arguments,
`logging` signale les rejets du parseur, `unittest` automatise les vérifications.
`Path` représente un chemin, les annotations décrivent les entrées/sorties et
`tracemalloc` sert uniquement aux mesures optionnelles. Aucun paquet
supplémentaire n'est nécessaire.

## Contrat P1 → P2

`logengine.ingestion.read_lines(path)` et `read_sources(paths)` fournissent un
`Iterator[str]`. P2 transmet ces lignes à son `build_pipeline`, qui appelle
`logengine.parsing.parse_line(line)` et élimine les retours `None`.

Le parseur retourne un dictionnaire avec les champs suivants :

| Champ | Type Python après parsing P1 |
|---|---|
| `timestamp` | `datetime.datetime`, conversion ISO, sans ajout de fuseau |
| `level` | `str`, conservée avant normalisation P2 |
| `ip` | `str` |
| `user_id` | `str` |
| `connection` | `tuple[str, int, str]` |
| `payload` | `dict` ou `str` |

Les six champs sont obligatoires. Les champs supplémentaires sont conservés.
Un mauvais type, une date invalide, une connexion incorrecte ou du JSON cassé
donnent `None` avec un avertissement et un extrait limité à 160 caractères.
Une ligne blanche donne `None` silencieusement. Un port booléen est rejeté.
P1 ne valide pas la syntaxe des IP, les bornes des ports ou les protocoles ;
il ne modifie pas les espaces ni la casse et laisse les niveaux inconnus à P2,
qui normalise puis filtre. Un payload texte est accepté dans un événement JSON,
pas comme ligne brute hors JSON. Le champ `alerts` est ajouté par P2.

Les interfaces ne transportent pas le chemin et le numéro de ligne jusqu'au
parseur : les avertissements contiennent une cause et un extrait seulement.
L'aide `parse_line_details(line)` retourne `(dict ou None, explication)` pour
le mode `--details`. L'interface `parse_line(line) -> dict | None` réutilise
les mêmes contrôles.

## Comprendre la lecture paresseuse

Un fichier est un **itérable**, parcourable avec `for`. Un **itérateur** fournit
la valeur suivante avec `next()`. Une fonction contenant `yield` crée un
**générateur**, qui est un itérateur : `yield` fournit une ligne puis suspend
la fonction jusqu'à la prochaine demande. `yield from` délègue ce parcours au
lecteur de chaque fichier, successivement.

L'appel à `read_lines` n'ouvre pas encore le fichier : l'ouverture se produit
à la première consommation. Le bloc `with` ferme le fichier à l'épuisement ou
à la fermeture du générateur.

La mémoire dépend surtout de la plus grande ligne, du dictionnaire courant
et des tampons de lecture. Aucun `read()` global, `readlines()` ou historique
des logs n'est construit. Une ligne gigantesque reste une limite. Les compteurs
et ensembles de l'analyse grandissent avec le nombre d'IP et d'utilisateurs
distincts, pas avec le nombre de lignes.

## Générer et mesurer un gros fichier

Les 10 Go sont une exigence de l'équipe, pas une taille imposée par le PDF.
La graine fixe rend les événements reproductibles ; la population reste bornée
à 32 utilisateurs/IP. Les dates sont chronologiques. La taille inclut les
octets UTF-8 et les sauts de ligne. La dernière ligne est complète : la cible
peut être dépassée de moins d'une ligne. Un fichier existant n'est jamais écrasé.
Une interruption ou un disque plein peut laisser un fichier partiel.

```powershell
.\.venv\Scripts\python.exe scripts/generate_logs.py --output data/generated/logs_10go.jsonl --size-gb 10 --seed 0
.\.venv\Scripts\python.exe main.py data/generated/logs_10go.jsonl --measure
```

Pour débuter, utiliser `--size-gb 0.00001` et un autre chemin (environ 10 ko).
Pour 15 Go, choisir `--size-gb 15` et un nouveau chemin. Les tailles sont
décimales : 10 Go = 10 000 000 000 octets. Prévoir l'espace disque avant l'essai.
`--measure` affiche durée, événements/s et pic d'allocations Python via
`tracemalloc` ; ce dernier ralentit le parcours et ne mesure pas toute la RAM.
Le fichier généré est ignoré par Git. Les mesures du parseur seul sont
consignées dans [le bilan P1](docs/BILAN_P1.md).

`requirements.txt` reste vide : `.venv\Scripts\python.exe -m pip freeze` ne
retourne aucune dépendance. Aucune installation supplémentaire n'est nécessaire.

## Git

Le dépôt commun est `https://github.com/enizah35/projet_pyth_logs`.
Travailler sur une branche `feat/p1-...`, `feat/p2-...` ou `feat/p3-...`, puis
faire relire une pull request vers `main`. Prévenir avant de modifier une
interface ou un fichier appartenant à un autre membre.

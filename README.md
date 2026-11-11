# Projet Python : analyse de logs en flux

Projet ING3 en trinôme, Python 3.10 ou supérieur. Le contrat de données et la
répartition figurent dans [le guide d'équipe](docs/GUIDE_EQUIPE.md).

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

## Analyse pédagogique et petit test visuel

Le récapitulatif de notre travail est disponible en
[PDF (7 pages)](docs/ANALYSE_P1.pdf) et en
[Markdown](docs/ANALYSE_P1.md).

Pour visualiser chaque décision sur cinq lignes :

```powershell
.\.venv\Scripts\python.exe main.py data/test_p1.jsonl --details
```

Résultat attendu : 5 lignes lues, 2 événements valides, 2 lignes rejetées et
1 ligne vide ignorée. L'affichage indique le numéro de chaque ligne et la
cause d'un rejet. La numérotation est globale et continue entre les fichiers.
Sans `--details`, seuls le bilan et les avertissements de rejet sont affichés.
Réserver les détails aux petits fichiers : ne pas afficher des millions de
résultats pendant l'essai volumineux.

Les outils de bibliothèque standard répondent à des besoins précis : `json`
décode le texte, `datetime` convertit la date, `argparse` récupère les arguments,
`logging` signale les rejets du parseur, `unittest` automatise les vérifications.
`Path` représente un chemin, les annotations décrivent les entrées/sorties,
`closing` ferme un générateur si son parcours s'interrompt et `tracemalloc`
sert uniquement aux mesures optionnelles. Aucun paquet supplémentaire n'est
nécessaire. Ces outils seront expliqués pendant la relecture du code.

## État de P1 et démonstration

P1 implémente la lecture, le parsing, la CLI et la génération. Les modules P2/P3
ne sont pas encore présents : cette commande compte les événements valides,
sans normaliser les niveaux ni appliquer de règles de sécurité.

```powershell
.\.venv\Scripts\python.exe main.py data/demo.jsonl --blacklist data/blacklist.txt --threshold 3
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Résultat : **10 événements valides**, un avertissement pour le JSON cassé et
aucun avertissement pour la ligne vide. Plusieurs chemins sont acceptés dans
l'ordre fourni. `--threshold` doit être un entier positif ; il est réservé à
la future analyse P3. La blacklist est chargée avant le parcours en `frozenset`.
Les erreurs de fichiers ou d'encodage donnent un code de sortie 1 ; une erreur
d'arguments donne 2 ; un parcours terminé donne 0, même avec des lignes rejetées.

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
il ne modifie pas les espaces ni la casse et laisse les niveaux inconnus à P2.
Un payload texte est accepté dans un événement JSON, pas comme ligne brute
hors JSON. Le champ `alerts` appartient à P2.

Les interfaces ne transportent pas le chemin et le numéro de ligne jusqu'au
parseur : les avertissements contiennent une cause et un extrait seulement.
L'aide `parse_line_details(line)` retourne `(dict ou None, explication)` pour
l'affichage P1. Le mode `--details` associe cette explication au numéro de ligne,
sans décoder deux fois le JSON. L'interface P2 `parse_line(line) -> dict | None`
reste identique et réutilise les mêmes contrôles.
Un `Iterator[dict]` issu de P2 doit fournir un dictionnaire à chaque demande,
sans liste globale et sans `None`. Il ne se consomme qu'une fois.

## Comprendre la lecture paresseuse

Un fichier est un **itérable**, parcourable avec `for`. Un **itérateur** fournit
la valeur suivante avec `next()`. Une fonction contenant `yield` crée un
**générateur**, qui est un itérateur : `yield` fournit une ligne puis suspend
la fonction jusqu'à la prochaine demande. `yield from` délègue ce parcours au
lecteur de chaque fichier, successivement.

L'appel à `read_lines` n'ouvre pas encore le fichier : l'ouverture se produit
à la première consommation. Le bloc `with` ferme le fichier à l'épuisement ou
à la fermeture du générateur. Si le parcours s'arrête tôt, appeler `close()`
sur le générateur ; `main.py` utilise `contextlib.closing` pour le garantir.

La mémoire P1 dépend surtout de la plus grande ligne, du dictionnaire courant
et des tampons de lecture. Aucun `read()` global, `readlines()` ou historique
des logs n'est construit. Une ligne gigantesque reste une limite. La mémoire
du moteur complet dépendra aussi des états distincts conservés par P2/P3.

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
Le fichier généré est ignoré par Git. Les mesures sont consignées dans
[le bilan P1](docs/BILAN_P1.md).

`requirements.txt` reste vide : `.venv\Scripts\python.exe -m pip freeze` ne
retourne aucune dépendance. Aucune installation supplémentaire n'est nécessaire.

## Suite du travail en équipe

Pour le raccordement, remplacer le comptage P1 de `main.py` par la chaîne du
guide : `read_sources → build_pipeline → apply_security_rules → analyze`.
Le pipeline recevra les lignes, sans parsing préalable dans `main.py`.
Les structures du bilan P3 et des alertes P2 restent à livrer par leurs auteurs.
Les modules P2/P3 ne sont ni remplacés ni simulés dans cette version.

## Git

Le dépôt commun est `https://github.com/enizah35/projet_pyth_logs`.
Travailler sur une branche `feat/p1-...`, `feat/p2-...` ou `feat/p3-...`, puis
faire relire une pull request vers `main`. Prévenir avant de modifier une
interface ou un fichier appartenant à un autre membre.

# Bilan P1 — ingestion et parsing

## Périmètre réalisé

Lecture UTF-8 avec `yield`, lecture multisource ordonnée avec `yield from`,
parsing JSONL en dictionnaires, conversion de la date en `datetime` et de la
connexion en tuple. La CLI charge la blacklist en `frozenset` puis compte les
événements valides. Le générateur écrit progressivement des données synthétiques
reproductibles et refuse d'écraser un fichier.

Les six champs, JSONL et le minimum de 10 milliards d'octets sont des conventions
du groupe. Le PDF impose les générateurs, la maîtrise mémoire, les dictionnaires
et les tuples, mais ne fixe pas cette taille. Les règles, normalisations,
statistiques, détection et audit restent aux personnes P2/P3.

## Vérifications fonctionnelles

Exécution avec le Python de `.venv`, version 3.14.6, sous Windows :

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe main.py data/demo.jsonl --blacklist data/blacklist.txt --threshold 3
```

Résultats : 19 tests réussis ; dix événements acceptés sur le jeu fourni,
une ligne JSON rejetée avec avertissement, une ligne blanche ignorée et deux IP
de blacklist chargées. Les tests vérifient notamment les champs manquants, les
types incorrects, les erreurs de date, la reprise après rejet, la lecture
paresseuse, la fermeture des fichiers et les tailles UTF-8 du générateur.
La syntaxe a aussi été analysée avec la grammaire Python 3.10 ; cela ne remplace
pas une exécution des tests sous un interpréteur Python 3.10 réel.

`python -m pip freeze`, exécuté dans `.venv`, ne retourne aucune dépendance :
`requirements.txt` reste vide. Aucun paquet n'a été installé.

## Essai volumineux du 5 novembre 2026

Commandes utilisées depuis la racine du dépôt :

```powershell
.\.venv\Scripts\python.exe scripts/generate_logs.py --output data/generated/logs_10go.jsonl --size-gb 10 --seed 0
.\.venv\Scripts\python.exe main.py data/generated/logs_10go.jsonl --measure
```

Génération terminée : **10 000 000 021 octets** sur disque, en **350,016 s**,
soit environ **28,57 Mo/s** (unités décimales). La cible est dépassée de 21 octets
pour conserver la dernière ligne entière.

Le parcours complet avec mesure mémoire a été interrompu à la demande de
l'utilisateur : aucun résultat final de débit ou de pic d'allocations n'est
revendiqué. Le fichier local est exclu de Git. L'essai porte sur P1 uniquement,
sans les modules P2/P3. Sa reprise devra être effectuée séparément.

## Reprise pédagogique du 11 novembre 2026

Analyse détaillée exportée dans `ANALYSE_P1.pdf`, avec sa source
`ANALYSE_P1.md`. Ajout du mode `--details` et du fichier `data/test_p1.jsonl`
pour visualiser un résultat par ligne, puis les compteurs : 2 valides,
2 rejets et 1 ligne vide sur 5 lignes.

La CLI compte les lignes sans conserver les événements. Son aide
`parse_line_details` fournit une cause de rejet ; `parse_line` conserve son
contrat avec P2. La numérotation continue entre les fichiers. Aucun module
P2/P3 n'a été modifié et aucun nouveau fichier de 10 Go n'a été généré.

Validation de cette reprise : **21 tests réussis**, dont les résultats détaillés,
les compteurs multisources et l'absence de double parsing. La commande de
démonstration détaillée correspond aux résultats attendus ; `git diff --check`
ne signale aucune erreur d'espacement.

## Limites et raccordement

La mémoire de P1 dépend surtout de la plus grande ligne. Le parseur ne conserve
pas les rejets ; il signale une cause et un extrait, sans numéro de ligne car
son interface ne reçoit pas cette information. Les types sont contrôlés, mais
aucune validation métier supplémentaire des IP/ports/protocoles n'est imposée.
La casse et les espaces sont préservés pour P2.

`tracemalloc` mesure les allocations Python suivies, pas toute la RAM du
processus ; son activation ralentit l'essai. Les performances dépendent du
matériel et ne constituent pas un engagement de latence « temps réel ».

À la livraison des modules de l'équipe, `main.py` devra transmettre les lignes
directement à `build_pipeline`, puis appeler les règles et l'analyse. Le parseur
P1 sera appelé par P2 : ne pas parser deux fois. Les formats du bilan P3 et des
alertes P2 restent nécessaires au raccordement et à son affichage final.

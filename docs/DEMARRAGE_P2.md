# Démarrer et comprendre ta partie P2

## Ce qui est disponible

- `logengine/pipeline.py` : nettoyage, `map`, `filter`, `lambda` et `match-case`.
- `logengine/rules.py` : fonctions de règles et moteur `*rules` / `**config`.
- `logengine/audit.py` : noms et types des variables, sans leurs valeurs.
- `examples/demo_p2.py` : petite démonstration qui ne dépend pas de P1 ou P3.
- `tests/` : vérifications fonctionnelles et traitement à la demande.

Le parseur JSON reste à P1. Le comptage final et la force brute restent à P3.
Le fichier de 10 Go sera généré par P1 : cette étape de démarrage ne le crée pas.

## Ton premier exercice

1. Lance `python -m examples.demo_p2` avec le Python de `.venv`.
2. Ouvre `examples/demo_p2.py` : tu y retrouves trois dictionnaires, avec une date
   `datetime` et une connexion en tuple, comme les futures sorties de P1.
3. Suis le premier événement dans `normalize_record` : ` warning ` devient
   `WARNING`, les espaces autour du nom disparaissent et le protocole devient
   `HTTPS`. Le dictionnaire original reste intact.
4. Suis le deuxième événement dans `rule_blacklist` : son IP est comparée à la
   configuration et une alerte lui est ajoutée.
5. Ouvre `output/p2/audit.json` : tu y vois les noms et types des variables des
   portées passées par la démonstration, sans leurs valeurs.
6. Change localement une IP ou un niveau dans la démonstration, relance et prédis
   la sortie avant de la lire. Rétablis l'exemple commun avant de partager.

## Comprendre le pipeline

`normalize_records(records)` reçoit déjà des dictionnaires. Il permet de
travailler maintenant, sans lire ni parser les fichiers à la place de P1.

Lorsque le parseur P1 est disponible, `build_pipeline(lines)` enchaîne :

```text
lignes -> filter(lambda ...) -> map(parse_line, ...)
       -> filter(None, ...) -> map(normalize_record, ...)
       -> filter(niveau reconnu, ...) -> dictionnaires nettoyés
```

Les itérateurs avancent uniquement lorsque l'étape suivante demande un élément.
Il ne faut pas transformer le flux complet en liste. Une liste de trois exemples
ou des résultats finis dans un test n'a pas le même coût qu'un fichier de 10 Go.

Le paramètre facultatif `parser=` sert à injecter une fonction dans les tests.
L'appel commun `build_pipeline(lines)` reste inchangé. Les erreurs structurelles
du log relèvent du parseur ; P2 filtre les niveaux inconnus après normalisation.

## Ce qu'il faut dire à P1

Fournir `logengine/parsing.py` avec `parse_line(line: str) -> dict | None` :
date convertie en `datetime`, connexion en tuple, champs vérifiés et entrée
invalide représentée par `None`. Ne pas rejeter ` warning ` avant normalisation.

Le point d'entrée commun `main.py` réalise déjà ce branchement et appelle
ensuite `analyze` de P3. Il attend encore les modules P1 et P3 pour une exécution
complète ; `python main.py --demo-p2` lance l'exemple disponible dès maintenant.
Le branchement P2 est :

```python
from logengine.pipeline import build_pipeline
from logengine.rules import apply_security_rules, rule_blacklist

records = build_pipeline(lines)
checked = apply_security_rules(
    rule_blacklist, records=records, blacklist=blacklist
)
```

`blacklist` est le `frozenset` chargé par P1. `rule_critical` peut être ajouté
comme deuxième fonction, mais doit rester désactivé pour retrouver le scénario
de référence. Pour l'audit, P1 appelle depuis la portée qu'il souhaite observer :

```python
from logengine.audit import export_audit

export_audit("audit.json", globals(), locals())
```

## Ce qu'il faut dire à P3

Chaque événement conserve ses champs et reçoit `alerts`, une liste vide ou
remplie pour cet événement. Les événements sans alerte ne sont pas supprimés.
Une alerte produite par une règle a cette forme :

```python
{
    "type": "blacklist",
    "timestamp": "2026-11-05T10:00:05",
    "ip": "192.168.1.66",
    "user_id": "carol",
    "message": "IP présente dans la blacklist",
}
```

P3 consomme `checked` une seule fois, compte ses alertes et ajoute celles de son
détecteur de force brute. Il garde au plus vingt exemples, mais compte tout.
P2 ne conserve pas une liste globale d'événements ou d'alertes.

## Git et suite du travail

La branche locale est `feat/p2-pipeline` et `origin` désigne le dépôt commun.
La branche `main` est déjà publiée avec les documents et données de base.
La V1 P2 et le point d'entrée commun sont livrés sur cette branche de travail,
puis proposés dans une pull request vers `main`.

Pour publier les prochains changements après vérification :

```powershell
git fetch origin main
git merge origin/main
# Ajouter explicitement les fichiers modifiés après avoir lu git diff.
git add logengine/pipeline.py logengine/rules.py logengine/audit.py
git commit -m "feat: ameliore le pipeline P2"
git push -u origin feat/p2-pipeline
```

Ensuite ouvrir une pull request de `feat/p2-pipeline` vers `main` pour une
relecture par le groupe. Les données générées de 10 Go, le venv et l'audit
restent hors de Git. Vérifier d'abord `git status` et les fichiers du commit.

## Avant de considérer P2 terminé

- Les tests passent et tu peux expliquer chaque fonction sans relire une IA.
- Le groupe accepte les interfaces et la structure des alertes.
- Un essai réel avec le parseur de P1 retrouve les dix événements et une alerte
  blacklist sur le jeu commun ; cet essai dépend encore de la livraison P1.
- Le branchement à l'analyse de P3 est vérifié, puis le groupe exécute son test
  complet sur le fichier de 10 Go.
- Tu fournis le texte de ta partie pour le rapport et les résultats réellement
  mesurés. Les tests de paresse ne remplacent pas cet essai volumineux.

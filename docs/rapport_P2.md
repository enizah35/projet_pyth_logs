# Rapport — partie P2 : pipeline, règles de sécurité et audit

Ce texte décrit la partie P2 du projet, à intégrer dans le rapport commun.
Il correspond aux modules 2 et 4 de l'énoncé.

## 1. Rôle de P2 dans la chaîne

```text
P1 : fichiers -> lignes -> dictionnaires
P2 : nettoyage -> normalisation -> règles de sécurité
P3 : statistiques, ensembles d'IP, force brute -> bilan
```

P2 reçoit les lignes lues par P1, appelle son parseur, nettoie les événements
obtenus, leur applique des règles de sécurité et les transmet à P3 avec un
champ `alerts`. Les fichiers concernés sont `logengine/pipeline.py`,
`logengine/rules.py` et `logengine/audit.py`.

Contrainte principale : ne jamais garder tous les événements en mémoire.
Chaque étape renvoie un itérateur. Un événement traverse toute la chaîne
avant que la ligne suivante soit lue.

## 2. Filtrage et normalisation avec `filter`, `map` et `lambda`

La fonction `build_pipeline` enchaîne quatre étapes :

```python
nonempty_lines = filter(lambda line: line.strip() != "", lines)
parsed_records = map(parser, nonempty_lines)
valid_records = filter(None, parsed_records)
return normalize_records(valid_records)
```

- `filter` avec une `lambda` écarte les lignes vides ou faites d'espaces.
  La `lambda` est une petite fonction anonyme écrite directement en argument.
- `map(parser, ...)` applique le parseur de P1 à chaque ligne. La fonction est
  passée sans parenthèses : c'est `map` qui l'appellera, ligne par ligne.
- `filter(None, ...)` retire les `None`, que le parseur renvoie pour une ligne
  invalide (JSON cassé, champ manquant, mauvais type).
- `normalize_records` applique `map(normalize_record, ...)`, puis un dernier
  `filter` qui retire les niveaux inconnus.

`map` et `filter` ne calculent rien à leur création. Ils produisent un
élément seulement quand l'étape suivante le demande. Un test le vérifie :
juste après l'appel à `build_pipeline`, aucune ligne n'a encore été lue.

`normalize_record` travaille sur une copie du dictionnaire reçu :

- `strip()` retire les espaces autour des chaînes et `upper()` passe le niveau
  et le protocole en majuscules : `" warning "` devient `"WARNING"` ;
- le tuple de connexion est déballé puis reconstruit, puisqu'un tuple ne se
  modifie pas ;
- une f-string construit un message lisible :
  `2026-11-05T10:00:01 [WARNING] user=bob ip=192.168.1.20 ...`.

Le filtre des niveaux vient après la normalisation : `" debug "` doit d'abord
devenir `"DEBUG"` pour être comparé aux quatre niveaux du `frozenset` `LEVELS`.

## 3. Analyse de structure avec `match-case`

`route_value` reconnaît le format d'une valeur sans enchaîner les `if`/`elif`.
Version simplifiée (chaque cas renvoie aussi la valeur d'origine) :

```python
match value:
    case str():
        return {"kind": "text", "summary": value}
    case {"event": str() as event, "status": str() as status}:
        return {"kind": "event", "summary": f"{event} : {status}"}
    case {"level": str() as level, "code": int() as code}:
        return {"kind": "event", "summary": f"{level} code {code}"}
    case dict():
        return {"kind": "event", "summary": "événement structuré"}
    case (str() as ip, int() as port, str() as protocol) if isinstance(
        value, tuple
    ):
        return {"kind": "connection", "summary": f"{protocol} {ip}:{port}"}
    case _:
        return {"kind": "unknown", "summary": "format non reconnu"}
```

Les trois formats demandés par l'énoncé sont couverts : chaîne brute,
dictionnaire d'événement et tuple de connexion. Trois sortes de motifs sont
utilisées :

- **motif de classe** (`str()`, `dict()`) : vérifie seulement le type ;
- **motif de dictionnaire** (`{"level": str() as level, "code": int() as code}`,
  sur le modèle de l'exemple de l'énoncé) : vérifie que les clés existent et
  que leurs valeurs ont le bon type, puis les range dans des variables. Les
  autres clés du dictionnaire sont acceptées. Un code écrit `"403"` (texte) ne
  correspond pas au motif et retombe sur le cas `dict()` ;
- **motif de séquence** (`(str() as ip, int() as port, str() as protocol)`) :
  déballe les trois éléments du tuple de connexion. Il accepterait aussi une
  liste ; la condition `if isinstance(value, tuple)` impose un vrai tuple.

L'ordre des cas compte : les motifs précis passent avant `dict()`, qui
attraperait sinon tous les dictionnaires. Le cas `_` joue le rôle d'un `else`.

Chaque événement normalisé reçoit `payload_description` et
`connection_description`, qui indiquent le format reconnu et son résumé, par
exemple `login : failure` ou `HTTPS 192.168.1.20:443`.

## 4. Moteur de règles avec `*args` et `**kwargs`

Une règle est une simple fonction : elle reçoit un événement et la
configuration, et renvoie une alerte (un dictionnaire) ou `None`.
Deux règles sont fournies :

- `rule_blacklist` : l'IP de l'événement figure dans la blacklist ;
- `rule_critical` : l'événement est de niveau CRITICAL.

Le moteur a cette signature :

```python
def apply_security_rules(*rules, records, **config):
```

- `*rules` regroupe dans un tuple toutes les fonctions passées en arguments
  positionnels. Il peut y en avoir zéro, une ou plusieurs.
- `records` est placé après `*rules` : il doit donc être donné par son nom
  (`records=flux`), sinon Python le prendrait pour une règle.
- `**config` regroupe les paramètres nommés restants (`blacklist=...`) dans un
  dictionnaire, transmis tel quel à chaque règle avec `rule(record, **config)`.

Les fonctions sont donc manipulées comme des objets : rangées dans un tuple,
parcourues avec `for`, puis appelées. Ajouter une règle ne demande aucune
modification du moteur :

```python
apply_security_rules(rule_blacklist, records=flux, blacklist=ips)
apply_security_rules(rule_blacklist, rule_critical, records=flux, blacklist=ips)
```

Le moteur renvoie chaque événement avec `yield`, même sans alerte, car P3 en a
besoin pour ses statistiques. La liste `alerts` ne concerne que l'événement en
cours : aucune liste globale d'alertes n'est construite.

Format d'une alerte, convenu avec P3 :

```python
{
    "type": "blacklist",
    "timestamp": "2026-11-05T10:00:05",
    "ip": "192.168.1.66",
    "user_id": "carol",
    "message": "IP présente dans la blacklist",
}
```

### Typage

Les fonctions P2 sont annotées pour documenter leurs entrées et sorties,
comme le demande le critère de qualité du barème :

```python
def build_pipeline(
    lines: Iterable[str],
    parser: Callable[[str], dict | None] = parse_line,
) -> Iterator[dict]:

def apply_security_rules(
    *rules: Callable[..., dict | None],
    records: Iterable[dict],
    **config: object,
) -> Iterator[dict]:
```

- `Iterable[str]` : un objet parcourable avec `for`, ici des lignes ;
- `Iterator[dict]` : un objet qui fournit ses dictionnaires un par un ;
- `Callable[[str], dict | None]` : une fonction qui reçoit une chaîne et
  renvoie un dictionnaire ou `None`, comme le parseur ;
- `Callable[..., dict | None]` : une règle, quels que soient ses arguments.

Ces annotations ne vérifient rien pendant l'exécution : elles servent à la
lecture et aux outils de vérification.

## 5. Audit des portées avec `globals()` et `locals()`

`export_audit(path, global_scope, local_scope)` écrit un fichier JSON qui
associe chaque nom de variable au nom de son type :

```json
{"globals": {"PROJECT_DIR": "WindowsPath", ...},
 "locals": {"blacklist": "frozenset", "summary": "dict", ...}}
```

- `globals()` renvoie le dictionnaire des variables du module, `locals()` celui
  de la fonction en cours. Ils sont appelés dans `main.py` puis passés à
  l'exporteur. Appelés dans `audit.py`, ils décriraient les variables de
  `audit.py` et non celles du programme principal.
- Seuls les noms et les types sont exportés, pas les valeurs : elles peuvent
  être sensibles, et certaines (modules, générateurs) ne s'écrivent pas en JSON.
- `type(value).__name__` ne parcourt pas un générateur : l'audit ne consomme
  pas le flux de logs.

## 6. Vérifications

Les tests sont lancés avec `python -m unittest discover -s tests`. Ils couvrent
notamment :

- la normalisation, sans modification du dictionnaire d'origine ;
- les trois formats de `match-case` et le cas non reconnu ;
- la poursuite du traitement après une ligne vide, invalide ou un niveau
  inconnu ;
- le traitement à la demande du pipeline ;
- le moteur avec zéro, une ou deux règles, et la conservation des événements
  sans alerte ;
- l'audit, qui n'exporte pas les valeurs et ne consomme pas de générateur.

Démonstration P2 sur trois dictionnaires (`python main.py --demo-p2`) :

| Scénario | Événements | Alertes |
|---|---|---|
| `rule_blacklist` seule | 3 | 1 (blacklist, carol) |
| `rule_blacklist` et `rule_critical` | 3 | 2 (blacklist et critical, carol) |

Fichier de logs de P1 (`data/logs_test_p1.jsonl`) passé dans le pipeline :
10 événements conservés (INFO 4, WARNING 3, ERROR 2, CRITICAL 1), toutes les
connexions reconnues comme tuples, un seul payload texte (david), aucune alerte
blacklist et une alerte CRITICAL (admin).

Chaîne complète sur le jeu commun (`python main.py data/demo.jsonl`) :
10 événements valides, 1 alerte blacklist et 1 alerte de force brute, ce qui
correspond aux résultats de référence du guide d'équipe.

## 7. Essai sur un fichier de 10 Go

Le fichier est produit par le générateur de P1, puis traité par la chaîne
complète (P1, P2 et P3), règle blacklist active et seuil de 3 :

```powershell
.\.venv\Scripts\python.exe scripts/generate_logs.py --output data/generated/logs_10go.jsonl --size-gb 10 --seed 0
.\.venv\Scripts\python.exe main.py data/generated/logs_10go.jsonl --blacklist data/blacklist.txt --threshold 3
```

Mesures du 11 novembre 2026, sous Windows, Python 3.14 :

| Mesure | Valeur |
|---|---|
| Taille du fichier | 10 000 000 021 octets |
| Génération | 1 017 s |
| Événements traités | 55 983 446 |
| Durée de la chaîne complète | 1 164 s, soit environ 48 000 événements/s |
| Pic de mémoire du processus | 19,5 Mo |
| Lignes rejetées | 0 |
| Alertes de force brute | 2 623 123, dont 20 conservées en exemple |
| Alertes blacklist | 0 |

La mémoire a été relevée sur le processus Python lui-même (working set
Windows), sans `--measure`, pour ne pas ralentir le parcours. Elle reste à
19,5 Mo pour un fichier de 10 Go : les événements et les alertes ne sont pas
accumulés.

Le générateur utilise 32 utilisateurs et les IP `192.168.1.1` à `.32`. Aucune
ne figure dans la blacklist de test (`.66` et `.99`), d'où l'absence d'alerte
blacklist. Le nombre d'alertes de force brute est élevé car les échecs de
connexion sont tirés au hasard. Avec seulement 32 couples `(ip, user_id)`, les
compteurs et ensembles de P3 restent petits.

## 8. Limites

- Le pipeline ne valide pas la syntaxe des IP : il nettoie seulement les
  espaces. Cette vérification n'est pas demandée par le contrat.
- `rule_critical` est désactivée dans la chaîne complète pour conserver les
  résultats de référence.
- `record.copy()` est une copie superficielle : un payload dictionnaire reste
  partagé avec l'original. Les fonctions P2 ne le modifient pas.
- L'audit décrit seulement la portée choisie par l'appelant, à l'instant de
  l'appel.

# Spec — ORC-01 Dépôt de données et workflow planifié

*Rédigé le : 28 octobre 2026*

## Contexte

COL-02 écrit, sur la machine qui le lance, les snapshots du jour (`cards-*.parquet`, `prices-*.parquet`), le brut gzip et un résumé sans prix. COL-T3 a fixé la durée attendue : ≈ 1 h 13 pour les prix, ≈ 3 h 46 le jour du catalogue. La spec maîtresse place le workflow planifié dans un dépôt de données public séparé, `cartograph-data` (N13), et les prix dans le dépôt privé `cartograph-prices` (T8).

Une machine GitHub Actions est effacée en fin de job : tout fichier non envoyé ailleurs est perdu, et un jour de prix manqué ne se récupère pas. Le workflow doit donc stocker lui-même ce qu'il collecte dès sa première exécution.

## Objectif

Collecte entièrement automatique : chaque jour, un workflow de `cartograph-data` installe le collecteur depuis `cartograph`, collecte les prix (et le catalogue le lundi ou à la demande), publie le catalogue et envoie prix et brut dans `cartograph-prices`, sans aucun prix dans ce qui est public.

## Périmètre

- Dépôt local `../cartograph-data` (à côté de `cartograph`) : `README.md` (rôle, attribution TCGdex MIT, aucun prix, mention Nintendo / The Pokémon Company), `.gitignore`, `.github/workflows/collect.yml`.
- Workflow `collect.yml` :
  - cron quotidien décalé (`17 3 * * *`) et `workflow_dispatch` avec paramètres `catalogue`, `prices`, `languages`, `code_ref` ;
  - `concurrency` (une collecte à la fois, sans annuler celle en cours), `timeout-minutes: 300`, permissions minimales ;
  - installation du collecteur : clone superficiel de `cartograph` à `code_ref` (défaut `main`), `uv sync --frozen --no-dev` avec cache ;
  - catalogue le lundi (cron) ou sur paramètre ; sinon le dernier `cards-*.parquet` est téléchargé depuis la Release publique `catalogue` ;
  - lancement de `python -m cartograph.bin.collect.run` ;
  - publication du catalogue du jour dans la Release `catalogue` de `cartograph-data` ;
  - envoi de `prices-*.parquet` et des `*.json.gz` bruts dans la Release `data-AAAA-MM` de `cartograph-prices` (jeton en secret) ;
  - résumé `collect-*.json` et log du jour en artefact (sans prix, 7 jours).
- Accès : variable `TCGDEX_USER_AGENT` et secret `PRICES_TOKEN` (jeton à grain fin, `contents: write` sur `cartograph-prices` seulement).
- Deux exécutions manuelles réussies, débit de la machine GitHub reporté dans la note COL-T3.
- Roadmap : périmètres de STO-01 et STO-03 ajustés (l'envoi quotidien est fait ici).

## Hors périmètre

- Embeddings des nouvelles cartes (EMB-03, P2) : l'étape s'ajoutera au même workflow.
- Manifeste sans prix commité chaque jour (STO-01) ; d'ici là, le cron ne risque pas la suspension des 60 jours.
- Archive mensuelle du brut (STO-03), `dbt build` et fraîcheur (QUA-02), healthchecks.io et résumé dans la page d'exécution (SUR-01).
- Épinglage des actions par SHA et Dependabot (CI-03) : actions épinglées par version majeure ici.
- Paramètre de date : les prix d'un jour passé ne se rejouent pas, la collecte prend toujours la date UTC du jour.
- Aucun changement du code `cartograph` attendu : `--data-dir` existe, les logs vont dans `logs/` du clone.

## Décisions

| Sujet | Décision | Raison |
| --- | --- | --- |
| Catalogue entre deux exécutions | Release publique `catalogue` de `cartograph-data`, un fichier daté par semaine (`--clobber` si relancé) ; le dernier par nom est téléchargé avant les prix | Catalogue MIT sans prix, publiable ; un cache Actions non lu 7 jours est effacé ; ≈ 52 fichiers par an, sous la limite de 1000 par Release |
| Prix et brut | Envoyés dès ORC-01 dans `cartograph-prices`, Release mensuelle `data-AAAA-MM` créée si absente | Collecte automatique sans jour perdu ; jamais d'artefact ni de log public avec des prix (T8) |
| Version du code | Branche `main` de `cartograph` par défaut, `code_ref` en paramètre manuel | Seul le code fusionné part en production ; une branche peut être testée à la main |
| Installation | Clone de `cartograph` + `uv sync --frozen --no-dev`, pas `pip install git+…` | `PROJECT_ROOT` reste la racine du clone : `logs/` et `.env` fonctionnent sans changer le code ; `uv.lock` figé |
| Jour du catalogue | Lundi pour le cron (`date -u +%u` = 1) | Hebdomadaire (F1) ; un jour fixe facilite le suivi |
| Échec du catalogue | Le processus continue avec le catalogue de la Release, le job finit en échec (code 1 → e-mail GitHub), les étapes de publication tournent quand même (`!cancelled()`) | Échec du catalogue non bloquant pour les prix (spec maîtresse) |
| Délai maximal | `timeout-minutes: 300` | COL-T3 : ≈ 3 h 46 le jour du catalogue, limite GitHub 6 h |
| Paramètres manuels | Passés aux scripts par `env:`, jamais en `${{ }}` dans `run:` | Pas d'injection de commande depuis les paramètres (N14) |
| Permissions | `permissions: {}` au niveau du workflow, `contents: write` sur le job (Release `catalogue`) | Moindre privilège ; le dépôt privé passe par `PRICES_TOKEN` |
| Contrôle du workflow | `actionlint` et `zizmor` lancés par `uvx` avant chaque push | Erreurs de syntaxe et failles connues des workflows détectées sans exécuter 4 h de collecte |

## Critères d'acceptation

- [ ] `cartograph-data` (public) et `cartograph-prices` (privé) existent ; variable et secret configurés.
- [ ] `collect.yml` passe `actionlint` et `zizmor` sans alerte haute.
- [ ] Une exécution manuelle avec `catalogue` réussit : `cards-AAAA-MM-JJ.parquet` dans la Release `catalogue`, prix et brut dans `data-AAAA-MM` de `cartograph-prices`.
- [ ] Une exécution manuelle sans `catalogue` réussit en lisant le catalogue de la Release.
- [ ] Les logs d'exécution et l'artefact ne contiennent aucune valeur de prix.
- [ ] Relancer le même jour remplace les fichiers du jour dans les deux Releases, sans doublon.
- [ ] Débit et durées de la machine GitHub reportés dans `docs/specs/col-t3-taille-duree.md`.

# Journal — cartograph

> **Usage — Claude Code** : ce fichier trace l'avancement du projet session par session —
> ce qui a été fait et ce qu'il reste à faire. Contrairement à `CURRENT.md` (état du code
> au moment d'une review), ce journal suit les décisions, les documents créés et les étapes
> franchies. Ajoute une entrée en haut (sous ce bloc) à chaque session de travail
> significative. Ne supprime pas les entrées précédentes.
>
> Format d'une entrée :
>
> ## [YYYY-MM-DD] — <titre court de la session>
> ### Fait
> - ce qui a été fait
>
> ### Reste à faire
> - ce qu'il reste à faire
>
> ### Références
> - fichiers, specs, plans

---

## [2026-11-19] — Audit : collecte sans perte de prix, tests restants

### Fait

- Session ouverte (`/workspace-init`).
- Plan fix-audit-2026-11-18 — Étape 2 : Collecte. `FetchResult.error` : `fetch_each` renvoie le partiel au lieu de lever ; prix reçus avant une panne écrits (brut et Parquet, étape `failed`) ; rotation garde les fiches lues de la langue coupée ; catalogue complet, sets et nouvelles cartes restent tout ou rien. `Retry-After` négatif → 0, `nan` → backoff. Logger nommé dans `run.py` (testé par `runpy` en `__main__`). `new_cards` dans le checkpoint. Docstring de `inv collect`. `inv ci` et `inv okflint` verts.
- Plan fix-audit-2026-11-18 — Étape 3 : Tests et doc restants. Fixture `isolated_logs` dans `conftest.py` (`LOG_DIR` patché dans `config`, `__main__`, `rebuild`, `collect.run`, `suivi.run`, handlers fermés) : `test_suivi_run` n'écrit plus dans `logs/` du dépôt. Tests ajoutés : rotation coupée par une panne via `main`, carte disparue puis revenue en collecte complète, `--catalogue --no-prices`, ensemble exact des fiches de la rotation (`raw_path`, l'ancienne assertion `%253F` ne pouvait pas échouer), prix entiers dans les fixtures, échec du téléchargement dans `inv rebuild`, vrai `.clean` sur le dépôt, lignes Énergie et Émissions. `CONTRIBUTING.md:141` corrigé. Test `-m` : client remplacé par une sous-classe (une lambda fait échouer beartype sur les annotations). `inv ci` (389 tests, 99,4 %) et `inv okflint` verts.
- Vérifié : la collecte du 19/11 (run 44450348025, succès) a supprimé `cards-2026-11-18.parquet` de la Release `catalogue` (« Supprimé de catalogue » dans le log) ; restent les `cards-` des lundis 02, 09, 16/11 et `cards-2026-11-19`.
- fix-audit-2026-11-18 clos : critères de fin cochés, entrée de l'audit complétée dans `CURRENT.md`, plan et spec `statut: fait`.
- Retiré du « Reste à faire » : « Porte 0 franchie le 15/11 » (constat, déjà acquis).

### Reste à faire

- Antoaneta : fusionner la PR `feature/fix-audit-2026-11-18` → `develop`, puis `inv release` (v0.8.1).
- Planifier DBT-02 (staging des prix) au standard SQL : `/workspace-plan dbt-02`.
- Avant la porte 1 : relire dans un navigateur les conditions de Cardmarket et de TCGplayer (veille).
- Rapport de novembre à régénérer en fin de mois (`inv suivi --mois 2026-11 --force`, commentaire gardé), puis `statut: fait` ; mettre à jour les chiffres de `docs/gouvernance/green-it.md`. Chaque début de mois : `inv ci` puis `inv suivi`, commentaire.
- Antoaneta : avant PRO-02, demander aux testeurs leur logiciel de caisse et un fichier d'import exemple.
- `cadrage-flux.md` : flux d'export pro (FX7 et FX8, écrans) à ajouter quand PRO-01 et PRO-02 seront planifiés.

### Références

- docs/plans/fix-audit-2026-11-18.md, docs/specs/fix-audit-2026-11-18.md
- src/cartograph/bin/collect/ (`__init__`, `batch`, `client`, `run`, `prices`, `catalogue`, `sets`), tasks/__init__.py
- tests/test_collect_run.py, tests/test_collect_client.py, tests/test_collect_failures.py
- tests/conftest.py, test_main.py, test_rebuild.py, test_suivi_run.py, test_fixtures_prices.py, test_tasks_rebuild.py, test_tasks_clean.py, test_suivi_report.py, CONTRIBUTING.md

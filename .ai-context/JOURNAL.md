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

## [2026-11-17] — Archive du journal, COL-04 collecte

### Fait

- Session ouverte (`/workspace-init`).
- `inv release` archive le journal : avant `cz bump`, toutes les entrées sauf la plus récente passent dans `.ai-context/LOG.md` sous `# vX.Y.Z — date`, commit `chore(journal): archive avant vX.Y.Z` ; `cz bump --get-next` arrête la tâche avant l'archive s'il n'y a rien à publier (`tasks/__init__.py`, `tests/test_tasks_release.py`).
- `inv suivi` compte les jours travaillés dans `JOURNAL.md` et `LOG.md` (`worked_days` prend une liste de fichiers, un fichier absent est ignoré).
- Entrées existantes déplacées dans `LOG.md` par version (v0.1.0, v0.2.1, v0.3.0, v0.3.1) ; à reporter dans `python-project-template` en fin de projet.
- Plan col-04-nouvelles-cartes-sets — Étape 1 : Étape `sets` de la collecte. `bin/collect/sets.py` (`list_set_ids`, `fetch_sets`, `set_path`), `snapshot.py` (`SET_SCHEMA`, `set_table`, `SnapshotPaths.sets`, `SET_SORT_BY`), `run.py` (`_collect_sets` après le catalogue, résumé écrit après chaque étape suivie d'une autre, `_write_table` prend le tri), `manifest.py` et `report.py` ; `catalogue.check_language` rendu public. Fixtures `tests/fixtures/tcgdex/*_sets*.json` enregistrées (listes et `cards` réduites à 2, `SM1+` pour l'encodage) ; `conftest.fixture_route` sert aussi `/sets`. Tests : `test_collect_sets.py`, `test_collect_run.py`, `test_collect_manifest.py`, `test_collect_report.py`. Décisions (colonnes, résumé intermédiaire) dans la spec, passée à `en cours`.
- Plan col-04-nouvelles-cartes-sets — Étape 2 : Étape `new_cards` de la collecte. `catalogue.new_card_ids`, `prices.new_card_targets`, `SnapshotPaths.new_cards` et `raw_new_cards`, `run._collect_new_cards` (prix des nouvelles fiches ajoutés à ceux du catalogue dans un seul `prices-*.parquet`, `_write_table` renvoie la table), `manifest.py` (`new-cards-*.parquet` public, brut privé), `report.py`. Tests : `test_collect_new_cards.py`, `test_collect_run.py` (nouvelle carte et prix, produit non doublé, sans nouveauté, liste en échec, conversion en échec, code de sortie 1, T8), manifeste, résumé. Décisions dans la spec : `new_cards` aussi quand le catalogue du jour échoue, langue absente du dernier catalogue ignorée.
- Plan col-04-nouvelles-cartes-sets — Étape 3 : Publication et validation sur GitHub (partie code et doc). `../cartograph-data/.github/workflows/collect.yml` : « Publier le catalogue » sans condition sur l'étape catalogue (sortie `catalogue` de « Lire le résumé » retirée), notes de la Release `catalogue` réécrites à chaque publication (`gh release edit`) pour `cards-`, `sets-`, `new-cards-` ; actionlint et zizmor verts. README de `cartograph` (« Collecte », « Collecte automatique ») et de `cartograph-data` (« Ce qui est publié », `steps` du manifeste) ; `docs/specs/cadrage-flux.md` (vue d'ensemble, FX1, FX2, séquence quotidienne).
- Ligne trop longue de `tasks/__init__.py` (docstring de l'archive du journal) raccourcie pour `inv ci`.

### Reste à faire

- Antoaneta : relire puis commiter `collect.yml` et le README de `cartograph-data` et `git envoyer` (dernière partie de la 1re case de l'étape 3, à cocher ensuite). L'envoi doit suivre la publication de `cartograph` sur `main` : avant, le workflow installe un `main` sans sets ni new-cards (sans dommage, la publication ne fait que lire le manifeste).
- docs/plans/col-04-nouvelles-cartes-sets.md — Étape 3, Antoaneta : PR `feature/col-04` → `develop` (`inv finish`), CI verte, `inv release`, PR vers `main` ; puis exécution manuelle `catalogue=oui` et exécution sans catalogue, manifestes vérifiés. Ensuite Étape 4 : Staging dbt (branche `feature/col-04-dbt`).
- Ensuite : DBT-02 au standard SQL.
- Supprimer la branche `feature/ci-02` (locale et `origin`) si ce n'est pas fait.
- Supprimer la branche `feature/dbt-01` (locale et `origin`) si ce n'est pas fait.
- Décision d'Antoaneta : collecte complète du catalogue gardée le lundi (corrections de fiches, ex. 36 raretés provisoires de M6 corrigées par TCGdex le 12/11) et contrôle quotidien des nouvelles cartes dans COL-04 (3 listes `/<langue>/cards` comparées au dernier catalogue, seules les fiches nouvelles téléchargées, prix dès le jour même). Ordre proposé : DBT-01 → CI-02 → COL-04 → DBT-02 ; à vérifier dans la spec COL-04 : l'API ne donne-t-elle que le prix du jour (premiers jours d'un set irrattrapables) ?
- Corriger le logger de `cartograph.bin.collect.run` (`__name__` vaut `__main__` sous `-m`) : petit `fix` à part.
- `inv release` sur `develop` quand STO-02 est fusionné (v0.4.0 : FND-02 contient un `feat`), puis PR `develop` → `main`.
- Avant la porte 1 : relire dans un navigateur les conditions de Cardmarket et de TCGplayer (veille).
- Rapport de novembre à régénérer en fin de mois (`inv suivi --mois 2026-11 --force`, commentaire gardé), puis `statut: fait` ; mettre à jour les chiffres de `docs/gouvernance/green-it.md`. Chaque début de mois : `inv ci` puis `inv suivi`, commentaire.
- optimisation-collecte : l'exécution `42687236424` (9 novembre au soir, `catalogue=oui`, 2 h 04) peut cocher l'exécution manuelle attendue ; reste la PR et la release si pas encore faites (code déjà sur `main`).
- Antoaneta : `inv release` sur `develop` (sans effet sur la version : seulement `docs` et `chore`, rien à taguer ; PR directe `develop` → `main` possible), PR `develop` → `main`. Puis vérifier `gh repo view AntoanetaStoyanova/cartograph --json licenseInfo` = MIT, cocher la dernière case de docs/plans/lot-doc-01-readme-licence.md et passer plan et spec à `fait`.
- Antoaneta : commit de la doc, PR `feature/collecte-rapide` vers `develop`, `inv release`, PR vers `main` ; commit et `git envoyer` du README de `cartograph-data`.
- Antoaneta : exécution manuelle `catalogue=oui` avant le lundi 16 novembre ; relever la durée de « Collecter », vérifier catalogue publié, prix dans `data-2026-11`, manifeste ; comparer le SHA-256 du catalogue au manifeste (STO-01). Puis cocher les dernières cases de docs/plans/optimisation-collecte.md et passer plan et spec à `fait`.
- Antoaneta : rattrapage du 9 novembre, relance prix seuls (`-f catalogue=non`, environ 1 h 20), à confirmer.
- Clore docs/plans/lot-sto-01-manifeste.md : après l'exécution `catalogue=oui`, comparer le SHA-256 du catalogue (`gh release download catalogue`) au manifeste, cocher le dernier critère de la spec, passer plan et spec à `fait`.
- Porte 0 franchie le 15 novembre 2026 (P0-DEC) : neuf tests tranchés dans la spec maîtresse.
- Antoaneta : avant PRO-02, demander aux testeurs leur logiciel de caisse et un fichier d'import exemple.
- `cadrage-flux.md` : flux d'export pro (FX7 et FX8, écrans) à ajouter quand PRO-01 et PRO-02 seront planifiés.

### Références

- docs/plans/col-04-nouvelles-cartes-sets.md, docs/specs/col-04-nouvelles-cartes-sets.md
- src/cartograph/bin/collect/sets.py, catalogue.py, prices.py, snapshot.py, run.py, manifest.py, report.py

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
> ### Reste à faire
> ### Références

---

## [2026-10-27] — Spec M2, feuille de route, FND-00, FND-01 et COL-T8

### Fait

- Session ouverte (`/workspace-init`).
- Revue de la spec M2 : T1 tranché d'avance (prix TCGdex identiques FR/EN, même `idProduct` Cardmarket) ; catalogue FR = 22 155 cartes.
- Vérifié sur 4 cartes (fr/en/de) : prix TCGdex identiques par `idProduct` ; les cartes japonaises ont leurs propres produits Cardmarket.
- Décisions validées : catalogue recollecté chaque semaine ; explorer `tcgdex/price-history` comme source de prix ; repli « moyenne par rareté » pour la référence du modèle A ; seuil de complétude (≥ 98 % des jours) + liste de trous acceptés ; dbt en staging / intermediate / marts (`fct_` / `dim_` dans marts).
- Décisions validées : invoke conservé ; projet 100 % gratuit (aucune API payante) ; embeddings calculés dans GitHub Actions sur CPU (à mesurer en phase 0), Kaggle réservé au fine-tuning P3.
- Décisions validées : modèle A reformulé (prix de référence Cardmarket du produit) ; deux dépôts (`cartograph` + `cartograph-data`) ; surveillance = e-mail GitHub + fraîcheur dbt + healthchecks.io ; Releases sans fusion ; collection en Parquet via la variable dbt `collection_path` ; fine-tuning décidé fin mars 2027 (jalon).
- Spec mise à jour avec toutes ces décisions (T1 tranché, T9 ajouté, couches dbt staging / intermediate / marts partout, grain prix par finition et devise, vérification pokemontcg.io / Scrydex).
- `docs/specs/roadmap-lots.md` et `docs/plans/roadmap-lots.md` créés : 14 actions, lots avec exigences, dépôt, livrable, dépendances et priorité ; ordre d'exécution par dépendances (collecte d'abord, T8 avant toute Release publique, P3 supprimables en dernier).
- Méthode par lot actée : lot de code → `/workspace-plan <ID>` puis `/workspace-dev`, et cocher dans `roadmap-lots.md` ; lot sans code (mesure, lecture, décision) → demande directe, décision consignée dans la spec maîtresse ; petits lots consécutifs planifiables ensemble.
- `docs/specs/lot-fnd-01-socle.md` et `docs/plans/lot-fnd-01-socle.md` créés. Constaté : `.venv` Windows seulement (uv absent de WSL) ; `.gitignore` ignore `uv.lock`, `src/cartograph/log/` et `src/cartograph/config/` ; découverte du paquet `where = ["."]` à vérifier. Décisions : WSL seul, `beartype_this_package()`, config TOML + dataclass figée, tâches invoke ajoutées avec leur lot.
- Décidé : développement sous WSL (VS Code + extension WSL), CI sous Ubuntu ; `uv.lock`, `log/` et `config/` versionnés. Plan FND-01 complété : sections « Pourquoi WSL » et « Mise en place du poste de travail ».
- Plan FND-01 : la mise en place du poste (points 2 à 8) est exécutée par Antoaneta, Claude donne et explique les commandes puis vérifie les sorties.
- Lot FND-00 « Poste de travail » créé (`docs/plans/lot-fnd-00-poste.md`), exécuté par Antoaneta avec explications ; FND-01 en dépend et démarre au `uv sync`.
- Plan lot-fnd-00-poste — point 1 : WSL et Ubuntu fait. `wsl -l -v` : Ubuntu (22.04) par défaut, version 2 (plus `docker-desktop`, sans effet). `wsl --install` inutile ; `wsl --update` lancé, à confirmer avec `wsl --version`. Point 1 et critère coché dans `docs/plans/lot-fnd-00-poste.md`.
- Plan lot-fnd-00-poste — point 2 : Paquets de base fait (git 2.34.1, curl 7.81.0 mis à jour, build-essential déjà présent). Mot de passe sudo retrouvé.
- Plan lot-fnd-00-poste — point 3 : Git fait (`user.name=AntoanetaStoyanova`, e-mail Gmail, `core.autocrlf=input`). Constaté `credential.helper=store` (jetons HTTPS stockés en clair dans `~/.git-credentials`) : à retirer une fois SSH en place.
- Plan lot-fnd-00-poste — point 4 : Accès GitHub fait. `~/.ssh` appartenait à root (créé en 2024) → `chown toni` + `chmod 700` ; clé ed25519 sans passphrase, ajoutée sur GitHub (« ToniPC WSL ») ; `ssh -T` OK (AntoanetaStoyanova). Remote `origin` encore en HTTPS et `~/.git-credentials` présent.
- `origin` passé en SSH (`git fetch` OK sans identifiant). Décidé : retrait de `credential.helper` et `~/.git-credentials` côté WSL seulement ; révocation du jeton GitHub reportée (risque pour les push Windows, à tester à part).
- Plan lot-fnd-00-poste — point 5 : uv 0.13.6 installé dans `~/.local/bin` (utilisateur toni, sans sudo).
- Plan lot-fnd-00-poste — points 6 et 7 faits : VS Code connecté (« WSL: Ubuntu »), extensions Python (Microsoft) et Ruff (Astral) actives côté WSL ; règle « tout dans le terminal WSL » actée. Erreur Ruff « Unexpected error while trying to find the Ruff binary » attendue : `.venv` Windows encore présent, résolu en FND-01 (`uv sync` + interpréteur `.venv/bin/python`).
- Jeton HTTPS de WSL révoqué sur GitHub ; push Windows vérifié (`git push --dry-run` OK).
- **Lot FND-00 terminé** : toutes les cases cochées, FND-00 coché dans `docs/plans/roadmap-lots.md`.
- README : section Prérequis réécrite (WSL 2 et pourquoi, SSH, uv, VS Code + WSL, lien vers le plan FND-00) ; URL de clone corrigée (SSH, pseudo manquant). CONTRIBUTING : titre « dbtidy » → « cartograph ».
- Plan lot-fnd-01-socle — Étape 1 : Environnement WSL et fichiers ignorés (en cours, interrompue). `.venv` Windows supprimé, `uv sync` sous WSL (Python 3.13.0, `uv.lock` inchangé). `import cartograph` échouait → `pyproject.toml` : `where = ["src"]`, `include` retiré ; import OK. `.gitignore` : retiré `src/cartograph/config/` et `docs/` (specs et plans non versionnés, décidé avec Antoaneta), ajouté `logs/` ; `uv.lock` et `log/` n'y étaient déjà plus. Ruff a corrigé des espaces dans `__main__.py` et `tasks/__init__.py`.

- Décidé : docstrings au format NumPy (plan et spec FND-01 corrigés, ils disaient Google).
- Plan lot-fnd-01-socle — Étape 2 : Module de logs codé. `setup_logging(name, log_dir=None, level)` idempotent, console sur stderr, fichier seulement si `log_dir` ; `tests/test_log.py` (5 tests, dont stderr) verts.
- Plan lot-fnd-01-socle — Étape 3 : beartype codé. `uv add beartype` (0.23.1) ; `beartype_this_package()` et docstring corrigée dans `src/cartograph/__init__.py` ; `tests/test_beartype.py` vert.
- `inv ci` lancé par Antoaneta (`uv run` ou `.venv` activé, pas d'invoke apt) : ruff et mypy verts, 6 tests verts, couverture 84 % < 88 % à cause de `__main__.py` (test prévu à l'Étape 5). Interpréteur VS Code choisi. Étapes 1 à 3 cochées dans le plan, critères correspondants cochés dans la spec.
- Décidé : pas de `settings.toml` ni de registre JSON des modèles ; constante `LANGUAGES` dans `config/__init__.py`. La correspondance langue → modèle viendra avec le lot des modèles (dict typé, fichier seulement si config par environnement). Plan et spec FND-01 mis à jour (Étape 4, décisions Configuration / Validation, critère).
- Plan lot-fnd-01-socle — Étape 4 : Configuration des langues faite. `src/cartograph/config/__init__.py` (`LANGUAGES = ("fr", "en")`), `tests/test_config.py` ; ruff, mypy et test verts.
- Mesuré dans TCGdex : 22 155 cartes FR, 23 770 EN, 13 006 JA (186 sets) ; japonais : prix Cardmarket sur 28 cartes sur 30 tirées au hasard, aucun prix TCGplayer, `idProduct` propres.
- Décidé : collecte japonaise dès le départ (catalogue chaque semaine, prix chaque jour) pour constituer l'historique ; prix collectés une fois par produit Cardmarket (européen commun, japonais à part, ~13 000 appels de plus par jour sauf si T4 couvre le japonais) ; modèle A sans les cartes japonaises ; scan / OCR / modèle japonais restent P3 (JPN-01), faits si le temps le permet. Spec maîtresse mise à jour (langues, F1, sources, orchestration, modèle A, T6, points ouverts) ; COL-01 dans `roadmap-lots.md` ; `LANGUAGES = ("fr", "en", "ja")`, plan et spec FND-01 alignés.
- Plan lot-fnd-01-socle — Étape 5 : Point d'entrée fait. `__main__.py` réécrit (journalise le démarrage et `Langues : fr, en, ja`, docstrings NumPy), `tests/test_main.py` ; ligne FND-01 de `roadmap-lots.md` mise à jour (tâches invoke reportées à COL-02, FND-02, APP-01). ruff, mypy et 8 tests verts, couverture 100 %.
- Décidé : `python -m cartograph` écrit ses logs dans `logs/cartograph_<AAAAMMJJ_HHMMSS>.log` (`LOG_DIR` dans `__main__.py`, `logs/` ignoré par Git) ; test `test_main_writes_log_file` ajouté ; spec et plan FND-01 mis à jour. 9 tests verts, couverture 100 %.
- Antoaneta a ajouté `get_chemin()` dans `__main__.py` (logs dans `src/cartograph/log/`). Constaté : fichiers `.log` dans le dossier source versionné (3 non suivis), `test_main_writes_log_file` en échec (8/9), `print()` et `try/except` contraires au CONTRIBUTING. Proposé : `ROOT_DIR = Path(__file__).resolve().parents[2]`, `LOG_DIR = ROOT_DIR / "logs"`, en attente de validation.
- Décidé par Antoaneta : logs dans `src/cartograph/log/` via `get_chemin()`. Docstring de `get_chemin` corrigée (résumé sur une ligne ; exemple ensuite retiré par Antoaneta, titre `Examples` resté vide) et test `test_get_chemin_points_to_package_folder` ajouté (vert).
- `.gitignore` : ajouté `src/cartograph/log/*.log`. `tests/test_main.py` : fixture `isolated_logger` qui redirige `PROJECT_DIR` vers `tmp_path` ; `test_main_writes_log_file` vert, les tests n'écrivent plus dans `src/cartograph/log/`. 10 tests verts, couverture 95,56 %. Ruff rouge : F821 `logger` non défini dans le `except` de `main()` (modification d'Antoaneta en cours).
- Antoaneta : `print()` retirés de `main()`, `inv ci` vert (10 tests, couverture 95,56 %). Constaté : le `except` (lignes 40-41, non couvertes) appelle `logger` qui n'existe pas si `get_chemin` ou `setup_logging` échoue (`UnboundLocalError`) ; `setup_logging` appelé deux fois ; f-strings dans `logger.info` ; docstring de `main()` dit encore `logs/`. Proposé : retirer le `try/except`, en attente de validation.
- `main()` simplifié par Antoaneta (plus de `try/except`, un seul `setup_logging`, logs `%s`) ; docstring corrigée (`src/cartograph/log/`). ruff, mypy, 10 tests verts, couverture 100 % ; `inv ci` vert chez Antoaneta. Spec et plan FND-01 alignés (décision Logs, `.gitignore`, tests).
- Décidé : option A pour Ruff, `fix = true` gardé dans `pyproject.toml`, `--no-fix` dans la tâche `lint` (`tasks/__init__.py`) : `inv lint` / `inv ci` vérifient sans modifier les fichiers.
- Rotation des logs : `setup_logging(..., max_files=10)` ; `_prune_logs` supprime les plus anciens `<name>_*.log` avant de créer le nouveau (tri par nom = ordre chronologique) ; `mkdir` rétabli (il avait été commenté). 4 tests ajoutés dans `tests/test_log.py`. `inv ci` vert : 14 tests, couverture 100 %. Spec et plan FND-01 mis à jour.
- **Lot FND-01 terminé** : plan et spec entièrement cochés, FND-01 coché dans `docs/plans/roadmap-lots.md` ; commité par Antoaneta (`8c1270f`).
- Constaté : `invoke ci` = `pre=[check, test]`, corps vide (normal) ; `[tool.ruff] fix = true` fait modifier les fichiers par `inv lint` / `inv ci` (décision d'Antoaneta en attente).
- COL-T8 (conditions de redistribution) : lecture faite. TCGdex : base sous MIT (« Copyright (c) 2021 TCGdex »), aucune condition publiée sur les prix relayés (Cardmarket, TCGplayer) ni sur les images. pokemontcg.io : en fin de vie, inscriptions fermées, clés valables jusqu'au 1er mars 2027, migration vers Scrydex ; aucune condition de redistribution publiée. Cardmarket et TCGplayer : pages de conditions bloquées (403), à lire par Antoaneta ; selon des sources secondaires, TCGplayer revendique ses prix et interdit leur redistribution sans accord écrit. Décision de visibilité en attente.
- COL-T8 : clause TCGplayer lue par Antoaneta (« pricing information and card databases are the property of TCGplayer, Inc. », scraping interdit sans permission) : republication des prix TCGplayer exclue. Recommandé : option C (`cartograph-data` public, prix bruts Cardmarket et TCGplayer dans un dépôt privé `cartograph-prices`, seuls catalogue TCGdex et résultats dérivés publiés). Antoaneta a copié l'analyse COL-T8 dans `docs/plans/annex.md`.
- **COL-T8 terminé** : option C validée. Spec maîtresse (Données publiées, T8, points ouverts 23 dont 5 levés) et `roadmap-lots.md` (COL-T8 coché ; STO-01 et STO-03 vers le dépôt privé `cartograph-prices` ; pas d'artefact ni de journal avec des prix, car publics sur un dépôt public) mis à jour. `docs/plans/annex.md` gardé tel quel comme trace.
- Vérifié : API TCGplayer fermée (« We are no longer granting new API access at this time ») ; pokemontcg.io : inscriptions fermées (échec de création de compte), Scrydex payant (29 $/mois minimum, contraire à N1).
- Décidé : pokemontcg.io abandonné (inscriptions fermées, fin le 1er mars 2027, Scrydex payant), avec F2 et F5. Spec maîtresse : choix techniques, F1, F2, F5, sources, `int_card_id_mapping` retiré, orchestration, secrets (N14 et sécurité), répartition P2, repli T2, risque, points ouverts (23 dont 6 levés), sources du 27 octobre ajoutées. `roadmap-lots.md` : COL-03, PTC-01, PTC-02 abandonnés et retirés de l'ordre d'exécution.

### Reste à faire

- Supprimer ou garder les 3 `.log` de lancements manuels dans `src/cartograph/log/` (ignorés par Git).
- Feuille de route : [roadmap-lots](../docs/plans/roadmap-lots.md), `/workspace-plan COL-01` (client TCGdex, catalogue FR/EN/JA, prix par produit Cardmarket).

### Références

- [Spécification M2](../docs/specs/Spécification%20du%20projet%20final%20M2%20plateforme%20de%20données%20Pokémon%20TCG%20(1).md)
- [Spec roadmap-lots](../docs/specs/roadmap-lots.md)
- [Plan roadmap-lots](../docs/plans/roadmap-lots.md)
- [Spec lot-fnd-01-socle](../docs/specs/lot-fnd-01-socle.md)
- [Plan lot-fnd-01-socle](../docs/plans/lot-fnd-01-socle.md)
- [Plan lot-fnd-00-poste](../docs/plans/lot-fnd-00-poste.md)
- [Annexe COL-T8](../docs/plans/annex.md)
- [log/__init__.py](../src/cartograph/log/__init__.py), [cartograph/__init__.py](../src/cartograph/__init__.py), [test_log.py](../tests/test_log.py), [test_beartype.py](../tests/test_beartype.py), [config/__init__.py](../src/cartograph/config/__init__.py), [test_config.py](../tests/test_config.py), [__main__.py](../src/cartograph/__main__.py), [test_main.py](../tests/test_main.py)

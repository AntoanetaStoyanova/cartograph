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

## [2026-10-27] — Revue de la spec M2 et feuille de route

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

### Reste à faire

- Exécuter [lot-fnd-01-socle](../docs/plans/lot-fnd-01-socle.md) — Étape 1 : Environnement WSL et fichiers ignorés.
- Feuille de route : [roadmap-lots](../docs/plans/roadmap-lots.md), COL-T8 (sans code) avant ORC-01.

### Références

- [Spécification M2](../docs/specs/Spécification%20du%20projet%20final%20M2%20plateforme%20de%20données%20Pokémon%20TCG%20(1).md)
- [Spec roadmap-lots](../docs/specs/roadmap-lots.md)
- [Plan roadmap-lots](../docs/plans/roadmap-lots.md)
- [Spec lot-fnd-01-socle](../docs/specs/lot-fnd-01-socle.md)
- [Plan lot-fnd-01-socle](../docs/plans/lot-fnd-01-socle.md)
- [Plan lot-fnd-00-poste](../docs/plans/lot-fnd-00-poste.md)

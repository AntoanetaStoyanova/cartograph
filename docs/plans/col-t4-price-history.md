# Plan — Test T4 : historique de tcgdex/price-history

*Rédigé le : 29 octobre 2026*
*Référence : [col-t4-price-history.md](../specs/col-t4-price-history.md)*

## Objectif

Mesurer ce que contient vraiment `tcgdex/price-history` et décider de son rôle : historique du modèle B, source quotidienne, secours d'une semaine manquée.

## Prérequis

- `gh` connecté (fait le 29 octobre 2026).
- `cards-2026-10-28.parquet` disponible (Release `catalogue` de `cartograph-data`).
- Aucun code de production : scripts dans le dossier temporaire de session, lancés avec `uv run python -I` depuis `cartograph`.

## Étape 1 — Inventaire et format

- [ ] `git clone --depth 1 https://github.com/tcgdex/price-history` dans le dossier temporaire ; taille sur disque.
- [ ] Inventaire par langue et par source : sets, fichiers, cartes ; liste des suffixes de fichiers (`.ebay.json`, `.tcgplayer.json`, autres).
- [ ] Format de chaque source : clés de premier niveau, variantes et états (`normal-good`…), champs par date ; unité et devise (centimes ? euros / dollars ?) vérifiées sur quelques cartes connues ; présence des moyennes 1 / 7 / 28 jours annoncées par le README.
- [ ] Fraîcheur : `meta/*.json`, dernier commit et activité (issues, commits sur 12 mois) par `gh api`.
- [ ] Licence : absence de `LICENSE` confirmée (contenu du dépôt, historique Git du fichier, `gh api repos/tcgdex/price-history/license`) ; licence des autres dépôts `tcgdex` pour comparaison.
- [ ] Section « Mesures — inventaire et format » ajoutée à la note.

## Étape 2 — Profondeur, densité et couverture

- [ ] Par source : première et dernière date, nombre de dates par carte et par variante, ventes (`count`) par carte ; distribution (médiane, quartiles).
- [ ] Part des cartes avec au moins 6 mois de points au moins hebdomadaires (une semaine ISO sans point = trou), par source et par langue.
- [ ] Correspondance avec notre catalogue : chemin `fr/<set>/<numéro>` contre `set_id` / `local_id` de `cards-2026-10-28.parquet` ; table de correspondance des noms de sets si besoin (ex. `2021swsh`) ; part des cartes et des produits Cardmarket (`id_product`) couverts.
- [ ] Section « Mesures — profondeur et couverture » ajoutée à la note, avec les commandes ou le script utilisé.

## Étape 3 — Décision et reports

- [ ] Note : sections « Limites » et « Décision » (modèle B P2 / P3, source quotidienne oui / non, secours oui / non, licence) ; critères d'acceptation cochés.
- [ ] Spec maîtresse : décision « Historique initial », F1 (mention « ou depuis tcgdex/price-history »), collecte (fréquence, semaine manquée), modèle B (règle de priorité), table des tests (T4 tranché), question ouverte sur le contenu du dépôt fermée.
- [ ] `docs/plans/roadmap-lots.md` : COL-T4 coché ; MLB-01 en P2 ou P3 ; P0-DEC informé.
- [ ] Si la licence reste incertaine : proposer à Antoaneta une question aux mainteneurs (issue GitHub), sans l'ouvrir.

## Critères de fin

- [ ] `uv run inv ci` passe (aucun code touché, vérification de non-régression)
- [ ] Critères d'acceptation de la spec cochés

# Test T4 — Historique de tcgdex/price-history

*Rédigé le : 29 octobre 2026*

## Contexte

Test informatif de la porte 0 ([spec maîtresse](Spécification%20du%20projet%20final%20M2%20plateforme%20de%20données%20Pokémon%20TCG%20(1).md), T4) : le dépôt public `tcgdex/price-history` a été vu mais pas exploré. La spec maîtresse lui prête trois rôles possibles :

- amorcer l'historique de prix (le modèle B passe de P3 à P2 avec au moins 6 mois d'historique exploitable) ;
- servir de source quotidienne des prix à la place des appels carte par carte (F1) ;
- rattraper un jour de collecte manqué.

Premier aperçu par l'API GitHub (29 octobre 2026), à confirmer par l'exploration :

- dossiers `fr/` et `en/` (137 sets chacun) et `meta/` ; un fichier JSON par carte et par source (`fr/base1/1.ebay.json`, `en/2021swsh/1.tcgplayer.json`) ;
- sources : **eBay** (fr) et **TCGplayer** (en), **pas Cardmarket** ;
- `meta/ebay-fr.json` : dernier relevé le 9 juin 2025 ; `meta/tcgplayer-en.json` : 24 septembre 2024 ; dernier commit le 9 juin 2025 ;
- format eBay : historique par variante et état (`normal-good`), une entrée par date avec `avg`, `count`, `min`, `max` (montants en centimes, à confirmer) ; ventes rares (souvent `count` = 1) ;
- le README annonce une licence MIT, mais le dépôt n'a pas de fichier `LICENSE` (404) et GitHub n'en détecte aucune.

## Objectif

Une note chiffrée qui répond aux trois rôles par oui ou non, et une décision écrite : priorité du modèle B (P2 ou P3), source quotidienne (oui / non), secours en cas de jour manqué (oui / non).

## Périmètre

- Clone superficiel du dépôt hors de `cartograph`, inventaire : sources, sets, cartes, variantes, taille.
- Format des fichiers de chaque source (clés, unités, devise, signification de `avg` et des moyennes sur 1, 7 et 28 jours annoncées).
- Profondeur et densité de l'historique par source : première et dernière date, jours avec au moins une vente, nombre de ventes par carte, part des cartes avec au moins 6 mois de points réguliers.
- Fraîcheur : derniers relevés, dernier commit, activité du dépôt.
- Couverture face à notre catalogue (`cards-2026-10-28.parquet`) : correspondance des identifiants (`set_id` / `local_id`), part des cartes et des produits Cardmarket couverts.
- Licence : statut réel (README contre absence de `LICENSE`) et conséquence pour un dépôt public.
- Décision et reports dans la spec maîtresse, la roadmap et le journal.

## Hors périmètre

- Aucun code dans `src/cartograph` ni dans `tasks/` : scripts d'exploration jetables (dossier temporaire), commandes reproduites dans la note.
- Aucune ingestion de l'historique dans les snapshots ni dans dbt (lot à créer seulement si la décision le justifie).
- Aucune comparaison de niveau de prix avec Cardmarket sur la même période : nos relevés commencent le 28 octobre 2026, après la fin du dépôt.

## Décisions

| Sujet | Décision | Raison |
| --- | --- | --- |
| Emplacement du clone | `git clone --depth 1` dans le dossier temporaire de session, jamais dans `cartograph` | ≈ 1,1 Go ; les fichiers portent déjà l'historique daté, l'historique Git n'apporte que la fraîcheur, lue par l'API |
| Outils | Python standard (`json`, `pathlib`) et `pyarrow` déjà présent, lancés avec `uv run python -I` | Pas de nouvelle dépendance pour un test informatif |
| Historique « exploitable » pour le modèle B | Source Cardmarket, ou source dont on montre qu'elle suit Cardmarket ; au moins 6 mois de points au moins hebdomadaires sur une part significative des produits du catalogue | La cible du modèle B est la variation du prix Cardmarket à 4 semaines ; un autre marché (eBay, TCGplayer en dollars) ne mesure pas la même chose |
| Source quotidienne | Exige un dépôt encore mis à jour et des prix Cardmarket | F1 collecte des prix Cardmarket ; un dépôt arrêté ne remplace pas la collecte |
| Licence | Sans fichier `LICENSE`, aucune réutilisation publiée tant que le statut n'est pas éclairci (issue ou question aux mainteneurs, à proposer à Antoaneta) | La mention du README seule est fragile pour un dépôt public de données |
| Forme du livrable | Ce document, complété des sections « Mesures », « Limites » et « Décision », comme la note COL-T3 | Même format que les autres tests de la porte 0 |

## Critères d'acceptation

- [ ] Inventaire chiffré : sources, nombre de sets et de cartes par langue, taille.
- [ ] Format décrit pour chaque source : clés, unité, devise, sens de `avg`, `count`, `min`, `max` et des moyennes annoncées.
- [ ] Profondeur et densité mesurées par source (dates extrêmes, distribution des ventes par carte, part des cartes avec 6 mois de points au moins hebdomadaires).
- [ ] Couverture de notre catalogue mesurée (cartes et produits Cardmarket).
- [ ] Fraîcheur et licence établies.
- [ ] Décision écrite pour les trois rôles ; spec maîtresse (décision « Historique initial », F1, risques, question ouverte), `roadmap-lots.md` (COL-T4 coché, MLB-01 P2 ou P3) et journal mis à jour.

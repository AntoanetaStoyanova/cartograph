# Test T4 — Historique de tcgdex/price-history

*Rédigé le : 29 octobre 2026*

## Contexte

Test informatif de la porte 0 ([spec maîtresse](Spécification%20du%20projet%20final%20M2%20plateforme%20de%20données%20Pokémon%20TCG%20(1).md), T4). `tcgdex/price-history` est un dépôt GitHub de l'équipe TCGdex, distinct de l'API que la collecte interroge. La spec maîtresse lui prêtait trois rôles possibles :

- amorcer l'historique de prix : avec au moins 6 mois d'historique exploitable, le modèle B passe de P3 à P2 ;
- servir de source quotidienne des prix à la place des appels carte par carte (F1) ;
- rattraper un jour de collecte manqué.

## Méthode

- `git clone --depth 1 https://github.com/tcgdex/price-history` dans un dossier temporaire (7 s, 304 Mo sans `.git`), commit `a1edbb9` du 9 juin 2025 ; fraîcheur et licence lues par `gh api`.
- Script jetable (Python standard + `pyarrow`, lancé avec `uv run python -I`) : parcours des 27 753 fichiers, dates et ventes par carte, plus longue suite de semaines ISO consécutives avec au moins un point, correspondance `<langue>/<set>/<numéro>` avec `set_id` / `local_id` de `cards-2026-10-28.parquet`.

## Mesures

### Inventaire et format

| | `en/` | `fr/` |
| --- | --- | --- |
| Source | TCGplayer (marché américain) | eBay |
| Sets / fichiers (un par carte) | 137 / 14 958 | 137 / 12 795 |
| Variantes | finition × état (`normal-good`, `reverse-nearmint`, `holo-good`…) | `normal` × état (`good`, `nearmint`, `mint`, `poor`) |
| Dernier relevé (`meta/*.json`) | 24 septembre 2024 | 9 juin 2025 |

Format d'un fichier : `data.<variante>` contient `avg`, `avg7`, `avg28` (valeurs courantes) et `history`, un relevé par date de vente avec `avg`, `count`, `min`, `max`. Montants entiers, probablement en centimes de la devise du marché (dollars pour TCGplayer : `25` pour une reverse courante).

### Profondeur et densité

| | TCGplayer (`en/`) | eBay (`fr/`) |
| --- | --- | --- |
| Période | 12 novembre 2022 → 24 septembre 2024 | 17 novembre 2022 → 9 juin 2025 |
| Dernière date par carte (médiane) | 22 septembre 2024 | 8 janvier 2025 |
| Dates avec vente par carte (q1 / médiane / q3) | 54 / 92 / 162 | 2 / 6 / 17 |
| Ventes par carte (q1 / médiane / q3) | 70 / 140 / 401 | 2 / 6 / 18 |
| Cartes avec 26 semaines consécutives ou plus | 1 028 (6,9 %) | 312 (2,4 %) |

### Couverture de notre catalogue

- Identifiants alignés sur TCGdex : 14 940 fichiers `en` sur 14 958 et 12 784 `fr` sur 12 795 trouvent leur carte dans le catalogue.
- Produits Cardmarket correspondants : 13 385 (`en`) et 11 995 (`fr`), sur 29 314 interrogés chaque jour. Aucune carte japonaise.

### Fraîcheur et licence

- Dernier commit le 9 juin 2025 ; plus aucune mise à jour depuis 16 mois (TCGplayer arrêté depuis 13 mois de plus). Dépôt non archivé, 1 issue ouverte.
- Le README annonce une licence MIT et renvoie à un fichier `LICENSE`, absent du dépôt ; GitHub ne détecte aucune licence (`gh api …/license` : 404).

## Limites

- Unité et devise déduites de quelques valeurs, non documentées.
- La densité est mesurée sur les dates de vente : une semaine sans vente compte comme un trou, ce qui est la bonne mesure pour une série de prix.
- Comparaison de niveau avec Cardmarket impossible : nos relevés commencent le 28 octobre 2026, après la fin du dépôt.

## Décision

**T4 défavorable : `tcgdex/price-history` n'est pas utilisé.**

| Rôle | Verdict | Raison |
| --- | --- | --- |
| Historique du modèle B | Non | Aucun prix Cardmarket : la cible du modèle B est le prix Cardmarket ; eBay trop clairsemé (6 ventes médianes par carte en deux ans et demi), TCGplayer en dollars sur un autre marché ; seules 2,4 % (eBay) et 6,9 % (TCGplayer) des cartes ont 6 mois de points hebdomadaires |
| Source quotidienne des prix | Non | Dépôt arrêté depuis juin 2025, pas de Cardmarket |
| Secours d'un jour manqué | Non | Il s'arrête avant le début de la collecte |

- **Modèle B en P3** (règle de la spec maîtresse) : il s'entraîne sur la collecte propre, commencée le 28 octobre 2026 ; prototype possible dès janvier 2027 (≈ 70 jours), première évaluation en avril (≈ 150 jours).
- Chaque relevé Cardmarket contient déjà `avg1`, `avg7`, `avg30` et `trend` : une tendance sur 30 jours existe dès le premier jour, sans historique externe.
- Licence incertaine : même pour une analyse ponctuelle, aucune donnée du dépôt n'est republiée.
- Second marché : les prix TCGplayer arrivent déjà avec chaque relevé TCGdex (`tcgplayer_json`, 17 587 produits sur 29 314 le 29 octobre 2026) ; à exploiter plus tard si besoin, sans dépendre de ce dépôt.

## Critères d'acceptation

- [x] Inventaire chiffré : sources, nombre de sets et de cartes par langue, taille.
- [x] Format décrit pour chaque source : clés, unité, devise, sens de `avg`, `count`, `min`, `max` et des moyennes annoncées.
- [x] Profondeur et densité mesurées par source (dates extrêmes, distribution des ventes par carte, part des cartes avec 6 mois de points au moins hebdomadaires).
- [x] Couverture de notre catalogue mesurée (cartes et produits Cardmarket).
- [x] Fraîcheur et licence établies.
- [x] Décision écrite pour les trois rôles ; spec maîtresse, `roadmap-lots.md` et journal mis à jour.

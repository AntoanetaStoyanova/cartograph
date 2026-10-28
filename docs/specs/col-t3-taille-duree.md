# Test T3 — Taille et durée de la collecte

*Rédigé le : 28 octobre 2026*

## Contexte

Test bloquant de la porte 0 ([spec maîtresse](Spécification%20du%20projet%20final%20M2%20plateforme%20de%20données%20Pokémon%20TCG%20(1).md), T3) : collecter une fois le catalogue, mesurer la durée des prix, le JSON brut et le Parquet, extrapoler sur 365 jours.

Seuils : Parquet annuel sous environ 1 Go (500 Mo en confort), reconstruction de la base en moins de 10 minutes, collecte quotidienne des prix en moins de 2 heures, 14 Go de disque sur une machine GitHub.

## Mesures

Collecte réelle `inv collect --catalogue --languages fr` du 28 octobre 2026, en local (WSL, connexion domestique), pause de 0,1 s entre requêtes.

| Étape | Lignes | Durée | Débit | Parquet zstd | Brut gzip |
| --- | --- | --- | --- | --- | --- |
| Catalogue fr | 22 155 fiches | 57 min 33 s | 6,4 req/s | 2,74 Mo (124 o/ligne) | 4,91 Mo (222 o/ligne) |
| Prix fr | 18 254 produits | 43 min 32 s | 7,0 req/s | 0,55 Mo (30 o/ligne) | 0,74 Mo (41 o/ligne) |

0 échec ; 2 978 cartes fr sans `idProduct` (86,6 % en ont un) ; 19 177 cartes avec produit donnent 18 254 produits distincts (95,2 %).

Listes de l'API le même jour : fr 22 155, en 23 770, ja 13 006 identifiants. L'anglais recouvre le français (22 062 identifiants communs, 1 708 propres à l'anglais) ; le japonais a ses propres identifiants (14 en commun).

## Extrapolation trois langues

Produits Cardmarket à interroger chaque jour, avec les ratios du français :

| Source | Calcul | Produits |
| --- | --- | --- |
| fr | mesuré | 18 254 |
| en seulement | 1 708 × 0,866 × 0,952 | ≈ 1 400 |
| ja | 13 006 × 0,866 × 0,952 | ≈ 10 700 |
| **Total** | | **≈ 30 400** (borne haute ≈ 32 700 si toutes les cartes ja ont un produit) |

| Mesure | Estimation | Seuil | Verdict |
| --- | --- | --- | --- |
| Prix quotidiens | 30 400 / 7,0 req/s ≈ **1 h 13** (borne haute 1 h 18) | < 2 h | Passé |
| Jour du catalogue | 58 931 fiches / 6,4 req/s ≈ 2 h 33, + prix ≈ **3 h 46** | job GitHub < 6 h | Passé, marge ≈ 2 h |
| Parquet des prix, 365 jours | 0,92 Mo/jour → **≈ 335 Mo** | | |
| Parquet du catalogue, 52 semaines | 7,3 Mo/semaine → **≈ 380 Mo** | | |
| **Parquet annuel total** | **≈ 715 Mo** | < 1 Go (confort 500 Mo) | Passé, au-dessus du confort |
| Brut gzip annuel (dépôt privé) | prix ≈ 450 Mo + catalogue ≈ 680 Mo ≈ **1,1 Go** | fichier de Release < 2 Gio | Passé (archives mensuelles ≈ 100 Mo) |
| Reconstruction | 365 fichiers de prix simulés (11,1 M lignes) : lecture pyarrow 1,0 s, agrégat par produit 0,1 s, 1,7 Go en mémoire | < 10 min | Passé, très large |
| Disque d'une machine GitHub | une année complète < 2 Go | 14 Go | Passé |

Simulation : 365 copies d'un fichier de prix de 30 400 lignes, lues avec `pyarrow.dataset`. Elle sous-estime un peu la taille (lignes répétées, mieux compressées) mais mesure bien le temps de lecture ; DuckDB et dbt lisent en flux, sans tout charger en mémoire.

## Limites

- Débit mesuré depuis la France ; celui d'une machine GitHub peut différer. La première exécution manuelle d'ORC-01 le confirmera.
- Taux de produits Cardmarket japonais supposé égal au français ; borne haute donnée.
- Parquet en delta non mesuré (il faut deux jours de prix) : inutile tant que le Parquet complet tient sous le seuil.

## Décision

**T3 passé.** Aucun repli nécessaire : Parquet complet quotidien, pas de delta, pas d'hébergement Hugging Face, pas de bascule vers `tcgdex/price-history` pour la durée.

- ORC-01 : un seul job ; délai maximal autour de 5 h le jour du catalogue (≈ 3 h 46 attendus) ; prix seuls ≈ 1 h 15.
- SUR-01 : alerter si la collecte des prix dépasse 2 h (signe d'un ralentissement de l'API).
- Le catalogue pèse plus que les prix sur l'année. Si l'on vise le confort de 500 Mo, la piste est le catalogue en delta (seules les fiches modifiées depuis la semaine précédente), à décider en P2, pas avant.
- À revoir après les sept jours de SUR-T5 avec les durées réelles des machines GitHub.

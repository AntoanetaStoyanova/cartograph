---
type: reference
statut: en cours
redige_le: 2026-11-15
---

# Dossier de veille

*Rédigé le 15 novembre 2026. Revu à chaque porte (section « Révisions ») ; un changement vu entre deux portes est noté tout de suite.*

Ce dossier suit les sources de données, les services gratuits, les conditions légales et les outils dont dépend Cartograph. Chaque ligne donne la source consultée, la date de vérification, le constat et la décision du projet qui en découle.

## Méthode

- **Sources** : page officielle d'abord (documentation, conditions, licence, API du service) ; une source secondaire est marquée comme telle. Une page illisible est notée avec sa date et la raison.
- **Datation** : chaque ligne porte sa date de vérification. Une ligne non revue depuis la porte précédente est revérifiée à la porte suivante.
- **Critère** : un constat est gardé s'il change ou confirme une décision du projet (spec maîtresse, test de la porte 0, lot de la roadmap) ; sinon il n'entre pas dans le dossier.
- **Suite** : un constat qui change une décision est reporté dans la spec maîtresse et la roadmap le jour même.

## Sources de données

| Source | Vérifié le | Constat | Décision | Lot |
| --- | --- | --- | --- | --- |
| [FAQ de TCGdex](https://tcgdex.dev/faq) | 15 novembre 2026 | « free to use and requires no API key » ; « no published hard rate limits, but please be considerate » ; mise en cache locale conseillée | Source principale ; pause de 0,1 s entre deux requêtes, aucune relecture inutile | COL-01 |
| [Prix relayés par TCGdex](https://tcgdex.dev/markets-prices) | 15 novembre 2026 | Deux fournisseurs : Cardmarket (EUR, quotidien ; moyenne, bas, tendance, moyennes à 1, 7 et 30 jours, versions holo) et TCGplayer (USD, horaire à quotidien ; par variante) ; fournisseur absent si la carte n'est pas en vente ; aucune condition de redistribution sur la page | Collecte quotidienne suffisante ; prix manquants traités comme absents ; redistribution tranchée par T8 (voir « Veille légale ») | COL-01, T8 |
| [État des langues de TCGdex](https://api.tcgdex.net/status) | 15 novembre 2026 | Fiches de cartes : anglais 23 912 sur 24 140 (99,06 %), français 22 342 sur 23 007 (97,11 %), japonais 13 156 sur 19 261 (68,30 %) | Français suffisant (T2) ; japonais collecté mais exclu du modèle A, scan japonais en repli par code et numéro (T6) | COL-T2, JPN-01 |
| [Documentation de pokemontcg.io](https://docs.pokemontcg.io/) | 15 novembre 2026 | « New account registrations are no longer available » ; clés existantes valables jusqu'au 1er mars 2027 ; migration vers Scrydex conseillée | Inchangé depuis le 27 octobre 2026 : source abandonnée (F2, F5) | — |
| [Tarifs de Scrydex](https://scrydex.com/pricing) | 15 novembre 2026 | Aucune offre gratuite ; à partir de 29 $ par mois (5 000 crédits) | Écarté : contraire à N1 (aucun service payant) | — |
| [API TCGplayer](https://docs.tcgplayer.com/docs/getting-started) | 15 novembre 2026 | « We are no longer granting new API access at this time » | Prix TCGplayer seulement par TCGdex | — |
| [`tcgdex/price-history`](https://github.com/tcgdex/price-history) (API GitHub) | 15 novembre 2026 | Dernier commit le 9 juin 2025 ; aucune licence déclarée ; dépôt non archivé | Inchangé depuis T4 : écarté, aucun historique externe | COL-T4 |
| [`tcgdex/cards-database`](https://github.com/tcgdex/cards-database) (API GitHub) | 15 novembre 2026 | Licence MIT ; dernier push le 14 novembre 2026 | Catalogue maintenu ; republication avec attribution (T8) | STO-01 |

## Quotas des services gratuits

| Service | Vérifié le | Constat | Décision | Lot |
| --- | --- | --- | --- | --- |
| [Runners GitHub](https://docs.github.com/en/actions/reference/runners/github-hosted-runners) | 15 novembre 2026 | Linux standard d'un dépôt public : 4 processeurs, 16 Go, 14 Go de SSD ; « free and unlimited on public repositories » | Collecte et index d'embeddings dans `cartograph-data` (public) | ORC-01, EMB-01 |
| [Limites de GitHub Actions](https://docs.github.com/en/actions/reference/limits) | 15 novembre 2026 | 6 h par job ; 20 jobs simultanés au plus (offre gratuite) | Collecte la plus longue mesurée : 2 h 04 le lundi, près de 3 fois sous la limite ; index d'embeddings découpé sur plusieurs jours s'il dépassait 6 h (repli de T9) | ORC-01, EMB-T9 |
| [Releases GitHub](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases) | 15 novembre 2026 | Moins de 2 Gio par fichier, 1 000 fichiers par Release, ni taille totale ni bande passante limitées | Release mensuelle `data-AAAA-MM` de `cartograph-prices` : 32 fichiers au 15 novembre 2026, soit environ 65 par mois, loin des 1 000 | COL-02, STO-01 |
| [cron-job.org](https://cron-job.org/en/faq/) | 15 novembre 2026 | « entirely free of charge » ; jusqu'à une exécution par minute ; délai de 30 s par requête ; 64 Ko de réponse lus | L'appel `workflow_dispatch` répond dès que l'exécution est créée, sans attendre la collecte : délai sans effet | ORC-02 |
| [healthchecks.io](https://healthchecks.io/pricing/) | 15 novembre 2026 | Offre Hobbyist gratuite : 20 contrôles, 100 entrées de journal par contrôle | Un contrôle utilisé (« Collecte cartograph ») | SUR-01 |
| [Stockage de Hugging Face Hub](https://huggingface.co/docs/hub/storage-limits) | 15 novembre 2026 | Compte gratuit : stockage public « best-effort », 100 Go en privé ; 500 Go au plus par fichier | Index d'embeddings de quelques dizaines de Mo : sans contrainte, public ou privé | EMB-02 |
| [Notebooks Kaggle](https://www.kaggle.com/docs/notebooks) | 15 novembre 2026 | Page rendue en JavaScript, quota GPU illisible en texte ; le chiffre de la spec maîtresse vient d'une source secondaire | Point ouvert maintenu ; à relire connecté avant toute décision de fine-tuning (porte 2) | SCN-D1 |

## Veille légale

Constats tirés des textes ; pas un avis juridique.

| Sujet | Source | Vérifié le | Constat | Décision | Lot |
| --- | --- | --- | --- | --- | --- |
| Prix Cardmarket | [Conditions générales de Cardmarket](https://www.cardmarket.com/en/Policies/GeneralTermsAndConditions/D) | 15 novembre 2026 | Page refusée sans navigateur (HTTP 403) ; lecture du 27 octobre 2026 conservée | Prix jamais republiés (T8) ; à relire dans un navigateur à la porte 1 | T8 |
| Droit des bases de données | [Directive 96/9/CE](https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:31996L0009), articles 7 et 10 | 15 novembre 2026 | Le fabricant peut interdire l'extraction et la réutilisation d'une partie substantielle ; l'extraction répétée et systématique de parties non substantielles l'est aussi si elle lèse ses intérêts ; durée de 15 ans | Prix bruts dans le dépôt privé `cartograph-prices` ; seuls des agrégats et des prédictions sont publiés | T8, STO-01 |
| Prix TCGplayer | [Conditions d'utilisation de TCGplayer](https://help.tcgplayer.com/hc/en-us/articles/205004918-Terms-of-ServiceTCGplayer) | 15 novembre 2026 | Page refusée sans navigateur (HTTP 403) ; lecture du 27 octobre 2026 conservée (« pricing information and card databases are the property of TCGplayer, Inc. ») | Prix TCGplayer collectés, jamais republiés | T8 |
| Catalogue TCGdex | [Licence de `tcgdex/cards-database`](https://github.com/tcgdex/cards-database) (API GitHub) | 15 novembre 2026 | MIT ; la FAQ dit seulement « open source » | Catalogue republié sans images, avec attribution (README) | DOC-01 |
| Code d'open_clip | [Licence d'open_clip](https://github.com/mlfoundations/open_clip/blob/main/LICENSE) | 15 novembre 2026 | Texte MIT (© Ilharco et al., 2012-2021), non reconnu automatiquement par GitHub | Utilisable et citable | EMB-02 |
| Poids open_clip ViT-B/32 laion2b_s34b_b79k | [Fiche du modèle](https://huggingface.co/laion/CLIP-ViT-B-32-laion2B-s34B-b79K) | 15 novembre 2026 | Licence MIT ; la fiche déclare hors cadre « any deployed use case of the model - whether commercial or not », déconseille la recherche d'images même en environnement restreint et limite l'usage à l'anglais | Licence compatible ; usage hors cadre recommandé par les auteurs : critère à peser dans le choix d'EMB-02 et à citer s'il est retenu | EMB-02 |
| Code et poids DINOv2 | [Fiche `timm`](https://huggingface.co/timm/vit_small_patch14_dinov2.lvd142m), [dépôt `facebookresearch/dinov2`](https://github.com/facebookresearch/dinov2) | 15 novembre 2026 | Apache 2.0 pour le code et les poids ; aucune restriction d'usage dans la fiche ; `timm` sous Apache 2.0 | Utilisable, publication des vecteurs possible avec la mention de licence | EMB-02 |
| Publication sur Hugging Face | [Conditions de Hugging Face](https://huggingface.co/terms-of-service) | 15 novembre 2026 | L'auteur est seul responsable de ses contenus et garantit en avoir le droit ; un dépôt public donne à tout utilisateur une licence perpétuelle d'usage ; les mentions de licence ne peuvent pas être retirées | Seuls les vecteurs et le code sont publiés, jamais les images ; licence du modèle citée dans la fiche du dépôt d'index | EMB-02 |
| Kaggle | [Conditions de Kaggle](https://www.kaggle.com/terms) | 15 novembre 2026 | Page rendue en JavaScript, illisible sans navigateur | À lire avant un fine-tuning (porte 2) | SCN-D1 |
| RGPD | [Règlement 2016/679](https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:32016R0679), article 2, paragraphe 2, point c | 15 novembre 2026 | Le règlement ne s'applique pas au traitement « par une personne physique dans le cadre d'une activité strictement personnelle ou domestique » | Aucune donnée personnelle collectée : la collection reste sur le poste de l'utilisateur, l'application des testeurs ne remonte rien ; à revoir si une remontée de données est ajoutée | GOV-01, GOV-03 |
| Marques Pokémon | [Mentions légales de Pokémon](https://www.pokemon.com/us/legal) | 15 novembre 2026 | « © 1995–2026 Nintendo/Creatures Inc./GAME FREAK inc. » ; noms des Pokémon déposés comme marques ; rien sur les images de cartes | Avertissement dans le README ; images de cartes jamais stockées ni publiées | DOC-01 |

## Changements constatés

Revérification du 15 novembre 2026 par rapport à la spec maîtresse (sources du 26 et du 27 octobre 2026) :

- Aucune décision à changer : pokemontcg.io, Scrydex, TCGplayer, `tcgdex/price-history` et les limites de GitHub sont tels que la spec les décrit.
- Chiffres nouveaux : couverture par langue de TCGdex, quotas de cron-job.org, healthchecks.io et Hugging Face, 20 jobs simultanés sur GitHub Actions.
- Le quota GPU de Kaggle reste non vérifié sur la page officielle (page non lisible sans navigateur).
- Conditions de Cardmarket et de TCGplayer : pages refusées sans navigateur le 15 novembre 2026 ; la lecture du 27 octobre 2026 tient jusqu'à la porte 1.
- Fiche du modèle open_clip laion2b : usage déployé déclaré hors cadre par les auteurs, alors que la licence MIT le permet. Fait nouveau pour EMB-02, sans changer de décision avant la comparaison des deux modèles.

## Révisions

| Date | Porte | Changement |
| --- | --- | --- |
| 15 novembre 2026 | 0 | Dossier créé (GOV-05) : sources de données, quotas et veille légale revérifiés sur les pages officielles |

# Spec — Découpage du projet en lots par action

*Rédigé le : 27 octobre 2026*

## Contexte

La [spec maîtresse](Spécification%20du%20projet%20final%20M2%20plateforme%20de%20données%20Pokémon%20TCG%20(1).md) décrit le quoi et le pourquoi du projet. Ce document fixe seulement la façon de la découper en unités de travail ; il n'en recopie pas le contenu.

## Objectif

Disposer d'une liste de lots regroupés par action, chacun livrable seul, avec ses dépendances, pour enchaîner les `/workspace-plan lot-<id>-<sujet>` puis `/workspace-dev` sans se reposer la question de l'ordre.

## Périmètre

- Toutes les exigences F1 à F22 et N1 à N16, et les tests T1 à T9 de la porte 0.
- Les deux dépôts : `cartograph` (code) et `cartograph-data` (workflow planifié, manifeste, Releases).

## Hors périmètre

- Calendrier et dates : l'ordre découle des dépendances, pas d'un planning.
- Détail des tâches à l'intérieur des lots : chaque lot aura son propre plan.
- Dagster : non planifié tant que la question ouverte de la spec maîtresse n'a pas reçu de « oui ».

## Décisions

| Sujet | Décision | Raison |
| --- | --- | --- |
| Unité de découpage | Le lot : livrable seul (code + tests verts, ou décision écrite), démontrable | Avancer par incréments vérifiables, compatibles avec des sessions de weekend |
| Regroupement | Par action (bloc fonctionnel), identifiant `<ACTION>-NN` | Retrouver vite ce qui touche à la collecte, à dbt, au scan… |
| Tests de la porte 0 | Un lot par test, identifiant `<ACTION>-T<n>`, rattaché à l'action qu'il valide ; la porte elle-même est un lot de décision (`P0-DEC`) | Les tests produisent des mesures et des décisions, pas seulement du code |
| T1 | Lot déjà fait (tranché le 27 octobre 2026) | Prix identiques entre langues européennes, modèle A reformulé |
| T8 avant toute publication | La lecture des conditions de redistribution précède la première Release publique | Un échec de T8 change la visibilité du dépôt de données |
| Collecte au plus tôt | Les lots qui font tourner la collecte passent juste après les fondations | Chaque jour de prix non collecté est perdu définitivement |
| Jeux du scan figés tôt | Le découpage réglage / test est figé avant le premier essai de scan | Exigence du protocole d'évaluation |
| Fine-tuning | Lot de décision `SCN-D1` après l'évaluation du scan ; `FT-01` n'existe que si la décision est « oui » | Ne pas l'oublier sans l'engager par défaut |
| Modèle B | Priorité fixée par T4 (P2 si au moins 6 mois d'historique exploitable, sinon P3) | Règle de la spec maîtresse |
| Lots P3 | En fin d'ordre, marqués supprimables, supprimés de bas en haut | Protéger le cœur |
| Plans de lot | Slug `lot-<id>-<sujet>` en minuscules (ex. `lot-fnd-01-socle`) | Lien direct entre la feuille de route et les plans détaillés |

## Critères d'acceptation

- [ ] Chaque exigence F1 à F22 et N1 à N16 est couverte par au moins un lot.
- [ ] Chaque test T1 à T9 a son lot, et `P0-DEC` dépend des six tests bloquants.
- [ ] Chaque lot indique ses exigences, son dépôt, son livrable, ses dépendances et sa priorité.
- [ ] L'ordre d'exécution respecte toutes les dépendances déclarées.
- [ ] Les lots P3 sont en fin d'ordre et marqués supprimables.

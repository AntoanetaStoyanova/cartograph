# Plan — Feuille de route par lots

## Étape 1 — Fondations (FND)

|     | Id | Lot | Exigences | Dépôt | Livrable vérifiable | Dépend de | Prio |
| --- | -- | --- | --------- | ----- | ------------------- | --------- | ---- |
| [x] | FND-01 | Socle | N9 | code | Paquet installable | FND-00 | P1 |
| [ ] | DBT-01 | Projet dbt | F4 | code | `dbt build` vert | FND-01 | P1 |
| — | STO-03 | ~~Archivage du brut~~ | F3 | — | Clos le 15 novembre 2026 | — | — |

## Étape 13 — Actions P2

|     | Id | Lot | Exigences | Dépôt | Livrable vérifiable | Dépend de | Prio |
| --- | -- | --- | --------- | ----- | ------------------- | --------- | ---- |
| [ ] | EMB-03 | Index incrémental | F19 | data | Index republié | EMB-02 | P2 |
| [ ] | MLB-01 | Modèle B — sans objet | F15 | code | Tendance | MLA-02 | — |

## Ordre d'exécution

1. **Porte 0** : DOC-01 → P0-DEC

## Critères de fin

- [ ] `uv run inv ci` passe à la fin de chaque lot de code.

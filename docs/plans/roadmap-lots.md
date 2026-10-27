# Plan — Feuille de route par lots

*Rédigé le : 27 octobre 2026*
*Référence : [roadmap-lots.md](../specs/roadmap-lots.md)*

## Objectif

Lister les lots du projet par action, avec leurs dépendances, puis un ordre d'exécution. Chaque lot se détaille au moment de le commencer avec `/workspace-plan lot-<id>-<sujet>`.

## Prérequis

- Spec maîtresse à jour du 27 octobre 2026.
- Dépôt : `code` = `cartograph`, `data` = `cartograph-data`.
- Statut : cocher un lot ici quand son plan détaillé est terminé.

## Étape 1 — Fondations (FND)

|     | Id | Lot | Exigences | Dépôt | Livrable vérifiable | Dépend de | Prio |
| --- | -- | --- | --------- | ----- | ------------------- | --------- | ---- |
| [x] | FND-00 | Poste de travail (exécuté par Antoaneta) | N8 | — | WSL, Git, SSH GitHub, uv et VS Code connecté à WSL, vérifiés ([plan](lot-fnd-00-poste.md)) | — | P1 |
| [x] | FND-01 | Socle Python | N2, N8 | code | beartype ajouté, module `log/` configuré, `config/` avec la liste des langues (`fr`, `en`, `ja`) ; `uv run inv ci` passe. Tâches invoke `collect` / `dbt` / `app` reportées à COL-02, FND-02, APP-01 | FND-00 | P1 |
| [ ] | FND-02 | Squelette dbt-duckdb | F6, N2 | code | Projet dbt (profil DuckDB, dossiers staging / intermediate / marts), tâche `inv dbt` ; `dbt debug` et `dbt build` vides passent | FND-01 | P1 |

## Étape 2 — Collecte (COL)

|     | Id | Lot | Exigences | Dépôt | Livrable vérifiable | Dépend de | Prio |
| --- | -- | --- | --------- | ----- | ------------------- | --------- | ---- |
| [x] | COL-T1 | Prix par langue (T1) | T1 | — | Tranché le 27 octobre 2026, consigné dans la spec maîtresse | — | P1 |
| [x] | COL-T8 | Conditions de redistribution (T8) | T8, N1 | — | Note écrite sur TCGdex, pokemontcg.io, Cardmarket, TCGplayer : republication autorisée, tolérée ou non, et décision de visibilité du dépôt de données. Fait le 27 octobre 2026 : option mixte, prix dans le dépôt privé `cartograph-prices` ([annexe](annex.md)) | — | P1 |
| [ ] | COL-01 | Client TCGdex | F1, N3, N10 | code | Récupération du catalogue (par langue, japonais compris) et des prix (une fois par produit Cardmarket : européen commun, japonais à part) avec pauses et nouvelles tentatives ; tests sur réponses enregistrées | FND-01 | P1 |
| [ ] | COL-02 | Snapshots Parquet | F3, N3 | code | `prices-AAAA-MM-JJ.parquet` quotidien et `cards-AAAA-MM-JJ.parquet` hebdomadaire, zstd, triés ; relancer le même jour remplace le fichier ; tâche `inv collect` | COL-01 | P1 |
| — | COL-03 | ~~Brut pokemontcg.io~~ | F1, N1 | — | Abandonné le 27 octobre 2026 : inscriptions fermées, fin du service le 1er mars 2027, Scrydex payant | — | — |
| [ ] | COL-T3 | Taille et durée de la collecte (T3) | T3, N16 | — | Mesures (durée, JSON, Parquet complet, delta) et extrapolation sur 365 jours, décision écrite | COL-02 | P1 |
| [ ] | COL-T4 | Exploration de tcgdex/price-history (T4) | T4 | — | Note : profondeur, format, fraîcheur, licence ; décision source quotidienne oui / non et priorité du modèle B | — | P1 |
| [ ] | COL-T2 | Couverture française et variantes (T2) | T2 | — | Part des cartes de tes sets avec fiche et prix, variantes vérifiées, décision écrite | COL-01, SCN-T7 | P1 |

## Étape 3 — Orchestration et stockage (ORC, STO)

|     | Id | Lot | Exigences | Dépôt | Livrable vérifiable | Dépend de | Prio |
| --- | -- | --- | --------- | ----- | ------------------- | --------- | ---- |
| [ ] | ORC-01 | Dépôt de données et workflow planifié | F1, N13, N14, N15 | data | `cartograph-data` créé ; cron décalé + `workflow_dispatch` avec paramètres, `concurrency`, délai max, permissions minimales, installation du collecteur depuis `cartograph` ; une exécution manuelle réussit | COL-02, COL-T8 | P1 |
| [ ] | STO-01 | Releases mensuelles et manifeste | F3, N13, N16 | data | Fichier du jour ajouté à `data-AAAA-MM` dans le dépôt privé `cartograph-prices` (jeton dans les secrets), manifeste sans prix (tailles, lignes, empreintes) commité chaque jour | ORC-01 | P1 |
| [ ] | STO-02 | Reconstruction de la base | N2 | code | `inv rebuild` télécharge les Releases et reconstruit le `.duckdb` local, jamais versionné | STO-01, FND-02 | P1 |
| [ ] | STO-03 | Archivage du brut | F3 | data | JSON brut envoyé directement dans le dépôt privé `cartograph-prices` (pas d'artefact : ils sont publics sur un dépôt public), archive compressée mensuelle en Release ; aucun prix dans les journaux d'exécution | STO-01 | P1 |

## Étape 4 — Surveillance (SUR)

|     | Id | Lot | Exigences | Dépôt | Livrable vérifiable | Dépend de | Prio |
| --- | -- | --- | --------- | ----- | ------------------- | --------- | ---- |
| [ ] | SUR-01 | Alertes et résumé | F4, N12 | data | E-mail d'échec GitHub actif, signal healthchecks.io en fin de collecte, résumé dans la page d'exécution | ORC-01 | P1 |
| [ ] | SUR-T5 | Sept jours de collecte (T5) | T5 | data | Sept jours sans trou, échec volontaire et collecte suspendue déclenchent bien les deux alertes ; décision écrite | SUR-01, STO-01 | P1 |
| [ ] | SUR-02 | Contrôle du jour 60 | N13 | data | Constat écrit que le cron tourne toujours après 60 jours | SUR-T5 (+ 60 jours) | P1 |

## Étape 5 — Transformations dbt (DBT)

|     | Id | Lot | Exigences | Dépôt | Livrable vérifiable | Dépend de | Prio |
| --- | -- | --- | --------- | ----- | ------------------- | --------- | ---- |
| [ ] | DBT-01 | Sources et staging du catalogue | F6 | code | `sources.yml`, `stg_tcgdex__cards`, `stg_tcgdex__sets` ; échantillon de snapshots versionné pour la CI | FND-02, COL-02 | P1 |
| [ ] | DBT-02 | Staging des prix | F6 | code | `stg_tcgdex__prices` au grain carte × marché × finition × date, avec devise | DBT-01 | P1 |
| [ ] | DBT-03 | Intermediate rareté | F6 | code | `int_rarity_mapping` construit sur les valeurs réellement collectées | DBT-01 | P1 |
| [ ] | DBT-04 | Marts du catalogue et des prix | F6 | code | `dim_card`, `dim_set`, `fct_price_snapshot` incrémental | DBT-02, DBT-03 | P1 |
| [ ] | DBT-05 | Collection personnelle | F16 | code | `stg_collection` via la variable `collection_path`, Parquet d'exemple versionné, `fct_collection_value` | DBT-04 | P1 |
| [ ] | DBT-06 | Référence et tendances | F14, F17 | code | `mart_price_baseline` (repli par rareté), `mart_price_trends` | DBT-04 | P1 |

## Étape 6 — Qualité des données (QUA)

|     | Id | Lot | Exigences | Dépôt | Livrable vérifiable | Dépend de | Prio |
| --- | -- | --- | --------- | ----- | ------------------- | --------- | ---- |
| [ ] | QUA-01 | Tests dbt | F7, N5 | code | Tests standards + personnalisés (prix négatif, complétude, couverture ≥ 98 % avec trous acceptés, fraîcheur) | DBT-04 | P1 |
| [ ] | QUA-02 | dbt après chaque collecte | F7, N5 | data | `dbt build` et tests dans le workflow quotidien ; un échec fait échouer l'exécution | QUA-01, ORC-01 | P1 |

## Étape 7 — Intégration continue et sécurité (CI)

|     | Id | Lot | Exigences | Dépôt | Livrable vérifiable | Dépend de | Prio |
| --- | -- | --- | --------- | ----- | ------------------- | --------- | ---- |
| [ ] | CI-01 | CI du code Python | N15 | code | Workflow ruff + mypy + pytest, cache uv, filtres de chemins, annulation des exécutions obsolètes | FND-01 | P1 |
| [ ] | CI-02 | CI des données | N5, N15 | code | `dbt build` sur échantillon et sqlfluff dans la CI | CI-01, QUA-01 | P1 |
| [ ] | CI-03 | Sécurité des dépôts | N14 | code, data | Dependabot, actions épinglées, secret scanning, CodeQL, protection de `main` | CI-01, ORC-01 | P2 |

## Étape 8 — Embeddings et index (EMB)

|     | Id | Lot | Exigences | Dépôt | Livrable vérifiable | Dépend de | Prio |
| --- | -- | --- | --------- | ----- | ------------------- | --------- | ---- |
| [ ] | EMB-T9 | Embeddings sur CPU (T9) | T9 | code | Mesure sur 500 images (runner et PC), modèle et prétraitement choisis, décision CPU / Kaggle écrite | COL-01 | P1 |
| [ ] | EMB-01 | Téléchargement des images | F8 | code | Images basse résolution téléchargées hors dépôt, reprenable | COL-02 | P1 |
| [ ] | EMB-02 | Index initial | F9 | code | Module d'embedding à révision figée ; workflow manuel qui calcule l'index sur CPU et le publie sur Hugging Face | EMB-T9, EMB-01 | P1 |

## Étape 9 — Scan et évaluation (SCN)

|     | Id | Lot | Exigences | Dépôt | Livrable vérifiable | Dépend de | Prio |
| --- | -- | --- | --------- | ----- | ------------------- | --------- | ---- |
| [ ] | SCN-T7 | Cartes physiques (T7), comptage japonais (T6) | T7, T6 | — | Inventaire FR / JP, photos prises, cartes FR vérifiées dans TCGdex, couverture JP notée ; décision écrite | COL-01 | P1 |
| [ ] | SCN-02 | Vérité terrain et jeux figés | F13 | code | Fichier de vérité terrain, découpage réglage / test par carte, figé et versionné | SCN-T7 | P1 |
| [ ] | SCN-01 | Scan par embeddings | F11 | code | Redressement OpenCV + plus proche voisin NumPy ; top-5 pour une photo | EMB-02, SCN-02 | P1 |
| [ ] | SCN-03 | Évaluation du scan | F13, N6 | code | top-1, top-5, temps, IC 95 % par carte, détail par condition, confusions de variantes comptées à part | SCN-01 | P1 |
| [ ] | SCN-D1 | Décision sur le fine-tuning | — | — | Décision écrite d'après le jeu de réglage | SCN-03 (et OCR-02 s'il est fait) | P1 |

## Étape 10 — Modèle A (MLA)

|     | Id | Lot | Exigences | Dépôt | Livrable vérifiable | Dépend de | Prio |
| --- | -- | --- | --------- | ----- | ------------------- | --------- | ---- |
| [ ] | MLA-01 | Variables et découpage | F14 | code | Jeu de variables (dont popularité), découpage dans le temps et par carte, sans fuite | DBT-06 | P1 |
| [ ] | MLA-02 | Références et LightGBM | F14 | code | Référence recalculée sur l'entraînement, régression linéaire, LightGBM ; métriques médianes et IC par bootstrap | MLA-01 | P1 |
| [ ] | MLA-03 | Prédictions publiées | F14 | code | Table `ml_predictions` avec version du modèle et marge d'erreur mesurée | MLA-02 | P1 |

## Étape 11 — Application Streamlit (APP)

|     | Id | Lot | Exigences | Dépôt | Livrable vérifiable | Dépend de | Prio |
| --- | -- | --- | --------- | ----- | ------------------- | --------- | ---- |
| [ ] | APP-01 | Socle et page Marché | F17 | code | Application lancée par `inv app`, lecture des marts seulement, tendances et complétude | DBT-06 | P1 |
| [ ] | APP-02 | Page Ma collection | F16, F17 | code | Valeur totale et évolution, répartitions, cartes les plus chères | DBT-05, APP-01 | P1 |
| [ ] | APP-03 | Page Scan | F11, F16, F17 | code | Envoi d'une photo, top-5 avec score, validation et ajout au Parquet de collection | SCN-01, APP-02 | P1 |
| [ ] | APP-04 | Page Qualité et suivi | F4, F7, F17 | code | Fraîcheur, résultats des tests, dernière collecte réussie | QUA-02, APP-01 | P1 |
| [ ] | APP-05 | Prix attendu dans Marché | F14, F17 | code | Prix attendu affiché avec nom du modèle et marge d'erreur | MLA-03, APP-01 | P1 |

## Étape 12 — Documentation et démonstration (DOC)

|     | Id | Lot | Exigences | Dépôt | Livrable vérifiable | Dépend de | Prio |
| --- | -- | --- | --------- | ----- | ------------------- | --------- | ---- |
| [ ] | DOC-01 | README et licence | N7 | code, data | README minimal, avertissement Nintendo / The Pokémon Company, licence choisie | FND-01 | P1 |
| [ ] | DOC-02 | Architecture et décisions | N7 | code | Schéma d'architecture, notes de décision, dictionnaire de données (`dbt docs`) | DBT-06 | P1 |
| [ ] | DOC-03 | Rapport des résultats | — | code | Résultats chiffrés du scan et du modèle A, limites, conclusion honnête | SCN-03, MLA-02 | P1 |
| [ ] | DOC-04 | Démonstration et plan B | — | code | Démonstration de bout en bout reproductible, vidéo enregistrée | APP-03, APP-05 | P1 |

## Porte 0

|     | Id | Lot | Exigences | Dépôt | Livrable vérifiable | Dépend de | Prio |
| --- | -- | --- | --------- | ----- | ------------------- | --------- | ---- |
| [ ] | P0-DEC | Décision de la porte 0 | T1 à T9 | — | Décision écrite dans la spec maîtresse pour chaque test, replis appliqués | COL-T1, COL-T2, COL-T3, SUR-T5, SCN-T7, COL-T8 (+ COL-T4, EMB-T9 informatifs) | P1 |

## Étape 13 — Actions P2

|     | Id | Lot | Exigences | Dépôt | Livrable vérifiable | Dépend de | Prio |
| --- | -- | --- | --------- | ----- | ------------------- | --------- | ---- |
| [ ] | OCR-01 | Lecture du numéro | F10 | code | EasyOCR et PaddleOCR comparés sur la barre du numéro | SCN-01 | P2 |
| [ ] | OCR-02 | Évaluation de l'OCR | F13 | code | OCR ajouté au protocole, comparaison appariée descriptive | OCR-01, SCN-03 | P2 |
| [ ] | EMB-03 | Index incrémental | F19, N4 | data | Après chaque collecte, nouvelles cartes embeddées et index republié ; images indisponibles listées | EMB-02, ORC-01 | P2 |
| [ ] | MLF-01 | Suivi MLflow | N9 | code | Expériences du modèle A tracées (paramètres, métriques, version des données) | MLA-01 | P2 |
| [ ] | ANO-01 | Prix anormaux | F18 | code | Cartes sur ou sous-évaluées et variations anormales dans Marché | MLA-03, APP-01 | P2 |
| [ ] | DCK-01 | Docker compose | F21, N11 | code | `docker compose up` lance l'application, MLflow et la reconstruction de la base | APP-05, MLF-01 | P2 |
| [ ] | DCK-02 | Image en CI | N11 | code | Image construite et testée en CI, publiée sur GHCR | DCK-01, CI-01 | P2 |
| — | PTC-01 | ~~Rapprochement des identifiants~~ | F5 | — | Abandonné le 27 octobre 2026, avec COL-03 | — | — |
| — | PTC-02 | ~~Recoupement des prix~~ | F2 | — | Abandonné le 27 octobre 2026, avec COL-03 | — | — |
| [ ] | MLB-01 | Modèle B (si T4 favorable) | F15 | code | Tendance à 4 semaines contre prix inchangé et moyenne mobile, évaluée par cohortes | MLA-02, COL-T4 | P2 ou P3 |

## Étape 14 — Actions P3 (supprimables)

|     | Id | Lot | Exigences | Dépôt | Livrable vérifiable | Dépend de | Prio |
| --- | -- | --- | --------- | ----- | ------------------- | --------- | ---- |
| [ ] | FT-01 | Fine-tuning (si SCN-D1 = oui) | — | code | Modèle affiné sur Kaggle, évalué sur le même jeu de test | SCN-D1 | P3 |
| [ ] | HYB-01 | Scan hybride | F12, F13 | code | Top-5 embeddings + OCR, évalué dans le protocole | OCR-02 | P3 |
| [ ] | EMB-04 | Second modèle d'embeddings | F13 | code | Comparaison de deux modèles sur le même jeu | SCN-03 | P3 |
| [ ] | JPN-01 | Robustesse japonaise | F13 | code | Index japonais et résultats sur les cartes JP | SCN-03, SCN-T7 | P3 |
| [ ] | WEB-01 | Scan webcam continu | F20 | code | Capture, vote sur plusieurs images, gain du vote chiffré | SCN-01 | P3 |
| [ ] | PAG-01 | Vitrine GitHub Pages | F22 | code | Documentation dbt et rapport de qualité en ligne, badges | DOC-02, QUA-02 | P3 |
| [ ] | MLB-01 | Modèle B (si T4 défavorable) | F15 | code | Voir étape 13 | MLA-02 | P3 |

## Ordre d'exécution recommandé

Déduit des dépendances. Les lots de mesure et de lecture (T4, T7, T8…) peuvent s'intercaler pendant que la collecte tourne.

1. **Mettre la collecte en route** : FND-00 → FND-01 → COL-T8 → COL-01 → COL-02 → ORC-01 → STO-01 → SUR-01 → SUR-T5 (tourne sept jours en fond) → STO-03
2. **Porte 0** : DOC-01 → COL-T3 → COL-T4 → SCN-T7 → COL-T2 → EMB-T9 → P0-DEC
3. **Pipeline de données** : CI-01 → FND-02 → STO-02 → DBT-01 → DBT-02 → DBT-03 → DBT-04 → QUA-01 → QUA-02 → CI-02 → DBT-05 → DBT-06 → SUR-02 (dès 60 jours de collecte)
4. **Application, première version** : APP-01 → APP-02 → APP-04
5. **Scan** : SCN-02 → EMB-01 → EMB-02 → SCN-01 → SCN-03 → OCR-01 (P2) → OCR-02 (P2) → SCN-D1
6. **Modèle A** : MLA-01 → MLF-01 (P2) → MLA-02 → MLA-03 → APP-05 → APP-03
7. **Finaliser le cœur** : DOC-02 → DOC-03 → DOC-04
8. **P2** : CI-03 → EMB-03 → ANO-01 → DCK-01 → DCK-02 → MLB-01 (si P2)
9. **P3, supprimables de bas en haut** : FT-01 (si décidé) → HYB-01 → EMB-04 → JPN-01 → MLB-01 (si P3) → PAG-01 → WEB-01

## Critères de fin

- [ ] `uv run inv ci` passe à la fin de chaque lot de code.
- [ ] Tous les lots P1 sont cochés.
- [ ] Toutes les exigences F1 à F22 et N1 à N16 sont couvertes par un lot terminé ou supprimé par décision écrite.
- [ ] `P0-DEC` et `SCN-D1` sont consignées dans la spec maîtresse.

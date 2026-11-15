---
type: reference
statut: en cours
redige_le: 2026-11-15
---

# Bilan Green IT

*Rédigé le 15 novembre 2026, chiffres d'octobre et de novembre 2026 (novembre arrêté au 15). Mis à jour avec les rapports de [suivi](suivi/).*

Cartograph tourne sans serveur ni GPU : une collecte par jour sur un runner GitHub, le reste sur un poste personnel. Ce bilan chiffre l'énergie du calcul distant et liste les choix qui la limitent.

## Choix sobres

| Choix | Effet mesuré | Source |
| --- | --- | --- |
| Une seule collecte par jour, lancée par cron-job.org | un job quotidien, sans relance automatique | ORC-02 |
| Une requête de prix par produit Cardmarket, pas par carte et par langue | 29 314 requêtes au lieu d'environ 58 000 | COL-01 |
| Le lundi, prix lus dans les fiches du catalogue au lieu d'une seconde passe | 2 h 04 au lieu de 3 h 54 de runner, soit environ 1 h 50 de moins par semaine | optimisation de la collecte, 9 novembre 2026 |
| Pause de 0,1 s entre deux requêtes, nouvelles tentatives espacées | charge limitée sur l'API gratuite de TCGdex | COL-01 |
| Parquet compressé en zstd, aucune donnée quotidienne commitée | environ 905 Mo de Parquet par an ; dépôt `cartograph-data` à 37 Kio | test T3, manifeste du 15 novembre 2026 |
| Images des cartes jamais stockées ni publiées | téléchargées le temps du calcul, puis supprimées avec la machine | spec maîtresse, licences |
| Modèles d'embedding pré-entraînés, utilisés sur CPU, sans entraînement | index complet estimé à 8 minutes (open_clip) ou 15 minutes (DINOv2) sur un runner | test T9 |
| Fine-tuning seulement s'il est décidé fin mars 2027, d'après le jeu de réglage | aucun calcul GPU à ce jour | SCN-D1 |

## Chiffres

Énergie estimée des minutes de runner de la collecte (`collect.yml` de `cartograph-data`), d'après les rapports de suivi :

| Mois | Exécutions | Minutes | Énergie | Émissions | Équivalent payant |
| --- | --- | --- | --- | --- | --- |
| Octobre 2026 | 9 | 650 | 0,20 kWh | 0,07 kg CO₂e | 7,80 $ |
| Novembre 2026 (au 15) | 20 | 1 879 | 0,57 kWh | 0,22 kg CO₂e | 22,55 $ |

Extrapolation sur un an, au rythme de novembre (prix seuls environ 76 minutes, lundi environ 124 minutes) : environ 580 minutes par semaine, soit environ 30 000 minutes, 9 kWh et 3,5 kg CO₂e par an. Le calcul de l'index d'embeddings ajoute moins de 15 minutes à chaque recalcul complet.

Pour comparer : 9 kWh correspondent à quelques jours de fonctionnement d'un réfrigérateur domestique ; c'est un ordre de grandeur, pas une mesure.

## Hypothèses

- Runner de dépôt public : 4 processeurs, 16 Go de mémoire.
- Puissance selon la méthode [Cloud Carbon Footprint](https://www.cloudcarbonfootprint.org/docs/methodology/) : moyenne Azure de 0,78 à 3,76 W par processeur, 50 % d'utilisation faute de mesure, 0,392 W par Go de mémoire, PUE de 1,185, soit 18,2 W.
- Facteur d'émission de la région East US (0,379 kg CO₂e par kWh) : la région réelle des runners n'est pas publiée.
- Minutes arrondies au-dessus par job, comme la facturation de GitHub ; équivalent payant au prix d'un runner Linux de 4 processeurs (0,012 $ la minute, [page de prix de GitHub](https://docs.github.com/en/billing/reference/actions-runner-pricing)). Rien n'est payé : les minutes sont gratuites pour un dépôt public.
- Valeurs dans `cartograph.config`, consultées le 15 novembre 2026.

## Limites

- Estimation, pas mesure : GitHub ne donne ni la consommation ni la région d'un runner.
- Hors périmètre : poste personnel, réseau, stockage des Releases, serveurs de TCGdex, fabrication du matériel.
- Novembre est un mois partiel ; le bilan se complète avec chaque rapport mensuel.

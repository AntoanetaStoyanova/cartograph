# Spécification du projet final M2 : plateforme de données Pokémon TCG

Oct 26, 2026 · @antoaneta · mis à jour le 27 octobre 2026

## Contexte et objectifs

Le projet construit une plateforme de données Pokémon TCG : elle collecte chaque jour les cartes françaises et leurs prix, historise leur évolution, identifie une carte à partir d'une photo, prédit des prix et les présente dans une application.

Il s'agit du projet final individuel de la deuxième année de master Big Data et IA à SUP de VINCI, présenté en soutenance en septembre 2027. Les notes des modules ne comptent pas pour le diplôme : le projet doit montrer que les compétences de l'année sont acquises.

**Objectifs :**

1. livrer un projet cohérent et démontrable de bout en bout, de la donnée brute à l'application ;
2. monter en compétence sur le pipeline de données (ingestion, dbt, qualité), la vision par ordinateur et le machine learning ;
3. produire une trace publique et reproductible (dépôt GitHub, documentation) utile pour la recherche de poste.

**Critères de réussite :**

- la collecte tourne seule et couvre au moins 98 % des jours de l'année, chaque trou étant expliqué ;
- les tests de qualité des données passent en intégration continue ;
- le scan est évalué sur toutes les cartes réelles disponibles (50 à 70 environ), avec des intervalles de confiance et des résultats chiffrés pour chaque méthode ;
- les modèles de prix sont comparés à des références simples, et la conclusion est honnête même si elle est négative ;
- la démonstration fonctionne de bout en bout, avec un plan B préparé.

## Périmètre et priorités

Le cœur du projet porte sur les cartes françaises ; tout le reste est ordonné par priorité et se supprime de bas en haut si le temps manque.

| Priorité | Contenu |
| --- | --- |
| P1, cœur obligatoire | Collecte quotidienne des prix et hebdomadaire du catalogue depuis TCGdex ; stockage en snapshots Parquet ; modèles dbt staging, intermediate et marts avec tests ; dashboard de collection et de marché ; scan par embeddings avec évaluation chiffrée ; modèle A de prix attendu ; documentation et démonstration reproductible |
| P2, important | lecture du numéro de carte par OCR pour départager les réimpressions ; recoupement avec pokemontcg.io et rapprochement des identifiants ; index d'embeddings mis à jour de façon incrémentale ; intégration continue complète ; Docker (image et docker compose) ; suivi des expériences avec MLflow |
| P3, bonus | Modèle B de tendance à 4 semaines (exploratoire) ; méthode hybride de scan ; scan continu par webcam (quasi temps réel) ; comparaison de deux modèles d'embeddings ; test de robustesse sur cartes japonaises ; fine-tuning de l'embedding (décision fin mars 2027) ; orchestration avec Dagster |
| Exclu | Application mobile ; scan en vrai temps réel (30 images par seconde) ; entraînement d'un modèle de zéro ; conseil d'achat ou d'investissement ; déploiement en production |

Les langues du catalogue (noms, textes, images) sont définies dans le module de configuration `cartograph.config` (français, anglais et japonais dès le départ) ; ajouter une langue revient à modifier cette seule liste. Les prix ne dépendent pas de la langue européenne : Cardmarket regroupe les langues européennes dans un même produit, et TCGdex relaie ce prix pour toutes ces langues (vérifié le 27 octobre 2026 : même `idProduct` et mêmes prix en français, anglais et allemand). Ils sont donc collectés une seule fois par produit Cardmarket. Les cartes japonaises sont des produits distincts, avec leurs propres prix : elles sont collectées dès le départ pour constituer leur historique, qui ne se rattrape pas (décidé le 27 octobre 2026).

## Hypothèses et contraintes

Le projet est individuel, gratuit et réalisé sur les weekends ; les points marqués « à confirmer » dépendent d'informations que l'école n'a pas encore données.

| Sujet | Hypothèse ou contrainte | Statut |
| --- | --- | --- |
| Soutenance | Septembre 2027, soit environ onze mois de travail | Annoncée, jour exact inconnu |
| Livrables | Code, rapport et démonstration | À confirmer |
| Validation des modules | Le projet valide tout ou partie des modules ; d'autres projets complètent à l'oral | À confirmer |
| Exigences techniques de l'école | Aucune technologie imposée (Spark, streaming) | À confirmer |
| Temps disponible | Weekends seulement ; hypothèse d'une journée par weekend (6 à 8 h) | À confirmer |
| Coût | Zéro : outils et quotas gratuits uniquement | Contrainte ferme |
| Matériel | Windows et Ubuntu, sans GPU ; embeddings calculés sur CPU dans GitHub Actions (test T9) ; Kaggle (GPU) réservé au fine-tuning (P3) | Contrainte ferme |
| Environnement de référence | Ubuntu (ou WSL), pour éviter les écarts entre machines | Décision |
| Dépôt | Public sur GitHub | Décision |
| Cartes réelles | Environ 50 à 70 cartes physiques françaises, toutes réservées au réglage et au test, jamais ajoutées à l'index ; cartes japonaises en plus, pour le seul test de robustesse | À compter (porte 0, test T7) |
| Employeur | Aucune donnée ni outil de l'environnement professionnel dans le projet | Contrainte ferme |
| Stockage du modèle et des embeddings | Hugging Face Hub (compte gratuit), révision du modèle figée | Décision |

Le volume de données reste modeste : un catalogue de l'ordre de plusieurs dizaines de milliers de cartes. Si le jury attend une volumétrie « Big Data », la profondeur viendra de l'historique quotidien, des images et des embeddings, pas d'un cluster.

## Décisions d'architecture

Vingt-deux décisions structurent le projet ; chacune a une raison et une alternative écartée, à défendre en soutenance.

| Sujet | Choix | Raison | Alternative écartée |
| --- | --- | --- | --- |
| Source principale | TCGdex | Cartes et images en français, prix intégrés, pas de clé | pokemontcg.io seul (catalogue en anglais uniquement) |
| Source de recoupement (P2) | pokemontcg.io | Clé gratuite à 20 000 requêtes par jour, prix TCGplayer et Cardmarket | Scrydex (payant) |
| Planification | GitHub Actions | Tourne sans ton PC, utile en travaillant les weekends | Tâche planifiée locale |
| Stockage de référence | Snapshots Parquet datés dans des Releases mensuelles | Historique par ajout, jamais réécrit | Fichier DuckDB versionné dans Git, ou fichiers quotidiens commités dans Git |
| Base analytique | DuckDB | Lit le Parquet directement, sans serveur | PostgreSQL avec pgvector |
| Transformation | dbt (dbt-duckdb) | Tests, documentation, lignage, profil code-first | Scripts SQL manuels |
| Embeddings | open\_clip ou DINOv2 pré-entraîné, utilisé sans entraînement ; calcul sur CPU dans GitHub Actions | L'inférence sur quelques dizaines de milliers d'images basse résolution tient sur CPU, aucun GPU n'est nécessaire | Kaggle en GPU (gardé pour le fine-tuning P3) ; Colab (quota variable) |
| Recherche par similarité | Calcul direct avec NumPy | Quelques dizaines de milliers de vecteurs suffisent | FAISS ou pgvector, gardés pour comparer |
| Lecture du numéro de carte (OCR, P2) | EasyOCR et PaddleOCR comparés | Gratuits, tournent sur CPU | Tesseract seul |
| Machine learning | scikit-learn, LightGBM ou XGBoost, MLflow en local | Tournent sur CPU, traçables | Réseaux récurrents (LSTM) |
| Application | Streamlit en local | Rapide à construire seule | Interface web séparée avec API |
| Historique initial | Explorer le dépôt tcgdex/price-history | Licence MIT, mis à jour chaque jour, dossiers en français | Démarrer sans historique |
| Emplacement du workflow planifié | Dans le dépôt de données | Les commits quotidiens évitent la suspension du cron après 60 jours sans commit | Workflow dans le dépôt de code, qui resterait sans commit |
| Modèle et index d'embeddings | Hugging Face Hub, avec la révision exacte du modèle | Versionnés, téléchargeables par le projet et par Kaggle | Fichiers dans le dépôt GitHub |
| Nouvelles cartes à embedder | Étape de GitHub Actions après la collecte : téléchargement temporaire des images, calcul sur CPU, publication de l'index sur Hugging Face | Aucune intervention manuelle ; les images ne vivent que sur la machine éphémère et ne sont jamais publiées | Issue automatique puis notebook Kaggle lancé à la main le weekend |
| Conteneurisation | Docker et docker compose pour l'application, MLflow et la reconstruction de la base | Reproductibilité et démonstration en une commande | Conteneuriser la collecte, plus lente que setup-python avec cache |
| Scan continu (P3) | OpenCV sur la machine hôte, vote sur plusieurs images | La webcam est difficile à utiliser dans Docker sous Windows et WSL | Scan dans un conteneur, vrai temps réel |
| Rotation des fichiers | Aucune fusion : chaque Release mensuelle garde ses fichiers quotidiens ; un fichier mensuel fusionné ne s'ajoute, sans rien supprimer, que si T3 montre une reconstruction trop lente | Environ 31 fichiers par Release, loin de la limite de 1000 ; aucun risque de perte, historique jamais réécrit | Fusion mensuelle puis suppression des quotidiens ; DuckDB seul (fichier local jetable, pas une source durable) |
| Surveillance | E-mail d'échec de GitHub, test de fraîcheur dbt après chaque collecte, signal envoyé à healthchecks.io (offre gratuite) en fin de collecte | Trois contrôles sans maintenance ; healthchecks.io alerte même si GitHub ne lance pas le cron | Cron hebdomadaire, issue d'échec et contrôle externe lancé depuis ta machine |
| Commandes du projet | invoke (`tasks/`, fourni par le template) et `uv.lock` pour figer les versions | En Python, multiplateforme, compatible avec `cruft update` | Makefile |
| Collection personnelle | Fichier Parquet local hors dépôt, jeu d'exemple Parquet versionné ; dbt lit le chemin dans la variable `collection_path` | Colonnes typées, même format que les snapshots ; le même modèle tourne en CI sur l'exemple et en local sur la vraie collection | CSV ; collection dans un dépôt privé ou un secret GitHub |
| Couches dbt | staging (`stg_`), intermediate (`int_`), marts (`fct_`, `dim_`, `mart_`) ; les données brutes sont déclarées comme sources | Conventions de dbt ; bronze, silver et gold correspondent aux sources, au staging et aux marts | Préfixes bronze, silver et gold |

## Architecture globale

&#91;embedded content: architecture · 8 composants, 3 chaînes\]

Les flèches suivent les données : la collecte alimente des snapshots datés, que dbt transforme dans DuckDB ; les modèles et l'application lisent les tables gold, et la colonne de gauche prépare l'index d'embeddings utilisé par le scan.

## Exigences fonctionnelles

Vingt-deux exigences découpent le projet ; leurs identifiants serviront de référence dans les lots de plan.

| Id | Exigence | Priorité |
| --- | --- | --- |
| F1 | Collecter chaque jour les prix (une fois par produit Cardmarket : un prix commun aux langues européennes, un prix propre à chaque carte japonaise) et chaque semaine le catalogue (une fois par langue, japonais compris) depuis TCGdex, ou depuis tcgdex/price-history si T4 le permet ; conserver dès la phase 0 ou 1 la réponse brute de pokemontcg.io (exploitation en P2) | P1 |
| F2 | Exploiter les données de pokemontcg.io pour recouper les prix de TCGdex | P2 |
| F3 | Conserver quelques jours la réponse brute et un snapshot Parquet daté par exécution, archivés dans des Releases mensuelles | P1 |
| F4 | Alerter par e-mail (GitHub) quand la collecte échoue et par healthchecks.io quand elle ne tourne pas, tester la fraîcheur après chaque collecte, et permettre un relancement manuel | P1 |
| F5 | Rapprocher les identifiants de cartes entre les deux sources | P2 |
| F6 | Construire les couches staging, intermediate et marts avec dbt | P1 |
| F7 | Tester la qualité des données (unicité, valeurs nulles, relations, prix négatifs, complétude) | P1 |
| F8 | Télécharger les images des cartes françaises en basse résolution (au départ, puis pour les seules nouvelles cartes), hors du dépôt public | P1 |
| F9 | Calculer sur CPU dans GitHub Actions (lancement manuel) les embeddings de toutes les cartes, et publier la révision du modèle et l'index sur Hugging Face | P1 |
| F10 | Lire le numéro de carte par OCR pour départager les réimpressions | P2 |
| F11 | Identifier une carte à partir d'une photo par similarité d'embeddings (méthode principale) | P1 |
| F12 | Combiner OCR et embeddings (méthode hybride) | P3 |
| F13 | Évaluer les méthodes de scan sur toutes les cartes réelles disponibles (50 à 70 environ) (top-1, top-5, temps, intervalles de confiance) | P1 |
| F14 | Estimer le prix Cardmarket attendu de chaque produit (modèle A), en début de phase 3, contre la référence « moyenne par rareté et par set » (repli : moyenne par rareté) construite en dbt dès la phase 1 | P1 |
| F15 | Prédire la tendance du prix à 4 semaines (modèle B, exploratoire) | P3 |
| F16 | Gérer une collection personnelle et calculer sa valeur dans le temps | P1 |
| F17 | Présenter scan, collection et marché dans une application Streamlit | P1 |
| F18 | Signaler les cartes dont le prix s'écarte du prix attendu ou varie de façon anormale | P2 |
| F19 | Après chaque collecte, embedder automatiquement dans GitHub Actions les cartes absentes de l'index et publier l'index à jour ; lister dans le résumé de l'exécution les cartes dont l'image est indisponible, avec la raison, réessayées à la collecte suivante | P2 |
| F20 | Scanner en continu avec la webcam, avec vote sur plusieurs images | P3 |
| F21 | Reconstruire la base et lancer l'application et MLflow avec docker compose | P2 |
| F22 | Publier la documentation dbt et un rapport de qualité en ligne (GitHub Pages) | P3 |

## Exigences non fonctionnelles

Le projet doit rester gratuit, reproductible et fiable avec très peu de temps de maintenance.

| Id | Domaine | Exigence |
| --- | --- | --- |
| N1 | Coût | Aucun service payant ; les quotas gratuits sont vérifiés et documentés |
| N2 | Reproductibilité | Une commande reconstruit la base DuckDB à partir des snapshots ; les versions des dépendances sont figées |
| N3 | Fiabilité | La collecte est idempotente (relancer le même jour ne crée pas de doublon) et réessaie après une erreur d'API |
| N4 | Maintenabilité | Aucune intervention de routine : la collecte, la mise à jour de l'index d'embeddings et la CI tournent sans action manuelle |
| N5 | Qualité des données | Les tests dbt bloquent la CI en cas d'échec ; un indicateur de complétude des prix est publié ; l'historique couvre au moins 98 % des jours, les trous connus étant listés et acceptés dans un fichier versionné |
| N6 | Performance | Les temps de scan sont mesurés ; aucun seuil n'est fixé avant la première mesure |
| N7 | Documentation | README, schéma d'architecture, note de décision par choix important, dictionnaire de données |
| N8 | Portabilité | Fonctionne sous Ubuntu et sous WSL (environnement de référence), sans CI sous Windows ; Docker reproduit l'environnement |
| N9 | Traçabilité (P2) | Chaque expérience de ML est tracée (paramètres, métriques, version des données) |
| N10 | Sobriété | Les appels aux APIs restent raisonnables, avec cache et pauses |
| N11 | Conteneurisation (P2) | Un docker compose up lance l'application et MLflow ; l'image est construite en CI |
| N12 | Surveillance | Un échec de collecte déclenche l'e-mail de GitHub ; un test de fraîcheur dbt tourne après chaque collecte ; healthchecks.io envoie un e-mail si aucun signal de fin de collecte n'arrive en 26 heures |
| N13 | Continuité du cron | Le workflow de collecte vit dans le dépôt de données pour recevoir des commits quotidiens et éviter la suspension après 60 jours sans commit |
| N14 | Sécurité de l'automatisation | Actions épinglées par version, Dependabot, permissions minimales, secrets (pokemontcg.io, Hugging Face, healthchecks.io, Kaggle en P3) jamais dans le dépôt |
| N15 | Vitesse de la CI | Cache des dépendances, clone superficiel, workflows séparés avec filtres de chemins, annulation des exécutions obsolètes |
| N16 | Taille du dépôt | Aucune donnée quotidienne n'est commitée ; la taille réelle du dépôt est mesurée et suivie dans le manifeste, et le seuil visé est fixé après le test T3 de la porte 0 |

## Données et modèle de données

Les données viennent de deux APIs gratuites et s'organisent en trois couches, avec une langue sur chaque carte pour permettre d'élargir le périmètre plus tard.

**Sources :**

- TCGdex : cartes, sets, images et prix Cardmarket (EUR) et TCGplayer (USD) par carte, en français et dans d'autres langues, sans clé ni limite stricte publiée. Les prix sont identiques pour toutes les langues européennes (même `idProduct` Cardmarket) ; les cartes japonaises sont des produits distincts. Les prix sont séparés par finition (normale et holo chez Cardmarket ; normal, holofoil et reverse chez TCGplayer). L'endpoint de liste ne renvoie que l'identifiant et le nom : les prix demandent un appel par carte (22 155 cartes françaises, 23 770 anglaises et 13 006 japonaises dans 186 sets au 27 octobre 2026). Japonais : prix Cardmarket présents sur 28 cartes sur 30 tirées au hasard, aucun prix TCGplayer. La complétude sur les sets que tu possèdes reste à mesurer (T6).
- pokemontcg.io (collecté dès la phase 0 ou 1, exploité en P2 pour le recoupement) : catalogue en anglais et prix, avec une clé gratuite à 20 000 requêtes par jour. Le service serait passé sous Scrydex (payant) : la clé gratuite est à reconfirmer en phase 0, et la source est abandonnée si elle devient payante.
- tcgdex/price-history : dépôt public sous licence MIT, à explorer pour amorcer l'historique et, s'il est complet et mis à jour chaque jour, pour remplacer les appels carte par carte (profondeur et format inconnus).

**Tables principales :**

| Couche | Table | Contenu | Grain |
| --- | --- | --- | --- |
| Sources (bronze) | `raw_tcgdex_cards`, `raw_tcgdex_prices`, `raw_ptcg_cards` (conservé dès la phase 0 ou 1, exploité en P2) | Parquet quotidiens (prix) et hebdomadaires (catalogue), déclarés dans `sources.yml` | Une ligne par carte et par snapshot |
| Staging (silver) | `stg_tcgdex__cards`, `stg_tcgdex__sets` | Cartes et sets typés et dédoublonnés, avec langue, rareté, type, numéro, date de sortie | Une ligne par carte et par langue |
| Staging (silver) | `stg_tcgdex__prices` | Prix par marché et par finition, avec devise, moyennes sur 1, 7 et 30 jours quand elles existent | Une ligne par carte, marché, finition et date |
| Staging (silver) | `stg_collection` | Collection personnelle lue depuis le Parquet désigné par la variable `collection_path` | Une ligne par carte possédée |
| Intermediate | `int_rarity_mapping` | Correspondance entre les noms de rareté des sources (nom d'origine conservé) et un niveau ordonné, construite à partir des valeurs réellement collectées | Une ligne par nom de rareté |
| Intermediate | `int_card_id_mapping` | (P2) Correspondance entre identifiants TCGdex et pokemontcg.io, avec méthode et niveau de confiance | Une ligne par carte |
| Marts (gold) | `dim_card`, `dim_set` | Dimensions propres pour les analyses et l'application | Une ligne par carte, par set |
| Marts (gold) | `fct_price_snapshot` | Historique complet des prix, alimenté par ajout | Une ligne par carte, marché, finition et date |
| Marts (gold) | `fct_collection_value` | Valeur de la collection personnelle dans le temps | Une ligne par date |
| Marts (gold) | `mart_price_trends` | Tendances par set et par rareté, cartes aux prix anormaux | Une ligne par set, rareté et date |
| Marts (gold) | `mart_price_baseline` | Prix moyen par rareté et par set, avec repli sur la moyenne par rareté quand le set manque ; référence à battre du modèle A (phase 1) | Une ligne par set, rareté et date |
| IA | card\_embeddings | Vecteur de chaque carte, nom et révision exacte du modèle, langue | Une ligne par carte et par modèle |
| IA | scan\_evaluation | Photo, carte réelle, méthode, cinq meilleures cartes proposées, temps | Une ligne par photo et par méthode |
| IA | ml\_predictions | Prédictions des modèles A et B, avec version du modèle | Une ligne par carte, date et modèle |

La collection personnelle (quelles cartes tu possèdes) est un fichier Parquet local, hors du dépôt public ; le dépôt contient un jeu d'exemple au même format. dbt lit le chemin dans la variable `collection_path` : en CI, elle désigne le jeu d'exemple ; en local, la vraie collection. Le volume réel du catalogue français est à mesurer lors de la première collecte. Le modèle d'embeddings et l'index sont publiés sur Hugging Face Hub (compte gratuit), avec la révision exacte du modèle.

## Collecte et stockage

Une tâche GitHub Actions quotidienne télécharge les prix (et le catalogue une fois par semaine), puis dépose de nouveaux fichiers datés : l'historique se construit par ajout et ne dépend jamais de ton ordinateur.

1. **Déclenchement** : un cron quotidien et un déclenchement manuel (`workflow_dispatch`) pour relancer en cas d'échec ou rejouer une collecte avec des paramètres (langue, date). Le cron est décalé de l'heure pile (par exemple 03:17 UTC), car les déclenchements à l'heure pile peuvent être retardés.
2. **Langues et fréquence** : le catalogue est collecté chaque semaine pour chaque langue de la configuration (français, anglais et japonais) ; les prix sont collectés chaque jour, une fois par produit Cardmarket : une fois par carte pour les langues européennes, plus une fois par carte japonaise (environ 13 000 appels de plus par jour, sauf si T4 couvre le japonais). Si tcgdex/price-history est complet et à jour (T4), il remplace les appels carte par carte pour les prix.
3. **Appels** : TCGdex en source principale, pokemontcg.io collecté dès la phase 0 ou 1 pour ne perdre aucun jour de prix (exploitation en P2) ; pagination, pauses entre requêtes, nouvelle tentative après une erreur temporaire, clé lue dans les secrets GitHub.
4. **Données brutes** : le JSON de chaque source reste quelques jours en artefact du workflow, pour le débogage, et une archive compressée par mois va dans une Release. Il n'est jamais commité chaque jour : pour un catalogue de dizaines de milliers de cartes, il dépasserait sans doute le Parquet (à mesurer, test T3 de la porte 0).
5. **Snapshot** : les prix sont écrits dans `prices-AAAA-MM-JJ.parquet`, et le catalogue hebdomadaire dans `cards-AAAA-MM-JJ.parquet` (compression zstd, triés par identifiant de carte). Relancer le même jour remplace le fichier du jour, sans créer de doublon.
6. **Stockage durable hors de l'historique Git** : chaque fichier est ajouté à la Release du mois (`data-AAAA-MM`) et y reste : ni fusion ni suppression, environ 31 fichiers par mois. Si T3 montre une reconstruction trop lente, un fichier mensuel fusionné s'ajoute à côté des quotidiens, sans les supprimer. Une copie locale des fichiers sert de sauvegarde. Selon la documentation de GitHub, un fichier de Release doit rester sous 2 Gio et une Release accepte jusqu'à 1000 fichiers, sans limite de taille totale ni de bande passante.
7. **Dépôt de données** : séparé du dépôt de code, pour que l'historique Git du code reste léger. Il contient le workflow planifié, qui installe le collecteur depuis le dépôt de code (chaque évolution du code est donc reprise sans toucher au dépôt de données), et un manifeste (fichiers, tailles, nombre de lignes, empreintes) commité chaque jour, ce qui garde le dépôt actif. Personne ne travaille dans ce dépôt : les commits du robot n'entrent jamais en conflit avec les tiens. Aucune donnée volumineuse n'y est commitée.
8. **Images** : téléchargées en basse résolution, sur la machine GitHub Actions le temps du calcul des embeddings et en local pour l'évaluation et la démonstration ; jamais publiées.
9. **DuckDB** : le fichier `.duckdb` est reconstruit à la demande à partir des fichiers téléchargés depuis les Releases, et n'est jamais versionné.

**Fiabilité et surveillance :**

- GitHub notifie par e-mail les échecs d'une tâche planifiée. En fin de collecte, le workflow envoie un signal à healthchecks.io (offre gratuite) : sans signal pendant 26 heures, un e-mail part. Ce contrôle couvre le cas où GitHub ne lance pas le cron, invisible depuis GitHub lui-même.
- Un test dbt échoue si le dernier snapshot a plus de deux jours, ou si la couverture de l'historique passe sous 98 % des jours. Les trous connus sont listés dans un fichier versionné et acceptés, pour qu'une panne passée ne bloque pas la CI indéfiniment.
- Les workflows planifiés d'un dépôt public sont suspendus après 60 jours sans commit dans le dépôt (confirmé par la documentation officielle de GitHub, page « Disabling and enabling a workflow »). Le workflow vit donc dans le dépôt de données, qui reçoit un commit chaque jour. L'action tierce keepalive-workflow est déconseillée : un miroir indique que son dépôt d'origine a été désactivé par GitHub. En secours, une étape github-script peut réactiver le workflow.
- Un script local peut relancer la collecte du jour, mais les prix d'un jour manqué ne se récupèrent pas ensuite : chaque jour perdu l'est définitivement, sauf si le dépôt tcgdex/price-history le contient.

**Optimisations du workflow :**

- `concurrency` (une seule collecte à la fois), délai maximal d'exécution et permissions minimales ;
- nouvelles tentatives avec attente dans le script, et déclenchement manuel avec paramètres ;
- cache des dépendances (pip ou uv, paquets dbt) et clone superficiel ;
- Parquet compressé en zstd et trié par identifiant de carte ; stockage des seuls prix modifiés (delta) si la taille gonfle, à mesurer ;
- jamais de `.duckdb` dans Git ni dans le cache ; les artefacts (conservés 90 jours par défaut) ne servent qu'aux fichiers temporaires ;
- `dbt build` et test de fraîcheur après chaque collecte, avec un résumé dans la page de l'exécution (cartes collectées, prix manquants, nouvelles cartes) ;
- actions épinglées par version et mises à jour par Dependabot.

Un dépôt public donne des machines gratuites et illimitées de 4 processeurs et 16 Go de mémoire, avec 14 Go de disque ; un dépôt privé n'en donne que 2 et 8 Go, avec un quota mensuel. Une tâche s'arrête après 6 heures, et il n'y a pas de GPU gratuit : les embeddings se calculent donc sur CPU, ce qui suffit pour de l'inférence (test T9) ; Kaggle n'est gardé que pour le fine-tuning (P3).

## Scan d'une carte

Les embeddings sont la méthode principale ; l'OCR se limite à la lecture du numéro de carte, et l'hybride combine les deux ; les méthodes sont comparées sur le même jeu de photos, et le résultat chiffré est le point fort de la soutenance.

| Méthode | Principe | Force | Faiblesse |
| --- | --- | --- | --- |
| A. Lecture du numéro par OCR (P2) | Redresser la carte avec OpenCV, lire le numéro (par exemple 025/165) et le code de set | Départage les réimpressions que les embeddings confondent | Fragile avec reflets, cartes holo et anciennes mises en page ; ne suffit pas à identifier une carte seule |
| B. Embeddings (méthode principale, P1) | Comparer l'embedding de la photo à celui de chaque carte (plus proche voisin) | Robuste aux reflets et aux angles | Confond les réimpressions (même illustration, sets différents) |
| C. Hybride (P3) | Cinq meilleurs candidats par embeddings, puis OCR du numéro pour départager | Combine les deux forces | Plus complexe à construire et à expliquer |

**Index d'embeddings :**

- Calcul initial : un workflow GitHub Actions lancé à la main télécharge les images en basse résolution par lots, calcule les embeddings sur CPU et publie l'index sur Hugging Face Hub ; les images disparaissent avec la machine. Le calcul est reprenable par lots si la limite de 6 heures approche.
- Mises à jour : à la fin de chaque collecte, une étape compare les cartes du dernier snapshot à l'index, embedde les nouvelles cartes sur CPU et publie l'index à jour. Les cartes dont l'image est indisponible (absente, illisible ou trop petite) sont listées avec la raison dans le résumé de l'exécution et réessayées à la collecte suivante.
- Même modèle partout : le nom et la révision exacte du modèle (Hugging Face Hub) ainsi que le prétraitement des images sont stockés avec les vecteurs ; changer de modèle ou de prétraitement impose de tout recalculer.

**Prétraitement des images :**

- la carte entière redressée est embeddée : OpenCV redresse la photo pour qu'elle ressemble à l'image de référence (même cadrage, sans fond) ;
- pas de recadrage central, qui couperait le haut et le bas de la carte (nom, barre du numéro) ; l'image est redimensionnée en gardant ses proportions, avec des bandes neutres sur les côtés, à vérifier sur le modèle choisi ;
- ce choix et la résolution sont fixés avant l'indexation initiale ;
- l'illustration est le signal principal, le cadre et le texte pèsent peu : deux impressions de la même carte se ressemblent, et l'OCR du numéro (barre du bas : numéro, code de set) sert à les départager ;
- les variantes marquées par un détail de l'illustration (par exemple un tampon d'événement) sont presque identiques pour l'embedding : vérifier que TCGdex les liste séparément (test T2), sinon le scan les attribue à la version sans tampon. Même listées séparément, elles ont très probablement le même numéro que la version sans tampon (à vérifier) : ni l'embedding ni l'OCR du numéro ne les départagent, et le scan peut les confondre. Cette limite est annoncée dans l'évaluation, sans solution prévue, et ces confusions sont comptées à part ;
- repli si l'évaluation est mauvaise : embedding de l'illustration seule, hors périmètre tant que ce n'est pas nécessaire ;
- fine-tuning (P3) : la décision est prise par écrit fin mars 2027, à l'arrêt du scan, d'après les résultats sur le jeu de réglage. Il n'est planifié que si le modèle pré-entraîné ne suffit pas (seuil fixé après la première mesure) et si le cœur est dans les temps. Il tourne sur Kaggle (GPU), sans aucune photo du jeu de test, et il est évalué sur ce même jeu de test.

**Protocole d'évaluation :**

- jeu de toutes les cartes françaises réelles disponibles (50 à 70 environ), une photo principale par carte, prises dans des conditions variées (éclairage, angle, cartes holo, fond encombré) ;
- vérité terrain saisie à la main dans un fichier ; l'index de référence est construit à partir des images de l'API uniquement, aucune photo de test n'y est ajoutée ;
- mesures : top-1, top-5 et temps par scan, pour chaque méthode, détaillées par condition ;
- séparation en deux jeux, par carte et non par photo : réglage de 10 à 15 cartes, test final d'environ 40 à 55 cartes ; aucune carte du test n'est vue pendant le réglage, et les deux jeux sont figés avant les premiers essais ;
- test de robustesse en bonus : quelques cartes japonaises, pour voir comment chaque méthode se comporte hors du français (tu possèdes des cartes japonaises ; il faut un index japonais, à vérifier dans TCGdex, test T6).

**Rigueur statistique :**

- intervalle de confiance à 95 % sur chaque top-1 : avec 40 à 55 cartes de test, environ plus ou moins 8 à 9 points à 90 % de réussite, 11 à 12 points à 80 % et 13 à 15 points à 50 % (approximation normale) ; ces intervalles restent larges ;
- les méthodes sont comparées sur les mêmes cartes avec un test apparié (McNemar ou bootstrap des différences), mais avec 40 à 55 cartes il ne détecte que des écarts d'environ 15 points ou plus ; la comparaison entre l'OCR et les embeddings est donc descriptive, et un écart de quelques points n'est jamais présenté comme significatif ;
- plusieurs photos d'une même carte ne sont pas des échantillons indépendants : l'unité d'analyse est la carte ;
- les résultats par condition (holo, éclairage, angle) portent sur peu de cartes et sont présentés comme exploratoires.

Si le nombre de cartes réelles est insuffisant, le jeu est complété par des photos d'écran dégradées, signalées comme telles dans les résultats.

**Scan continu par webcam (P3) :**

- il s'agit d'un quasi temps réel, pas d'un vrai temps réel : une à trois images par seconde sur CPU est un ordre de grandeur à mesurer ;
- chaîne : capture, détection et redressement de la carte (OpenCV), embedding, recherche du plus proche voisin, vote sur les dernières images ;
- l'OCR ne tourne que sur une image stabilisée, car il est trop lent pour chaque image ;
- mesure : top-1 sur une image contre top-1 avec vote, pour chiffrer le gain ;
- le scan tourne sur la machine hôte (fenêtre OpenCV, puis Streamlit si possible), jamais dans Docker, où l'accès à la webcam est difficile sous Windows et WSL ;
- une webcam d'ordinateur rend le petit texte illisible, ce qui pénalise l'OCR plus que les embeddings.

## Machine learning

Deux modèles complémentaires : le modèle A fonctionne dès le catalogue disponible, le modèle B demande de l'historique de prix et reste exploratoire (P3) ; le modèle A, avec le scan par embeddings, couvre l'exigence de ML de l'école. La priorité du modèle B se décide à la fin de la phase 0 d'après le test T4 : au moins 6 mois d'historique dans tcgdex/price-history, il passe en P2 ; sinon il reste en P3.

|  | Modèle A : prix attendu | Modèle B : tendance à 4 semaines (P3, exploratoire) |
| --- | --- | --- |
| Question | Quel prix Cardmarket un produit (langues européennes confondues) devrait-il avoir d'après ses caractéristiques ? | Le prix va-t-il monter, rester stable ou baisser dans 4 semaines ? |
| Cible | Logarithme du prix Cardmarket actuel du produit, par finition | Variation relative du prix à 4 semaines, et sa version en 3 classes |
| Variables | Set, rareté (normalisée par une table de correspondance), type, points de vie, illustrateur, date de sortie, légalité en tournoi ; popularité du Pokémon (nombre de cartes imprimées pour ce Pokémon dans le catalogue ; génération et statut légendaire ou mythique depuis une source libre comme PokeAPI, à vérifier) ; embedding de l'image en option | Les mêmes, plus le prix courant, les moyennes sur 1, 7 et 30 jours et le nombre de jours depuis la sortie du set |
| Références à battre | Moyenne par rareté et par set, avec repli sur la moyenne par rareté ; régression linéaire | Prix inchangé ; moyenne mobile |
| Modèles | LightGBM ou XGBoost | LightGBM ou XGBoost |
| Disponibilité | Dès que le catalogue est collecté ; construit au début de la phase 3 (avril), avant le modèle B et avant Docker | Dès que l'historique est suffisant (phase 3, après le modèle A) |

**Règles de rigueur :**

- découpage dans le temps (entraînement sur le passé, test sur le futur), jamais aléatoire, pour éviter les fuites d'information ;
- une carte reste dans un seul des deux ensembles pour le modèle A, afin de ne pas mesurer une mémorisation ;
- la référence « moyenne par rareté et par set » est recalculée sur les seules cartes d'entraînement, sinon elle contient le prix des cartes de test ; un set absent de l'entraînement prend la moyenne par rareté ;
- métriques : erreur médiane (absolue et en pourcentage), robuste aux cartes rares et peu liquides, plus l'erreur moyenne ; détaillées par rareté et par tranche de prix ; pour les classes, exactitude et rappel de chaque classe ;
- chaque expérience est tracée avec MLflow en local (paramètres, métriques, version des données) ;
- le résultat est présenté comme une analyse, jamais comme un conseil d'achat.

**Utilisation du modèle A :** l'écart entre le prix réel et le prix attendu alimente la liste de cartes sur ou sous-évaluées dans le dashboard (F18).

**Référence à battre :** la moyenne par rareté et par set est construite dès la phase 1 comme un simple modèle dbt (par exemple `mart_price_baseline`) ; elle alimente le dashboard ; pour la comparaison avec le modèle A, elle est recalculée sur l'ensemble d'entraînement.

**Conclusion honnête :** si un modèle ne bat pas sa référence, le résultat est publié tel quel, avec une analyse des causes possibles (marché peu liquide, événements de sortie de set, données insuffisantes).

**Les prix selon la langue :** tranché le 27 octobre 2026 (test T1). Les prix relayés par TCGdex sont ceux du produit Cardmarket, communs à toutes les langues européennes. Le modèle A prédit donc le « prix de référence Cardmarket du produit », entraîné sur le catalogue des langues européennes sans distinction de langue ; les cartes japonaises, produits distincts sur un autre marché, sont exclues de l'entraînement, leur historique étant collecté pour un usage ultérieur ; le projet ne prétend pas prédire le prix des cartes françaises. Le pipeline, le scan et l'application, en français, ne changent pas. Aucune source gratuite et autorisée ne donne de prix par langue : l'API Cardmarket est réservée aux comptes validés, et extraire les annonces par langue enfreint ses conditions.

**Limites statistiques à annoncer :**

- le gain du modèle A sur la moyenne par rareté et par set sera sans doute faible, puisque ces variables sont déjà la référence ; il viendra surtout de l'illustrateur, de la popularité du Pokémon et de l'embedding ;
- les prix Cardmarket des cartes rares sont bruités et peu liquides : filtre sur un nombre minimal de ventes si la source le fournit (non confirmé), sinon métrique médiane et rapport par tranche de prix ;
- les intervalles de confiance du modèle A viennent d'un bootstrap par carte, ceux du modèle B d'un bootstrap par carte et par période ;
- modèle B : moins d'un an d'historique, forte saisonnalité liée aux sorties de sets, ensemble de test forcément petit et intervalles de confiance larges ; les résultats sont présentés comme exploratoires et évalués par cohortes de sets.

## Application et dashboard

L'application Streamlit tourne en local et couvre trois usages : scanner une carte, suivre sa collection, lire le marché.

| Page | Contenu | Exigences |
| --- | --- | --- |
| Scan | Envoi d'une photo, affichage des 5 meilleures cartes candidates avec leur score, validation de la bonne carte, ajout à la collection ; mode webcam continu en P3 | F10, F11, F16 |
| Ma collection | Valeur totale et son évolution dans le temps, répartition par set et par rareté, cartes les plus chères | F16 |
| Marché | Tendances de prix par set et par rareté, complétude des données, cartes aux prix anormaux, prix attendu et tendance prédite pour une carte | F14, F15, F18 |
| Qualité et suivi | Fraîcheur des données, résultats des tests, dernière collecte réussie | F4, F7 |

**Choix de conception :**

- l'application lit uniquement les tables gold et les index ; elle ne modifie jamais les données collectées ;
- la collection personnelle est stockée dans un fichier Parquet local, hors du dépôt public, avec un jeu d'exemple pour la démonstration ;
- chaque prédiction affichée indique le nom du modèle et sa marge d'erreur mesurée, pour éviter une fausse impression de certitude ;
- une démonstration enregistrée (vidéo ou captures) sert de plan B en cas de panne le jour de la soutenance.

Le déploiement en ligne est hors périmètre : la démonstration se fait en local, avec docker compose pour l'application et MLflow ; seul le scan par webcam tourne directement sur la machine hôte.

## Qualité, tests et intégration continue

La CI se déclenche à chaque modification du code et vérifie le code, les transformations et les données d'exemple ; la collecte quotidienne a son propre workflow.

| Niveau | Outil | Ce qui est vérifié |
| --- | --- | --- |
| Style du code | ruff | Formatage et erreurs courantes |
| Code Python | pytest | Fonctions de collecte, rapprochement d'identifiants, OCR sur quelques images, calcul de l'index |
| Données | Tests dbt standards | Unicité, valeurs nulles, relations entre tables, valeurs acceptées |
| Données | Tests dbt personnalisés | Prix négatif, couverture de l'historique (au moins 98 % des jours, hors trous acceptés), écart anormal entre les deux sources, complétude minimale |
| Transformations | `dbt build` sur un échantillon | Les modèles staging, intermediate et marts se construisent sans erreur |
| Modèles | Comparaison à la référence | Un modèle ne remplace le précédent que s'il fait au moins aussi bien |
| Documentation | `dbt docs` | Lignage des tables et dictionnaire de données à jour |
| Données | dbt build et test de fraîcheur après chaque collecte | Un résultat anormal fait échouer le workflow ; un résumé liste les cartes collectées, les prix manquants et les nouvelles cartes |
| SQL | sqlfluff | Style des modèles dbt |
| Conteneur | Image Docker construite en CI | L'image se construit et les tests passent dedans ; publication sur GitHub Container Registry (gratuit à ce jour d'après la documentation de GitHub, qui ne s'engage pas à le rester) |
| Sécurité | Dependabot, actions épinglées, contrôle des secrets, CodeQL | Dépendances à jour et aucun secret publié (gratuits sur un dépôt public, selon GitHub) |
| Branches | Protection de la branche principale | Aucune fusion si une vérification obligatoire échoue |

**Environnements :** `uv.lock` pour figer les versions, des tâches invoke (`tasks/`) pour les commandes principales (collecte, build dbt, tests, application), et un Dockerfile avec un docker compose (application Streamlit, interface MLflow, reconstruction de la base) pour reproduire l'environnement.

**Jeux d'essai :** un petit échantillon de snapshots et une collection d'exemple, en Parquet, sont versionnés dans le dépôt pour faire tourner la CI sans appeler les APIs.

**Optimisation de la CI :** cache des dépendances (pip ou uv, paquets dbt), clone superficiel, workflows séparés (collecte, CI du code, tests de données, publication) avec filtres de chemins, et annulation des exécutions devenues obsolètes.

**Vitrine (P3) :** documentation dbt et rapport de qualité publiés sur GitHub Pages, badges dans le README (état de la CI, fraîcheur des données) et versions étiquetées. GitHub Pages est disponible gratuitement sur les dépôts publics, avec un site limité à 1 Go et un déploiement limité à 10 minutes.

## Sécurité, légalité et éthique

Le dépôt étant public, rien de personnel, de secret ou de protégé par un droit d'auteur n'y est publié.

- **Secrets** : la clé pokemontcg.io vit dans les secrets GitHub et dans un fichier `.env` ignoré par Git ; un contrôle automatique des secrets est activé sur le dépôt.
- **Images des cartes** : elles appartiennent à The Pokémon Company ; elles restent hors du dépôt, dans un dossier local ignoré par Git ou, pour le calcul des embeddings, sur la machine éphémère de GitHub Actions, sans être publiées ni mises en cache. Le dépôt contient seulement les scripts pour les télécharger.
- **Données personnelles** : ni liste de tes cartes, ni photo qui permettrait de t'identifier ; le dépôt contient un jeu d'exemple. Les photos de test sont dans un dossier ignoré, ou publiées en version dégradée si tu le souhaites.
- **Conditions des APIs** : les limites et les conditions d'usage de chaque source sont notées dans la documentation, et les requêtes restent raisonnables.
- **Données publiées** : avant de republier l'historique de prix dans le dépôt public, les conditions d'utilisation de TCGdex, de pokemontcg.io et des données Cardmarket et TCGplayer qu'ils relaient sont vérifiées (le caractère public d'une donnée n'autorise pas sa republication) ; le projet n'est ni produit ni soutenu par Nintendo ni The Pokémon Company, et le dépôt l'indique dans le README.
- **Licence** : une licence est choisie pour le code (par exemple MIT) ; les données collectées gardent leur licence d'origine.
- **Éthique de la prédiction** : les prix prédits sont présentés comme une analyse, pas comme un conseil d'achat ou d'investissement.
- **Environnement professionnel** : aucun outil, donnée ou code de ton employeur n'entre dans le projet.

**Hugging Face et Kaggle :** seuls les vecteurs et le code sont publiés, jamais les images de cartes ; la licence du modèle d'embeddings (et du modèle de base en cas de fine-tuning publié) est vérifiée avant toute publication ; les jetons d'accès (écriture sur Hugging Face, API Kaggle) vivent dans les secrets de GitHub et de Kaggle, jamais dans le dépôt.

## Calendrier et jalons

&#91;embedded content: calendrier · 5 phases, 4 portes de contrôle\]

> Le contenu de ce bloc et celui du schéma d'architecture ont été perdus à l'export Markdown ; le découpage en phases est à reconstruire lors du premier plan.

Les portes sont des points de contrôle : si l'une n'est pas franchie, les bonus sont supprimés avant de toucher au cœur. Le calendrier suppose une journée de travail par weekend et une soutenance en septembre 2027 ; il se redimensionne dès que l'école précise ses critères et que tu confirmes ton temps disponible.

**Répartition des éléments P2 :** la lecture du numéro par OCR se fait en phase 2, juste après les embeddings (l'arrêt de fin mars s'applique aux deux méthodes) ; la collecte de pokemontcg.io démarre dès la phase 0 ou 1, car un jour de prix non collecté est perdu ; le recoupement et le rapprochement des identifiants dans dbt viennent en phase 3, seulement si le temps le permet, et sont les premiers candidats à la suppression ; le modèle A est construit au début de la phase 3 (avril), avant le modèle B et avant Docker, et sa référence « moyenne par rareté et par set » est un modèle dbt de la phase 1.

**Décision sur le fine-tuning :** fin mars 2027, à l'arrêt du scan (voir Scan d'une carte). C'est un jalon du calendrier, à reporter dans les lots dès le découpage en phases.

Les lots de plan se déduiront de ce document : chaque exigence (F1 à F22, N1 à N16) sera rattachée à une phase, puis découpée en lots d'un weekend.

## Porte 0 : critères de passage

La phase 0 se termine par une décision écrite sur neuf tests, dont six sont bloquants (T1, déjà tranché, T2, T3, T5, T7 et T8) ; chaque échec a un repli prévu, et les seuils proposés sont à ajuster.

| Test | Méthode | Critère de réussite | Si échec |
| --- | --- | --- | --- |
| T1. Prix par langue (bloquant, tranché le 27 octobre 2026) | Comparer le `idProduct` et les prix Cardmarket d'une même carte en français, anglais et allemand dans TCGdex | Les prix français diffèrent des prix anglais | Échec constaté sur 4 cartes (même `idProduct`, mêmes prix) : modèle A reformulé en prix de référence Cardmarket du produit ; pipeline et scan inchangés |
| T2. Couverture française et variantes (bloquant) | Calculer, pour les sets que tu possèdes, la part des cartes françaises qui ont une fiche et un prix ; vérifier aussi que les variantes que tu possèdes (par exemple l'Évoli à tampon « Tournée Pokémon 2025 ») existent comme cartes séparées | Au moins 90 % des cartes des sets que tu possèdes (seuil proposé), et chacune de tes variantes est une carte distincte dans TCGdex | Restreindre le périmètre aux sets bien couverts, ou compléter avec pokemontcg.io ; si une variante n'existe pas comme carte séparée, le scan l'attribue à la version de base et la limite est annoncée |
| T3. Taille et durée de la collecte (bloquant) | Collecter une fois tout le catalogue ; mesurer la durée de la collecte des prix, le JSON brut, le Parquet complet et le Parquet en delta ; extrapoler sur 365 jours | Extrapolation chiffrée ; Parquet annuel sous environ 1 Go et reconstruction de la base en moins de 10 minutes et collecte quotidienne des prix en moins de 2 heures (500 Mo restent un objectif de confort) ; les fichiers étant dans des Releases, les vraies contraintes sont le temps de reconstruction et les 14 Go de disque d'une machine GitHub | Passer au Parquet en delta, réduire les champs conservés, ou héberger les données sur Hugging Face ; si la collecte est trop longue, passer par tcgdex/price-history |
| T4. Historique de tcgdex/price-history (informatif) | Cloner le dépôt ; relever les dossiers, la profondeur, le format, la date du dernier commit et la licence ; vérifier s'il est assez complet et à jour pour servir de source quotidienne des prix | Au moins 6 mois d'historique exploitable : le modèle B démarre alors en avril, juste après le modèle A, et passe de P3 à P2 | Le modèle B attend l'historique de la propre collecte (environ 6 mois en avril 2027) et reste en P3, exploratoire |
| T5. Collecte automatique (bloquant) | Sept jours consécutifs de collecte sans échec ; un échec volontaire déclenche l'e-mail ; le test de fraîcheur échoue quand il le doit ; une collecte désactivée volontairement déclenche l'alerte de healthchecks.io | Sept jours sans trou et les deux alertes reçues ; ce test ne couvre pas le seuil de 60 jours, à refaire après le jour 60 | Corriger avant de passer à la phase 1 |
| T6. Japonais (informatif) | Tester le code ja de TCGdex sur les sets de tes cartes japonaises physiques (comptées en T7) | Couverture suffisante pour un test de robustesse du scan | Abandonner le test de scan japonais ; la collecte japonaise (catalogue et prix) continue, sans conséquence sur le reste |
| T7. Cartes physiques (bloquant) | Compter séparément tes cartes physiques françaises et japonaises, les photographier ; vérifier que les françaises existent en français dans TCGdex | Au moins 60 cartes françaises retrouvables dans TCGdex (visée avec marge ; 50 au strict minimum) | Emprunter des cartes dès maintenant pour viser 60 ; sinon réduire le périmètre du scan |
| T8. Conditions de redistribution des prix (bloquant) | Lire les conditions d'utilisation de TCGdex, de pokemontcg.io et des données Cardmarket et TCGplayer qu'ils relaient | Republication de l'historique autorisée ou tolérée | Publier des agrégats seulement, ou passer le dépôt de données en privé, ce qui fait perdre les machines gratuites et illimitées (dépôt privé : 2 processeurs, 8 Go et un quota mensuel) |
| T9. Embeddings sur CPU (informatif) | Calculer les embeddings de 500 images basse résolution sur un runner GitHub Actions et sur ton PC, avec le modèle retenu | Index complet (environ 22 000 cartes) extrapolé sous 3 heures sur un runner | Indexation initiale sur Kaggle (GPU), mises à jour toujours sur CPU dans GitHub Actions ; ou modèle plus petit |

La porte est franchie quand T1, T2, T3, T5, T7 et T8 sont passés, ou tranchés par écrit dans ce document avec la décision prise en cas d'échec ; T4, T6 et T9 informent sans bloquer. Date limite : fin novembre 2026.

## Risques et plans B

Le risque principal est de passer l'année sur le scan au détriment du pipeline de données, d'où un cœur qui ne dépend pas de lui.

| Risque | Conséquence | Plan B |
| --- | --- | --- |
| Le scan reste imprécis | Démonstration peu convaincante | Présenter les résultats chiffrés et les limites ; restreindre aux sets récents ou aux cartes non holo ; limiter le temps passé à mars 2027 |
| Une API change, tombe en panne ou disparaît | Collecte interrompue | JSON brut conservé, seconde source en place, alerte en cas d'échec |
| Le workflow GitHub est désactivé ou échoue | Trous dans l'historique | Alerte e-mail de GitHub, alerte healthchecks.io, déclenchement manuel |
| Le calcul des embeddings est trop lent sur CPU | Indexation initiale retardée | Calcul par lots reprenable, modèle plus petit, ou indexation initiale sur Kaggle (GPU) |
| Historique trop court pour le modèle B | Pas de résultat probant | Garder le modèle A en cœur ; présenter le B comme une expérience avec ses limites |
| Temps limité aux weekends | Retard sur le calendrier | Lots courts et démontrables, bonus supprimés en premier, gel fin juin |
| Livrables de l'école différents de l'hypothèse | Périmètre à revoir | Garder le cœur data, adapter la restitution et le rapport |
| Prix manquants pour certaines cartes | Dashboard biaisé | Indicateur de complétude, cartes signalées |
| Fin d'alternance et recherche d'emploi en septembre 2027 | Manque de temps avant la soutenance | Version finale prête dès fin juillet, août pour la répétition |
| Hugging Face ou Kaggle change ses conditions ou ses quotas | Index ou calcul indisponible | Copie locale du fichier d'embeddings ; le calcul tourne déjà sur CPU |
| Le workflow planifié est suspendu pour inactivité | Trous dans l'historique de prix | Workflow dans le dépôt de données avec commits quotidiens ; étape de réactivation en secours |
| Le scan par webcam est trop lent ou trop imprécis | Bonus sans valeur | Le scan par photo reste la démonstration principale ; le mode webcam est supprimé en premier |
| Docker complique l'environnement sous Windows | Temps perdu | Docker limité à l'application et à MLflow ; le reste fonctionne sans conteneur, sous Ubuntu ou WSL |
| Les Releases sont limitées ou indisponibles | Perte d'accès aux snapshots | Copie locale des fichiers ; dépôt de jeu de données sur Hugging Face en option |
| pokemontcg.io devient payant | Pas de recoupement des prix | Abandonner F2 et F5, sans conséquence sur le cœur |
| La décision sur le fine-tuning est oubliée | Scan imprécis sans recours prévu | Décision écrite fin mars 2027, inscrite comme jalon du calendrier |

## Hypothèses à confirmer et points ouverts

Vingt-deux points sont suivis, dont quatre levés le 27 octobre 2026 ; les premiers se règlent dès la phase 0 (fin octobre et novembre 2026).

- [ ] **Contenu de `tcgdex/price-history`** : profondeur de l'historique, format des fichiers, mise à jour réelle, et possibilité de l'utiliser comme source quotidienne des prix (le dépôt a été vu mais pas exploré).
- [x] **Prix par langue** : tranché le 27 octobre 2026 : les prix TCGdex sont ceux du produit Cardmarket, identiques pour les langues européennes (test T1) ; modèle A reformulé.
- [ ] **Complétude du français et du japonais** dans TCGdex pour les sets que tu possèdes (catalogue global mesuré le 27 octobre 2026 : 13 006 cartes japonaises, prix Cardmarket sur 28 sur 30).
- [ ] **Quotas et conditions** : revérifier sur les pages officielles les limites de pokemontcg.io, de TCGdex et de Kaggle avant de les citer en soutenance ; celles de GitHub (Pages, Releases, GHCR, CodeQL, machines Actions) ont été relues dans sa documentation et ses annonces le 26 octobre 2026.
- [x] **Workflows planifiés d'un dépôt public** : suspension après 60 jours sans activité confirmée par la documentation officielle de GitHub ; à surveiller après le lancement.
- [ ] **Critères de l'école** : date exacte de la soutenance, livrables (rapport, code, démonstration), règle de validation des modules par le projet, technologies imposées.
- [ ] **Temps réel disponible** par weekend, pour ajuster la taille des lots.
- [ ] **Cartes réelles** : nombre de cartes françaises (environ 50 à 70 cartes physiques, toutes réservées au réglage et au test ; voir T7) et japonaises.
- [x] **Collecte japonaise** : tranché le 27 octobre 2026 : catalogue et prix japonais collectés dès le départ pour l'historique ; exclus du modèle A.
- [ ] **Japonais** : décider si le test de robustesse du scan (et un modèle japonais) est conservé selon la couverture de TCGdex et le temps disponible (P3).
- [ ] **Licence du dépôt** : choisir la licence du code.
- [ ] **MLflow** : confirmer qu'il est gardé en P2 : suivi des modèles A et B et, si tu l'acceptes, de l'évaluation du scan.
- [ ] **Dagster** : veux-tu l'utiliser, oui ou non ? Tant que la réponse est « non » ou absente, il n'est pas planifié dans les lots. Si oui, il reste en P3 et ne se planifie que si le cœur est stable (à partir de juin) ; si non, il est retiré du périmètre (tableau de périmètre, ligne P3).
- [x] **Effectif du catalogue français** : 22 155 cartes au 27 octobre 2026 (endpoint de liste de TCGdex).

**Ajoutés lors de la dernière mise à jour :**

- [ ] **Compte Hugging Face** : créer le compte, choisir la visibilité du dépôt d'index (public ou privé) et lire les conditions d'usage.
- [ ] **Licences** : vérifier celle du modèle d'embeddings choisi et ce que tu as le droit de publier.
- [ ] **Docker** : choisir entre Docker Desktop sous Windows et Docker Engine sous WSL ou Ubuntu.
- [ ] **Webcam** : tester la qualité de ta webcam sur quelques cartes avant de décider du scan continu.

**Ajoutés le 27 octobre 2026 :**

- [ ] **pokemontcg.io** : vérifier que la clé gratuite existe toujours depuis le passage sous Scrydex ; sinon, abandonner F2 et F5.
- [ ] **healthchecks.io** : créer le compte gratuit et le contrôle de la collecte.
- [ ] **Fine-tuning** : décision écrite fin mars 2027, à l'arrêt du scan, d'après les résultats sur le jeu de réglage.
- [ ] **Calendrier** : reconstruire le découpage en phases, perdu à l'export Markdown, en y inscrivant ce jalon.

## Sources consultées

Les chiffres de quotas et de couverture viennent d'extraits de résultats de recherche, sauf la page du dépôt `tcgdex/price-history`, ouverte directement ; ils sont à revérifier sur les pages officielles.

- [Limites de pokemontcg.io (API Evangelist)](https://raw.githubusercontent.com/api-evangelist/pokemon-tcg/refs/heads/main/rate-limits/pokemon-tcg-rate-limits.yml)
- [FAQ de TCGdex](https://tcgdex.dev/faq)
- [État des langues de TCGdex](https://tcgdex.dev/status)
- [Erreur de langue invalide de TCGdex](https://tcgdex.dev/errors/language-invalid)
- [Dépôt tcgdex/price-history](https://github.com/tcgdex/price-history)
- [Best Pokemon Card APIs in 2026 (ScrapingBee)](https://www.scrapingbee.com/blog/pokemon-card-api/)
- [Catalogue de pokemontcg.io en anglais seulement (DEV Community)](https://dev.to/riccskywalker/a-pokemon-tcg-api-that-covers-the-japanese-and-chinese-print-runs-with-prices-that-say-where-they-ba2)
- [Prix selon la langue (Eyevo)](https://eyevotcg.com/features/languages/)
- [Options de GPU gratuits : quota Kaggle (GMI Cloud)](https://www.gmicloud.ai/en/blog/best-free-gpu-cloud-options-for-ai-startups-and-researchers)

**Ajouts pour GitHub Actions :**

- [Runners hébergés par GitHub (documentation)](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
- [Keepalive Workflow : suspension après 60 jours](https://github.com/gautamkrishnar/keepalive-workflow)
- [Miroir indiquant la désactivation du dépôt d'origine](https://gitea.com/sekedus/keepalive-workflow)
- [Cache Actions au-delà de 10 Go (GitHub Changelog)](https://github.blog/changelog/2025-11-20-github-actions-cache-size-can-now-exceed-10-gb-per-repository/)
- [Limites de stockage GitHub](https://fast.io/resources/github-storage-limit.md)

**Vérifications GitHub du 26 octobre 2026 :**

- [Limites de GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)
- [À propos des Releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)
- [Fonctions de sécurité de GitHub en 2020 : code scanning et secret scanning gratuits sur les dépôts publics](https://github.blog/security/application-security/github-security-features-highlights-from-2020)
- [Question de la communauté sur le statut « currently free » de GHCR](https://github.com/orgs/community/discussions/183054)

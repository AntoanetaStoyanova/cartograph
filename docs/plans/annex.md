COL-T8 : ce qu'on a le droit de republier

Source: TCGdex, catalogue (noms, sets, raretés, numéros)
Ce que j'ai pu lire: Base de données sous licence MIT (« Copyright (c) 2021
TCGdex »)
Republication publique: Autorisée, à condition de citer la source et de
joindre la licence
────────────────────────────────────────
Source: TCGdex, images
Ce que j'ai pu lire: Aucune licence publiée ; ce sont des visuels de The
Pokémon Company
Republication publique: Non, c'est déjà prévu dans la spec
────────────────────────────────────────
Source: Prix Cardmarket (relayés par TCGdex)
Ce que j'ai pu lire: TCGdex dit seulement que les prix viennent des places
de marché, sans aucune condition. La licence MIT de TCGdex ne peut pas
donner sur ces prix des droits que TCGdex n'a pas. Les conditions de
Cardmarket me sont bloquées (403).
Republication publique: Risquée ; voir le point juridique sous le tableau
────────────────────────────────────────
Source: Prix TCGplayer (USD)
Ce que j'ai pu lire: Pages bloquées (403). D'après des sources secondaires,
TCGplayer considère ses prix comme sa propriété et interdit leur
redistribution sans accord écrit.
Republication publique: Non
────────────────────────────────────────
Source: pokemontcg.io
Ce que j'ai pu lire: Aucune condition de redistribution publiée. Le service
 est en fin de vie : inscriptions fermées, clés valables jusqu'au 1er
mars 2027, migration annoncée vers Scrydex.
Republication publique: Non pour les données brutes

Le point juridique. Cardmarket est une entreprise allemande, donc le droit européen des bases de données (directive 96/9/CE) s'applique. Il interdit d'extraire ou de réutiliser une partie substantielle d'une base sans accord. Republier chaque jour l'historique complet des prix de tous les produits ressemble à une réutilisation substantielle. Le relais par TCGdex n'y change rien. Je ne suis pas juriste, mais le risque est réel.

Le choix de visibilité

- A, tout public (dépôt et Releases avec les prix bruts) : le plus simple, mais tu publies des données de prix dont tu n'as pas les droits.
- B, dépôt de données privé : sans risque, mais les machines GitHub ne sont gratuites en illimité que sur un dépôt public. Un dépôt privé n'a que 2 000 minutes par mois. Avec ~35 000 appels par jour, la collecte prendrait probablement 1 à 2 h par jour, soit 1 800 à 3 600 minutes par mois : ça dépasse. T3 le mesurera.
- C, mixte (recommandé) :
  - cartograph-data reste public, pour les machines gratuites et le cron.
  - Les prix bruts vont dans un stockage privé gratuit, au choix :
    - les Releases d'un 3ᵉ dépôt GitHub privé : le workflow y publie avec un jeton, et seul le stockage est privé, pas le calcul ;
    - ou un dataset privé sur Hugging Face.
  - Est publié : le catalogue TCGdex (MIT, avec attribution, sans images), le code, et seulement des résultats dérivés : statistiques agrégées, sorties des modèles, valeur de ta collection. L'application et la démo de soutenance tournent en local avec les vraies données.

Ce qu'il te reste à faire

1. Ouvre dans ton navigateur les conditions générales de Cardmarket (https://www.cardmarket.com/en/Policies/GeneralTermsAndConditions/D) et les conditions de TCGplayer (https://help.tcgplayer.com/hc/en-us/articles/205004918-Terms-of-ServiceTCGplayer). Cherche les mots « scraping », « automated », « database », « reproduce » et « redistribute », et dis-moi ce qu'ils disent.
2. Choisis A, B ou C.

À part, l'impact de pokemontcg.io. Sa réponse brute devait être conservée dès la phase 0 ou 1 pour une exploitation en P2. Après le 1er mars 2027, il n'y aura plus de collecte possible. As-tu déjà une clé ? Sinon, cette source tombe et il faut décider : Scrydex ou rien.

Une fois ta décision prise, je la consigne dans la spec maîtresse (T8, « Données publiées », F1 pour pokemontcg.io) et je coche COL-T8. Le journal est à jour.

Sources :
- tcgdex/cards-database (MIT) (https://github.com/tcgdex/cards-database)
- Licence TCGdex (https://raw.githubusercontent.com/tcgdex/cards-database/master/LICENSE)
- TCGdex, prix (https://tcgdex.dev/markets-prices)
- TCGdex, FAQ (https://tcgdex.dev/faq)
- tcgdex/price-history (https://github.com/tcgdex/price-history)
- Documentation pokemontcg.io (https://docs.pokemontcg.io/)
- Conditions générales Cardmarket (https://www.cardmarket.com/en/Policies/GeneralTermsAndConditions/D)
- TCGplayer Terms of Service (https://help.tcgplayer.com/hc/en-us/articles/205004918-Terms-of-ServiceTCGplayer)
- TCGplayer, accès aux prix (https://help.tcgplayer.com/hc/en-us/articles/201577976-How-can-I-get-access-to-your-card-pricing-data)
- Alternatives à l'API TCGplayer (2026) (https://cardgrader.ai/blog/tcgplayer-api-alternatives)
- ScrapingBee, scraping de TCGplayer (https://www.scrapingbee.com/blog/how-to-scrape-tcgplayer/)
- Cardboard Connection, procès Beckett (https://www.cardboardconnection.com/law-of-cards-beckett-sues-two-more-for-scraping-data)
- Conditions Card-Codex (https://cardcodex.com/?p=54226)
- Apify, Cardmarket Price Guide (https://apify.com/kamerozkan/cardmarket-price-guide)
- Apify, Cardmarket Pokémon Trend Scraper (https://apify.com/scrap_them_all/cardmarket-pokemon-trend-scraper)
- API Evangelist, Pokémon TCG (https://providers.apievangelist.com/providers/pokemon-tcg/)
- pokemon-tcg-data (Apache 2.0) (https://github.com/pkgreen90/pokemon-tcg-data)
- Conditions PokePriceTracker (https://www.pokemonpricetracker.com/terms)
- parse.gl, pokemontcg io (https://parse.gl/brands/pokemontcg-io)
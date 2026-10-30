## v0.2.0 (2026-10-30)

### Nouveautés

- tâche inv release. Commitizen et hook commit-msg

### Réécritures

- version lue dans pyproject.toml par importlib.metadata

### Documentation

- cycle de release et préfixes de commit dans CONTRIBUTING
- contrôles avant pull request, specs et plans locaux
- contrôles locaux et branches feature dans CONTRIBUTING

### Maintenance

- okflint pour les specs et plans (inv okflint)
- markdownlint et prettier au commit

## v0.1.0 (2026-10-30)

### Nouveautés

- manifeste quotidien sans prix (fichiers, Release, SHA-256, taille du dépôt)
- résumé Markdown de la collecte
- snapshots Parquet et commande inv collect (COL-02)
- client TCGdex COL-01 et cadrage des flux
- socle Python FND-01 (logs, beartype, langues)

### Corrections

- retire les vrais prix des fixtures TCGdex

### Réécritures

- résumé de collecte typé, doublons retirés et docstrings relues

### Documentation

- surveillance de la collecte dans le README
- note COL-T4, tcgdex/price-history écarté
- retour aux prix quotidiens
- retour aux prix quotidiens
- ORC-01 vérifié et collecte hebdomadaire

### Maintenance

- hooks pre-push retirés, blocage reporté à la CI GitHub
- hooks pre-commit et pre-push
- fins de ligne LF
- specs et plans gardés en local
- initial project structure from cruft template

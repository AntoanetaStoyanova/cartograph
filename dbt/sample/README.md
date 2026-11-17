# Échantillon de snapshots

Extrait des snapshots publics du catalogue (Release `catalogue` de `cartograph-data`), lu par `inv dbt --sample` et donc par `inv ci`, sans `data/snapshots/` ni appel aux APIs. Aucun prix : ils sont privés et ce dépôt est public.

| Contenu | Cas couvert |
| ------- | ----------- |
| `en` `tk-xy-su` (30 cartes le 9, 29 le 16) | `tk-xy-su-26` disparue le 16 ; trois catégories |
| `fr` `hgss3` (91 cartes) | `local_id` non numérique (`THREE`) ; catégories en français |
| `ja` `SV2P` (99 cartes) | 28 raretés vides |
| `ja` `M6-077`, `M6-078` | fiche corrigée par TCGdex le 12 (rareté provisoire `Mega Hyper Rare` → `Illustration rare`) : le modèle doit garder la version du 16 |

## Recette

À rejouer depuis la racine du dépôt, après `uv run inv rebuild`, si le schéma des snapshots change :

```sql
copy (
    select * from 'data/snapshots/cards-2026-11-09.parquet'
    where (language, set_id) in (('en', 'tk-xy-su'), ('fr', 'hgss3'), ('ja', 'SV2P'))
       or card_id in ('M6-077', 'M6-078') and language = 'ja'
) to 'dbt/sample/snapshots/cards-2026-11-09.parquet' (format parquet, compression zstd);
copy (
    select * from 'data/snapshots/cards-2026-11-16.parquet'
    where (language, set_id) in (('en', 'tk-xy-su'), ('fr', 'hgss3'), ('ja', 'SV2P'))
       or card_id in ('M6-077', 'M6-078') and language = 'ja'
) to 'dbt/sample/snapshots/cards-2026-11-16.parquet' (format parquet, compression zstd);
```

Par exemple, la requête enregistrée dans `extract.sql` : `uv run python -c "import duckdb, sys; duckdb.sql(open(sys.argv[1]).read())" extract.sql`.

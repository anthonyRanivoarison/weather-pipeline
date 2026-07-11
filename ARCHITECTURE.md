# Architecture du pipeline qualité de l'air

## Stack technique

| Couche | Technologie choisie | Justification |
|--------|-------------------|---------------|
| **API temps réel** | [OpenWeatherMap Air Pollution](https://openweathermap.org/api/air-pollution) | API gratuite (60 appels/min, 1M/mois), fournit AQI + 8 polluants, déjà intégrée au projet |
| **API historique** | [Open-Meteo Air Quality](https://open-meteo.com/en/docs/air-quality-api) | Gratuite sans clé, historique disponible depuis 2020, permet le backfill 12 mois sans coût |
| **Orchestrateur** | GitHub Actions (cron `0 * * * *`) | Gratuit, exécution horaire automatique, historique des runs visible, pas de serveur à maintenir |
| **Stockage raw** | Système de fichiers (`data/raw/`) versionné dans Git | Un fichier JSON par ville et par appel, jamais modifié = backup immuable |
| **Stockage clean** | Fichier CSV unique (`data/clean/air_quality.csv`) versionné dans Git | Format universel, une ligne par ville et par heure, trié chronologiquement |
| **Warehouse** | Neon.tech PostgreSQL (serverless, free tier) | PostgreSQL gratuit (0.5 Go), persistant, accessible depuis GitHub Actions via Internet |
| **Langage** | Python 3.11+ | Écosystème data riche (pandas, SQLAlchemy, requests) |

## Flux de données

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         BACKFILL (exécution unique)                      │
│                                                                         │
│  src/extract.py --backfill                                              │
│  Source: Open-Meteo Air Quality API                                     │
│  Période: 12 mois (2024-07 → 2025-07)                                  │
│  Sortie: data/raw/{ville}/YYYY-MM-DD_HH.json  (format Open-Meteo)     │
│                                                                         │
│  ↓                                                                      │
│                                                                         │
│  src/transform.py  →  data/clean/air_quality.csv                       │
│  src/validate.py    →  validation du contrat clean/                     │
│  src/load_warehouse.py →  upsert dans Neon.tech PostgreSQL             │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                    PIPELINE HORAIRE (GitHub Actions cron)                │
│                                                                         │
│  Toutes les heures (cron: 0 * * * *)                                   │
│  Déclencheur: GitHub Actions schedule + workflow_dispatch               │
│                                                                         │
│  ┌──────────┐    ┌──────────────┐    ┌──────────┐    ┌──────────────┐  │
│  │ extract  │ →  │  transform   │ →  │ validate │ →  │ load         │  │
│  │ .py      │    │  .py         │    │ .py      │    │ _warehouse.py│  │
│  └──────────┘    └──────────────┘    └──────────┘    └──────────────┘  │
│       │                 │                  │                 │          │
│       ▼                 ▼                  ▼                 ▼          │
│  data/raw/       data/clean/         stdout:         Neon.tech         │
│  {ville}/        air_quality.csv     OK/FAIL         PostgreSQL         │
│  timestamp.json  (reconstruit)                                         │
│                                                                         │
│  ↓ git add data/ && git commit && git push                              │
│  → raw/ et clean/ persistés dans le repo                                │
└─────────────────────────────────────────────────────────────────────────┘
```

## Modélisation dimensionnelle (schéma en étoile)

### Justification du choix étoile vs flocon

Schéma **en étoile** choisi car :
- Plus simple : une table de faits + deux dimensions plates
- Pas de hiérarchie complexe dans les dimensions (ville n'a pas de sous-dimension qui justifie une normalisation)
- Requêtes plus rapides (pas de jointures multiples)
- Conforme au cours

### Schéma

```
┌──────────────────────────────────┐
│           dim_time               │
├──────────────────────────────────┤
│ id          (PK, SERIAL)         │
│ datetime    (TIMESTAMP, UNIQUE)  │
│ date        (DATE)               │
│ hour        (SMALLINT 0-23)      │
│ day_of_week (VARCHAR 10)         │
│ is_weekend  (BOOLEAN)            │
│ month       (SMALLINT 1-12)      │
│ year        (SMALLINT)           │
└──────────────┬───────────────────┘
               │
┌──────────────┴───────────────────┐    ┌──────────────────────────────────┐
│       fact_air_quality           │    │           dim_city               │
├──────────────────────────────────┤    ├──────────────────────────────────┤
│ id          (PK, SERIAL)         │    │ id          (PK, SERIAL)         │
│ time_id     (FK → dim_time)      │◄──►│ city_name   (VARCHAR 100,        │
│ city_id     (FK → dim_city)      │    │              UNIQUE)             │
│ aqi         (SMALLINT 1-5)      │    │ country     (VARCHAR 2)          │
│ co          (DOUBLE PRECISION)   │    │ latitude    (DOUBLE PRECISION)   │
│ no          (DOUBLE PRECISION)   │    │ longitude   (DOUBLE PRECISION)   │
│ no2         (DOUBLE PRECISION)   │    └──────────────────────────────────┘
│ o3          (DOUBLE PRECISION)   │
│ so2         (DOUBLE PRECISION)   │
│ pm2_5       (DOUBLE PRECISION)   │
│ pm10        (DOUBLE PRECISION)   │
│ nh3         (DOUBLE PRECISION)   │
│ UNIQUE(time_id, city_id)         │
└──────────────────────────────────┘
```

### Règles de modélisation respectées

- ✅ **Pas de mesures dans les dimensions** : AQI et polluants sont uniquement dans `fact_air_quality`
- ✅ **Pas de colonnes descriptives dans la table de faits** : les clés étrangères pointent vers les dimensions
- ✅ **Granularité** : une ligne par ville et par heure dans la table de faits

## Contrat de données (clean/air_quality.csv)

Une ligne par ville et par heure, tri chronologique, sans doublons.

| Colonne | Type Python | Unité | Description |
|---------|------------|-------|-------------|
| `city` | string | — | Nom de la ville |
| `country` | string | — | Code pays ISO 3166-1 alpha-2 |
| `latitude` | float | degrés décimaux | Latitude WGS84 |
| `longitude` | float | degrés décimaux | Longitude WGS84 |
| `datetime` | string (ISO 8601) | UTC | Horodatage de la mesure (YYYY-MM-DDTHH:00:00Z) |
| `aqi` | int | — | Air Quality Index OWM (1=Bon, 2=Fair, 3=Modéré, 4=Mauvais, 5=Très mauvais) |
| `co` | float | μg/m³ | Monoxyde de carbone |
| `no` | float | μg/m³ | Monoxyde d'azote |
| `no2` | float | μg/m³ | Dioxyde d'azote |
| `o3` | float | μg/m³ | Ozone |
| `so2` | float | μg/m³ | Dioxyde de soufre |
| `pm2_5` | float | μg/m³ | Particules fines ≤ 2.5 μm |
| `pm10` | float | μg/m³ | Particules fines ≤ 10 μm |
| `nh3` | float | μg/m³ | Ammoniac |

## Villes surveillées

| Ville | Pays | Latitude | Longitude |
|-------|------|----------|-----------|
| Paris | FR | 48.8566 | 2.3522 |
| London | GB | 51.5074 | -0.1278 |
| Berlin | DE | 52.5200 | 13.4050 |
| Madrid | ES | 40.4168 | -3.7038 |
| Rome | IT | 41.9028 | 12.4964 |

## Période couverte

- **Backfill initial** : 12 mois (juillet 2024 – juillet 2025) via Open-Meteo
- **Pipeline temps réel** : à partir du déploiement, toutes les heures via OpenWeatherMap

## Trous connus et écarts

- L'API OpenWeatherMap temps réel peut occasionnellement retourner une erreur (rate limiting, panne passagère) → la ligne est sautée pour cette heure
- L'API Open-Meteo historique ne fournit pas exactement les mêmes horaires que OWM → certaines heures peuvent manquer
- Nombre de lignes attendu : 5 villes × 24h × 365j = 43 800 lignes/an (backfill)
- Écart possible : ± quelques % selon les indisponibilités API

## Connexion à la base

- **Hôte** : ep-xxx.region.aws.neon.tech
- **Base** : neondb
- **SSL** : requis (sslmode=require)
- **Chaîne de connexion** : stockée dans le secret GitHub `NEON_DB_URL` et dans `.env`

## Déploiement

Le pipeline est déployé via GitHub Actions :
1. Les secrets (`OWM_API_KEY`, `NEON_DB_URL`) sont configurés dans le dépôt GitHub
2. Le workflow `pipeline-horaire.yml` s'exécute automatiquement toutes les heures
3. Les données sont commitées dans le repo après chaque exécution
4. Le warehouse Neon.tech est mis à jour à chaque run (upsert)

## Scripts du pipeline

| Script | Rôle |
|--------|------|
| `src/extract.py` | Appelle les APIs (OWM ou Open-Meteo) et écrit dans `data/raw/` |
| `src/transform.py` | Lit `data/raw/`, normalise, déduplique, trie, écrit `data/clean/air_quality.csv` |
| `src/validate.py` | Valide le CSV clean (colonnes, types, doublons, tri) |
| `src/load_warehouse.py` | Charge `data/clean/air_quality.csv` dans PostgreSQL (Neon.tech) |
| `scripts/schema.sql` | DDL des tables du warehouse |

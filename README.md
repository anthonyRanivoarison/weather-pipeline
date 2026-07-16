# Weather Pipeline — Qualité de l'air

Pipeline de collecte automatique de données de qualité de l'air (AQI) pour 5 villes européennes, avec stockage dimensionnel dans un data warehouse PostgreSQL.

**Stack** : OpenWeatherMap + Open-Meteo → GitHub Actions → Neon.tech PostgreSQL

## Architecture

Voir [ARCHITECTURE.md](ARCHITECTURE.md) pour le détail complet.

```
extract.py (OWM temps réel / Open-Meteo historique)
    → data/raw/{ville}/{horodatage}.json
    → transform.py → data/clean/air_quality.csv
    → validate.py → vérifie le contrat
    → load_warehouse.py → Neon.tech PostgreSQL
```

## Prérequis

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- Une clé [OpenWeatherMap](https://home.openweathermap.org/users/sign_up) (gratuite)
- Un compte [Neon.tech](https://neon.tech) (gratuit)

## Installation

```bash
git clone <url-du-repo>
cd weather-pipeline
git checkout feat/air-quality-pipeline
uv sync
```

## Configuration

Copier `.env.example` vers `.env` et remplir les valeurs :

```env
OPENWEATHERMAP_API_KEY=votre_clé_owm
NEON_DB_URL=postgresql://user:pass@ep-xxx.region.aws.neon.tech/neondb?sslmode=require
```

## Utilisation

### Extraction temps réel (OpenWeatherMap)

```bash
uv run python src/extract.py
```

### Backfill historique (Open-Meteo, 12 mois)

```bash
uv run python src/extract.py --backfill
```

### Transformation raw → clean

```bash
uv run python src/transform.py
```

### Validation du contrat clean

```bash
uv run python src/validate.py
```

### Chargement du warehouse (Neon.tech)

```bash
uv run python src/load_warehouse.py
```

### Pipeline complet (une étape)

```bash
uv run python src/extract.py && \
uv run python src/transform.py && \
uv run python src/validate.py && \
uv run python src/load_warehouse.py
```

## Pipeline automatisé (GitHub Actions)

Le workflow `.github/workflows/pipeline-horaire.yml` s'exécute automatiquement toutes les heures via GitHub Actions. Il exécute la séquence complète et persist les données dans le repo et le warehouse Neon.tech.

Pour activer le pipeline automatique :

1. Pousser la branche `feat/air-quality-pipeline` vers GitHub
2. Configurer les secrets dans **Settings → Secrets and variables → Actions** :
   - `OWM_API_KEY` — votre clé OpenWeatherMap
   - `NEON_DB_URL` — chaîne de connexion Neon.tech
3. Activer les workflows dans l'onglet **Actions**

## Villes surveillées

| Ville | Pays | Latitude | Longitude |
|-------|------|----------|-----------|
| Paris | FR | 48.8566 | 2.3522 |
| London | GB | 51.5074 | -0.1278 |
| Berlin | DE | 52.5200 | 13.4050 |
| Madrid | ES | 40.4168 | -3.7038 |
| Rome | IT | 41.9028 | 12.4964 |

## Contrat de données (clean/air_quality.csv)

Une ligne par ville et par heure, tri chronologique, sans doublons. Consulter [ARCHITECTURE.md](ARCHITECTURE.md#contrat-de-données) pour la liste complète des colonnes et unités.

## Structure du dépôt

```
weather-pipeline/
├── .github/workflows/
│   ├── pipeline-horaire.yml     # Exécution horaire automatique
│   └── backfill-12mois.yml       # Backfill historique (exécution unique)
├── src/
│   ├── extract.py               # Appels API (OWM + Open-Meteo)
│   ├── transform.py             # raw/ → clean/air_quality.csv
│   ├── validate.py              # Validation du contrat clean/
│   └── load_warehouse.py        # Chargement dans PostgreSQL (Neon.tech)
├── scripts/
│   └── schema.sql               # DDL du warehouse (schéma étoile)
├── data/
│   ├── raw/{ville}/             # Fichiers JSON bruts (1 par appel)
│   └── clean/air_quality.csv    # CSV unique nettoyé
├── ARCHITECTURE.md              # Documentation d'architecture
├── TODO.md                      # Suivi des tâches
├── pyproject.toml               # Dépendances
└── README.md                    # Ce fichier
```

## Image prête au lancement

### 1. Construire l'image Docker
Placez-vous à la racine du projet (là où se trouve le fichier `Dockerfile`) et exécutez :
```bash
docker build -t weather-pipeline .
```

### 2. Lancer le conteneur en local
Assurez-vous d'avoir un fichier `.env` configuré à la racine du projet (sur le modèle du fichier `.env.example`). 

Lancez ensuite le conteneur avec la commande suivante :
```bash
docker run --rm -it --env-file .env weather-pipeline
```

## Trous connus dans les données

Le pipeline horaire utilise un déclencheur `schedule: cron` GitHub Actions
(`0 * * * *`). GitHub Actions ne garantit pas une exécution pile à l'heure :
en période de forte charge, les runs planifiés peuvent être retardés de
quelques minutes à plusieurs heures, voire sautés (comportement documenté
par GitHub). Cela explique les écarts irréguliers entre certains points
horaires dans clean/air_quality.csv (voir historique des commits
`chore(data): automatic pipeline run` pour le détail exact des horaires
réels d'exécution).

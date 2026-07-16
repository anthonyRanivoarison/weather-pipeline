# TODO — Pipeline Qualité de l'Air

> Stack : OpenWeatherMap (temps réel) + Open-Meteo (backfill) → GitHub Actions → Neon.tech PostgreSQL
> Schéma : Étoile (dim_time, dim_city, fact_air_quality)
> Branche : `feat/air-quality-pipeline`

---

## ✅ Phase 1 — Fondations (faite)

- [x] **1.1** Mettre à jour `pyproject.toml` : remplacer Airflow/pyarrow → psycopg2-binary
- [x] **1.2** Mettre à jour `.env.example` : ajouter `NEON_DB_URL`
- [x] **1.3** Créer les dossiers `data/raw/{paris,london,berlin,madrid,rome}`, `data/clean/`, `scripts/`, `notebooks/`, `.github/workflows/`
- [x] **1.4** Créer `scripts/schema.sql` (DDL des 3 tables du warehouse)
- [x] **1.5** Créer `.gitkeep` dans chaque dossier `data/raw/*`

## ✅ Phase 2 — Extraction (faite)

- [x] **2.1** Implémenter `src/extract.py` :
  - [x] `extract_current()` → OWM temps réel → `raw/{city}/{YYYY-MM-DD}_{HH}.json`
  - [x] `extract_backfill()` → Open-Meteo 12 mois → `raw/{city}/backfill_*.json`
  - [x] Métadonnée `_meta.source` dans chaque fichier pour identifier la provenance
- [x] **2.2** Tester l'extraction sur une ville (à faire quand une clé API sera disponible)

## ✅ Phase 3 — Transformation (faite)

- [x] **3.1** Implémenter `src/transform.py` :
  - [x] Parcourt `raw/*/*.json`
  - [x] Détection automatique du format (OWM vs Open-Meteo)
  - [x] Normalisation vers le schéma clean
  - [x] Déduplication (même ville + même heure)
  - [x] Tri chronologique
  - [x] Écrit `data/clean/air_quality.csv`
- [x] **3.2** Tester la transformation (quand raw/ contient des données)

## ✅ Phase 4 — Validation (faite)

- [x] **4.1** Implémenter `src/validate.py` :
  - [x] Vérifie toutes les colonnes du contrat
  - [x] Vérifie `aqi` dans [0, 5]
  - [x] Vérifie absence de doublons
  - [x] Vérifie tri chronologique
  - [x] Code de sortie 0 = OK, 1 = échec

## ✅ Phase 5 — Chargement du warehouse (faite)

- [x] **5.1** Implémenter `src/load_warehouse.py` :
  - [x] Connexion PostgreSQL via psycopg2
  - [x] Création des tables via `scripts/schema.sql`
  - [x] Upsert `dim_time` (ON CONFLICT datetime)
  - [x] Upsert `dim_city` (ON CONFLICT city_name)
  - [x] Upsert `fact_air_quality` (ON CONFLICT time_id, city_id)
- [ ] **5.2** Tester le chargement (quand une base Neon.tech sera disponible)

## ✅ Phase 6 — Orchestration GitHub Actions (faite)

- [x] **6.1** Créer `.github/workflows/pipeline-horaire.yml`
- [x] **6.2** Créer `.github/workflows/backfill-12mois.yml`
- [ ] **6.3** Configurer les secrets GitHub : `OWM_API_KEY`, `NEON_DB_URL`
- [ ] **6.4** Pousser la branche et activer les workflows sur GitHub

---

## 🔲 Phase 7 — Intégration & Déploiement

- [x] **7.1** Pousser la branche `feat/air-quality-pipeline` vers GitHub
- [ ] **7.2** Configurer les secrets dans Settings → Secrets and variables → Actions
- [ ] **7.3** Vérifier que le PAT (GITHUB_TOKEN) a les droits d'écriture
- [x] **7.4** Exécuter `uv sync` sur une machine avec uv (installation validée)
- [ ] **7.5** Tester le pipeline complet en local avec une clé OWM

## 🔲 Phase 8 — Backfill

- [ ] **8.1** Exécuter le workflow `backfill-12mois.yml` depuis GitHub Actions
- [x] **8.2** (Alternative) Exécuter en local : `uv run python src/extract.py --backfill`
- [ ] **8.3** Vérifier que `raw/` contient les 5 villes × 12 mois
- [x] **8.4** Vérifier que `clean/air_quality.csv` est correct via `validate.py`
- [ ] **8.5** Vérifier que Neon.tech contient les données

## 🔲 Phase 9 — Pipeline horaire

- [x] **9.1** Vérifier que le cron `0 * * * *` déclenche le workflow
- [x] **9.2** Vérifier les commits automatiques de `data/` dans le repo
- [x] **9.3** Vérifier que les données s'accumulent dans Neon.tech
- [ ] **9.4** Capturer l'historique des exécutions (5+ jours, heures décalées)

## 🔲 Phase 10 — Documentation finale

- [ ] **10.1** Finaliser `ARCHITECTURE.md` (période couverte, trous connus, nb lignes)
- [ ] **10.2** Ajouter les infos de connexion Neon.tech dans le README
- [ ] **10.3** Créer `notebooks/exploration.ipynb` si pertinent

## 🔲 Phase 11 — Rapport de projet

- [ ] **11.1** Méthode de travail du groupe
- [ ] **11.2** Répartition des tâches
- [ ] **11.3** Difficultés rencontrées et solutions
- [ ] **11.4** Choix techniques justifiés

## 🔲 Phase 12 — Vidéo (3 min max)

- [ ] **12.1** Pipeline qui tourne (historique GitHub Actions)
- [ ] **12.2** Zones de stockage (raw/ + clean/ dans le repo)
- [ ] **12.3** Requête SQL sur le warehouse Neon.tech
- [ ] **12.4** Montage et rendu final

## 🔲 Phase 13 — Vérification finale

- [ ] **13.1** `git status` : aucun fichier sensible (.env, clés) dans l'historique
- [ ] **13.2** `src/validate.py` passe sur clean/
- [ ] **13.3** Warehouse accessible et requêtable
- [ ] **13.4** Tous les livrables exigés par le sujet sont présents
- [ ] **13.5** Commits des 5 membres dans l'historique
- [ ] **13.6** Merge de `feat/air-quality-pipeline` → `main`

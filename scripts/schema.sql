-- ============================================================
-- Schéma du warehouse — Modélisation dimensionnelle (étoile)
-- Base : PostgreSQL (Neon.tech)
-- ============================================================

CREATE TABLE IF NOT EXISTS dim_time (
    id          SERIAL PRIMARY KEY,
    datetime    TIMESTAMP NOT NULL UNIQUE,
    date        DATE NOT NULL,
    hour        SMALLINT NOT NULL CHECK (hour BETWEEN 0 AND 23),
    day_of_week VARCHAR(10) NOT NULL,
    is_weekend  BOOLEAN NOT NULL,
    month       SMALLINT NOT NULL CHECK (month BETWEEN 1 AND 12),
    year        SMALLINT NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_city (
    id          SERIAL PRIMARY KEY,
    city_name   VARCHAR(100) NOT NULL UNIQUE,
    country     VARCHAR(2) NOT NULL,
    latitude    DOUBLE PRECISION NOT NULL,
    longitude   DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_air_quality (
    id          SERIAL PRIMARY KEY,
    time_id     INTEGER NOT NULL REFERENCES dim_time(id),
    city_id     INTEGER NOT NULL REFERENCES dim_city(id),
    aqi         SMALLINT NOT NULL CHECK (aqi BETWEEN 1 AND 5),
    co          DOUBLE PRECISION,
    no          DOUBLE PRECISION,
    no2         DOUBLE PRECISION,
    o3          DOUBLE PRECISION,
    so2         DOUBLE PRECISION,
    pm2_5       DOUBLE PRECISION,
    pm10        DOUBLE PRECISION,
    nh3         DOUBLE PRECISION,
    UNIQUE (time_id, city_id)
);

CREATE INDEX IF NOT EXISTS idx_fact_time   ON fact_air_quality(time_id);
CREATE INDEX IF NOT EXISTS idx_fact_city   ON fact_air_quality(city_id);

import csv
import os
import sys
from datetime import datetime, timezone

import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

CLEAN_CSV = "data/clean/air_quality.csv"
SCHEMA_SQL = "scripts/schema.sql"
DB_URL = os.getenv("NEON_DB_URL")


def _dict_to_dim_time(dt_str: str) -> dict:
    dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00")).replace(tzinfo=None)
    return {
        "datetime": dt,
        "date": dt.date(),
        "hour": dt.hour,
        "day_of_week": dt.strftime("%A"),
        "is_weekend": dt.weekday() >= 5,
        "month": dt.month,
        "year": dt.year,
    }


def load() -> int:
    if not DB_URL:
        print("ERROR: NEON_DB_URL not set", file=sys.stderr)
        return 1

    try:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = False
    except Exception as e:
        print(f"ERROR: cannot connect to database: {e}", file=sys.stderr)
        return 1

    with open(SCHEMA_SQL) as f:
        ddl = f.read()

    try:
        with conn.cursor() as cur:
            cur.execute(ddl)
        conn.commit()
    except Exception as e:
        print(f"ERROR: schema creation failed: {e}", file=sys.stderr)
        conn.close()
        return 1

    with open(CLEAN_CSV, newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print("WARNING: clean CSV is empty, nothing to load", file=sys.stderr)
        conn.close()
        return 0

    try:
        with conn.cursor() as cur:
            # Batch dim_time — unique datetimes only
            time_rows = []
            seen_times = set()
            for row in rows:
                dt_key = row["datetime"]
                if dt_key not in seen_times:
                    seen_times.add(dt_key)
                    t = _dict_to_dim_time(dt_key)
                    time_rows.append((
                        t["datetime"], t["date"], t["hour"],
                        t["day_of_week"], t["is_weekend"],
                        t["month"], t["year"],
                    ))

            execute_values(
                cur,
                """INSERT INTO dim_time (datetime, date, hour, day_of_week, is_weekend, month, year)
                   VALUES %s ON CONFLICT (datetime) DO NOTHING""",
                time_rows,
            )

            cur.execute("SELECT id, datetime FROM dim_time")
            time_ids = {dt.replace(tzinfo=None).isoformat(): tid for tid, dt in cur.fetchall()}

            # Batch dim_city
            city_rows = []
            cities_seen = set()
            for row in rows:
                name = row["city"]
                if name in cities_seen:
                    continue
                cities_seen.add(name)
                city_rows.append((
                    row["city"], row["country"],
                    float(row["latitude"]), float(row["longitude"]),
                ))

            execute_values(
                cur,
                """INSERT INTO dim_city (city_name, country, latitude, longitude)
                   VALUES %s ON CONFLICT (city_name) DO NOTHING""",
                city_rows,
            )

            cur.execute("SELECT id, city_name FROM dim_city")
            city_ids = {cn: cid for cid, cn in cur.fetchall()}

            # Batch fact_air_quality
            fact_rows = []
            for row in rows:
                dt_key = datetime.fromisoformat(
                    row["datetime"].replace("Z", "+00:00")
                ).replace(tzinfo=None).isoformat()
                tid = time_ids.get(dt_key)
                cid = city_ids.get(row["city"])
                if tid is None or cid is None:
                    continue
                fact_rows.append((
                    tid, cid,
                    int(row["aqi"]) if row.get("aqi") else None,
                    float(row["co"]) if row.get("co") else None,
                    float(row["no"]) if row.get("no") else None,
                    float(row["no2"]) if row.get("no2") else None,
                    float(row["o3"]) if row.get("o3") else None,
                    float(row["so2"]) if row.get("so2") else None,
                    float(row["pm2_5"]) if row.get("pm2_5") else None,
                    float(row["pm10"]) if row.get("pm10") else None,
                    float(row["nh3"]) if row.get("nh3") else None,
                ))

            execute_values(
                cur,
                """INSERT INTO fact_air_quality
                       (time_id, city_id, aqi, co, no, no2, o3, so2, pm2_5, pm10, nh3)
                   VALUES %s
                   ON CONFLICT (time_id, city_id)
                   DO UPDATE SET
                       aqi = EXCLUDED.aqi, co = EXCLUDED.co, no = EXCLUDED.no,
                       no2 = EXCLUDED.no2, o3 = EXCLUDED.o3, so2 = EXCLUDED.so2,
                       pm2_5 = EXCLUDED.pm2_5, pm10 = EXCLUDED.pm10, nh3 = EXCLUDED.nh3""",
                fact_rows,
            )

        conn.commit()
        print(f"Loaded {len(fact_rows)} rows into fact_air_quality")
    except Exception as e:
        conn.rollback()
        print(f"ERROR: load failed: {e}", file=sys.stderr)
        conn.close()
        return 1

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(load())
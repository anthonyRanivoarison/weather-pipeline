```python
import csv
import os
import sys
from datetime import datetime

import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

CLEAN_CSV = "data/clean/air_quality.csv"
SCHEMA_SQL = "scripts/schema.sql"
DB_URL = os.getenv("NEON_DB_URL")


def parse_datetime(dt_str: str) -> datetime:
    """
    Convertit une date ISO provenant du CSV en datetime sans timezone.
    Exemple :
        2026-08-29T10:00:00Z
        -> 2026-08-29 10:00:00
    """
    return datetime.fromisoformat(
        dt_str.strip().replace("Z", "+00:00")
    ).replace(tzinfo=None)


def clean_city_name(city: str) -> str:
    """Normalise le nom d'une ville pour éviter les problèmes d'espaces/casse."""
    return city.strip()


def value_float(value):
    """Convertit une valeur CSV en float ou None."""
    if value is None:
        return None

    value = str(value).strip()

    if value == "":
        return None

    return float(value)


def value_int(value):
    """Convertit une valeur CSV en int ou None."""
    if value is None:
        return None

    value = str(value).strip()

    if value == "":
        return None

    return int(float(value))


def load() -> int:

    if not DB_URL:
        print(
            "ERROR: NEON_DB_URL not set",
            file=sys.stderr,
        )
        return 1



    if not os.path.exists(CLEAN_CSV):
        print(
            f"ERROR: clean CSV not found: {CLEAN_CSV}",
            file=sys.stderr,
        )
        return 1

    try:
        with open(CLEAN_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except Exception as e:
        print(
            f"ERROR: cannot read {CLEAN_CSV}: {e}",
            file=sys.stderr,
        )
        return 1

    print(f"CSV rows found: {len(rows)}")

    if not rows:
        print(
            "WARNING: clean CSV is empty, nothing to load",
            file=sys.stderr,
        )
        return 0


    try:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = False
    except Exception as e:
        print(
            f"ERROR: cannot connect to database: {e}",
            file=sys.stderr,
        )
        return 1

    try:


        if not os.path.exists(SCHEMA_SQL):
            print(
                f"ERROR: schema file not found: {SCHEMA_SQL}",
                file=sys.stderr,
            )
            conn.close()
            return 1

        with open(SCHEMA_SQL, encoding="utf-8") as f:
            ddl = f.read()

        with conn.cursor() as cur:
            cur.execute(ddl)

        conn.commit()

        print("Database schema ready.")


        normalized_rows = []

        for index, row in enumerate(rows, start=1):
            try:
                city = clean_city_name(row["city"])
                country = row["country"].strip()

                latitude = value_float(row["latitude"])
                longitude = value_float(row["longitude"])

                dt = parse_datetime(row["datetime"])

                normalized_rows.append(
                    {
                        "city": city,
                        "country": country,
                        "latitude": latitude,
                        "longitude": longitude,
                        "datetime": dt,
                        "aqi": value_int(row.get("aqi")),
                        "co": value_float(row.get("co")),
                        "no": value_float(row.get("no")),
                        "no2": value_float(row.get("no2")),
                        "o3": value_float(row.get("o3")),
                        "so2": value_float(row.get("so2")),
                        "pm2_5": value_float(row.get("pm2_5")),
                        "pm10": value_float(row.get("pm10")),
                        "nh3": value_float(row.get("nh3")),
                    }
                )

            except Exception as e:
                print(
                    f"WARNING: invalid CSV row #{index}: {e}",
                    file=sys.stderr,
                )

        if not normalized_rows:
            print(
                "ERROR: no valid rows after normalization",
                file=sys.stderr,
            )
            conn.close()
            return 1

        print(
            f"Valid rows after normalization: "
            f"{len(normalized_rows)}"
        )


        unique_times = {}

        for row in normalized_rows:
            dt = row["datetime"]
            unique_times[dt] = (
                dt,
                dt.date(),
                dt.hour,
                dt.strftime("%A"),
                dt.weekday() >= 5,
                dt.month,
                dt.year,
            )

        time_rows = list(unique_times.values())

        print(f"Unique timestamps: {len(time_rows)}")

        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO dim_time
                    (
                        datetime,
                        date,
                        hour,
                        day_of_week,
                        is_weekend,
                        month,
                        year
                    )
                VALUES %s
                ON CONFLICT (datetime)
                DO NOTHING
                """,
                time_rows,
            )

            # Récupération directe des IDs après insertion.
            cur.execute(
                """
                SELECT id, datetime
                FROM dim_time
                """
            )

            time_ids = {}

            for time_id, dt in cur.fetchall():
                if dt is not None:
                    time_ids[dt.replace(tzinfo=None)] = time_id

        print(f"Time dimension IDs available: {len(time_ids)}")


        unique_cities = {}

        for row in normalized_rows:
            city = row["city"]

            if city not in unique_cities:
                unique_cities[city] = (
                    city,
                    row["country"],
                    row["latitude"],
                    row["longitude"],
                )

        city_rows = list(unique_cities.values())

        print(f"Unique cities: {len(city_rows)}")

        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO dim_city
                    (
                        city_name,
                        country,
                        latitude,
                        longitude
                    )
                VALUES %s
                ON CONFLICT (city_name)
                DO UPDATE SET
                    country = EXCLUDED.country,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude
                """,
                city_rows,
            )

            # Récupération directe des IDs.
            cur.execute(
                """
                SELECT id, city_name
                FROM dim_city
                """
            )

            city_ids = {
                clean_city_name(city_name): city_id
                for city_id, city_name in cur.fetchall()
            }

        print(f"City dimension IDs available: {len(city_ids)}")


        fact_rows = []
        skipped_time = 0
        skipped_city = 0

        for row in normalized_rows:
            time_id = time_ids.get(row["datetime"])
            city_id = city_ids.get(row["city"])

            if time_id is None:
                skipped_time += 1
                print(
                    f"WARNING: missing time_id for "
                    f"{row['datetime']}",
                    file=sys.stderr,
                )
                continue

            if city_id is None:
                skipped_city += 1
                print(
                    f"WARNING: missing city_id for "
                    f"{row['city']}",
                    file=sys.stderr,
                )
                continue

            fact_rows.append(
                (
                    time_id,
                    city_id,
                    row["aqi"],
                    row["co"],
                    row["no"],
                    row["no2"],
                    row["o3"],
                    row["so2"],
                    row["pm2_5"],
                    row["pm10"],
                    row["nh3"],
                )
            )

        print(f"Fact rows prepared: {len(fact_rows)}")
        print(f"Skipped rows - missing time: {skipped_time}")
        print(f"Skipped rows - missing city: {skipped_city}")

        if not fact_rows:
            print(
                "ERROR: no fact rows prepared. "
                "Nothing will be inserted.",
                file=sys.stderr,
            )
            conn.rollback()
            conn.close()
            return 1


        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO fact_air_quality
                    (
                        time_id,
                        city_id,
                        aqi,
                        co,
                        no,
                        no2,
                        o3,
                        so2,
                        pm2_5,
                        pm10,
                        nh3
                    )
                VALUES %s
                ON CONFLICT (time_id, city_id)
                DO UPDATE SET
                    aqi = EXCLUDED.aqi,
                    co = EXCLUDED.co,
                    no = EXCLUDED.no,
                    no2 = EXCLUDED.no2,
                    o3 = EXCLUDED.o3,
                    so2 = EXCLUDED.so2,
                    pm2_5 = EXCLUDED.pm2_5,
                    pm10 = EXCLUDED.pm10,
                    nh3 = EXCLUDED.nh3
                """,
                fact_rows,
            )

        conn.commit()

        print(
            f"Loaded {len(fact_rows)} rows into fact_air_quality"
        )

    except Exception as e:
        conn.rollback()

        print(
            f"ERROR: load failed: {e}",
            file=sys.stderr,
        )

        conn.close()
        return 1

    conn.close()

    print("Warehouse load completed successfully.")

    return 0


if __name__ == "__main__":
    sys.exit(load())
```

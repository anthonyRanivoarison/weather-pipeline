import csv
import json
import os
import sys
from datetime import datetime, timezone
from utils.convert import convert_eaqi_to_owm
RAW_DIR = "data/raw"
CLEAN_DIR = "data/clean"
CLEAN_CSV = os.path.join(CLEAN_DIR, "air_quality.csv")

FIELDS = [
    "city", "country", "latitude", "longitude",
    "datetime", "aqi",
    "co", "no", "no2", "o3", "so2", "pm2_5", "pm10", "nh3",
]


def _parse_owm(data: dict) -> list[dict]:
    meta = data.get("_meta", {})
    city = meta.get("city", "unknown")
    country = meta.get("country", "")
    lat = data.get("coord", {}).get("lat")
    lon = data.get("coord", {}).get("lon")

    rows = []
    for entry in data.get("list", []):
        dt = entry.get("dt")
        if dt is None:
            continue
        parsed_dt = datetime.fromtimestamp(dt, tz=timezone.utc)
        comp = entry.get("components", {})
        rows.append({
            "city": city,
            "country": country,
            "latitude": lat,
            "longitude": lon,
            "datetime": parsed_dt.strftime("%Y-%m-%dT%H:00:00Z"),
            "aqi": entry.get("main", {}).get("aqi"),
            "co": comp.get("co"),
            "no": comp.get("no"),
            "no2": comp.get("no2"),
            "o3": comp.get("o3"),
            "so2": comp.get("so2"),
            "pm2_5": comp.get("pm2_5") or comp.get("pm25"),
            "pm10": comp.get("pm10"),
            "nh3": comp.get("nh3"),
        })
    return rows


def _parse_openmeteo(data: dict) -> list[dict]:
    meta = data.get("_meta", {})
    city = meta.get("city", "unknown")
    country = meta.get("country", "")
    lat = data.get("latitude")
    lon = data.get("longitude")
    hourly = data.get("hourly", {})

    times = hourly.get("time", [])
    if not times:
        return []

    rows = []
    for i, t in enumerate(times):
        aqi = hourly.get("european_aqi", [None] * len(times))[i]
        rows.append({
            "city": city,
            "country": country,
            "latitude": lat,
            "longitude": lon,
            "datetime": t.replace("T", "T") + ":00Z",
            "aqi": convert_eaqi_to_owm(aqi),
            "co": hourly.get("carbon_monoxide", [None] * len(times))[i],
            "no": hourly.get("nitrogen_monoxide", [None] * len(times))[i],
            "no2": hourly.get("nitrogen_dioxide", [None] * len(times))[i],
            "o3": hourly.get("ozone", [None] * len(times))[i],
            "so2": hourly.get("sulphur_dioxide", [None] * len(times))[i],
            "pm2_5": hourly.get("pm2_5", [None] * len(times))[i],
            "pm10": hourly.get("pm10", [None] * len(times))[i],
            "nh3": hourly.get("ammonia", [None] * len(times))[i],
        })
    return rows

def _clean_row(row: dict) -> dict | None:
    """Nettoie une mesure de qualite de l'air : strip des strings,
    cast numerique, bornes physiques/geographiques.
    Retourne None si la ligne est inexploitable (pas de datetime)."""
    if not row.get("datetime"):
        return None

    row["city"] = (row.get("city") or "unknown").strip().title()
    row["country"] = (row.get("country") or "").strip().upper()

    def _to_float(val, lo=None):
        """Cast en float, coerce en None si invalide ou hors borne physique."""
        try:
            f = float(val)
        except (TypeError, ValueError):
            return None
        if lo is not None and f < lo:
            return None
        return f

    lat = _to_float(row.get("latitude"))
    row["latitude"] = lat if lat is not None and -90 <= lat <= 90 else None

    lon = _to_float(row.get("longitude"))
    row["longitude"] = lon if lon is not None and -180 <= lon <= 180 else None

    return row

def _parse_file(path: str) -> list[dict] | None:
    try:
        with open(path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"ERROR: cannot read {path}: {e}", file=sys.stderr)
        return None

    if "hourly" in data:
        return _parse_openmeteo(data)
    if "list" in data:
        return _parse_owm(data)
    print(f"WARNING: unknown format in {path}, skipping", file=sys.stderr)
    return None


def transform():
    os.makedirs(CLEAN_DIR, exist_ok=True)

    all_rows = []
    for root, _dirs, files in os.walk(RAW_DIR):
        for fname in sorted(files):
            if not fname.endswith(".json") or fname == ".gitkeep":
                continue
            path = os.path.join(root, fname)
            parsed = _parse_file(path)
            if parsed:
                all_rows.extend(parsed)

    seen = set()
    unique = []
    for row in all_rows:
        key = (row["city"], row["datetime"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)

    unique.sort(key=lambda r: (r["datetime"], r["city"]))

    os.makedirs(CLEAN_DIR, exist_ok=True)
    with open(CLEAN_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(unique)

    print(f"Clean CSV: {CLEAN_CSV}")
    print(f"Rows written: {len(unique)} (deduplicated from {len(all_rows)})")
    return 0


if __name__ == "__main__":
    sys.exit(transform())

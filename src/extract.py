import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

CITIES = {
    "paris":  {"lat": 48.8566, "lon": 2.3522,  "country": "FR"},
    "london": {"lat": 51.5074, "lon": -0.1278, "country": "GB"},
    "berlin": {"lat": 52.5200, "lon": 13.4050, "country": "DE"},
    "madrid": {"lat": 40.4168, "lon": -3.7038, "country": "ES"},
    "rome":   {"lat": 41.9028, "lon": 12.4964, "country": "IT"},
}

RAW_DIR = "data/raw"
API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")


def _raw_path(city: str, filename: str) -> str:
    city_dir = os.path.join(RAW_DIR, city)
    os.makedirs(city_dir, exist_ok=True)
    return os.path.join(city_dir, filename)


def _fetch_owm(lat: float, lon: float) -> dict | None:
    url = "https://api.openweathermap.org/data/2.5/air_pollution"
    resp = requests.get(url, params={"lat": lat, "lon": lon, "appid": API_KEY}, timeout=15)
    if resp.status_code != 200:
        print(f"OWM error {resp.status_code}: {resp.text}", file=sys.stderr)
        return None
    return resp.json()


def extract_current() -> int:
    if not API_KEY:
        print("ERROR: OPENWEATHERMAP_API_KEY not set", file=sys.stderr)
        return 1

    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d_%H")

    success = 0
    for name, coords in CITIES.items():
        data = _fetch_owm(coords["lat"], coords["lon"])
        if data is None:
            continue
        data["_meta"] = {"city": name, "country": coords["country"], "source": "openweathermap"}
        path = _raw_path(name, f"{date_str}.json")
        with open(path, "w") as f:
            json.dump(data, f)
        print(f"Wrote {path}")
        success += 1

    print(f"Extracted {success}/{len(CITIES)} cities")
    return 0 if success == len(CITIES) else 1


def extract_backfill() -> int:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=365)
    start_str = start.strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")

    params = {
      feat/backfill-and-fixes
        "hourly": "european_aqi,pm2_5,pm10,nitrogen_dioxide,ozone,sulphur_dioxide,carbon_monoxide,nitrogen_monoxide,ammonia",

         main
        "start_date": start_str,
        "end_date": end_str,
        "timezone": "UTC",
    }

    success = 0
    for name, coords in CITIES.items():
        params["latitude"] = coords["lat"]
        params["longitude"] = coords["lon"]
        resp = requests.get(
            "https://air-quality-api.open-meteo.com/v1/air-quality",
            params=params,
            timeout=30,
        )
        if resp.status_code != 200:
            print(f"Open-Meteo error {resp.status_code}: {resp.text}", file=sys.stderr)
            continue
        data = resp.json()
        data["_meta"] = {"city": name, "country": coords["country"], "source": "open-meteo"}
        path = _raw_path(name, f"backfill_{start_str}_{end_str}.json")
        with open(path, "w") as f:
            json.dump(data, f)
        print(f"Wrote {path}")
        success += 1

    print(f"Backfill extracted {success}/{len(CITIES)} cities")
    return 0 if success == len(CITIES) else 1


def main():
    parser = argparse.ArgumentParser(description="Extract air quality data")
    parser.add_argument("--backfill", action="store_true", help="Run historical backfill via Open-Meteo")
    args = parser.parse_args()

    if args.backfill:
        return extract_backfill()
    return extract_current()


if __name__ == "__main__":
    sys.exit(main())

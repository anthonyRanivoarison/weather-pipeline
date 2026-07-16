import csv
import sys

CLEAN_CSV = "data/clean/air_quality.csv"

REQUIRED_FIELDS = [
    "city", "country", "latitude", "longitude",
    "datetime", "aqi",
    "co", "no", "no2", "o3", "so2", "pm2_5", "pm10", "nh3",
]

REQUIRED_NOT_NULL = ["city", "datetime", "aqi"]


def validate() -> int:
    errors = []

    try:
        with open(CLEAN_CSV, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except FileNotFoundError:
        print(f"ERROR: {CLEAN_CSV} not found", file=sys.stderr)
        return 1

    if not rows:
        print("ERROR: empty CSV", file=sys.stderr)
        return 1

    fields = reader.fieldnames or []
    for field in REQUIRED_FIELDS:
        if field not in fields:
            errors.append(f"Missing column: {field}")

    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        return 1

    seen = set()
    prev_datetime = ""
    for i, row in enumerate(rows, start=2):
        for col in REQUIRED_NOT_NULL:
            val = row.get(col, "")
            if val is None or val.strip() == "":
                errors.append(f"Row {i}: {col} is empty")

        aqi_raw = row.get("aqi", "")
        if aqi_raw:
            try:
                aqi = int(aqi_raw)
                if aqi < 1 or aqi > 5:
                    errors.append(f"Row {i}: aqi={aqi} out of range [0-5]")
            except ValueError:
                errors.append(f"Row {i}: aqi='{aqi_raw}' not an integer")

        key = (row.get("city", ""), row.get("datetime", ""))
        if key in seen:
            errors.append(f"Row {i}: duplicate city='{key[0]}' datetime='{key[1]}'")
        seen.add(key)

        dt = row.get("datetime", "")
        if dt < prev_datetime:
            errors.append(f"Row {i}: datetime '{dt}' < previous '{prev_datetime}' (not sorted)")
        prev_datetime = dt

    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        print(f"Validation FAILED: {len(errors)} error(s)", file=sys.stderr)
        return 1

    print(f"Validation PASSED: {len(rows)} rows, {len(fields)} columns")
    return 0


if __name__ == "__main__":
    sys.exit(validate())

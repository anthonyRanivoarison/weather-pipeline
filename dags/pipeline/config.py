from pathlib import Path
from typing import Final

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parent.parent

DATA_DIR: Final[Path] = PROJECT_ROOT / "data"
RAW_DIR: Final[Path] = DATA_DIR / "raw"
PROCESSED_DIR: Final[Path] = DATA_DIR / "processed"
LOGS_DIR: Final[Path] = PROJECT_ROOT / "logs"

LOG_FILE: Final[Path] = LOGS_DIR / "pipeline.log"

OPENAQ_BASE_URL: Final[str] = "https://api.openaq.org/v2"
OPENAQ_ENDPOINT: Final[str] = "/latest"
OPENAQ_PARAMS: Final[dict] = {
    "limit": 1000,
    "parameter": ["pm25", "pm10", "no2", "o3", "so2", "co"],
}

REQUEST_TIMEOUT: Final[int] = 30
MAX_RETRIES: Final[int] = 3
RETRY_DELAY: Final[int] = 5

CSV_FILENAME: Final[str] = "air_quality_clean.csv"
PARQUET_FILENAME: Final[str] = "air_quality_clean.parquet"
RAW_FILENAME_TEMPLATE: Final[str] = "air_quality_raw_{timestamp}.json"

CLEAN_COLUMNS: Final[list[str]] = [
    "location",
    "city",
    "country",
    "latitude",
    "longitude",
    "parameter",
    "value",
    "unit",
    "last_updated",
]

DTYPE_MAPPING: Final[dict] = {
    "value": "float64",
    "latitude": "float64",
    "longitude": "float64",
    "parameter": "category",
    "unit": "category",
    "country": "category",
}
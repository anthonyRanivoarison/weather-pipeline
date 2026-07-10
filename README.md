# Weather Pipeline

A data engineering project that ingests weather data from the [OpenWeatherMap API](https://openweathermap.org/api) and processes it through an orchestrated ETL pipeline.

The pipeline fetches real-time weather data, transforms it into a structured format, and stores it for further analysis — demonstrating a production-ready data workflow with modern tooling.

**Language:** Python 3.11+

## Prerequisites

- Python 3.11 or later
- [uv](https://docs.astral.sh/uv/) — modern Python package manager
- An [OpenWeatherMap API key](https://home.openweathermap.org/users/sign_up) (free tier works)

## Installation

```bash
uv sync
```

All dependencies are resolved and locked via `uv.lock`.

## Configuration

Create a `.env` file in the project root:

```env
OPENWEATHERMAP_API_KEY=your_api_key_here
```

The project reads this file automatically via `python-dotenv` on startup.

## Usage

```bash
uv run python src/main.py
```

You will be prompted to enter a city name. The script fetches current weather data for that city and outputs the raw JSON response. Subsequent development will add transformation, storage, and Airflow orchestration steps.

## Project Structure

```
weather-pipeline/
├── pyproject.toml      # Project metadata and dependencies
├── uv.lock             # Lockfile (uv)
└── src/
    └── main.py         # Pipeline entry point
```

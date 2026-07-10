import os
import requests
from dotenv import load_dotenv


load_dotenv()
API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")


def get_coords(city: str) -> dict | None:
    """Récupère les coordonnées (lat, lon) d'une ville via l'API météo."""
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": API_KEY,
        "units": "metric",
        "lang": "fr",
    }
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        print(f"Erreur météo: {resp.status_code} - {resp.text}")
        return None
    return resp.json()


def get_air_quality(lat: float, lon: float) -> dict | None:
    """Récupère la qualité de l'air aux coordonnées données."""
    url = "https://api.openweathermap.org/data/2.5/air_pollution"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": API_KEY,
    }
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        print(f"Erreur air pollution: {resp.status_code} - {resp.text}")
        return None
    return resp.json()


def main() -> dict | None:
    city = input("Enter a city: ")

    # 1. Météo
    weather_data = get_coords(city)
    if weather_data is None:
        return None

    # 2. Qualité de l'air — besoin des coordonnées de la ville
    lat = weather_data["coord"]["lat"]
    lon = weather_data["coord"]["lon"]
    air_data = get_air_quality(lat, lon)

    # 3. Assembler les deux dans un seul dict
    result = {
        "city": city,
        "weather": weather_data,
        "air_quality": air_data,
    }
    print(result)       # affichage dans le terminal
    return result       # ET retourne le JSON


if __name__ == "__main__":
    main()

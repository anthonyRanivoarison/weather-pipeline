import os
import requests
from dotenv import load_dotenv



load_dotenv()
API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")



def main():
    city =  input("enter a city : ")
    url = "https://api.openweathermap.org/data/2.5/weather"

    params= {
        "q":city,
        "appid": API_KEY,
        "units": "metric",
        "lang": "fr"
    }
    response = requests.get(url,params=params)

    data =  response.json()
    print(data)


if __name__ == "__main__":
    main()










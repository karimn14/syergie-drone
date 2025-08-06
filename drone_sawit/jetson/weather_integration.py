"""
weather_integration.py
Fetches live weather data and provides mission adaptation hooks.
"""
import requests
import os

OPENWEATHER_API_KEY = os.environ.get('OPENWEATHER_API_KEY', 'demo')


def get_weather(lat, lon):
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
    resp = requests.get(url)
    if resp.status_code == 200:
        data = resp.json()
        wind = data['wind']['speed']
        rain = data.get('rain', {}).get('1h', 0)
        temp = data['main']['temp']
        return {'wind': wind, 'rain': rain, 'temp': temp}
    else:
        return {'wind': None, 'rain': None, 'temp': None}

if __name__ == "__main__":
    print(get_weather(-2.2, 113.9))

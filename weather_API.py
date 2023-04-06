import requests

def get_weather_info():

    base_url = "http://api.openweathermap.org/data/2.5/weather?"

    # Replace {API_KEY} with your actual API key from OpenWeatherMap
    api_key = "API_KEY"

    city = "CITY_NAME"

    url = base_url + "appid=" + api_key + "&q=" + city

    response = requests.get(url).json()

    city_name = response['name']
    country_code = response['sys']['country']
    temperature =   response['main']['temp'] - 273
    description = response['weather'][0]['description'] 
    humidity = response['main']['humidity']
    wind_speed__kmh = response['wind']['speed'] * 1.60934

    weather_text = f"Current weather in {city_name}, {country_code}: Temperature: {temperature:.1f}°C, Description: {description.capitalize()}, Humidity: {humidity}%, Wind speed: {wind_speed__kmh} kmh"
    return weather_text
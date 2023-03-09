import os
from abc import ABC, abstractmethod
from collections import defaultdict
from json import JSONDecodeError
from typing import List

from flask import Flask, render_template, request
import requests

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__, template_folder='')


class WeatherResponse:
    def __init__(self, min_temperature: float, max_temperature: float, temperature: float, year: int, month: int, day: int):
        self.min_temperature: float = min_temperature
        self.max_temperature: float = max_temperature
        self.temperature: float = temperature
        self.year: int = year
        self.month: int = month
        self.day: int = day

    def __str__(self):
        return f"{{min: {self.min_temperature}, max: {self.max_temperature}, temp: {self.temperature}, date:{self.year}-{self.month}-{self.day}}}"

    def __repr__(self):
        return self.__str__()


class WeatherForecast:
    def __init__(self,
                 avg_min_temperature: float,
                 stderr_min_temperature: float,
                 avg_max_temperature: float,
                 stderr_max_temperature: float,
                 avg_temperature: float,
                 stderr_temperature: float,
                 contributed_services_amount: int,
                 date: str,
                 ):
        self.avg_min_temperature: float = avg_min_temperature
        self.stderr_min_temperature: float = stderr_min_temperature
        self.avg_max_temperature: float = avg_max_temperature
        self.stderr_max_temperature: float = stderr_max_temperature
        self.avg_temperature: float = avg_temperature
        self.stderr_temperature: float = stderr_temperature
        self.contributed_services_amount: int = contributed_services_amount
        self.date: str = date


class WeatherService(ABC):
    @abstractmethod
    def get_city_id(self, city_name: str):
        ...

    @abstractmethod
    def fetch_weather_forecast(self, city_id, days: int) -> List[WeatherResponse]:
        ...


class CityNotFoundException(RuntimeError):
    pass


class WeatherNotFetchedException(RuntimeError):
    pass


class MeteoSourceService(WeatherService):

    API_URL = "https://www.meteosource.com/api/v1/free"
    API_KEY = os.getenv("METEO_SOURCE_API_KEY")
    NAME = "MeteoSource"

    def get_city_id(self, city_name: str):
        response = requests.get(
            f"{MeteoSourceService.API_URL}/find_places",
            params={'language': 'en', 'text': city_name, 'key': MeteoSourceService.API_KEY}
        )
        if response.status_code != 200:
            print(f"MeteoSourceService:get_city_id received {response.status_code} status code")
            try:
                print(response.json())
            except JSONDecodeError:
                print(response.content)
            raise CityNotFoundException()

        cities = response.json()
        if not cities:
            raise CityNotFoundException()

        return cities[0]["place_id"]

    def fetch_weather_forecast(self, city_id, days: int) -> List[WeatherResponse]:
        response = requests.get(
            f"{MeteoSourceService.API_URL}/point",
            params={'language': 'en', 'place_id': city_id, "sections": 'daily', 'key': MeteoSourceService.API_KEY, 'units': 'metric'}
        )
        if response.status_code != 200:
            print(f"MeteoSourceService:fetch_weather_forecast received {response.status_code} status code")
            try:
                print(response.json())
            except JSONDecodeError:
                print(response.content)
            raise WeatherNotFetchedException()

        weather = response.json()
        daily_weather_forecast = weather["daily"]["data"][:days]

        results = []
        for daily_weather in daily_weather_forecast:
            date = daily_weather["day"].split("-")
            year, month, day = int(date[0]), int(date[1]), int(date[2])

            results.append(
                WeatherResponse(
                    daily_weather["all_day"]["temperature_min"],
                    daily_weather["all_day"]["temperature_max"],
                    daily_weather["all_day"]["temperature"],
                    year,
                    month,
                    day
                )
            )

        return results


class M3OService(WeatherService):

    API_URL = "https://api.m3o.com"
    API_KEY = os.getenv("M3O_API_KEY")
    NAME = "M3O"

    def get_city_id(self, city_name: str):
        return city_name

    def fetch_weather_forecast(self, city_id, days: int) -> List[WeatherResponse]:
        response = requests.post(
            f"{M3OService.API_URL}/v1/weather/Forecast",
            json={'location': city_id, 'days': days},
            headers={'Authorization': f'Bearer {M3OService.API_KEY}'}
        )
        if response.status_code != 200:
            print(f"M3OService:fetch_weather_forecast received {response.status_code} status code")
            try:
                print(response.json())
            except JSONDecodeError:
                print(response.content)
            raise WeatherNotFetchedException()

        weather = response.json()
        daily_weather_forecast = weather["forecast"]

        results = []
        for daily_weather in daily_weather_forecast:
            date = daily_weather["date"].split("-")
            year, month, day = int(date[0]), int(date[1]), int(date[2])

            results.append(
                WeatherResponse(
                    daily_weather["min_temp_c"],
                    daily_weather["max_temp_c"],
                    daily_weather["avg_temp_c"],
                    year,
                    month,
                    day
                )
            )

        return results


@app.route('/', methods=['GET'])
def form_home_page():
    return render_template('form.html')


@app.route('/weather', methods=['GET'])
def submit_form():

    city = request.args.get('city')
    if not city:
        return render_template('form.html', error='City not found')

    days = int(request.args.get('days', 3))
    if not 1 <= days <= 5:
        return render_template('form.html', error='Days amount in wrong range. Should be in 1-5')

    weather_services: List[WeatherService] = [MeteoSourceService(), M3OService()]

    all_weather_responses = defaultdict(lambda: [])
    city_fetch_errors = 0
    weather_fetch_errors = 0
    for service in weather_services:
        try:
            city_id = service.get_city_id(city)
            weather_responses = service.fetch_weather_forecast(city_id, days)
            for response in weather_responses:
                all_weather_responses[f"{response.year}-{response.month}-{response.day}"].append(response)
        except CityNotFoundException:
            city_fetch_errors += 1
        except WeatherNotFetchedException:
            weather_fetch_errors += 1

    weather_forecasts = []
    for date, response_list in all_weather_responses.items():
        responses_amount = len(response_list)

        avg_temperature = sum(map(lambda response: response.temperature, response_list))/responses_amount
        avg_min_temperature = sum(map(lambda response: response.min_temperature, response_list))/responses_amount
        avg_max_temperature = sum(map(lambda response: response.max_temperature, response_list))/responses_amount

        if responses_amount > 1:
            stderr_temperature = ((sum(map(lambda response: (response.temperature-avg_temperature)**2, response_list))/(responses_amount-1))**0.5)/(responses_amount**0.5)
            stderr_min_temperature = ((sum(map(lambda response: (response.min_temperature-avg_min_temperature)**2, response_list))/(responses_amount-1))**0.5)/(responses_amount**0.5)
            stderr_max_temperature = ((sum(map(lambda response: (response.max_temperature-avg_max_temperature)**2, response_list))/(responses_amount-1))**0.5)/(responses_amount**0.5)
        else:
            stderr_temperature = 0
            stderr_min_temperature = 0
            stderr_max_temperature = 0

        weather_forecasts.append(
            WeatherForecast(
                round(avg_min_temperature, 2),
                round(stderr_min_temperature, 2),
                round(avg_max_temperature, 2),
                round(stderr_max_temperature, 2),
                round(avg_temperature, 2),
                round(stderr_temperature, 2),
                responses_amount,
                date
            )
        )

    return render_template(
        'weather.html',
        city=city,
        days=days,
        services_amount=len(weather_services),
        city_fetch_errors=city_fetch_errors,
        weather_fetch_errors=weather_fetch_errors,
        weather_forecasts=weather_forecasts
    )


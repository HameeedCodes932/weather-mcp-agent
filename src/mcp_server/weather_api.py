import asyncio
import httpx

GEOCODING_BASE = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_BASE = "https://api.open-meteo.com/v1/forecast"
TIMEOUT = 10.0
MAX_RETRIES = 2

WMO_CODES: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}

WIND_DIRECTIONS: list[str] = [
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
]


def weather_code_to_description(code: int) -> str:
    return WMO_CODES.get(code, f"Unknown code ({code})")


def wind_direction_to_compass(degrees: float) -> str:
    index = round(degrees / 22.5) % 16
    return WIND_DIRECTIONS[index]


async def geocode_city(city_name: str) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        params = {"name": city_name, "count": 1, "language": "en", "format": "json"}
        for attempt in range(MAX_RETRIES + 1):
            try:
                resp = await client.get(GEOCODING_BASE, params=params)
                resp.raise_for_status()
                data = resp.json()
                results = data.get("results")
                if not results:
                    raise ValueError(
                        f"I couldn't find '{city_name}'. Could you check the spelling?"
                    )
                r = results[0]
                return {
                    "latitude": r["latitude"],
                    "longitude": r["longitude"],
                    "name": r.get("name", city_name),
                    "country": r.get("country", ""),
                }
            except httpx.TimeoutException:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                raise
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500 and attempt < MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                raise ConnectionError(
                    "Weather service is temporarily unavailable. Please try again in a moment."
                )
            except httpx.RequestError:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                raise ConnectionError(
                    "Could not reach the weather service. Check your internet connection."
                )


async def _fetch_forecast(latitude: float, longitude: float, params: dict) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        for attempt in range(MAX_RETRIES + 1):
            try:
                resp = await client.get(FORECAST_BASE, params=params)
                resp.raise_for_status()
                return resp.json()
            except httpx.TimeoutException:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                raise ConnectionError(
                    "Weather service timed out. Please try again in a moment."
                )
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500 and attempt < MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                raise ConnectionError(
                    "Weather service is temporarily unavailable. Please try again."
                )
            except httpx.RequestError:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                raise ConnectionError(
                    "Could not reach the weather service. Check your internet connection."
                )


async def get_weather(latitude: float, longitude: float) -> dict:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,wind_direction_10m",
        "timezone": "auto",
    }
    data = await _fetch_forecast(latitude, longitude, params)
    current = data["current"]
    return {
        "temperature": current["temperature_2m"],
        "humidity": current["relative_humidity_2m"],
        "apparent_temperature": current["apparent_temperature"],
        "precipitation": current["precipitation"],
        "weather_code": current["weather_code"],
        "wind_speed": current["wind_speed_10m"],
        "wind_direction": current["wind_direction_10m"],
        "description": weather_code_to_description(current["weather_code"]),
    }


async def get_weather_by_city(city_name: str) -> dict:
    geo = await geocode_city(city_name)
    weather = await get_weather(geo["latitude"], geo["longitude"])
    weather["city"] = geo["name"]
    weather["country"] = geo["country"]
    return weather


async def get_forecast_by_city(city_name: str, days: int = 3) -> list[dict]:
    geo = await geocode_city(city_name)
    params = {
        "latitude": geo["latitude"],
        "longitude": geo["longitude"],
        "daily": "temperature_2m_max,temperature_2m_min,weather_code,precipitation_sum,wind_speed_10m_max",
        "timezone": "auto",
        "forecast_days": days,
    }
    data = await _fetch_forecast(geo["latitude"], geo["longitude"], params)
    daily = data["daily"]
    forecast = []
    for i in range(len(daily["time"])):
        forecast.append({
            "date": daily["time"][i],
            "temp_max": daily["temperature_2m_max"][i],
            "temp_min": daily["temperature_2m_min"][i],
            "weather_code": daily["weather_code"][i],
            "description": weather_code_to_description(daily["weather_code"][i]),
            "precipitation": daily["precipitation_sum"][i],
            "wind_speed": daily["wind_speed_10m_max"][i],
        })
    return forecast

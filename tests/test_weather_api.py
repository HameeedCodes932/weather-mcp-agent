import pytest
from src.mcp_server.weather_api import (
    geocode_city,
    get_weather,
    get_weather_by_city,
    get_forecast_by_city,
    weather_code_to_description,
    wind_direction_to_compass,
)


@pytest.mark.asyncio
async def test_geocode_london():
    result = await geocode_city("London")
    assert "latitude" in result
    assert "longitude" in result
    assert "name" in result
    assert "country" in result
    assert 51.4 < result["latitude"] < 51.6
    assert -0.2 < result["longitude"] < 0
    assert "London" in result["name"]
    assert "United Kingdom" in result["country"]


@pytest.mark.asyncio
async def test_geocode_lahore():
    result = await geocode_city("Lahore")
    assert 31.4 < result["latitude"] < 31.7
    assert 74.2 < result["longitude"] < 74.5
    assert "Pakistan" in result["country"]


@pytest.mark.asyncio
async def test_geocode_tokyo():
    result = await geocode_city("Tokyo")
    assert 35.5 < result["latitude"] < 35.8
    assert 139.5 < result["longitude"] < 139.9
    assert "Japan" in result["country"]


@pytest.mark.asyncio
async def test_geocode_unknown_city():
    with pytest.raises(ValueError, match="Could you check the spelling"):
        await geocode_city("XyzzyvilleDoesNotExist12345")


@pytest.mark.asyncio
async def test_get_weather_returns_all_fields():
    geo = await geocode_city("London")
    weather = await get_weather(geo["latitude"], geo["longitude"])
    expected = {"temperature", "humidity", "apparent_temperature", "precipitation",
                "weather_code", "wind_speed", "wind_direction", "description"}
    assert expected.issubset(weather.keys())
    assert isinstance(weather["temperature"], (int, float))
    assert isinstance(weather["humidity"], (int, float))
    assert isinstance(weather["wind_speed"], (int, float))


@pytest.mark.asyncio
async def test_get_weather_by_city_includes_city_country():
    result = await get_weather_by_city("Paris")
    assert "city" in result
    assert "country" in result
    assert "Paris" in result["city"]
    assert "France" in result["country"]
    assert "temperature" in result


@pytest.mark.asyncio
async def test_get_forecast_by_city_returns_list():
    forecast = await get_forecast_by_city("Tokyo", days=3)
    assert len(forecast) == 3
    for day in forecast:
        assert "date" in day
        assert "temp_max" in day
        assert "temp_min" in day
        assert "description" in day
        assert "precipitation" in day
        assert "wind_speed" in day
        assert isinstance(day["temp_max"], float)


@pytest.mark.asyncio
async def test_forecast_days_range():
    f1 = await get_forecast_by_city("London", days=1)
    assert len(f1) == 1
    f7 = await get_forecast_by_city("London", days=7)
    assert len(f7) == 7


def test_weather_code_to_description():
    assert weather_code_to_description(0) == "Clear sky"
    assert weather_code_to_description(61) == "Slight rain"
    assert weather_code_to_description(95) == "Thunderstorm"
    assert weather_code_to_description(999) == "Unknown code (999)"


def test_wind_direction_to_compass():
    assert wind_direction_to_compass(0) == "N"
    assert wind_direction_to_compass(90) == "E"
    assert wind_direction_to_compass(180) == "S"
    assert wind_direction_to_compass(270) == "W"
    assert wind_direction_to_compass(45) == "NE"

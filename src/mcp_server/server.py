import logging
import sys

from mcp.server.fastmcp import FastMCP

try:
    from .weather_api import get_weather_by_city, get_forecast_by_city
except ImportError:
    from weather_api import get_weather_by_city, get_forecast_by_city

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger("weather-mcp")

mcp = FastMCP("Weather MCP Server")


@mcp.tool()
async def get_current_weather(city: str) -> str:
    """Get the current weather for a city. Returns temperature, humidity, wind, and conditions.

    Args:
        city: City name (e.g., "Lahore", "London", "Tokyo")
    """
    try:
        data = await get_weather_by_city(city)
        desc = data["description"]
        compass = _wind_deg_to_compass(data["wind_direction"])
        return (
            f"Weather in {data['city']}, {data['country']}: {desc}\n"
            f"Temperature: {data['temperature']}°C (feels like {data['apparent_temperature']}°C)\n"
            f"Humidity: {data['humidity']}%\n"
            f"Wind: {data['wind_speed']} km/h {compass}\n"
            f"Precipitation: {data['precipitation']} mm"
        )
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        logger.exception("Unexpected error fetching weather for %s", city)
        return f"Unexpected error fetching weather for '{city}'"


@mcp.tool()
async def get_weather_forecast(city: str, days: int = 3) -> str:
    """Get weather forecast for a city for the next N days (1-7).

    Args:
        city: City name (e.g., "Lahore", "London", "Tokyo")
        days: Number of forecast days (1-7, default 3)
    """
    days = max(1, min(7, days))
    try:
        forecast = await get_forecast_by_city(city, days)
        lines = [f"Forecast for {forecast[0]['date'][:10]}"]
        for day in forecast:
            lines.append(
                f"{day['date']}: {day['description']}, "
                f"H:{day['temp_max']}°C L:{day['temp_min']}°C, "
                f"Wind:{day['wind_speed']} km/h, Precip:{day['precipitation']}mm"
            )
        return "\n".join(lines)
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        logger.exception("Unexpected error fetching forecast for %s", city)
        return f"Unexpected error fetching forecast for '{city}'"


def _wind_deg_to_compass(deg: float) -> str:
    dirs = [
        "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
    ]
    return dirs[round(deg / 22.5) % 16]


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

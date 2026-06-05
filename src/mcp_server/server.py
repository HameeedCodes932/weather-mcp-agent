import logging
import sys

from mcp.server.fastmcp import FastMCP

try:
    from .weather_api import get_weather_by_city, get_forecast_by_city
    from .file_tools import (
        read_file,
        write_file,
        append_file,
        list_directory,
        delete_file,
        get_file_info,
        search_files,
    )
except ImportError:
    from weather_api import get_weather_by_city, get_forecast_by_city
    from file_tools import (
        read_file,
        write_file,
        append_file,
        list_directory,
        delete_file,
        get_file_info,
        search_files,
    )

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger("weather-mcp")

mcp = FastMCP("Weather + File System MCP Server")


# ── Weather Tools ──

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


# ── File System Tools ──

@mcp.tool()
def read_file_tool(path: str) -> str:
    """Read the contents of a file from the workspace.

    Args:
        path: Relative path to the file from the workspace root (e.g., "notes.txt", "src/main.py")
    """
    return read_file(path)


@mcp.tool()
def write_file_tool(path: str, content: str) -> str:
    """Write content to a file in the workspace. Creates parent directories automatically.

    Args:
        path: Relative path to the file from the workspace root
        content: Text content to write
    """
    return write_file(path, content)


@mcp.tool()
def append_file_tool(path: str, content: str) -> str:
    """Append content to an existing file in the workspace.

    Args:
        path: Relative path to the file from the workspace root
        content: Text content to append
    """
    return append_file(path, content)


@mcp.tool()
def list_directory_tool(path: str = ".") -> str:
    """List all files and directories in a workspace directory.

    Args:
        path: Relative directory path from the workspace root (default: ".")
    """
    return list_directory(path)


@mcp.tool()
def delete_file_tool(path: str) -> str:
    """Delete a file or empty directory from the workspace.

    Args:
        path: Relative path to the file or directory from the workspace root
    """
    return delete_file(path)


@mcp.tool()
def file_info_tool(path: str) -> str:
    """Get metadata (size, type, modified time) of a file or directory.

    Args:
        path: Relative path from the workspace root
    """
    return get_file_info(path)


@mcp.tool()
def search_files_tool(pattern: str) -> str:
    """Search for files matching a glob pattern in the workspace.

    Args:
        pattern: Glob pattern (e.g., "*.txt", "src/**/*.py", "data/*.csv")
    """
    return search_files(pattern)


# ── Helpers ──

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

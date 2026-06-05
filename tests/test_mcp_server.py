import pytest
from src.mcp_server.server import mcp


@pytest.mark.asyncio
async def test_mcp_has_nine_tools():
    tools = await mcp.list_tools()
    assert len(tools) == 9


@pytest.mark.asyncio
async def test_mcp_tool_names():
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert names == {
        "get_current_weather",
        "get_weather_forecast",
        "read_file_tool",
        "write_file_tool",
        "append_file_tool",
        "list_directory_tool",
        "delete_file_tool",
        "file_info_tool",
        "search_files_tool",
    }


@pytest.mark.asyncio
async def test_get_current_weather_tool_signature():
    tools = await mcp.list_tools()
    tool = next(t for t in tools if t.name == "get_current_weather")
    assert tool.description
    assert "city" in tool.inputSchema.get("properties", {})
    assert "city" in tool.inputSchema.get("required", [])


@pytest.mark.asyncio
async def test_get_weather_forecast_tool_signature():
    tools = await mcp.list_tools()
    tool = next(t for t in tools if t.name == "get_weather_forecast")
    assert tool.description
    props = tool.inputSchema.get("properties", {})
    assert "city" in props
    assert "days" in props
    assert "city" in tool.inputSchema.get("required", [])


@pytest.mark.asyncio
async def test_call_get_current_weather_london():
    result = await mcp.call_tool("get_current_weather", {"city": "London"})
    assert result is not None
    text = result[0].text if hasattr(result[0], "text") else str(result)
    assert "London" in text
    assert "United Kingdom" in text or "UK" in text
    assert "°C" in text or "Temperature" in text


@pytest.mark.asyncio
async def test_call_get_current_weather_tokyo():
    result = await mcp.call_tool("get_current_weather", {"city": "Tokyo"})
    text = result[0].text if hasattr(result[0], "text") else str(result)
    assert "Japan" in text or "Tokyo" in text


@pytest.mark.asyncio
async def test_call_get_weather_forecast():
    result = await mcp.call_tool("get_weather_forecast", {"city": "Lahore", "days": 3})
    text = result[0].text if hasattr(result[0], "text") else str(result)
    assert "Forecast" in text
    assert "°C" in text


@pytest.mark.asyncio
async def test_unknown_city_returns_error():
    result = await mcp.call_tool("get_current_weather", {"city": "Xyzzyville"})
    text = result[0].text if hasattr(result[0], "text") else str(result)
    assert "Error" in text or "spelling" in text


@pytest.mark.asyncio
async def test_forecast_clamps_days():
    result = await mcp.call_tool("get_weather_forecast", {"city": "London", "days": 10})
    text = result[0].text if hasattr(result[0], "text") else str(result)
    lines = text.strip().split("\n")
    # 1 header + up to 7 forecast lines
    assert len(lines) <= 8

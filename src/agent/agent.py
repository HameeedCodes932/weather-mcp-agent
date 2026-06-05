import asyncio
import json
import os
import sys
import logging
import time

from groq import Groq, RateLimitError, APIStatusError, APIError
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

from .memory import ConversationMemory

logger = logging.getLogger("weather-agent")

SYSTEM_PROMPT = """You are a friendly and enthusiastic weather assistant! 🌤️

- Detect the user's language and ALWAYS respond in the same language.
- For 'current weather' use get_current_weather. For 'forecast' use get_weather_forecast.
- Use weather emojis: ☀️ Clear, ⛅ Partly cloudy, ☁️ Overcast, 🌧️ Rain, 🌨️ Snow, ⛈️ Thunderstorm, 🌫️ Fog.
- Never make up weather data — always use the tools.
- Include feels-like temperature, humidity, and wind details.
- Keep responses conversational and warm.
- If the user writes in Urdu/Roman Urdu, respond in Roman Urdu. Otherwise respond in English."""

MODEL_NAME = "llama-3.3-70b-versatile"
MAX_RETRIES = 3
MCP_RECONNECT_ATTEMPTS = 2


class WeatherAgent:
    def __init__(self, api_key: str | None = None, server_script: str | None = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError(
                "❌ GROQ_API_KEY is missing. "
                "Set it in a .env file: GROQ_API_KEY=your_key_here\n"
                "Get a free key at: https://console.groq.com/keys"
            )
        self.server_script = server_script or self._find_server_script()
        if not os.path.exists(self.server_script):
            raise FileNotFoundError(
                f"❌ MCP server script not found at: {self.server_script}"
            )
        self.groq_client = Groq(api_key=self.api_key)
        self.memory = ConversationMemory()
        self._mcp_session: ClientSession | None = None
        self._tools = []
        self._openai_tools = []

    @staticmethod
    def _find_server_script() -> str:
        candidates = [
            os.path.join(os.path.dirname(__file__), "..", "mcp_server", "server.py"),
            os.path.join(os.getcwd(), "src", "mcp_server", "server.py"),
        ]
        for path in candidates:
            normalized = os.path.normpath(path)
            if os.path.exists(normalized):
                return normalized
        return os.path.normpath(candidates[0])

    async def _connect_mcp(self) -> bool:
        server_params = StdioServerParameters(
            command=sys.executable,
            args=[self.server_script],
        )
        for attempt in range(MCP_RECONNECT_ATTEMPTS):
            try:
                self._stdio = stdio_client(server_params)
                self._read, self._write = await self._stdio.__aenter__()
                self._mcp_session = await ClientSession(self._read, self._write).__aenter__()
                await self._mcp_session.initialize()
                mcp_tools = (await self._mcp_session.list_tools()).tools
                self._tools = mcp_tools
                self._openai_tools = []
                for t in mcp_tools:
                    schema = dict(t.inputSchema)
                    props = schema.get("properties", {})
                    for pname, pinfo in props.items():
                        if isinstance(pinfo, dict) and pinfo.get("type") == "integer":
                            pinfo["type"] = "string"
                    self._openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": t.name,
                            "description": t.description or "",
                            "parameters": schema,
                        },
                    })
                logger.info("MCP connected with %d tools", len(mcp_tools))
                return True
            except Exception as e:
                logger.warning("MCP connection attempt %d failed: %s", attempt + 1, e)
                await self._close_mcp()
                if attempt < MCP_RECONNECT_ATTEMPTS - 1:
                    await asyncio.sleep(1)
        return False

    async def _close_mcp(self):
        if self._mcp_session:
            try:
                await self._mcp_session.__aexit__(None, None, None)
            except Exception:
                pass
            self._mcp_session = None
        if hasattr(self, "_stdio"):
            try:
                await self._stdio.__aexit__(None, None, None)
            except Exception:
                pass

    async def __aenter__(self):
        ok = await self._connect_mcp()
        if not ok:
            raise ConnectionError(
                "❌ Could not connect to the MCP weather server. "
                "Try restarting the application."
            )
        return self

    async def __aexit__(self, *args):
        await self._close_mcp()

    def _build_messages(self, session_id: str, user_message: str) -> list[dict]:
        history = self.memory.get_history(session_id, max_messages=10)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in history:
            if msg["role"] in ("user", "assistant"):
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })
        messages.append({"role": "user", "content": user_message})
        return messages

    async def chat(self, session_id: str, message: str) -> str:
        messages = self._build_messages(session_id, message)
        final_text = await self._tool_calling_loop(messages)
        self.memory.save_message(session_id, "user", message)
        self.memory.save_message(session_id, "assistant", final_text)
        return final_text

    async def _tool_calling_loop(self, messages: list[dict]) -> str:
        for iteration in range(5):
            response = await self._call_groq_with_retry(messages)
            if response is None:
                return "I'm having trouble connecting to the AI service. Please try again."

            choice = response.choices[0]
            msg = choice.message

            if msg.content:
                return msg.content

            if msg.tool_calls:
                messages.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                })
                for tc in msg.tool_calls:
                    args = json.loads(tc.function.arguments)
                    self._coerce_tool_args(tc.function.name, args)
                    try:
                        tool_result = await self._execute_tool(tc.function.name, args)
                    except Exception as e:
                        tool_result = f"Error: {e}"
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": tool_result,
                    })
                continue

            return "I didn't quite understand that. Could you rephrase?"

        return "I've reached the limit of follow-up questions. Let me know if you need anything else!"

    async def _call_groq_with_retry(self, messages: list[dict]):
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                return self.groq_client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=messages,
                    tools=self._openai_tools if self._openai_tools else None,
                    tool_choice="auto",
                )
            except RateLimitError as e:
                last_error = e
                wait = 2 ** (attempt + 1)
                logger.warning("Rate limited. Retrying in %ds (attempt %d/%d)", wait, attempt + 1, MAX_RETRIES)
                await asyncio.sleep(wait)
            except APIStatusError as e:
                if e.status_code >= 500 and attempt < MAX_RETRIES - 1:
                    last_error = e
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise
            except APIError as e:
                if "invalid_api_key" in str(e).lower() or "auth" in str(e).lower():
                    raise ValueError(
                        "❌ Invalid GROQ_API_KEY. Check your key at: https://console.groq.com/keys"
                    ) from e
                raise
        logger.error("All Groq API retries exhausted: %s", last_error)
        return None

    def _coerce_tool_args(self, tool_name: str, args: dict) -> None:
        for tool in self._tools:
            if tool.name != tool_name:
                continue
            for prop_name, prop_schema in tool.inputSchema.get("properties", {}).items():
                if prop_name not in args:
                    continue
                expected = prop_schema.get("type")
                val = args[prop_name]
                if expected == "integer" and isinstance(val, str):
                    try:
                        args[prop_name] = int(val)
                    except (ValueError, TypeError):
                        pass
                elif expected == "number" and isinstance(val, str):
                    try:
                        args[prop_name] = float(val)
                    except (ValueError, TypeError):
                        pass
            return

    async def _execute_tool(self, tool_name: str, args: dict) -> str:
        try:
            result = await self._mcp_session.call_tool(tool_name, args)
            text_parts = [c.text for c in result.content if hasattr(c, "text") and c.text]
            return "\n".join(text_parts) if text_parts else str(result.content)
        except Exception as e:
            # Try reconnecting once
            logger.warning("MCP call failed, attempting reconnect: %s", e)
            await self._close_mcp()
            ok = await self._connect_mcp()
            if ok:
                result = await self._mcp_session.call_tool(tool_name, args)
                text_parts = [c.text for c in result.content if hasattr(c, "text") and c.text]
                return "\n".join(text_parts) if text_parts else str(result.content)
            raise ConnectionError(
                "The weather service is not responding. Please restart the application."
            ) from e

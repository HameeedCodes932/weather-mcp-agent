# 🌦️ Weather MCP Server + AI Agent

**A complete MCP-based AI agent with weather and file system capabilities, built from scratch.**

## 📋 What We Built

```
┌─────────────────────────────────────────────────────┐
│                    USER INTERFACES                   │
│  ┌─────────────────┐       ┌──────────────────┐     │
│  │   Rich CLI       │       │  Streamlit Web   │     │
│  │  (terminal)      │       │  (browser)       │     │
│  └────────┬─────────┘       └────────┬─────────┘     │
│           │                          │               │
│           └──────────┬───────────────┘               │
│                      ▼                               │
│  ┌─────────────────────────────────────────────────┐ │
│  │              AI AGENT (agent.py)                 │ │
│  │  • Groq Llama 3.3-70B LLM                       │ │
│  │  • MCP Client (stdio transport)                 │ │
│  │  • Tool calling loop (auto-retry, coerce args)  │ │
│  │  • Conversation memory (JSON files)             │ │
│  └────────────────────┬────────────────────────────┘ │
│                       │ MCP protocol (stdio)         │
│  ┌────────────────────▼────────────────────────────┐ │
│  │              MCP SERVER (server.py)              │ │
│  │  FastMCP — 9 tools total                        │ │
│  │                                                   │ │
│  │  🌦️ WEATHER (weather_api.py)                     │ │
│  │  ├─ get_current_weather                           │ │
│  │  └─ get_weather_forecast                          │ │
│  │                                                   │ │
│  │  📁 FILE SYSTEM (file_tools.py)                   │ │
│  │  ├─ read_file_tool                                │ │
│  │  ├─ write_file_tool                               │ │
│  │  ├─ append_file_tool                              │ │
│  │  ├─ list_directory_tool                           │ │
│  │  ├─ delete_file_tool                              │ │
│  │  ├─ file_info_tool                                │ │
│  │  └─ search_files_tool                             │ │
│  └────────────────────┬────────────────────────────┘ │
│                       │                               │
│  ┌────────────────────▼────────────────────────────┐ │
│  │         EXTERNAL SERVICES                        │ │
│  │  • Open-Meteo API (free, no key needed)          │ │
│  │  • Groq API (free tier, needs key)               │ │
│  └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

---

## 🛠️ Technologies Used

| Technology | Purpose | Why |
|-----------|---------|-----|
| **Python 3.10+** | Language | Reliable, async support, huge ecosystem |
| **uv** | Package manager | 10x faster than pip, lockfile support |
| **FastMCP** (from `mcp` SDK) | MCP server framework | Simplifies building MCP tools massively |
| **Groq** (`llama-3.3-70b-versatile`) | LLM | 270 tok/s, free tier, better than Gemini free |
| **Open-Meteo API** | Weather data | Free forever, no API key, accurate |
| **Rich** | CLI UI | Beautiful terminal formatting, panels, spinners |
| **Streamlit** | Web UI | Fastest way to build Python web apps |
| **pytest** | Testing | Standard Python testing framework |
| **MCP Protocol** (stdio) | Agent↔Server IPC | Standardized tool calling, decoupled architecture |

---

## 🔧 Build Walkthrough (Phase-by-Phase)

### Phase 1: Project Foundation

**What we did:**
- Created project structure with `src/`, `tests/`, `pyproject.toml`
- Set up `uv` virtual environment
- Installed dependencies: `mcp`, `groq`, `httpx`, `rich`, `streamlit`, `python-dotenv`, `pytest`

**Key files created:**
- `pyproject.toml` — Python project config with dependencies, build system
- `.env.example` — Template for `GROQ_API_KEY`
- `.gitignore` — Ignores `.env`, `memory/`, `.venv`, `__pycache__`
- `LICENSE` — MIT

### Phase 2: Weather API Client

**File:** `src/mcp_server/weather_api.py`

**What we built:**
- **Geocoding** — Convert city names to lat/lon using Open-Meteo's geocoding API
  - Handles unknown cities gracefully ("City 'Foobar' not found")
- **Current weather** — Fetch temperature, humidity, wind, precipitation
- **Forecast** — Fetch N-day forecast (1-7 days)
- **WMO weather codes** — Convert numeric codes to human-readable descriptions (0=Clear, 61=Slight rain, etc.)
- **Wind direction** — Degrees → compass direction (N, NNE, NE...)
- **Error handling** — 10s HTTP timeout, retry on failure

**Key decisions:**
- Open-Meteo is free with no API key — ideal for open source
- Used `httpx.AsyncClient` for async HTTP

### Phase 3: MCP Server

**File:** `src/mcp_server/server.py`

**What we built:**
- FastMCP server named "Weather MCP Server"
- Registered 2 weather tools as `@mcp.tool()`:
  - `get_current_weather(city: str)` — Real-time weather
  - `get_weather_forecast(city: str, days: int=3)` — N-day forecast
- Server runs on **stdio transport** (not HTTP) — talks to agent via stdin/stdout
- Later extended with 7 file system tools:
  - `read_file_tool`, `write_file_tool`, `append_file_tool`
  - `list_directory_tool`, `delete_file_tool`
  - `file_info_tool`, `search_files_tool`
- File tools are **sandboxed** — all paths resolved to `os.getcwd()` base directory

**Why MCP?**
- Standard protocol for AI tool calling
- Separes tool implementation from agent logic
- Can be used with ANY MCP-compatible client, not just ours

### Phase 4: File System Tools

**File:** `src/mcp_server/file_tools.py`

**What we built:**
7 functions, each sandboxed to the workspace directory:

| Function | What it does | Security |
|----------|-------------|----------|
| `read_file` | Read any text file | Resolves to base dir |
| `write_file` | Create/overwrite files, creates parent dirs | Resolves to base dir |
| `append_file` | Append to existing files | Checks file exists |
| `list_directory` | List files/dirs, show type + size | Handles empty dirs |
| `delete_file` | Delete files or empty directories | Won't delete base dir |
| `get_file_info` | Size, type, modified time | Read-only |
| `search_files` | Glob pattern matching (e.g., `*.txt`, `**/*.py`) | Limited to workspace |

### Phase 5: AI Agent

**File:** `src/agent/agent.py`

**What we built:**
- **MCP Client** — Connects to MCP server via stdio subprocess
  - `StdioServerParameters(sys.executable, [server_script])`
  - Spawns MCP server as a child process
  - Auto-reconnects if server crashes
- **Groq LLM** — Calls `llama-3.3-70b-versatile` (fast, 270 tok/s)
  - `tool_choice="auto"` — model decides when to call tools
  - Exponential backoff for rate limits (2s → 4s → 8s)
  - Parses "try again in XmYs" from rate limit errors
- **Tool calling loop** — Up to 5 iterations:
  1. Call Groq with conversation + tool definitions
  2. If Groq returns text → done, return it
  3. If Groq returns tool calls → execute each via MCP
  4. Feed results back to Groq for final response
  5. If Groq rejects a tool call (400 `tool_use_failed`) → retry without tools
- **Schema coercion** — Converts string → int/float for tool params
- **System prompt** — Tells the model about all 9 tools, language detection, emoji usage

### Phase 6: Conversation Memory

**File:** `src/agent/memory.py`

**What we built:**
- JSON file-based storage in `memory/` directory
- Each session gets its own JSON file
- Methods: `save_message`, `get_history`, `clear_session`, `list_sessions`
- Automatically timestamps all messages
- Limits history to last N messages (10 by default)
- Thread-safe via per-file locking (simple append + rewrite)

**Why JSON, not a database?**
- Zero setup — no SQLite, no PostgreSQL
- Portable — just delete the `memory/` folder
- Easy to inspect with any text editor
- Sufficient for single-user/small-scale use

### Phase 7: CLI Interface

**File:** `src/cli/main.py`

**What we built:**
- Rich-powered terminal chatbot
- Features:
  - `/quit` — Exit
  - `/clear` — Reset conversation
  - `/history` — Show past messages
  - Colored panels (blue for user, green for assistant)
  - Spinner while waiting for AI response
  - Custom app title + commands bar
- Creates one `WeatherAgent` for the session lifetime
- Error messages displayed gracefully (not stack traces)

**Why Rich?**
- Prettier than standard `print()` and `input()`
- Built-in panels, spinners, colors — no extra UI framework needed

### Phase 8: Web Interface

**File:** `src/web/app.py`

**What we built:**
- Streamlit single-page app
- Sidebar with session management:
  - "New Session" button
  - Session history list
  - Clear session button
- Chat message display (user + assistant)
- Loading spinner during AI response
- **Critical design choice**: Fresh agent per interaction
  - Why? Streamlit's `@st.cache_resource` + async MCP causes "cancel scope in different task" crash
  - Each query creates → connects → responds → closes the agent

### Phase 9: Testing

**Files:** `tests/test_weather_api.py`, `tests/test_mcp_server.py`, `tests/test_memory.py`

**What we tested:**
- **29 tests total**, all passing
- **Weather API** (10 tests) — Geocoding, error handling, field validation, forecast range
- **MCP Server** (9 tests) — Tool count, names, signatures, real API calls, edge cases
- **Memory** (10 tests) — CRUD operations, persistence, isolation, special characters
- Tests hit real Open-Meteo API (no mocking — real data is more reliable)

### Phase 10: Error Handling & Reliability

**What we added:**
- **10s HTTP timeout** on all weather API calls
- **Retry with backoff** for Groq rate limits (429)
- **Parsed retry-after** from Groq error messages (handles "9m24s" waits)
- **Tool call failure recovery** — retry without tools if Groq rejects the format
- **MCP reconnection** — if tool execution fails, reconnect once automatically
- **Schema validation** — coerce string → int/float for tool parameters
- **Startup validation** — checks `.env`, API key, server script exist

---

## 📊 Data Flow (Request → Response)

```
You: "Lahore ka mausam batao"
  │
  ├─ 1. CLI/Web receives input
  ├─ 2. Agent builds messages: [system prompt + history + user message]
  ├─ 3. Agent calls Groq API with tool definitions
  │
  ├─ [Groq decides to call get_current_weather(Lahore)]
  │     │
  │     ├─ 4. Agent executes tool via MCP client → MCP server (stdio)
  │     ├─ 5. MCP server calls weather_api.get_weather_by_city("Lahore")
  │     ├─ 6. weather_api geocodes "Lahore" → 31.5497°N, 74.3436°E
  │     ├─ 7. weather_api calls Open-Meteo API → JSON response
  │     ├─ 8. MCP server formats: "33°C, clear, humidity 39%..."
  │     └─ 9. Tool result returned to Agent
  │
  ├─ [Groq receives tool result, generates final response]
  │
  ├─ 10. Agent returns: "Lahore ka mosam aaj bilkul saaf hai..."
  ├─ 11. Message saved to memory/ (JSON)
  └─ 12. Displayed in CLI/Web UI
```

---

## 🎮 How to Use

### 1. Setup
```bash
# Already done — you have .env with GROQ_API_KEY

# Install (if starting fresh)
uv sync
```

### 2. Run
```bash
# Terminal chatbot
.venv\Scripts\python -m src.cli.main

# OR web UI
.venv\Scripts\streamlit run src\web\app.py
```

### 3. Chat examples
```
# Weather queries (any language)
"What's the weather in Tokyo?"
"Lahore ka mausam kya hai?"
"3 din ka forecast batao London ka"

# File operations
"Create a file called notes.txt with content 'Milk, Eggs, Bread'"
"Read notes.txt"
"List all .py files"
"Append 'Butter' to notes.txt"
"Delete old_backup.txt"

# Combined
"Read cities.txt, then check weather for each city"
"Create a todo.txt with 5 tasks, then show me the file"

# Casual chat (no tools needed)
"Tell me a joke"
"What can you do?"
```

### 4. CLI Commands
| Command | Action |
|---------|--------|
| `/quit` | Exit |
| `/clear` | Reset conversation |
| `/history` | Show past messages |

---

## 🧪 Run Tests
```bash
.venv\Scripts\python -m pytest tests/ -v
```

---

## 🔮 Possible Extensions

- **Weather alerts** — Check for extreme weather and send notifications
- **CSV/JSON parsers** — File tools that parse structured data
- **Web scraping tool** — Fetch and summarize web pages
- **Clipboard integration** — Read/write system clipboard
- **Image generation** — DALL-E/Stable Diffusion via Groq
- **Database tools** — SQLite read/write queries
- **Email tools** — Send emails via SMTP
- **Git tools** — Commit, push, check status
- **Multi-agent** — Specialized sub-agents for different domains

---

## 📄 License
MIT

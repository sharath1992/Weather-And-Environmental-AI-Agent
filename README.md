# Weather & Environmental Reporting Agent

An autonomous AI agent built with Claude and the free Open-Meteo APIs. Give it a city name and it plans its own steps: it finds the coordinates, pulls the weather forecast, air quality, and marine data, writes a styled HTML dashboard, and saves the report to disk.

The project is a hands-on example of the ReAct (Reason + Act) pattern, tool use with the Claude API, and agent orchestration in plain Python, with no agent framework.

## Agent Workflow

!workflow.png


## Features

- **Autonomous planning.** Claude decides which tools to call, in what order, and when it has enough data to finish.
- **Five tools.** Geocoding, weather forecast, air quality, marine conditions, and saving the HTML file.
- **Graceful adaptation.** Inland cities have no marine data, so the agent notices this and leaves that section out instead of failing.
- **Layered error handling.** Tool failures, network errors, and API rate limits are caught and handled without crashing the agent.
- **Retries with exponential backoff.** Temporary Claude API errors are retried automatically (2s → 4s → 8s).
- **Safety limits.** An iteration cap stops runaway loops, and filename sanitization prevents path traversal.
- **Visible reasoning.** Claude's thinking between tool calls is printed to the console.

## How It Works

### Orchestration

The agent has three parts, and each has a clear job:


**Python (`run_weather_agent`)** - Orchestrator - Runs the loop, calls the Claude API, executes tools, stores the conversation history, and enforces the safety limits. 
**Claude (`claude-sonnet-4-6`)** - Decision maker - Reads the conversation, decides which tool to call next and with what arguments, interprets the results, and writes the HTML report.
**Tools + Open-Meteo APIs** - Workers - Fetch real data or write the file, and return results as dictionaries or strings.

The key idea is that **Claude never runs code itself.** It only *asks* for a tool by returning a `tool_use` block, such as "call `get_coordinates` with `{"city": "Chicago"}`". The Python orchestrator looks up the function in `TOOL_MAP`, runs it, and sends the result back.

Pieces that connect Claude's requests to real Python functions:

1. **`tools_schema`**: the "menu" sent to Claude. It lists each tool's name, a plain-English description, and its input parameters as JSON Schema. Claude uses the descriptions to decide which tool fits the task.
2. **`TOOL_MAP`**: It maps each tool name to its function.

`TOOL_MAP[block.name](**block.input)` runs the requested function, with `**` unpacking Claude's input dictionary into named arguments.

A **system prompt** gives Claude its role and a suggested plan (get coordinates, fetch data, adapt to missing data, build the HTML, save it). Claude still makes every individual decision itself, which is what makes the agent autonomous rather than a fixed script.

### The ReAct Loop

Instead of answering in one shot, the agent works in a cycle:

1. **Reason.** Claude reviews everything so far and decides what it needs next.
2. **Act.** Claude requests a tool call, and Python executes it.
3. **Observe.** The tool's result is added to the conversation.
4. **Repeat** until Claude has enough to finish the task.

In code, the loop is driven by the response's `stop_reason`:

`"tool_use"`: Claude wants one or more tools run. Execute them, append the results, loop again.
`"end_turn"`: Claude has finished the task. Stop the loop.

A typical run for a coastal city looks like this:

```
2026-09-25 21:59:12,204 [INFO] ---- Starting Agent Session for 'Chicago' ----
2026-09-25 21:59:12,205 [INFO] Turn 1/10
2026-09-25 21:59:15,036 [INFO] HTTP Request: POST https://api.anthropic.com/v1/messages "HTTP/1.1 200 OK"

[Claude]: Sure! Let's kick things off. The first step is to get Chicago's coordinates, and then I'll fetch all relevant data in parallel!

**Step 1: Getting coordinates for Chicago...**
2026-09-25 21:59:15,095 [INFO] Executing tool 'get_coordinates' with args: {'city': 'Chicago'}
2026-09-25 21:59:15,860 [INFO] Turn 2/10
2026-09-25 21:59:19,273 [INFO] HTTP Request: POST https://api.anthropic.com/v1/messages "HTTP/1.1 200 OK"

[Claude]: Got it! Chicago is at **41.85°N, 87.65°W**. Now let's fire all three data requests simultaneously!

**Step 2: Fetching weather forecast, air quality, and marine data in parallel...**
2026-09-25 21:59:19,278 [INFO] Executing tool 'get_weather_forecast' with args: {'latitude': 41.85003, 'longitude': -87.65005}
2026-09-25 21:59:19,506 [INFO] Executing tool 'get_air_quality' with args: {'latitude': 41.85003, 'longitude': -87.65005}
2026-09-25 21:59:20,466 [INFO] Executing tool 'get_marine_weather' with args: {'latitude': 41.85003, 'longitude': -87.65005}
2026-09-25 21:59:21,285 [INFO] Turn 3/10
2026-09-25 22:01:21,814 [INFO] HTTP Request: POST https://api.anthropic.com/v1/messages "HTTP/1.1 200 OK"

[Claude]: Excellent! All three data sources returned successfully — including marine data for Lake Michigan! Now let me compile everything into a beautiful, responsive HTML dashboard.

**Step 3: Building and saving the HTML report...**
2026-09-25 22:01:21,819 [INFO] Executing tool 'save_html_report' with args: {'filename': 'chicago_weather_report.html', 'html_content': '<!DOCTYPE html>\n<html lang="en">\n<head>\n  <meta charset="UTF-8" />\n  <meta name="viewport" content="...'}
2026-09-25 22:01:21,823 [INFO] Turn 4/10
2026-09-25 22:01:38,915 [INFO] HTTP Request: POST https://api.anthropic.com/v1/messages "HTTP/1.1 200 OK"

[Claude]: The report has been successfully generated and saved! 🎉 Here's a complete summary of everything that was compiled:

---

## ✅ Chicago Weather & Environmental Report — Summary

### 📍 Location
**Chicago, IL** · 41.85°N, 87.65°W · Elevation: 178m · Timezone: CDT (GMT−5)

---

### ⚡ Current Conditions (Sep 25, 21:45 CDT)
| Metric | Value |
|---|---|
| Temperature | **13.3°C (55.9°F)** |
| Sky Condition | ☀️ Clear |
| Humidity | 71% |
| US AQI | 51 (Moderate) |
| Wave Height | 0.22 m (Calm) |

---

### 📅 3-Day Forecast
| Date | High / Low | Condition | Rain Prob. | Max Wind |
|---|---|---|---|---|
| Sep 26 (Sat) | 16.9°C / 12.1°C | ☀️ Clear | 0% | 16.9 km/h |
| Sep 27 (Sun) | 19.0°C / 9.4°C | 🌤️ Mostly Clear | 0% | 11.0 km/h |
| Sep 28 (Mon) | 20.6°C / 14.6°C | ⛅ Partly Cloudy | 0% | 12.0 km/h |

> ⚠️ **Extended Outlook:** Rain arrives Sep 29–Oct 1 with up to 13mm and 51% precipitation probability.

---

### 🌬️ Air Quality (US AQI: 51 — Moderate)
- **PM2.5:** 9.3 μg/m³ | **PM10:** 9.3 μg/m³
- **CO:** 232 μg/m³ | **NO₂:** 31.2 μg/m³ | **O₃:** 57.0 μg/m³
- Sensitive groups should limit prolonged outdoor exertion.

---

### 🌊 Lake Michigan Marine Conditions
- **Wave Height:** 0.22 m (Very Calm) | **Direction:** 69° ENE | **Period:** 2.5 s
- ⛵ **Boating Conditions: Favorable** — ideal for kayaking and paddleboarding.

---

### 💡 Key Actionable Insights
1. ✅ **Use the Sep 26–28 window** — zero rain, mild temps, perfect for outdoor/lakefront activities.
2. 😷 **Sensitive groups** should moderate outdoor time due to Moderate AQI (51) and ozone levels.
3. 🌊 **Lake Michigan is calm** — excellent for water sports and recreational boating.
4. 🧥 **Layer up in mornings** — lows dip to 9.4°C on Sunday; afternoon conditions are comfortable.
5. 🌧️ **Prepare for rain from Sep 29** — heavy precipitation (13mm) expected by Oct 1.
6. 💨 **Wind advisory for cyclists** — gusts to 16.9 km/h tomorrow along exposed lakefront areas.

---

📁 **File saved:** `chicago_weather_report.html` — Open in any browser to view the fully styled, responsive dashboard!
2026-09-25 22:01:38,923 [INFO] Agent signaled task completion
```

For an inland city like Raleigh, `get_marine_weather` returns a `notice` instead of wave data, and Claude adapts by leaving the marine section out of the report.

```
2026-09-25 22:05:05,565 [INFO] ---- Starting Agent Session for 'Raleigh' ----
2026-09-25 22:05:05,567 [INFO] Turn 1/10
2026-09-25 22:05:08,231 [INFO] HTTP Request: POST https://api.anthropic.com/v1/messages "HTTP/1.1 200 OK"

[Claude]: Sure! Let's kick things off. First, I need to get the coordinates for Raleigh before I can fetch weather, air quality, and marine data. Let me do that now!

**Step 1: Getting coordinates for Raleigh...**
2026-09-25 22:05:08,294 [INFO] Executing tool 'get_coordinates' with args: {'city': 'Raleigh'}
2026-09-25 22:05:09,057 [INFO] Turn 2/10
2026-09-25 22:05:12,530 [INFO] HTTP Request: POST https://api.anthropic.com/v1/messages "HTTP/1.1 200 OK"

[Claude]: Got the coordinates for Raleigh (35.7721, -78.6386)! Now let me simultaneously fetch the weather forecast, air quality, and marine data in parallel!

**Step 2: Fetching weather forecast, air quality, and marine data in parallel...**
2026-09-25 22:05:12,544 [INFO] Executing tool 'get_weather_forecast' with args: {'latitude': 35.7721, 'longitude': -78.63861}
2026-09-25 22:05:12,779 [INFO] Executing tool 'get_air_quality' with args: {'latitude': 35.7721, 'longitude': -78.63861}
2026-09-25 22:05:13,661 [INFO] Executing tool 'get_marine_weather' with args: {'latitude': 35.7721, 'longitude': -78.63861}
2026-09-25 22:05:14,399 [INFO] Turn 3/10
2026-09-25 22:06:55,795 [INFO] HTTP Request: POST https://api.anthropic.com/v1/messages "HTTP/1.1 200 OK"

[Claude]: All data retrieved! Marine data is unavailable (Raleigh is an inland city — as expected!). I'll gracefully omit that section. Now let me compile everything into a beautiful, responsive HTML dashboard and save it!

**Step 3: Generating and saving the HTML report...**
2026-09-25 22:06:55,805 [INFO] Executing tool 'save_html_report' with args: {'filename': 'raleigh_weather_report.html', 'html_content': '<!DOCTYPE html>\n<html lang="en">\n<head>\n  <meta charset="UTF-8" />\n  <meta name="viewport" content="...'}
2026-09-25 22:06:55,807 [INFO] Turn 4/10
2026-09-25 22:07:07,992 [INFO] HTTP Request: POST https://api.anthropic.com/v1/messages "HTTP/1.1 200 OK"

[Claude]: The report has been successfully generated and saved! 🎉 Here's a complete summary of everything that was collected and included:

---

## ✅ Raleigh Environmental Report — Complete

### 📍 Location
**Raleigh, North Carolina** | 35.7721°N, 78.6386°W | Timezone: America/New_York

---

### 🌤️ 3-Day Weather Forecast

| Day | High | Low | Rain | Wind | Precip |
|-----|------|-----|------|------|--------|
| **Fri, Sep 26** | 26.2°C (79°F) | 11.4°C (52°F) | 0% | 22.0 km/h | 0.0 mm |
| **Sat, Sep 27** | 26.7°C (80°F) | 12.7°C (55°F) | 4% | 18.9 km/h | 0.0 mm |
| **Sun, Sep 28** | 27.5°C (82°F) | 16.6°C (62°F) | 0% | 13.7 km/h | 0.0 mm |

A **clear, rain-free, and warming weekend** is in store for Raleigh!

---

### 🍃 Air Quality (Current)
- **US AQI: 38 — ✅ Good**
- PM2.5: 3.3 μg/m³ | PM10: 3.5 μg/m³
- CO: 154.0 μg/m³ | NO₂: 4.3 μg/m³ | Ozone: 70.0 μg/m³
- No air quality concerns for any population group

---

### 🌊 Marine Data
- **Not applicable** — Raleigh is an inland city ~170 miles from the Atlantic coast. The section was gracefully omitted with a helpful note directing users to nearby coastal cities like Wilmington, NC.

---

### 💡 Key Actionable Insights
1. 🏃 **Perfect for outdoor activities** — zero rain across all 3 days
2. 🌡️ **Warming trend** — nights getting warmer through Sunday
3. 🌬️ **Breezy Friday** — winds up to 22 km/h, calming by Sunday
4. 🍃 **Clean air** — AQI 38, no health restrictions
5. ☀️ **Use sunscreen** during midday outdoor hours
6. 💧 **Stay hydrated** — dry air + warm temps + no rain

---

📁 **File saved as:** `raleigh_weather_report.html` — open it in any browser for the fully styled, responsive dashboard!
2026-09-25 22:07:07,995 [INFO] Agent signaled task completion
```

### State Management

**Claude has no memory between API calls.** Each call to `client.messages.create` starts fresh. The agent "remembers" earlier steps only because the orchestrator resends the entire conversation every turn.

That makes the `messages` list the agent's memory. After a few turns it looks like this:

```python
[
    {"role": "user",      "content": "Generate a detailed weather ... report for Chicago ..."},
    {"role": "assistant", "content": [text, tool_use: get_coordinates]},
    {"role": "user",      "content": [tool_result: {"latitude": 41.85, ...}]},
    {"role": "assistant", "content": [tool_use: get_weather_forecast, tool_use: get_air_quality, ...]},
    {"role": "user",      "content": [tool_result, tool_result, tool_result]},
    ...
]
```

### Tools

`get_coordinates(city)`: [Open-Meteo Geocoding API](https://open-meteo.com/en/docs/geocoding-api) 
`get_weather_forecast(latitude, longitude)`: [Open-Meteo Forecast API](https://open-meteo.com/en/docs) 
`get_air_quality(latitude, longitude)`: [Open-Meteo Air Quality API](https://open-meteo.com/en/docs/air-quality-api)
`get_marine_weather(latitude, longitude)`: [Open-Meteo Marine API](https://open-meteo.com/en/docs/marine-weather-api)
`save_html_report(filename, html_content)`: HTML report

### Error Handling

Errors are handled in layers so that one failure doesn't stop the whole agent:

**API requests** (`api_request`): Timeouts, HTTP errors, network failures, bad JSON. Returned as `{"error": "..."}` instead of raised, so Claude can read the problem and adapt
**Claude API** (`call_claude`): Rate limits (429), server errors (5xx), connection issues. Retried with exponential backoff (2s → 4s → 8s). Client errors (4xx, e.g. a bad API key) fail fast.

## Built With

- [Anthropic Claude API](https://docs.claude.com/) with tool use
- [Open-Meteo](https://open-meteo.com/) free weather APIs
- Python

# ------------------------------------------------------------------------------------------------
"""
        Weather & Environmental Reporting Agent: An AI agent that uses Claude and the free 
        Open-Meteo APIs to build a 3-day weather, air quality, and marine report for a city,
        saved as an HTML file.
"""
# -------------------------------------------------------------------------------------------------


# Import libraries

import json
import logging
import os
import sys
import time
from typing import Any, Dict
import anthropic
import requests
from dotenv import load_dotenv


# Logging

logging.basicConfig(


    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# -------------------------------------------------
#   TOOL DEFINITIONS
# -------------------------------------------------

# Making an API request (with error handling)

def api_request(url: str, timeout: int = 10) -> Dict[str, Any]:

    # Errors are returned as dictionaries instead of being raised to keep the agent from crashing 
    # and let Claude read what went wrong and adapt

    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.Timeout:
        return {"error": f"Request timed out after {timeout} seconds!"}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP Error {response.status_code}: {str(e)}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Network Request Failed: {str(e)}"}
    except json.JSONDecodeError:
        return {"error": "Failed to parse API JSON response!"}


# Get coordinates using the open-meteo Geocoding API

def get_coordinates(city: str) -> Dict[str, Any]:

    if not city or not city.strip():
        return {"ERROR": "City name cannot be empty!"}

    # Geocoding API that resolves city and place names to WGS84 coordinates, country, timezone, and elevation.

    url = f"https://geocoding-api.open-meteo.com/v1/search?name={city.strip()}&count=10&language=en&format=json"

    """
        Example output (Illustrative Format from open-meteo):
        
        {
        "results": [
            {
                "id": 2950159,
                "name": "Berlin",
                "latitude": 52.52437,
                "longitude": 13.41053,
                "elevation": 74.0,
                "feature_code": "PPLC",
                "country_code": "DE",
                "admin1_id": 2950157,
                "admin2_id": 0,
                "admin3_id": 6547383,
                "admin4_id": 6547539,
                "timezone": "Europe/Berlin",
                "population": 3426354,
                "postcodes": [
                    "10967",
                    "13347"
                ],
                "country_id": 2921044,
                "country": "Deutschland",
                "admin1": "Berlin",
                "admin2": "",
                "admin3": "Berlin, Stadt",
                "admin4": "Berlin"
            },
    
            {
            ...
            }
            ]
        }
        """

    data = api_request(url)

    # check whether the returned data has a key called "error"

    if "error" in data:
        return data

    if not data.get("results"):
        return {"error": f"City '{city}' was not found. Check spelling!"}

    try:
        result = data["results"][0]  # The API returns up to 10 matches ranked by relevance - take the first one

        return {
            "city": result["name"],
            "country": result.get("country", ""),
            "latitude": result["latitude"],
            "longitude": result["longitude"],
            "timezone": result.get("timezone", "UTC")
        }

    except (KeyError, IndexError) as e:
        return {"error": f"Failed to parse geocoding result schema: {str(e)}"}


# Get weather forecast using the open-meteo Weather Forecast API

def get_weather_forecast(latitude: float, longitude: float) -> Dict[str, Any]:

    # Hourly and daily weather forecasts for any global location

    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}"
        "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max"
        "&current=temperature_2m,relative_humidity_2m,weather_code"
        "&timezone=auto"
    )

    """
    Example output (Illustrative Format from open-meteo):

    {
    "latitude": 52.52,
    "longitude": 13.419,
    "elevation": 44.812,
    "generationtime_ms": 2.2119,
    "utc_offset_seconds": 0,
    "timezone": "Europe/Berlin",
    "timezone_abbreviation": "CEST",
    "hourly": {
        "time": ["2022-07-01T00:00", "2022-07-01T01:00", "2022-07-01T02:00", ...],
        "temperature_2m": [13, 12.7, 12.7, 12.5, 12.5, 12.8, 13, 12.9, 13.3, ...]
    },
    "hourly_units": {
        "temperature_2m": "°C"
        }
    }
    """

    return api_request(url)

# Get Air Quality data using the open-meteo Air Quality API

def get_air_quality(latitude: float, longitude: float) -> Dict[str, Any]:

    # Current values for PM2.5, PM10, NO₂, O₃, SO₂, CO, dust, UV index, and pollen (grass, birch, alder) from the 
    # Copernicus Atmosphere Monitoring Service (CAMS) with global and European coverage.

    url = (
        f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={latitude}&longitude={longitude}"
        "&current=us_aqi,pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,ozone"
        "&timezone=auto"            
        )

    
    """
    Example output (Illustrative Format from open-meteo):

    {
    "latitude": 52.52,
    "longitude": 13.419,
    "elevation": 44.812,
    "generationtime_ms": 2.2119,
    "utc_offset_seconds": 0,
    "timezone": "Europe/Berlin",
    "timezone_abbreviation": "CEST",
    "hourly": {
        "time": ["2022-07-01T00:00", "2022-07-01T01:00", "2022-07-01T02:00", ...],
        "pm10": [1, 1.7, 1.7, 1.5, 1.5, 1.8, 2.0, 1.9, 1.3, ...]
    },
    "hourly_units": {
        "pm10": "μg/m³"
     },
    }
    """
    
    return api_request(url)

# Get Ocean Wave forecasts data using the open-meteo Marine Weather API

def get_marine_weather(latitude: float, longitude: float) -> Dict[str, Any]:

    # Wave height, period, and direction from global and regional ocean wave models.

    url = (
        f"https://marine-api.open-meteo.com/v1/marine?latitude={latitude}&longitude={longitude}"
        "&current=wave_height,wave_direction,wave_period,ocean_current_velocity"
        "&timezone=auto"
    )

    """
    Example output (Illustrative Format from open-meteo):

    {
    "latitude": 52.52,
    "longitude": 13.419,
    "generationtime_ms": 2.2119,
    "utc_offset_seconds": 0,
    "timezone": "Europe/Berlin",
    "timezone_abbreviation": "CEST",
    "hourly": {
        "time": ["2022-07-01T00:00", "2022-07-01T01:00", "2022-07-01T02:00", ...],
        "wave_height": [1, 1.7, 1.7, 1.5, 1.5, 1.8, 2.0, 1.9, 1.3, ...]
    },
    "hourly_units": {
        "wave_height": "m"
        },
    }
    """

    data = api_request(url)

    if "error" in data:
        return data

    # if the entered city is inland, then return a notice to Claude

    if data.get("current", {}).get("wave_height") is None:
        return {"notice": "Marine data is unavailable or this city is inland!"}

    return data

# Create a weather report (in html) based on the data ingested from the above APIs

def save_html_report(filename: str, html_content: str) -> str:

    # provide a default file name in case the agent returns an empty name or a non html file

    if not filename or not filename.endswith(".html"):
        filename = "today's_weather_report.html"

    # to avoid the agent reading/saving to a sensitive folder

    filename = os.path.basename(filename)

    # open and write to file and return a SUCCESS message if successful
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html_content)
        return f"Successfully saved HTML report to file: '{filename}'"
    except IOError as e:
        return f"File System Error: Could not write file. Details: {str(e)}"


# -------------------------------------------------
#   TOOL SCHEMA
# -------------------------------------------------

# define the tool schema: describe each tool - its name, what it does, and what inputs it needs for Claude
# to understand the purpose of each tool

tools_schema = [
    {
        "name": "get_coordinates",
        "description": "Get latitude and longitude coordinates for a target city name.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "Name of the city, e.g. Chicago, Miami"}
            },
            "required": ["city"],
        },
    },
    {
        "name": "get_weather_forecast",
        "description": "Fetch weather forecast metrics given latitude and longitude coordinates.",
        "input_schema": {
            "type": "object",
            "properties": {
                "latitude": {"type": "number", "description": "Latitude coordinate"},
                "longitude": {"type": "number", "description": "Longitude coordinate"},
            },
            "required": ["latitude", "longitude"],
        },
    },
    {
        "name": "get_air_quality",
        "description": "Fetch current air quality index (US AQI), PM2.5, PM10, and pollutants.",
        "input_schema": {
            "type": "object",
            "properties": {
                "latitude": {"type": "number", "description": "Latitude coordinate"},
                "longitude": {"type": "number", "description": "Longitude coordinate"},
            },
            "required": ["latitude", "longitude"],
        },
    },
    {
        "name": "get_marine_weather",
        "description": "Fetch ocean wave height, direction, and velocity for coastal locations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "latitude": {"type": "number", "description": "Latitude coordinate"},
                "longitude": {"type": "number", "description": "Longitude coordinate"},
            },
            "required": ["latitude", "longitude"],
        },
    },
    {
        "name": "save_html_report",
        "description": "Save the final generated HTML string to a local .html file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Output filename ending in .html"},
                "html_content": {"type": "string", "description": "Complete HTML markup string"},
            },
            "required": ["filename", "html_content"],
        },
    },
]


# -------------------------------------------------
#   TOOL MAP
# -------------------------------------------------

# connect each tool's name to the actual function.

TOOL_MAP = {
    "get_coordinates": get_coordinates,
    "get_weather_forecast": get_weather_forecast,
    "get_air_quality": get_air_quality,
    "get_marine_weather": get_marine_weather,
    "save_html_report": save_html_report
}

# -------------------------------------------------
#   AGENT EXECUTION LOOP
# -------------------------------------------------

# Retries temporary failures using exponential backoff: waits 2s, then 4s, then 8s between attempts
# Rate limits, connection issues, and server errors are retried. Other client errors  fail fast, 
# since retrying won't fix them.

def call_claude(client: anthropic.Anthropic, **kwargs) -> anthropic.types.Message:
    max_retries = 3
    delay = 2
 
    for attempt in range(1, max_retries + 1):
        try:
            return client.messages.create(**kwargs)
        except anthropic.RateLimitError:
            logging.warning(f"Rate limit hit. Retrying in {delay}s (Attempt {attempt}/{max_retries})...")
            time.sleep(delay)
            delay *= 2
        except anthropic.APIConnectionError as e:
            logging.warning(f"Connection issue: {e}. Retrying in {delay}s (Attempt {attempt}/{max_retries})...")
            time.sleep(delay)
            delay *= 2
        except anthropic.APIStatusError as e:
            if e.status_code < 500 and e.status_code != 429:
                logging.error(f"Non-retryable API error: {e.status_code} - {e.message}")
                raise e
            logging.warning(f"Server error {e.status_code}. Retrying in {delay}s...")
            time.sleep(delay)
            delay *= 2
 
    # Final attempt
    return client.messages.create(**kwargs)
 
 
def run_weather_agent(city: str, max_iterations: int = 10):

    # load Claude's API Key
 
    load_dotenv()
 
    # SDK retries off, since my call_claude function handles retries
    client = anthropic.Anthropic(max_retries=0)

    # provide a system prompt to help the agent understand its purpose

    system_prompt = (
        "You are an autonomous Weather & Environmental Reporting Agent. "
        "Your goal is to generate a styled, modern HTML dashboard report for a specified city for the next 3 days. "
        "Steps:\n"
        "1. Obtain coordinates for the city.\n"
        "2. Retrieve general weather forecast, air quality, and marine data.\n"
        "3. If any tool returns an error or notices data is missing (e.g. inland city with no marine data), "
        "gracefully adapt and omit that section without failing.\n"
        "4. Generate a responsive HTML file with CSS styling tailored to weather status.\n"
        "5. The report should provide the general weather forecast, air quality, any marine related insights "
        "and a quick summary about any actionable insights for the day.\n"
        "6. Save the report using the save_html_report tool.\n"
    )

    # The messages list is the agent's memory

    messages = [
        {
            "role": "user",
            "content": f"Generate a detailed weather, air quality, and marine environmental report for {city} "
                       f"for the next 3 days and save it to HTML."
        }
    ]
 
    logging.info(f"---- Starting Agent Session for '{city}' ----")
 
    iteration = 0

    #  The ReAct loop starts here: Agent reasons -> Acts by calling necessary tools -> Observes the result
    # -> Repeats until it has enough to give a final answer

    while iteration < max_iterations:  # Iterations before the agent stops stops repeating
        iteration += 1
        logging.info(f"Turn {iteration}/{max_iterations}")
 
        try:    
            response = call_claude(       # make the call to Claude API
                client=client,
                model="claude-sonnet-4-6",
                max_tokens=16000,  
                system=system_prompt,
                tools=tools_schema,
                messages=messages
            )
        except Exception as e:
            logging.error(f"Fatal error interacting with Claude API: {str(e)}")
            break

        # Save Claude's full response (text + tool requests) to the history
        # Claude must see its own tool requests before it sees their results

        messages.append({"role": "assistant", "content": response.content})
 
        # show Claude's reasoning by printing any text Claude wrote in its response

        for block in response.content:
            if block.type == "text":
                print(f"\n[Claude]: {block.text}")

        # Claude reasons and acts by using the defined tools

        if response.stop_reason == "tool_use": # Claude wants to run one or more tools
            tool_results = []
 
            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name 
                    tool_input = block.input
                    tool_id = block.id
 
                    # Claude executes the necessary tool with the input received from the respective API
                    
                    log_input = {k: (v[:100] + "..." if isinstance(v, str) and len(v) > 100 else v)
                                 for k, v in tool_input.items()}
                    logging.info(f"Executing tool '{tool_name}' with args: {log_input}")

                    tool_func = TOOL_MAP.get(tool_name)
 
                    if not tool_func:
                        result = {"error": f"Tool '{tool_name}' is not recognized"}
                    else:
                        try:
                            result = tool_func(**tool_input)
                        except Exception as e:
                            logging.exception(f"Unexpected crash in '{tool_name}'")
                            result = {"error": f"Internal execution exception in tool '{tool_name}': {str(e)}"}
 
                    # Every tool_use gets a matching tool_result, recognized or not
                    is_error = isinstance(result, dict) and "error" in result
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": json.dumps(result, default=str),
                            "is_error": is_error
                        }
                    )
 
            # Send all results back in a single user message, after the loop
            messages.append({"role": "user", "content": tool_results})
 
        elif response.stop_reason == "end_turn": # Claude has finished the task
            logging.info("Agent signaled task completion")
            break
 
        else: # response cutoff -> stop
            logging.error(f"Unexpected stop reason '{response.stop_reason}'. Stopping.")
            break
 
    else:
        logging.warning("Agent reached maximum allowed iteration steps without self-terminating.")
 

if __name__ == "__main__":
    run_weather_agent("Chicago")

        

        
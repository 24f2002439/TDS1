from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import yaml
from dotenv import dotenv_values
import os

app = FastAPI()

# Enable CORS so the grader tool can read your endpoint
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def format_type(key: str, value: str):
    """Converts the string values into integers or booleans where required."""
    if key in ["port", "workers"]:
        return int(value)
    if key == "debug":
        if isinstance(value, bool):
            return value
        return str(value).lower() in ["true", "1", "yes", "on"]
    return str(value)

@app.get("/effective-config")
async def get_config(request: Request):
    # Layer 1: Hardcoded Defaults
    config = {
        "port": 8000,
        "workers": 1,
        "debug": False,
        "log_level": "info",
        "api_key": "default-secret-000"
    }

    # Layer 2: config.development.yaml
    try:
        with open("config.development.yaml", "r") as file:
            yaml_data = yaml.safe_load(file)
            if yaml_data:
                for k, v in yaml_data.items():
                    if k in config:
                        config[k] = format_type(k, v)
    except FileNotFoundError:
        pass

    # Layer 3: .env file
    env_data = dotenv_values(".env")
    if "NUM_WORKERS" in env_data:
        config["workers"] = format_type("workers", env_data["NUM_WORKERS"])
    if "APP_LOG_LEVEL" in env_data:
        config["log_level"] = format_type("log_level", env_data["APP_LOG_LEVEL"])
    if "APP_API_KEY" in env_data:
        config["api_key"] = format_type("api_key", env_data["APP_API_KEY"])

    # Layer 4: OS Environment Variables
    if "APP_PORT" in os.environ:
        config["port"] = format_type("port", os.environ["APP_PORT"])
    if "APP_DEBUG" in os.environ:
        config["debug"] = format_type("debug", os.environ["APP_DEBUG"])
    if "APP_API_KEY" in os.environ:
        config["api_key"] = format_type("api_key", os.environ["APP_API_KEY"])

    # Layer 5: CLI Overrides via Query Parameters (?set=key=value)
    for query_key, query_value in request.query_params.multi_items():
        if query_key == "set" and "=" in query_value:
            key, val = query_value.split("=", 1)
            # Apply the override
            config[key] = format_type(key, val)

    # Final Security Step: Mask the API Key before sending it to the user
    config["api_key"] = "****"

    return config

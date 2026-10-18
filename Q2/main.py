from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import dotenv_values
import yaml
import os

app = FastAPI()

# Enable CORS so the assignment grader's browser can access your API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper function to convert strings like "true" or "yes" into real Booleans
def parse_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("true", "1", "yes", "on")

@app.get("/effective-config")
def get_effective_config(request: Request):
    # Layer 1: Hardcoded Defaults
    config = {
        "port": 8000,
        "workers": 1,
        "debug": False,
        "log_level": "info",
        "api_key": "default-secret-000"
    }

    # Layer 2: YAML file
    try:
        with open("config.development.yaml", "r") as f:
            yaml_data = yaml.safe_load(f)
            if yaml_data:
                config.update(yaml_data)
    except Exception:
        pass

    # Layer 3: .env file
    env_data = dotenv_values(".env")
    if "NUM_WORKERS" in env_data:
        config["workers"] = env_data["NUM_WORKERS"]
    if "APP_LOG_LEVEL" in env_data:
        config["log_level"] = env_data["APP_LOG_LEVEL"]
    if "APP_API_KEY" in env_data:
        config["api_key"] = env_data["APP_API_KEY"]

    # Layer 4: OS Environment Variables
    if "APP_PORT" in os.environ:
        config["port"] = os.environ["APP_PORT"]
    if "APP_DEBUG" in os.environ:
        config["debug"] = os.environ["APP_DEBUG"]
    if "APP_API_KEY" in os.environ:
        config["api_key"] = os.environ["APP_API_KEY"]

    # Layer 5: CLI Overrides via Query Parameters (e.g., ?set=port=9000)
    for key, value in request.query_params.multi_items():
        if key == "set" and "=" in value:
            k, v = value.split("=", 1)
            config[k] = v

    # Clean up the types (coercion) before sending the final answer
    config["port"] = int(config["port"])
    config["workers"] = int(config["workers"])
    config["debug"] = parse_bool(config["debug"])
    config["log_level"] = str(config["log_level"])
    
    # Security rule: Never expose the real API key
    config["api_key"] = "****"

    return config
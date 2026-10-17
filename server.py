import os
import yaml
from fastapi import FastAPI, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional

app = FastAPI()

# Enable CORS for browser checks
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def coerce_value(key: str, value: str):
    if key in ("port", "workers"):
        return int(value)
    if key == "debug":
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("true", "1", "yes", "on")
    return str(value)

@app.get("/effective-config")
def get_effective_config(set: Optional[List[str]] = Query(None)):
    # Layer 1: Defaults
    config = {
        "port": 8000,
        "workers": 1,
        "debug": False,
        "log_level": "info",
        "api_key": "default-secret-000"
    }
    
    # Layer 2: config.development.yaml (if present)
    yaml_file = "config.development.yaml"
    if os.path.exists(yaml_file):
        try:
            with open(yaml_file, "r") as f:
                yaml_data = yaml.safe_load(f) or {}
                for k, v in yaml_data.items():
                    config[k] = coerce_value(k, v)
        except Exception:
            pass

    # Layer 3: .env file or OS Env variables mapping with APP_ prefix & aliases
    # Mapping table: APP_PORT -> port, APP_WORKERS -> workers, APP_DEBUG -> debug, APP_LOG_LEVEL -> log_level, APP_API_KEY -> api_key
    env_mapping = {
        "APP_PORT": "port",
        "APP_WORKERS": "workers",
        "NUM_WORKERS": "workers", # Alias rule
        "APP_DEBUG": "debug",
        "APP_LOG_LEVEL": "log_level",
        "APP_API_KEY": "api_key"
    }

    for env_key, config_key in env_mapping.items():
        val = os.environ.get(env_key)
        if val is not None:
            config[config_key] = coerce_value(config_key, val)

    # Layer 4 / CLI Overrides via query params (?set=key=value)
    if set:
        for item in set:
            if "=" in item:
                parts = item.split("=", 1)
                k = parts[0].strip()
                v = parts[1].strip()
                if k in config:
                    config[k] = coerce_value(k, v)

    # Secret Masking rule: api_key must always be "*****"
    response_config = config.copy()
    response_config["api_key"] = "*****"
    
    return response_config

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
import os
from typing import Any, Dict, Optional

class ConfigurationException(Exception):
    """Exception raised for configuration validation errors."""
    pass

def parse_simple_yaml(content: str) -> Dict[str, Any]:
    """Parses simple 2-level YAML files to dictionaries without external dependencies."""
    result = {}
    current_section = None
    for line in content.splitlines():
        if not line.strip() or line.strip().startswith('#'):
            continue
        indent = len(line) - len(line.lstrip())
        line_str = line.strip()
        if ':' in line_str:
            key, val = line_str.split(':', 1)
            key = key.strip()
            val = val.strip()

            # Clean quotes
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]

            # Type casting
            if val == "":
                val = None
            elif val.lower() == 'true':
                val = True
            elif val.lower() == 'false':
                val = False
            elif val.isdigit():
                val = int(val)
            else:
                try:
                    val = float(val)
                except ValueError:
                    pass

            if indent == 0:
                if val is None:
                    current_section = key
                    result[current_section] = {}
                else:
                    result[key] = val
                    current_section = None
            else:
                if current_section is not None:
                    result[current_section][key] = val
                else:
                    result[key] = val
    return result

class ProductionConfig:
    """Manages active Production Runtime Configurations with YAML loading and Env Overrides."""
    def __init__(self, config_path: Optional[str] = None) -> None:
        self.api_host: str = "127.0.0.1"
        self.api_port: int = 8000
        self.mt5_symbol: str = "XAUUSD"
        self.mt5_timeframe: str = "H1"
        self.logging_level: str = "INFO"
        self.logging_rotation: str = "daily"
        self.workers_research: bool = True
        self.workers_intelligence: bool = True
        self.ai_confidence_threshold: int = 70

        # Secrets - strictly NOT stored in repository / yaml
        self.mt5_password: Optional[str] = None
        self.api_key: Optional[str] = None

        self._load_config(config_path)
        self._load_env_overrides()
        self._validate()

    def _load_config(self, config_path: Optional[str] = None) -> None:
        if not config_path:
            env = os.environ.get("TRADEYAR_ENV", os.environ.get("RG_ENV", "production")).lower()
            config_filename = f"{env}.yaml"
            possible_paths = [
                os.path.join("config", config_filename),
                os.path.join("../config", config_filename),
                config_filename
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    config_path = path
                    break

        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    content = f.read()
                data = parse_simple_yaml(content)

                if "api" in data:
                    self.api_host = data["api"].get("host", self.api_host) or self.api_host
                    self.api_port = data["api"].get("port", self.api_port) or self.api_port
                if "mt5" in data:
                    self.mt5_symbol = data["mt5"].get("symbol", self.mt5_symbol) or self.mt5_symbol
                    self.mt5_timeframe = data["mt5"].get("timeframe", self.mt5_timeframe) or self.mt5_timeframe
                if "logging" in data:
                    self.logging_level = data["logging"].get("level", self.logging_level) or self.logging_level
                    self.logging_rotation = data["logging"].get("rotation", self.logging_rotation) or self.logging_rotation
                if "workers" in data:
                    self.workers_research = data["workers"].get("research", self.workers_research)
                    self.workers_intelligence = data["workers"].get("intelligence", self.workers_intelligence)
                if "ai" in data:
                    self.ai_confidence_threshold = data["ai"].get("confidence_threshold", self.ai_confidence_threshold) or self.ai_confidence_threshold
            except Exception as e:
                print(f"Warning: Failed to load config from {config_path}: {e}")

    def _load_env_overrides(self) -> None:
        self.api_host = os.environ.get("TRADEYAR_API_HOST", os.environ.get("RG_API_HOST", self.api_host))

        env_port = os.environ.get("TRADEYAR_API_PORT", os.environ.get("RG_API_PORT"))
        if env_port:
            self.api_port = int(env_port)

        self.mt5_symbol = os.environ.get("TRADEYAR_MT5_SYMBOL", os.environ.get("RG_MT5_SYMBOL", self.mt5_symbol))
        self.mt5_timeframe = os.environ.get("TRADEYAR_MT5_TIMEFRAME", os.environ.get("RG_MT5_TIMEFRAME", self.mt5_timeframe))
        self.logging_level = os.environ.get("TRADEYAR_LOG_LEVEL", os.environ.get("RG_LOG_LEVEL", self.logging_level)).upper()
        self.logging_rotation = os.environ.get("TRADEYAR_LOG_ROTATION", self.logging_rotation)

        env_res = os.environ.get("TRADEYAR_WORKERS_RESEARCH")
        if env_res:
            self.workers_research = env_res.lower() == "true"

        env_intel = os.environ.get("TRADEYAR_WORKERS_INTELLIGENCE")
        if env_intel:
            self.workers_intelligence = env_intel.lower() == "true"

        env_conf = os.environ.get("TRADEYAR_AI_CONFIDENCE_THRESHOLD")
        if env_conf:
            self.ai_confidence_threshold = int(env_conf)

        self.mt5_password = os.environ.get("TRADEYAR_MT5_PASSWORD")
        self.api_key = os.environ.get("TRADEYAR_API_KEY")

    def _validate(self) -> None:
        if self.api_port <= 0 or self.api_port > 65535:
            raise ConfigurationException(f"Invalid API port: {self.api_port}")
        if self.ai_confidence_threshold < 0 or self.ai_confidence_threshold > 100:
            raise ConfigurationException(f"Confidence threshold must be between 0 and 100: {self.ai_confidence_threshold}")
        if self.logging_level not in ("DEBUG", "INFO", "WARNING", "ERROR"):
            raise ConfigurationException(f"Invalid logging level: {self.logging_level}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "api": {
                "host": self.api_host,
                "port": self.api_port
            },
            "mt5": {
                "symbol": self.mt5_symbol,
                "timeframe": self.mt5_timeframe
            },
            "logging": {
                "level": self.logging_level,
                "rotation": self.logging_rotation
            },
            "workers": {
                "research": self.workers_research,
                "intelligence": self.workers_intelligence
            },
            "ai": {
                "confidence_threshold": self.ai_confidence_threshold
            }
        }

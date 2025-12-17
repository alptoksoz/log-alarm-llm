"""Konfigürasyon yönetimi."""

import os
import re
from pathlib import Path
from typing import Any

import yaml


def resolve_env_vars(value: Any) -> Any:
    """String içindeki ${VAR} formatındaki env değişkenlerini çözümle."""
    if isinstance(value, str):
        pattern = r'\$\{([^}]+)\}'
        matches = re.findall(pattern, value)
        for var_name in matches:
            env_value = os.environ.get(var_name, "")
            value = value.replace(f"${{{var_name}}}", env_value)
        return value
    elif isinstance(value, dict):
        return {k: resolve_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [resolve_env_vars(item) for item in value]
    return value


def load_config(config_path: str | None = None) -> dict:
    """Konfigürasyon dosyasını yükle."""
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config dosyası bulunamadı: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return resolve_env_vars(config)


class Config:
    """Konfigürasyon erişim sınıfı."""

    def __init__(self, config_path: str | None = None):
        self._config = load_config(config_path)

    @property
    def openai_api_key(self) -> str:
        return self._config["openai"]["api_key"]

    @property
    def openai_model(self) -> str:
        return self._config["openai"]["model"]

    @property
    def openai_max_tokens(self) -> int:
        return self._config["openai"]["max_tokens"]

    @property
    def log_sources(self) -> list[dict]:
        return [s for s in self._config["log_sources"] if s.get("enabled", True)]

    @property
    def batch_size(self) -> int:
        return self._config["analysis"]["batch_size"]

    @property
    def interval_seconds(self) -> int:
        return self._config["analysis"]["interval_seconds"]

    @property
    def severity_threshold(self) -> str:
        return self._config["analysis"]["severity_threshold"]

    @property
    def prompt_template(self) -> str:
        return self._config["prompt_template"]

    @property
    def console_alerting(self) -> dict:
        return self._config["alerting"]["console"]

    @property
    def email_alerting(self) -> dict:
        return self._config["alerting"]["email"]

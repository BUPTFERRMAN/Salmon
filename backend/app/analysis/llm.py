import json
from pathlib import Path
from typing import Any, Dict, Optional
from urllib import error, request

from app.schemas import ModelConfig, ModelConfigView

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
CONFIG_PATH = DATA_DIR / "model_config.json"
API_TXT_CANDIDATES = [
    Path("D:/Vibe Coding/history/api.txt"),
    Path(__file__).resolve().parents[4] / "api.txt",
]


def _default_config() -> ModelConfig:
    api_key = _read_api_key_from_file()
    return ModelConfig(
        provider_name="DeepSeek",
        base_url="https://api.deepseek.com",
        # DeepSeek's stable reasoning alias; official docs map it to the latest thinking tier.
        model="deepseek-reasoner",
        api_key=api_key,
        enabled=bool(api_key),
        request_timeout_seconds=None,
    )


def _read_api_key_from_file() -> str:
    for path in API_TXT_CANDIDATES:
        try:
            if path.exists():
                return path.read_text(encoding="utf-8").strip()
        except OSError:
            continue
    return ""


def _hydrate_deepseek_defaults(config: ModelConfig) -> ModelConfig:
    changed = False
    if not config.provider_name:
        config.provider_name = "DeepSeek"
        changed = True
    if not config.base_url:
        config.base_url = "https://api.deepseek.com"
        changed = True
    if not config.model:
        config.model = "deepseek-reasoner"
        changed = True
    if not config.api_key:
        api_key = _read_api_key_from_file()
        if api_key:
            config.api_key = api_key
            changed = True
    if config.api_key and not config.enabled:
        config.enabled = True
        changed = True
    if getattr(config, "request_timeout_seconds", None) is None:
        config.request_timeout_seconds = None
    if changed:
        save_model_config(config)
    return config


def load_model_config() -> ModelConfig:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists():
        config = _default_config()
        CONFIG_PATH.write_text(config.model_dump_json(indent=2), encoding="utf-8")
        return config

    try:
        config = ModelConfig.model_validate_json(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        config = _default_config()
        CONFIG_PATH.write_text(config.model_dump_json(indent=2), encoding="utf-8")
        return config
    return _hydrate_deepseek_defaults(config)


def save_model_config(payload: ModelConfig) -> ModelConfig:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(payload.model_dump_json(indent=2), encoding="utf-8")
    return payload


def model_config_view(payload: Optional[ModelConfig] = None) -> ModelConfigView:
    config = payload or load_model_config()
    key_hint = ""
    if config.api_key:
        key_hint = f"{config.api_key[:4]}...{config.api_key[-4:]}" if len(config.api_key) > 8 else "saved"
    return ModelConfigView(
        provider_name=config.provider_name,
        base_url=config.base_url,
        model=config.model,
        enabled=config.enabled,
        has_api_key=bool(config.api_key),
        api_key_hint=key_hint,
        request_timeout_seconds=config.request_timeout_seconds,
    )


class OpenAICompatibleClient:
    def __init__(self, config: Optional[ModelConfig] = None) -> None:
        self.config = config or load_model_config()

    @property
    def enabled(self) -> bool:
        return bool(
            self.config.enabled
            and self.config.api_key.strip()
            and self.config.base_url.strip()
            and self.config.model.strip()
        )

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        timeout: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return None

        effective_timeout = self.config.request_timeout_seconds if timeout is None else timeout

        payload = {
            "model": self.config.model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        # DeepSeek's reasoning alias does not use sampling controls in the same way as chat-tuned models.
        if "reasoner" not in self.config.model:
            payload["temperature"] = 0.3

        req = request.Request(
            f"{self.config.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.api_key}",
            },
        )
        try:
            if effective_timeout is None or effective_timeout <= 0:
                response = request.urlopen(req)
            else:
                response = request.urlopen(req, timeout=effective_timeout)
            with response:
                body = json.loads(response.read().decode("utf-8"))
        except (error.URLError, TimeoutError, json.JSONDecodeError):
            return None

        try:
            message = body["choices"][0]["message"]
            content = message.get("content", "")
            cleaned = _clean_json_block(content)
            return json.loads(cleaned)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError):
            return None


def _clean_json_block(content: str) -> str:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned

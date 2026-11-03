import json
import os
from pathlib import Path
from typing import Any, Dict

DEFAULT_CONFIG: Dict[str, Any] = {
    "general": {
        "hotkey_screenshot": "alt+q",
        "hotkey_toggle_window": "alt+w",
        "enable_selection_trigger": True,
        "mini_button_timeout": 3.0,
        "auto_hide_on_blur": True,
        "theme": "light"
    },
    "translation": {
        "provider": "bing",  # "bing" (微软翻译, 国内直连推荐), "youdao" (网易有道), "google" (需翻墙), "openai" (大模型)
        "target_lang": "auto",  # "auto" (自动判定: 中译英, 非中译简中), 或 "zh-CN", "en", "ja", "ko", etc.
        "openai": {
            "base_url": "https://api.siliconflow.cn/v1",
            "api_key": "",
            "model": "Qwen/Qwen2.5-7B-Instruct",
            "temperature": 0.3,
            "system_prompt": "You are a professional, accurate translator. Translate the given text directly into the target language. Do not add explanations, conversational phrases, or quotes. Output ONLY the translation."
        }
    },
    "ocr": {
        "engine": "rapidocr",
        "auto_copy_ocr": False
    }
}

class ConfigManager:
    """Manages application configuration, reading and writing to config.json."""
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path).resolve()
        self._data: Dict[str, Any] = {}
        self.load()

    def load(self) -> Dict[str, Any]:
        """Loads configuration from file or generates default if missing."""
        if not self.config_path.exists():
            self._data = json.loads(json.dumps(DEFAULT_CONFIG))
            self.save()
            return self._data

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            # Merge with default config to ensure missing keys are populated
            self._data = self._deep_merge(DEFAULT_CONFIG, loaded)
        except Exception as e:
            print(f"[ConfigManager] Error reading config: {e}. Falling back to default.")
            self._data = json.loads(json.dumps(DEFAULT_CONFIG))
        return self._data

    def save(self):
        """Saves current configuration to file."""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[ConfigManager] Error writing config: {e}")

    def get(self, *keys, default=None):
        """Safely retrieves a nested configuration value."""
        curr = self._data
        for k in keys:
            if isinstance(curr, dict) and k in curr:
                curr = curr[k]
            else:
                return default
        return curr

    def set(self, *keys_and_value):
        """Sets a nested configuration value and persists it."""
        if len(keys_and_value) < 2:
            return
        keys = keys_and_value[:-1]
        val = keys_and_value[-1]
        curr = self._data
        for k in keys[:-1]:
            if k not in curr or not isinstance(curr[k], dict):
                curr[k] = {}
            curr = curr[k]
        curr[keys[-1]] = val
        self.save()

    def _deep_merge(self, default: dict, user: dict) -> dict:
        result = json.loads(json.dumps(default))
        for key, val in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(val, dict):
                result[key] = self._deep_merge(result[key], val)
            else:
                result[key] = val
        return result

# Singleton instance
config = ConfigManager()

import re
import time
import urllib.parse
from typing import Optional, Tuple, Dict, Any
import httpx
from config import config

CHINESE_PATTERN = re.compile(r'[\u4e00-\u9fff]')

def is_primarily_chinese(text: str) -> bool:
    """Returns True if the text contains Chinese characters."""
    return bool(CHINESE_PATTERN.search(text))

class BingAuthCache:
    """Caches Bing translator session tokens to avoid hitting cn.bing.com every call."""
    def __init__(self):
        self.ig: str = ""
        self.key: str = ""
        self.token: str = ""
        self.expires_at: float = 0.0

    def is_valid(self) -> bool:
        return bool(self.ig and self.key and self.token and time.time() < self.expires_at)

    def refresh(self, timeout: float = 6.0):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
        }
        with httpx.Client(timeout=timeout, headers=headers) as client:
            resp = client.get("https://cn.bing.com/translator")
            resp.raise_for_status()
            text = resp.text
            
            ig_match = re.search(r'IG:"([A-Za-z0-9]+)"', text)
            if not ig_match:
                raise ValueError("Bing IG token not found")
            self.ig = ig_match.group(1)

            token_match = re.search(r'params_AbusePreventionHelper\s*=\s*\[([0-9]+),"([^"]+)"', text)
            if not token_match:
                raise ValueError("Bing AbusePreventionHelper token not found")
            self.key = token_match.group(1)
            self.token = token_match.group(2)
            self.expires_at = time.time() + 900  # Valid for 15 minutes

bing_auth = BingAuthCache()

def translate_bing(text: str, target_lang: str = "auto") -> str:
    """Translates text using Bing cn.bing.com translator (Direct, Free in China)."""
    if target_lang == "auto":
        to_lang = "en" if is_primarily_chinese(text) else "zh-Hans"
    elif target_lang in ("zh-CN", "zh"):
        to_lang = "zh-Hans"
    else:
        to_lang = target_lang

    for attempt in range(2):
        try:
            if not bing_auth.is_valid():
                bing_auth.refresh()

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://cn.bing.com/translator",
                "Origin": "https://cn.bing.com"
            }
            url = f"https://cn.bing.com/ttranslatev3?isVertical=1&&IG={bing_auth.ig}&IID=translator.5028"
            data = {
                "text": text,
                "fromLang": "auto-detect",
                "to": to_lang,
                "key": bing_auth.key,
                "token": bing_auth.token
            }
            with httpx.Client(timeout=6.0, headers=headers) as client:
                resp = client.post(url, data=data)
                resp.raise_for_status()
                json_data = resp.json()
                if isinstance(json_data, list) and len(json_data) > 0:
                    translations = json_data[0].get("translations", [])
                    if translations and "text" in translations[0]:
                        return translations[0]["text"]
            raise ValueError(f"Invalid Bing response format: {json_data}")
        except Exception as e:
            bing_auth.expires_at = 0  # Invalidate cache to force token refresh next time
            if attempt == 1:
                raise e

def translate_youdao(text: str, target_lang: str = "auto") -> str:
    """Translates text using NetEase Youdao Translator (Direct, Free in China)."""
    lang_map = {
        "auto": "Auto",
        "zh-CN": "zh-CHS",
        "zh": "zh-CHS",
        "en": "en",
        "ja": "ja",
        "ko": "ko",
        "fr": "fr",
        "de": "de",
        "es": "es",
        "ru": "ru"
    }
    to_lang = lang_map.get(target_lang, "Auto")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://aidemo.youdao.com/"
    }
    data = {
        "q": text,
        "from": "Auto",
        "to": to_lang
    }
    with httpx.Client(timeout=6.0, headers=headers) as client:
        resp = client.post("https://aidemo.youdao.com/trans", data=data)
        resp.raise_for_status()
        json_data = resp.json()
        trans_list = json_data.get("translation")
        if trans_list and isinstance(trans_list, list):
            return "\n".join(trans_list)
        raise ValueError(f"Invalid Youdao response format: {json_data}")

def translate_google(text: str, target_lang: str = "auto") -> str:
    """Translates text using Google web endpoint (Requires VPN / overseas network)."""
    if target_lang == "auto":
        tl = "en" if is_primarily_chinese(text) else "zh-CN"
    else:
        tl = target_lang

    encoded_text = urllib.parse.quote(text)
    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={tl}&dt=t&q={encoded_text}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    with httpx.Client(timeout=6.0, headers=headers) as client:
        response = client.get(url)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
            chunks = [item[0] for item in data[0] if isinstance(item, list) and len(item) > 0 and item[0]]
            return "".join(chunks)
        raise ValueError("Invalid Google Translate response format")

def translate_openai(text: str, target_lang: str = "auto") -> str:
    """Translates text using an OpenAI-compatible API endpoint (DeepSeek, SiliconFlow, OpenAI, Ollama, etc.)."""
    lang_name_map = {
        "en": "English",
        "zh-CN": "Simplified Chinese",
        "zh": "Simplified Chinese",
        "ja": "Japanese",
        "ko": "Korean",
        "fr": "French",
        "de": "German",
        "es": "Spanish",
        "ru": "Russian"
    }
    if target_lang == "auto":
        tgt_name = "English" if is_primarily_chinese(text) else "Simplified Chinese"
    else:
        tgt_name = lang_name_map.get(target_lang, target_lang)

    openai_cfg = config.get("translation", "openai", default={})
    base_url = openai_cfg.get("base_url", "https://api.openai.com/v1").rstrip("/")
    api_key = openai_cfg.get("api_key", "").strip()
    model = openai_cfg.get("model", "gpt-4o-mini")
    system_prompt = openai_cfg.get("system_prompt", "You are a professional, accurate translator. Translate the given text directly into the target language. Do not add explanations, conversational phrases, or quotes. Output ONLY the translation.")

    if not api_key and not base_url.startswith("http://localhost") and not base_url.startswith("http://127.0.0.1"):
        raise ValueError("未配置大模型 API Key。请在设置中输入 API Key，或切换为【微软 Bing】/【网易有道】免费源。")

    headers = {
        "Authorization": f"Bearer {api_key}" if api_key else "",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "temperature": openai_cfg.get("temperature", 0.3),
        "messages": [
            {"role": "system", "content": f"{system_prompt}\nTarget language: {tgt_name}."},
            {"role": "user", "content": text}
        ]
    }

    endpoint = f"{base_url}/chat/completions"
    with httpx.Client(timeout=20.0) as client:
        response = client.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        choice = data["choices"][0]["message"]["content"]
        return choice.strip()

def translate(text: str, target_lang: Optional[str] = None) -> str:
    """Main translation entry point dispatching based on config with smart fallbacks."""
    cleaned = text.strip()
    if not cleaned:
        return ""
        
    if target_lang is None:
        target_lang = config.get("translation", "target_lang", default="auto")

    provider = config.get("translation", "provider", default="bing")
    if provider == "openai":
        return translate_openai(cleaned, target_lang)

    # Strategy priority
    if provider == "bing":
        pipeline = [("微软 Bing", translate_bing), ("网易有道", translate_youdao), ("Google", translate_google)]
    elif provider == "youdao":
        pipeline = [("网易有道", translate_youdao), ("微软 Bing", translate_bing), ("Google", translate_google)]
    elif provider == "google":
        pipeline = [("Google", translate_google), ("微软 Bing", translate_bing), ("网易有道", translate_youdao)]
    else:  # "free" or other
        pipeline = [("微软 Bing", translate_bing), ("网易有道", translate_youdao), ("Google", translate_google)]

    errors = []
    for name, func in pipeline:
        try:
            res = func(cleaned, target_lang)
            if res and res.strip():
                return res.strip()
        except Exception as e:
            errors.append(f"{name}: {e}")
            print(f"[Translator] {name} translation failed: {e}. Trying fallback...")

    raise RuntimeError(f"翻译服务连接失败 ({'; '.join(errors)})")

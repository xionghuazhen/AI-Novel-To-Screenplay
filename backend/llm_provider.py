"""统一 LLM Provider 封装 - 支持 Claude / GPT / DeepSeek / Qwen"""
import json
import re
import httpx
from .config import app_config, LLMConfig


class LLMProvider:
    """统一的 LLM 调用接口"""

    def __init__(self, config: LLMConfig | None = None):
        self.cfg = config or app_config.llm

    def _build_headers(self) -> dict:
        if self.cfg.provider == "claude" or self.cfg.provider == "deepseek":
            return {
                "x-api-key": self.cfg.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
        else:
            return {
                "Authorization": f"Bearer {self.cfg.api_key}",
                "content-type": "application/json",
            }

    def _build_body(self, messages: list[dict], system: str = "") -> dict:
        if self.cfg.provider in ("claude", "deepseek"):
            body = {
                "model": self.cfg.model,
                "max_tokens": self.cfg.max_tokens,
                "temperature": self.cfg.temperature,
                "messages": messages,
                "thinking": {"type": "disabled"},
            }
            if system:
                body["system"] = system
            return body
        else:
            msgs = []
            if system:
                msgs.append({"role": "system", "content": system})
            msgs.extend(messages)
            return {
                "model": self.cfg.model,
                "max_tokens": self.cfg.max_tokens,
                "temperature": self.cfg.temperature,
                "messages": msgs,
            }

    def _build_url(self) -> str:
        if self.cfg.provider in ("claude", "deepseek"):
            return f"{self.cfg.base_url}/v1/messages"
        else:
            return f"{self.cfg.base_url}/chat/completions"

    def _extract_text(self, data: dict) -> str:
        if self.cfg.provider in ("claude", "deepseek"):
            # 优先找 text 类型的 content block
            for block in data["content"]:
                if block.get("type") == "text":
                    return block["text"]
            # 兼容 thinking 类型的 block（DeepSeek 思维链）
            for block in data["content"]:
                if block.get("type") == "thinking":
                    return block.get("thinking", "")
            raise KeyError(f"No text/thinking block in response: {data.get('content', [])}")
        else:
            return data["choices"][0]["message"]["content"]

    def chat(self, user_message: str, system: str = "", temperature: float | None = None, max_tokens: int | None = None) -> str:
        """发送单轮对话，返回文本响应"""
        messages = [{"role": "user", "content": user_message}]
        body = self._build_body(messages, system)
        if temperature is not None:
            body["temperature"] = temperature
        if max_tokens is not None:
            body["max_tokens"] = max_tokens

        url = self._build_url()
        headers = self._build_headers()

        with httpx.Client(timeout=120) as client:
            resp = client.post(url, headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()
            return self._extract_text(data)

    def extract_json(self, text: str) -> dict | list:
        """从 LLM 响应中提取 JSON（优先数组，再对象）"""
        # 先尝试提取 JSON 数组
        match = re.search(r"\[[\s\S]*\]", text)
        if match:
            return json.loads(match.group())
        # 再尝试提取 JSON 对象
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Cannot extract JSON from: {text[:200]}...")


# 全局单例
_llm_instance: LLMProvider | None = None


def get_llm() -> LLMProvider:
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = LLMProvider()
    return _llm_instance

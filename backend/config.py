"""配置管理 - 通过环境变量切换 LLM Provider"""
import os
from dataclasses import dataclass, field


@dataclass
class LLMConfig:
    provider: str = os.getenv("LLM_PROVIDER", "deepseek")  # claude | openai | deepseek | qwen
    model: str = ""
    api_key: str = ""
    base_url: str = ""
    max_tokens: int = 4096
    temperature: float = 0.7

    def __post_init__(self):
        providers = {
            "claude": {
                "model": "claude-sonnet-4-6",
                "api_key": os.getenv("ANTHROPIC_API_KEY", ""),
                "base_url": "https://api.anthropic.com",
            },
            "openai": {
                "model": "gpt-4o",
                "api_key": os.getenv("OPENAI_API_KEY", ""),
                "base_url": "https://api.openai.com/v1",
            },
            "deepseek": {
                "model": "deepseek-v4-pro",
                "api_key": os.getenv("ANTHROPIC_AUTH_TOKEN", ""),
                "base_url": os.getenv("ANTHROPIC_BASE_URL", "https://api.deepseek.com/anthropic"),
            },
            "qwen": {
                "model": "qwen-max",
                "api_key": os.getenv("DASHSCOPE_API_KEY", ""),
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            },
        }
        cfg = providers.get(self.provider, providers["deepseek"])
        if not self.model:
            self.model = cfg["model"]
        if not self.api_key:
            self.api_key = cfg["api_key"]
        if not self.base_url:
            self.base_url = cfg["base_url"]


@dataclass
class AppConfig:
    llm: LLMConfig = field(default_factory=LLMConfig)
    max_chapter_words: int = 15000  # 单章节最大字数(分片阈值)
    max_scenes_per_chapter: int = 10
    enable_scoring: bool = True
    enable_consistency_check: bool = True
    rag_memory_enabled: bool = False  # 50万字方案标记
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"


app_config = AppConfig()

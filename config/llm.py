import os
from openai import AsyncOpenAI

# =====================================================================
# Переключение провайдера — менять ТОЛЬКО здесь
# Ollama (локально):  LLM_PROVIDER=ollama  LLM_MODEL=qwen2.5-coder:7b
# OpenAI:             LLM_PROVIDER=openai  LLM_MODEL=gpt-4o-mini
# =====================================================================

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5-coder:7b")


def get_llm_client() -> tuple[AsyncOpenAI, str]:
    if LLM_PROVIDER == "ollama":
        client = AsyncOpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama",
        )
    else:
        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    return client, LLM_MODEL
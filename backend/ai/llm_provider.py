import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()


class LLMConfigurationError(Exception):
    """Raised when the LLM configuration is invalid."""


@lru_cache(maxsize=1)
def get_llm():
    """
    Returns the configured Gemini chat model.

    API keys are loaded from environment variables.
    No credentials are hardcoded.
    """

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise LLMConfigurationError(
            "GEMINI_API_KEY is missing. Configure it in your .env file."
        )

    model_name = os.getenv(
        "GEMINI_MODEL",
        "gemini-2.5-flash"
    )

    temperature = float(
        os.getenv("LLM_TEMPERATURE", "0.2")
    )

    try:
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=temperature,
            max_retries=2,
            timeout=60,
        )

    except Exception as exc:
        raise LLMConfigurationError(
            f"Failed to initialize LLM provider: {exc}"
        ) from exc
"""OpenRouter chat completion client (OpenAI-compatible API)."""
from __future__ import annotations

import logging
from dataclasses import dataclass

import openai
from openai import OpenAI

from app.config import Settings, is_free_model

logger = logging.getLogger(__name__)


class LLMError(RuntimeError):
    """Base class. `user_message` is safe to show in the UI."""
    status_code = 502
    user_message = "The language model is currently unavailable. Please try again shortly."


class LLMConfigError(LLMError):
    status_code = 503
    user_message = "The chatbot is not configured with an OpenRouter API key yet."


class LLMAuthError(LLMError):
    status_code = 503
    user_message = "The OpenRouter API key was rejected. The administrator needs to update it."


class LLMRateLimitError(LLMError):
    status_code = 429
    user_message = "The free model is rate-limited right now. Please wait a minute and try again."


class LLMTimeoutError(LLMError):
    status_code = 504
    user_message = "The language model took too long to respond. Please try again."


class LLMUnavailableError(LLMError):
    status_code = 503
    user_message = "The free model is temporarily unavailable. Please try again in a moment."


@dataclass
class Generation:
    text: str
    model: str


class OpenRouterGenerator:
    def __init__(self, settings: Settings):
        self.settings = settings
        if not is_free_model(settings.openrouter_model):   # defence in depth (config validates too)
            raise LLMConfigError(f"Refusing non-free model {settings.openrouter_model}")
        self._client: OpenAI | None = None

    @property
    def configured(self) -> bool:
        return bool(self.settings.openrouter_api_key.strip())

    @property
    def client(self) -> OpenAI:
        if not self.configured:
            raise LLMConfigError("OPENROUTER_API_KEY is not set")
        if self._client is None:
            self._client = OpenAI(
                api_key=self.settings.openrouter_api_key,
                base_url=self.settings.openrouter_base_url,
                timeout=self.settings.llm_timeout_seconds,
                max_retries=self.settings.llm_max_retries,   # SDK retries 429/5xx/timeouts with backoff
                default_headers={"X-Title": "Real Estate RAG Assistant (demo)"},
            )
        return self._client

    def generate(self, messages: list[dict]) -> Generation:
        try:
            resp = self.client.chat.completions.create(
                model=self.settings.openrouter_model,
                messages=messages,
                temperature=self.settings.llm_temperature,
                max_tokens=self.settings.llm_max_tokens,
            )
        except openai.AuthenticationError as e:
            raise LLMAuthError(str(e)) from e
        except openai.RateLimitError as e:
            raise LLMRateLimitError(str(e)) from e
        except openai.APITimeoutError as e:
            raise LLMTimeoutError(str(e)) from e
        except openai.PermissionDeniedError as e:   # e.g. 402 / moderation / no free capacity
            raise LLMUnavailableError(str(e)) from e
        except (openai.NotFoundError, openai.BadRequestError, openai.InternalServerError,
                openai.APIConnectionError, openai.APIStatusError) as e:
            raise LLMUnavailableError(str(e)) from e

        if not resp.choices:
            raise LLMUnavailableError("Empty response from model")
        text = (resp.choices[0].message.content or "").strip()
        if not text:
            raise LLMUnavailableError("Model returned no text")
        used = getattr(resp, "model", None) or self.settings.openrouter_model
        logger.info("LLM answered with model=%s", used)
        return Generation(text=text, model=used)

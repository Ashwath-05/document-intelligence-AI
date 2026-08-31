"""Groq-backed LLM provider.

Concrete implementation of the LLMProvider seam (see base.py). No other
module should import this directly -- only the composition root
(routes/generation.py's DI function) constructs it, the same rule
services/__init__.py states for the interface itself.
"""

from groq import AsyncGroq, GroqError

from app.core.config import Settings
from app.providers.llm.base import LLMGenerationError, LLMProvider, LLMResponse


class GroqProvider(LLMProvider):
    def __init__(self, settings: Settings):
        self._model = settings.llm_model
        # AsyncGroq, not the sync Groq client -- generate() is declared
        # async on the interface specifically so a real network call here
        # never blocks the event loop (see base.py's docstring).
        self._client = AsyncGroq(
            api_key=settings.groq_api_key,
            timeout=settings.llm_timeout_seconds,
        )

    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        history: list[dict[str, str]] | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        # Order matters and mirrors every chat-completion API: system
        # instruction first, then prior turns oldest-to-newest, then the
        # current prompt last. `history` is passed straight through --
        # it's already {"role": ..., "content": ...} dicts, the same shape
        # Groq's SDK expects, so there's nothing to transform here.
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        # Groq's SDK distinguishes "argument omitted" from "argument is
        # None" (its Omit sentinel vs an explicit null) -- only add
        # max_tokens when a real cap was requested, rather than passing
        # None through and relying on the SDK to treat them the same.
        create_kwargs = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            create_kwargs["max_tokens"] = max_tokens

        try:
            completion = await self._client.chat.completions.create(**create_kwargs)
        except GroqError as e:
            # Normalised at the boundary, same principle as LLMResponse --
            # GenerationService and the route layer handle one error type
            # regardless of which provider is behind LLMProvider.
            raise LLMGenerationError(f"Groq request failed: {e}") from e

        choice = completion.choices[0]
        usage = completion.usage
        return LLMResponse(
            text=choice.message.content or "",
            model=completion.model,
            prompt_tokens=usage.prompt_tokens if usage else None,
            completion_tokens=usage.completion_tokens if usage else None,
        )

    @property
    def model_name(self) -> str:
        return self._model

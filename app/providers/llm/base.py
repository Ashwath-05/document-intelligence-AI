"""LLM provider contract.

This is the seam that makes multi-provider support additive instead of a
rewrite. Services depend on this abstraction; they must never import a
concrete provider. GroqProvider lives in `groq_provider.py` beside this
file, and when OpenAI/Gemini/Claude arrive later they are new classes here
-- no service or router changes.

If you ever find a service importing `groq_provider`, dependency inversion is
broken and the swap-ability is gone.

No implementation lives in this file. On purpose.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMResponse:
    """Normalised result from any provider.

    Every vendor returns a differently-shaped payload. Normalising at the
    boundary means the rest of the codebase never sees vendor-specific JSON,
    which is the whole point of the adapter pattern.

    Token counts are here from the start because cost and context-window
    limits become load-bearing concerns the moment real documents arrive.
    """

    text: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class LLMProvider(ABC):
    """Interface every LLM provider must satisfy.

    ABC + @abstractmethod is enforcement, not documentation: Python refuses to
    instantiate any subclass that hasn't implemented every abstract method.
    A half-finished provider fails at construction, not in production.
    """

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        history: list[dict[str, str]] | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Generate a completion for a single prompt, optionally continuing
        a conversation.

        Declared async because every real implementation is a network call.
        Making the interface async now means adding a provider later never
        forces a signature change up the call chain -- an async contract can
        wrap a sync SDK, but a sync contract can never become async without
        touching every caller.

        Args:
            prompt: The user-facing instruction or question -- always the
                LAST message sent, i.e. the current turn.
            system_prompt: Optional role/behaviour instruction.
            history: Optional prior turns, oldest first, each shaped like
                {"role": "user" | "assistant", "content": "..."}. Inserted
                between system_prompt and prompt in the actual messages
                sent to the model -- this is what makes a call
                conversational instead of single-shot. Chat-completion APIs
                are built around exactly this array-of-turns shape; flattening
                history into one prompt string instead loses the role
                boundaries the model was trained on. None/empty means a
                plain single-shot call, e.g. Phase 8's stateless /generate,
                or Phase 9's own query-reformulation step on the first turn
                of a conversation (nothing to condense against yet).
            temperature: Sampling randomness. Low values suit extraction and
                summarisation, where determinism matters more than variety.
            max_tokens: Optional cap on the generated response length.

        Returns:
            An LLMResponse with vendor-specific fields already normalised.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Identifier of the model actually being used.

        Useful for logging, cost attribution, and debugging which model
        produced a given answer once several providers are in play.
        """
        raise NotImplementedError


class LLMGenerationError(Exception):
    """Raised when a provider's completion call fails.

    Normalised across providers, same principle as LLMResponse but for the
    failure path: callers (GenerationService, then the route layer) catch
    this one type regardless of which vendor's SDK -- and which
    vendor-specific exception class -- actually raised it.
    """

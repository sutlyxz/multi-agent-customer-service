"""Intent Agent for classifying customer messages and extracting entities."""

from __future__ import annotations

from typing import Any, Literal, Protocol

from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, ConfigDict, Field

from prompts import build_intent_agent_prompt


SupportedIntent = Literal[
    "product_inquiry",
    "order_tracking",
    "return_request",
    "general_question",
]


class StructuredOutputModel(Protocol):
    """Minimal LangChain model interface required by the Intent Agent."""

    def with_structured_output(
        self,
        schema: type[IntentResult],
    ) -> Any:
        """Return a runnable configured for the requested structured schema."""


class IntentEntities(BaseModel):
    """Entities extracted from the customer's message."""

    model_config = ConfigDict(extra="forbid")

    product_name: str | None = Field(
        default=None,
        description="Product name explicitly mentioned by the customer, or null.",
    )

    size: str | None = Field(
        default=None,
        description="Product size explicitly mentioned by the customer, or null.",
    )

    color: str | None = Field(
        default=None,
        description="Product color explicitly mentioned by the customer, or null.",
    )

    order_id: str | None = Field(
        default=None,
        description="Order ID explicitly mentioned by the customer, or null.",
    )


class IntentResult(BaseModel):
    """Structured result returned by the Intent Agent."""

    model_config = ConfigDict(extra="forbid")

    intent: SupportedIntent | list[SupportedIntent] = Field(
        description="One supported intent, or a list for a multi-intent request.",
    )

    entities: IntentEntities


class IntentAgentError(RuntimeError):
    """Raised when the Intent Agent cannot produce a valid structured result."""


class IntentAgent:
    """Classify customer messages without answering or performing business actions."""

    def __init__(
        self,
        model: str = "gemini-3.6-flash",
        llm: StructuredOutputModel | None = None,
        temperature: float = 0.0,
    ) -> None:
        """Create an agent, optionally using an injected LangChain chat model."""

        self.llm = llm or ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
        )

        self.structured_llm = self.llm.with_structured_output(
            IntentResult,
            method="json_schema",
        )

    def analyze(self, user_message: str) -> IntentResult:
        """Classify a customer message and extract only explicitly stated entities."""

        if not isinstance(user_message, str) or not user_message.strip():
            raise ValueError("user_message must be a non-empty string")

        try:
            result = self.structured_llm.invoke(
                build_intent_agent_prompt(user_message.strip())
            )

            return IntentResult.model_validate(result)

        except Exception as exc:
            print("\n[Intent Agent Error]")
            print(type(exc).__name__)
            print(exc)

            raise IntentAgentError(
                "Intent Agent failed to produce a valid structured result"
            ) from exc


def analyze(self, user_message: str) -> IntentResult:
    if not isinstance(user_message, str) or not user_message.strip():
        raise ValueError("user_message must be a non-empty string")

    try:
        result = self.structured_llm.invoke(
            build_intent_agent_prompt(user_message.strip())
        )

        return IntentResult.model_validate(result)

    except Exception as exc:
        print("\n[Intent Agent Error]")
        print(type(exc).__name__)
        print(exc)

        raise IntentAgentError(
            "Intent Agent failed to produce a valid structured result"
        ) from exc
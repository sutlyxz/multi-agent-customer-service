"""Resolution Agent for composing customer responses from verified results."""

from __future__ import annotations

from typing import Any, Mapping, Protocol, TypedDict

from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, ConfigDict, Field

from prompts import build_resolution_agent_prompt


class AgentResult(TypedDict):
    """Result from one upstream agent."""

    agent: str
    data: dict[str, Any]


class ResolutionInput(TypedDict):
    """Input contract for the Resolution Agent."""

    customer_message: str
    results: list[AgentResult]


class ResolutionResult(BaseModel):
    """Structured final response returned to the workflow."""

    model_config = ConfigDict(extra="forbid")

    response: str = Field(
        description="Natural-language response based only on the supplied agent results.",
    )


class StructuredOutputModel(Protocol):
    """Minimal LangChain model interface required by the Resolution Agent."""

    def with_structured_output(
        self,
        schema: type[ResolutionResult],
    ) -> Any:
        """Return a runnable configured for the requested structured schema."""


class ResolutionAgentError(RuntimeError):
    """Raised when the Resolution Agent cannot produce a valid response."""


class ResolutionAgent:
    """Compose a customer response from upstream agent results only."""

    def __init__(
        self,
        model: str = "gemini-3.6-flash",
        llm: StructuredOutputModel | None = None,
        temperature: float = 0.0,
    ) -> None:
        """Create a Gemini-based Resolution Agent."""

        self.llm = llm or ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
        )

        self.structured_llm = self.llm.with_structured_output(
            ResolutionResult,
            method="json_schema",
        )

    def resolve(
        self,
        customer_message: str,
        results: list[AgentResult],
    ) -> ResolutionResult:
        """Create a response using only the supplied upstream agent results."""

        if not isinstance(customer_message, str) or not customer_message.strip():
            raise ValueError("customer_message must be a non-empty string")

        if not isinstance(results, list):
            raise ValueError("results must be a list")

        if any(not isinstance(result, Mapping) for result in results):
            raise ValueError("each result must be a mapping")

        try:
            prompt = build_resolution_agent_prompt(
                customer_message.strip(),
                [dict(result) for result in results],
            )

            response = self.structured_llm.invoke(prompt)

            return ResolutionResult.model_validate(response)

        except Exception as exc:
            raise ResolutionAgentError(
                "Resolution Agent failed to produce a valid response"
            ) from exc

    def run(
        self,
        resolution_input: Mapping[str, object],
    ) -> ResolutionResult:
        """Process a JSON-like resolution input payload."""

        if not isinstance(resolution_input, Mapping):
            raise ValueError("resolution_input must be a mapping")

        customer_message = resolution_input.get("customer_message")
        results = resolution_input.get("results")

        if not isinstance(customer_message, str):
            raise ValueError("customer_message must be a string")

        if not isinstance(results, list):
            raise ValueError("results must be a list")

        return self.resolve(
            customer_message,
            results,  # type: ignore[arg-type]
        )


def resolve_customer_message(
    customer_message: str,
    results: list[AgentResult],
    agent: ResolutionAgent | None = None,
) -> ResolutionResult:
    """Convenience function for invoking the Resolution Agent."""

    return (agent or ResolutionAgent()).resolve(
        customer_message,
        results,
    )
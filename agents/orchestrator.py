"""Workflow controller for routing Intent Agent results to specialist agents."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from agents.order import OrderAgent
from agents.product import ProductAgent
from agents.resolution import AgentResult, ResolutionAgent
from state import AgentState


SUPPORTED_INTENTS = {
	"product_inquiry",
	"order_tracking",
	"return_request",
	"general_question",
}


class OrchestratorError(ValueError):
	"""Raised when orchestration input is invalid."""


def _as_mapping(value: object, name: str) -> Mapping[str, Any]:
	"""Convert a mapping-like or Pydantic result to a mapping."""
	if isinstance(value, Mapping):
		return value
	if hasattr(value, "model_dump"):
		result = value.model_dump()
		if isinstance(result, Mapping):
			return result
	raise OrchestratorError(f"{name} must be a mapping or Pydantic model")


def _intent_tasks(intent_result: object) -> list[tuple[str, Mapping[str, Any]]]:
	"""Normalize single or multi-intent output into dispatchable tasks."""
	result = _as_mapping(intent_result, "intent_result")
	intent_value = result.get("intent")

	if isinstance(intent_value, str):
		return [(intent_value, _entities_from_result(result))]

	if isinstance(intent_value, list):
		tasks: list[tuple[str, Mapping[str, Any]]] = []
		for item in intent_value:
			if isinstance(item, str):
				tasks.append((item, _entities_from_result(result)))
				continue
			item_mapping = _as_mapping(item, "intent item")
			item_intent = item_mapping.get("intent")
			if not isinstance(item_intent, str):
				raise OrchestratorError("each intent item must contain a string intent")
			tasks.append((item_intent, _entities_from_result(item_mapping)))
		return tasks

	raise OrchestratorError("intent_result.intent must be a string or list")


def _entities_from_result(result: Mapping[str, Any]) -> Mapping[str, Any]:
	"""Read entities from Intent Agent output or shared state fields."""
	entities = result.get("entities")
	if isinstance(entities, Mapping):
		return entities
	return {
		"product_name": result.get("product_name"),
		"size": result.get("size"),
		"color": result.get("color"),
		"order_id": result.get("order_id"),
	}


def _capability_result(intent: str) -> AgentResult:
	"""Record an intent that has no specialist Agent in the MVP."""
	return {
		"agent": "orchestrator",
		"data": {
			"intent": intent,
			"supported": False,
			"message": "This capability is not supported yet.",
		},
	}


def _resolution_only_result(intent: str) -> AgentResult:
	"""Record an intent that needs no specialist Agent before resolution."""
	return {
		"agent": "orchestrator",
		"data": {
			"intent": intent,
			"supported": True,
			"message": "No specialist agent is required for this intent.",
		},
	}


class Orchestrator:
	"""Route intents, collect specialist results, and invoke Resolution Agent."""

	def __init__(
		self,
		product_agent: ProductAgent | None = None,
		order_agent: OrderAgent | None = None,
		resolution_agent: ResolutionAgent | None = None,
	) -> None:
		self.product_agent = product_agent or ProductAgent()
		self.order_agent = order_agent or OrderAgent()
		self.resolution_agent = resolution_agent or ResolutionAgent()

	def run(self, state: AgentState, intent_result: object) -> AgentState:
		"""Route Intent Agent output and return the updated shared state."""
		if not isinstance(state, Mapping):
			raise OrchestratorError("state must be a mapping")
		user_message = state.get("user_message")
		if not isinstance(user_message, str) or not user_message.strip():
			raise OrchestratorError("state.user_message must be a non-empty string")

		updated_state = dict(state)
		agent_results: list[AgentResult] = []
		try:
			for intent, entities in _intent_tasks(intent_result):
				if intent == "product_inquiry":
					product_result = self.product_agent.run({
						"product_name": entities.get("product_name"),
						"size": entities.get("size"),
						"color": entities.get("color"),
					})
					updated_state["product_result"] = product_result
					agent_results.append({"agent": "product_agent", "data": dict(product_result)})
				elif intent == "order_tracking":
					order_result = self.order_agent.run({
						"order_id": entities.get("order_id"),
					})
					updated_state["order_result"] = order_result
					agent_results.append({"agent": "order_agent", "data": dict(order_result)})
				elif intent == "general_question":
					agent_results.append(_resolution_only_result(intent))
				else:
					agent_results.append(_capability_result(intent))

			resolution_result = self.resolution_agent.run({
				"customer_message": user_message,
				"results": agent_results,
			})
			updated_state["agent_results"] = agent_results
			updated_state["final_response"] = resolution_result.response
			return updated_state  # type: ignore[return-value]
		except OrchestratorError:
			raise
		except Exception as exc:
			raise OrchestratorError("Orchestrator failed to complete the workflow") from exc


def orchestrate(
	state: AgentState,
	intent_result: object,
	orchestrator: Orchestrator | None = None,
) -> AgentState:
	"""Convenience function for running the orchestration workflow."""
	return (orchestrator or Orchestrator()).run(state, intent_result)
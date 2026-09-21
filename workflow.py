"""LangGraph workflow for the multi-agent customer service system."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Callable, cast

from langgraph.graph import END, START, StateGraph

from agents.intent import IntentAgent
from agents.order import OrderAgent
from agents.product import ProductAgent
from agents.resolution import ResolutionAgent
from state import AgentState


IntentAgentLike = IntentAgent
ProductAgentLike = ProductAgent
OrderAgentLike = OrderAgent
ResolutionAgentLike = ResolutionAgent


def _to_mapping(value: object) -> Mapping[str, Any]:
	"""Convert a Pydantic result or mapping into a read-only mapping view."""
	if isinstance(value, Mapping):
		return value
	if hasattr(value, "model_dump"):
		result = value.model_dump()
		if isinstance(result, Mapping):
			return result
	raise TypeError("Intent Agent result must be a mapping or Pydantic model")


def _intent_names(intent: object) -> list[str]:
	"""Normalize one or many intent values for conditional routing."""
	if isinstance(intent, str):
		return [intent]
	if isinstance(intent, list) and all(isinstance(item, str) for item in intent):
		return cast(list[str], intent)
	if isinstance(intent, list) and all(isinstance(item, Mapping) for item in intent):
		names: list[str] = []
		for item in intent:
			name = item.get("intent")
			if not isinstance(name, str):
				raise ValueError("each intent item must contain a string intent")
			names.append(name)
		return names
	raise ValueError("intent must be a string or a list of intent values")


def _merge_intent_entities(
	intent_result: Mapping[str, Any],
) -> dict[str, Any]:
	"""Extract shared entity fields from single or multi-intent output."""
	entities = intent_result.get("entities")
	merged: dict[str, Any] = {
		"product_name": None,
		"size": None,
		"color": None,
		"order_id": None,
	}
	if isinstance(entities, Mapping):
		merged.update({key: entities.get(key) for key in merged})

	intent_value = intent_result.get("intent")
	if isinstance(intent_value, list):
		for item in intent_value:
			if not isinstance(item, Mapping):
				continue
			item_entities = item.get("entities")
			if isinstance(item_entities, Mapping):
				merged.update({key: item_entities.get(key) for key in merged})
	return merged


def _intent_node(
	state: AgentState,
	intent_agent: IntentAgentLike,
) -> dict[str, Any]:
	"""Call Intent Agent and place its result into shared state fields."""
	user_message = state.get("user_message")
	if not isinstance(user_message, str) or not user_message.strip():
		raise ValueError("user_message must be a non-empty string")
	result = _to_mapping(intent_agent.analyze(user_message))
	entities = _merge_intent_entities(result)
	return {
		"intent": result.get("intent"),
		**entities,
	}


def _orchestrator_node(state: AgentState) -> dict[str, Any]:
	"""Validate the routing state before conditional branch selection."""
	if state.get("intent") is None:
		raise ValueError("intent is required before orchestration")
	_intent_names(state["intent"])
	return {}


def _route_agents(state: AgentState) -> list[str]:
	"""Select all specialist branches required by one or more intents."""
	intents = set(_intent_names(state["intent"]))
	routes: list[str] = []
	if "product_inquiry" in intents:
		routes.append("product_agent")
	if "order_tracking" in intents:
		routes.append("order_agent")
	if not routes:
		routes.append("collect_results")
	return routes


def _product_node(
	state: AgentState,
	product_agent: ProductAgentLike,
) -> dict[str, Any]:
	"""Run Product Agent using only entities extracted by Intent Agent."""
	return {
		"product_result": product_agent.run({
			"product_name": state.get("product_name"),
			"size": state.get("size"),
			"color": state.get("color"),
		})
	}


def _order_node(
	state: AgentState,
	order_agent: OrderAgentLike,
) -> dict[str, Any]:
	"""Run Order Agent using only the order ID extracted by Intent Agent."""
	return {"order_result": order_agent.run({"order_id": state.get("order_id")})}


def _collect_results_node(state: AgentState) -> dict[str, Any]:
	"""Combine specialist results and record unsupported capabilities."""
	results: list[dict[str, Any]] = []
	product_result = state.get("product_result")
	if isinstance(product_result, Mapping):
		results.append({"agent": "product_agent", "data": dict(product_result)})
	order_result = state.get("order_result")
	if isinstance(order_result, Mapping):
		results.append({"agent": "order_agent", "data": dict(order_result)})

	for intent in _intent_names(state["intent"]):
		if intent == "return_request":
			results.append({
				"agent": "orchestrator",
				"data": {
					"intent": intent,
					"supported": False,
					"message": "This capability is not supported yet.",
				},
			})
		elif intent not in {"product_inquiry", "order_tracking", "general_question"}:
			results.append({
				"agent": "orchestrator",
				"data": {
					"intent": intent,
					"supported": False,
					"message": "This capability is not supported yet.",
				},
			})
	return {"agent_results": results}


def _resolution_node(
	state: AgentState,
	resolution_agent: ResolutionAgentLike,
) -> dict[str, Any]:
	"""Call Resolution Agent with the original message and collected results."""
	result = resolution_agent.run({
		"customer_message": state["user_message"],
		"results": state.get("agent_results", []),
	})
	return {"final_response": result.response}


def build_workflow(
	intent_agent: IntentAgentLike | None = None,
	product_agent: ProductAgentLike | None = None,
	order_agent: OrderAgentLike | None = None,
	resolution_agent: ResolutionAgentLike | None = None,
) -> Any:
	"""Build and compile the LangGraph workflow with optional injected Agents."""
	intent = intent_agent or IntentAgent()
	product = product_agent or ProductAgent()
	order = order_agent or OrderAgent()
	resolution = resolution_agent or ResolutionAgent()

	graph = StateGraph(AgentState)
	graph.add_node("intent_agent", lambda state: _intent_node(state, intent))
	graph.add_node("orchestrator", _orchestrator_node)
	graph.add_node("product_agent", lambda state: _product_node(state, product))
	graph.add_node("order_agent", lambda state: _order_node(state, order))
	graph.add_node("collect_results", _collect_results_node)
	graph.add_node("resolution_agent", lambda state: _resolution_node(state, resolution))

	graph.add_edge(START, "intent_agent")
	graph.add_edge("intent_agent", "orchestrator")
	graph.add_conditional_edges(
		"orchestrator",
		_route_agents,
		{
			"product_agent": "product_agent",
			"order_agent": "order_agent",
			"collect_results": "collect_results",
		},
	)
	graph.add_edge("product_agent", "collect_results")
	graph.add_edge("order_agent", "collect_results")
	graph.add_edge("collect_results", "resolution_agent")
	graph.add_edge("resolution_agent", END)
	return graph.compile()


def run_workflow(user_message: str, graph: Any | None = None) -> AgentState:
	"""Invoke the compiled workflow for one customer message."""
	if not isinstance(user_message, str) or not user_message.strip():
		raise ValueError("user_message must be a non-empty string")
	workflow = graph or build_workflow()
	initial_state: AgentState = {
		"user_message": user_message,
		"intent": None,
		"product_name": None,
		"size": None,
		"color": None,
		"order_id": None,
		"product_result": None,
		"order_result": None,
		"agent_results": [],
		"final_response": None,
	}
	return cast(AgentState, workflow.invoke(initial_state))
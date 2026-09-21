"""Shared state schema for the multi-agent customer service workflow."""

from typing import Optional, TypedDict


class AgentState(TypedDict):
	"""Data shared between agents while processing a customer request."""

	user_message: str  # Original message from the customer.
	intent: Optional[str]  # Intent identified by the Intent Agent.
	product_name: Optional[str]  # Product name mentioned in the request.
	size: Optional[str]  # Product size requested by the customer.
	color: Optional[str]  # Product color requested by the customer.
	order_id: Optional[str]  # Order number related to the request.
	product_result: Optional[dict]  # Result returned by the Product Agent.
	order_result: Optional[dict]  # Result returned by the Order Agent.
	agent_results: list  # Results collected from multiple agents.
	final_response: Optional[str]  # Final response prepared for the customer.
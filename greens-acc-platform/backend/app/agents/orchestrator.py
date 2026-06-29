"""
Greens ACC Multi-Agent System

Father Agent: Orchestrates legal, compliance, and structural deal boundaries.
Son Agent: Handles rapid automated negotiation, itemization, and pricing logistics.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentProfile:
    name: str
    responsibility: str


class TradingOrchestrator:
    """Static placeholder for the future LangGraph-based father-son workflow."""

    def describe(self) -> list[AgentProfile]:
        return [
            AgentProfile(
                name="Father Agent",
                responsibility="Controls governance, compliance, and approval constraints.",
            ),
            AgentProfile(
                name="Son Agent",
                responsibility="Executes negotiation, pricing, and operational packaging.",
            ),
        ]

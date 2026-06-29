from app.agents.orchestrator import TradingOrchestrator
from app.models.platform import PlatformOverview


class PlatformService:
    def __init__(self) -> None:
        self._orchestrator = TradingOrchestrator()

    def overview(self) -> PlatformOverview:
        systems = [
            "Multi-Agent Negotiation Matrix",
            "Supabase Ledger Sync",
            *[profile.name for profile in self._orchestrator.describe()],
        ]
        return PlatformOverview(
            status="online",
            platform="Greens ACC Engine",
            systems=systems,
        )

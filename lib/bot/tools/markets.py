"""Market related tools."""
from typing import Dict, Any, List, Optional
from .base import BaseTool
from ...repositories.markets import MarketsRepository


class GetMarketDetailsTool(BaseTool):
    """Get market details."""
    
    @property
    def name(self) -> str:
        return "get_market_details"
    
    @property
    def description(self) -> str:
        return "Get detailed information about a specific market including title, description, outcomes, and current status. Use this BEFORE placing a bet to understand what you're betting on."
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "market_slug": {
                    "type": "string",
                    "description": "Market slug identifier"
                }
            },
            "required": ["market_slug"]
        }
    
    def execute(self, bot, market_slug: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Get market details."""
        print(f"  [Fetching market details for {market_slug}...]")
        markets_repo = MarketsRepository()
        return markets_repo.get_market_details(market_slug)


class GetActiveMarketsTool(BaseTool):
    """Get active markets."""
    
    @property
    def name(self) -> str:
        return "get_active_markets"
    
    @property
    def description(self) -> str:
        return "Get list of currently active markets on Polymarket"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of markets to return (default: 20)",
                    "default": 20
                }
            },
            "required": []
        }
    
    def execute(self, bot, limit: int = 20, **kwargs) -> List[Dict[str, Any]]:
        """Get active markets."""
        print(f"  [Fetching {limit} active markets...]")
        markets_repo = MarketsRepository()
        return markets_repo.get_active_markets(limit)

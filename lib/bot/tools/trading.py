"""Trading execution tools."""
from typing import Dict, Any
from .base import BaseTool
from ...repositories.trades import TradesRepository


class GetTradeHistoryTool(BaseTool):
    """Get trade history."""
    
    @property
    def name(self) -> str:
        return "get_trade_history"
    
    @property
    def description(self) -> str:
        return "Get complete trading history showing all bets placed during this session with performance metrics"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of trades to return (default: 10)",
                    "default": 10
                }
            },
            "required": []
        }
    
    def execute(self, bot, limit: int = 10, **kwargs) -> Dict[str, Any]:
        """Get trading history."""
        if bot.dry_run:
            if not bot.simulated_trades:
                return {
                    "total_trades": 0,
                    "trades": [],
                    "message": "No trades placed yet (dry-run mode)"
                }
            
            recent_trades = bot.simulated_trades[-limit:]
            
            return {
                "total_trades": len(bot.simulated_trades),
                "showing": len(recent_trades),
                "mode": "DRY_RUN",
                "trades": [
                    {
                        "market_slug": t['market_slug'],
                        "market_title": t.get('market_title', t['market_slug']),
                        "outcome": t['outcome'],
                        "amount": round(t['amount'], 2),
                        "reasoning": t['reasoning'],
                        "timestamp": t['timestamp']
                    }
                    for t in recent_trades
                ]
            }
        else:
            if not bot.wallet_address:
                return {
                    "error": "No wallet address configured",
                    "message": "Set POLYMARKET_WALLET in .env file"
                }
            
            print(f"  [Fetching trade history for wallet...]")
            try:
                trades_repo = TradesRepository()
                trades = trades_repo.get_active_trades(bot.wallet_address, limit=limit)
                
                return {
                    "total_trades": len(trades),
                    "showing": len(trades),
                    "mode": "LIVE",
                    "trades": [
                        {
                            "market_slug": t.get('slug', ''),
                            "market_title": t.get('title', 'Unknown'),
                            "outcome": t.get('outcome', 'Unknown'),
                            "side": t.get('side', 'Unknown'),
                            "amount": round(float(t.get('size', 0)) * float(t.get('price', 0)), 2),
                            "price": round(float(t.get('price', 0)), 4),
                            "timestamp": t.get('timestamp', 0)
                        }
                        for t in trades
                    ],
                    "note": "Only showing trades in active markets"
                }
            except Exception as e:
                return {
                    "error": str(e),
                    "message": "Could not fetch trade history"
                }


class PlaceBetTool(BaseTool):
    """Place a bet."""
    
    @property
    def name(self) -> str:
        return "place_bet"
    
    @property
    def description(self) -> str:
        return "Place a bet on a specific market outcome. CRITICAL: You MUST call get_market_details first to understand the market before betting. Use this only after thorough analysis of trader consensus and market conditions."
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "market_slug": {
                    "type": "string",
                    "description": "Market slug identifier"
                },
                "outcome": {
                    "type": "string",
                    "description": "Outcome to bet on (e.g., 'Yes', 'No', or specific option)"
                },
                "amount_usd": {
                    "type": "number",
                    "description": "Amount in USD to bet"
                },
                "reasoning": {
                    "type": "string",
                    "description": "Your detailed reasoning for this bet including: which traders agree, their metrics, consensus strength, and why you believe this is a good opportunity"
                }
            },
            "required": ["market_slug", "outcome", "amount_usd", "reasoning"]
        }
    
    def execute(self, bot, **kwargs) -> Any:
        """Execute via bet placer."""
        return bot.bet_placer.place_bet(**kwargs)

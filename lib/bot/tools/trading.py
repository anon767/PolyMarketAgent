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
            if not bot.polymarket_client:
                return {
                    "error": "Polymarket client not initialized",
                    "message": "Cannot fetch live trades without CLOB client"
                }
            
            print(f"  [Fetching trade history from CLOB...]")
            try:
                from ...repositories.markets import MarketsRepository
                
                # Use CLOB client to get trades
                trades = bot.polymarket_client.get_trades()
                
                # Limit results
                trades = trades[:limit] if len(trades) > limit else trades
                
                # Enrich with market details
                markets_repo = MarketsRepository()
                enriched_trades = []
                
                for t in trades:
                    market_id = t.get('market', '')
                    
                    # Try to get market details by condition_id
                    market_info = None
                    if market_id:
                        try:
                            # Search for market by condition_id
                            import requests
                            resp = requests.get(
                                f'https://gamma-api.polymarket.com/markets',
                                params={'condition_id': market_id, 'limit': 1}
                            )
                            if resp.status_code == 200:
                                markets = resp.json()
                                if markets:
                                    market_info = markets[0]
                        except:
                            pass
                    
                    trade_data = {
                        "market_id": market_id,
                        "asset_id": t.get('asset_id', 'Unknown'),
                        "outcome": t.get('outcome', 'Unknown'),
                        "side": t.get('side', 'Unknown'),
                        "size": round(float(t.get('size', 0)), 4),
                        "price": round(float(t.get('price', 0)), 4),
                        "amount": round(float(t.get('size', 0)) * float(t.get('price', 0)), 2),
                        "status": t.get('status', 'Unknown'),
                        "match_time": t.get('match_time', 'Unknown')
                    }
                    
                    # Add market details if found
                    if market_info:
                        trade_data['market_title'] = market_info.get('question', 'Unknown')
                        trade_data['market_slug'] = market_info.get('market_slug', 'Unknown')
                        trade_data['description'] = market_info.get('description', 'N/A')
                        trade_data['end_date'] = market_info.get('end_date_iso', 'Unknown')
                    else:
                        trade_data['market_title'] = 'Unknown (could not fetch details)'
                        trade_data['market_slug'] = 'Unknown'
                    
                    enriched_trades.append(trade_data)
                
                return {
                    "total_trades": len(enriched_trades),
                    "showing": len(enriched_trades),
                    "mode": "LIVE",
                    "trades": enriched_trades,
                    "note": "Trades from CLOB client with market details"
                }
            except Exception as e:
                import traceback
                return {
                    "error": str(e),
                    "message": "Could not fetch trade history from CLOB",
                    "traceback": traceback.format_exc()
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

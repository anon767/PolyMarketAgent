"""Trader analysis tools."""
import time
from typing import Dict, Any, List
from .base import BaseTool
from ...analysis import (
    get_top_traders_by_sharpe,
    TraderMetrics,
    get_top_volume_trades,
    find_consensus_bets,
    analyze_trader
)
from ...repositories.markets import MarketsRepository
from ...repositories.wallets import WalletsRepository


# Shared cache for top traders
_top_traders_cache = None
_cache_time = None


class GetTopTradersTool(BaseTool):
    """Get top traders by Sharpe ratio."""
    
    @property
    def name(self) -> str:
        return "get_top_traders"
    
    @property
    def description(self) -> str:
        return "Get top N traders ranked by Sharpe ratio (risk-adjusted returns). Returns trader metrics including Sharpe ratio, win rate, max drawdown (percentage loss from peak), P&L, and total trades. Max drawdown shows risk - closer to 0% is better, more negative means higher losses."
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "n": {
                    "type": "integer",
                    "description": "Number of top traders to return (default: 10, max: 50)",
                    "default": 10
                }
            },
            "required": []
        }
    
    def execute(self, bot, n: int = 10, **kwargs) -> List[Dict[str, Any]]:
        """Get top N traders by Sharpe ratio."""
        global _top_traders_cache, _cache_time
        
        n = min(n, 50)
        
        # Cache for 5 minutes
        if _top_traders_cache and _cache_time:
            if time.time() - _cache_time < 300:
                return _top_traders_cache[:n]
        
        print(f"  [Analyzing top 50 traders from leaderboard...]")
        traders = get_top_traders_by_sharpe(n=50, sample_size=50)
        
        result = []
        for i, trader in enumerate(traders, 1):
            result.append({
                "rank": i,
                "username": trader.username,
                "wallet": trader.wallet,
                "sharpe_ratio": round(trader.sharpe_ratio, 4),
                "win_rate": round(trader.win_rate, 2),
                "max_drawdown": round(trader.max_drawdown, 2),
                "total_trades": trader.total_trades,
                "leaderboard_rank": trader.leaderboard_rank,
                "pnl": round(trader.leaderboard_pnl, 2)
            })
        
        _top_traders_cache = result
        _cache_time = time.time()
        
        return result


class GetTraderTopTradesTool(BaseTool):
    """Get top trades for a specific trader."""
    
    @property
    def name(self) -> str:
        return "get_trader_top_trades"
    
    @property
    def description(self) -> str:
        return "Get the top N highest volume trades for a specific trader wallet"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "wallet": {
                    "type": "string",
                    "description": "Trader's wallet address"
                },
                "n": {
                    "type": "integer",
                    "description": "Number of top trades to return (default: 5)",
                    "default": 5
                }
            },
            "required": ["wallet"]
        }
    
    def execute(self, bot, wallet: str, n: int = 5, **kwargs) -> List[Dict[str, Any]]:
        """Get top trades for a specific trader."""
        print(f"  [Fetching top {n} trades for wallet...]")
        trades = get_top_volume_trades(wallet, n * 3)
        
        markets_repo = MarketsRepository()
        result = []
        for trade in trades:
            if markets_repo.is_active(trade.market_slug):
                result.append({
                    "market": trade.market_title,
                    "market_slug": trade.market_slug,
                    "outcome": trade.outcome,
                    "side": trade.side,
                    "volume_usd": round(trade.value, 2),
                    "price": round(trade.price, 4),
                    "shares": round(trade.size, 2),
                    "status": "active"
                })
                
                if len(result) >= n:
                    break
        
        return result


class GetConsensusBetsTool(BaseTool):
    """Find consensus bets among top traders."""
    
    @property
    def name(self) -> str:
        return "get_consensus_bets"
    
    @property
    def description(self) -> str:
        return "Find bets where multiple top traders agree (same market and outcome). Returns markets with 2+ traders betting on the same outcome."
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "min_traders": {
                    "type": "integer",
                    "description": "Minimum number of traders that must agree (default: 2)",
                    "default": 2
                }
            },
            "required": []
        }
    
    def execute(self, bot, min_traders: int = 2, **kwargs) -> List[Dict[str, Any]]:
        """Find consensus bets among top traders."""
        global _top_traders_cache
        
        print(f"  [Finding consensus bets...]")
        
        if not _top_traders_cache:
            # Get top traders first
            get_top_traders_tool = GetTopTradersTool()
            get_top_traders_tool.execute(bot, n=10)
        
        # Convert cache back to TraderMetrics
        traders = []
        for t in _top_traders_cache:
            traders.append(TraderMetrics(
                wallet=t['wallet'],
                username=t['username'],
                leaderboard_rank=t['leaderboard_rank'],
                leaderboard_vol=0,
                leaderboard_pnl=t['pnl'],
                total_trades=t['total_trades'],
                sharpe_ratio=t['sharpe_ratio'],
                avg_return=0,
                volatility=0,
                win_rate=t['win_rate'],
                max_drawdown=t['max_drawdown']
            ))
        
        consensus = find_consensus_bets(traders)
        
        markets_repo = MarketsRepository()
        result = []
        for market_slug, outcome, trader_count, avg_volume in consensus:
            if trader_count >= min_traders and markets_repo.is_active(market_slug):
                result.append({
                    "market_slug": market_slug,
                    "outcome": outcome,
                    "trader_count": trader_count,
                    "avg_volume_usd": round(avg_volume, 2),
                    "status": "active"
                })
        
        return result[:20]


class GetSuggestedWhalesTool(BaseTool):
    """Get suggested whale traders."""
    
    @property
    def name(self) -> str:
        return "get_suggested_whales"
    
    @property
    def description(self) -> str:
        return "Get recommended whale traders from PolyWhaler.com - these are high-volume traders with recent activity. Returns wallet addresses, names, recent trade counts, volumes, and last trade times. Alternative to get_top_traders for finding active whales."
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of suggested whales to return (default: 10)",
                    "default": 50
                }
            },
            "required": []
        }
    
    def execute(self, bot, limit: int = 50, **kwargs) -> Dict[str, Any]:
        """Get recommended whale traders with Sharpe ratio analysis."""
        print(f"  [Fetching {limit} suggested whales...]")
        
        wallets_repo = WalletsRepository()
        whales = wallets_repo.get_suggested_whales(limit)
        
        if not whales:
            return {"error": "PolyWhaler unavailable", "whales": []}
        
        print(f"  [Analyzing {len(whales)} whales for risk metrics...]")
        enriched_whales = []
        
        for w in whales:
            wallet = w['wallet']
            print(f"    Analyzing {w.get('name', wallet)}...")
            
            metrics = analyze_trader(
                wallet=wallet,
                username=w.get('name', 'Unknown'),
                rank=0,
                vol=w.get('recentVolume', 0),
                pnl=0
            )
            
            if metrics:
                enriched_whales.append({
                    "wallet": wallet,
                    "name": w.get('name', 'Unknown'),
                    "recent_trades": w.get('recentTradeCount', 0),
                    "recent_volume": round(w.get('recentVolume', 0), 2),
                    "sharpe_ratio": round(metrics.sharpe_ratio, 4),
                    "win_rate": round(metrics.win_rate, 2),
                    "max_drawdown": round(metrics.max_drawdown, 2),
                    "total_trades": metrics.total_trades,
                    "last_trade_time": w.get('lastTradeTime', 0)
                })
            else:
                enriched_whales.append({
                    "wallet": wallet,
                    "name": w.get('name', 'Unknown'),
                    "recent_trades": w.get('recentTradeCount', 0),
                    "recent_volume": round(w.get('recentVolume', 0), 2),
                    "sharpe_ratio": 0.0,
                    "win_rate": 0.0,
                    "max_drawdown": 0.0,
                    "total_trades": 0,
                    "last_trade_time": w.get('lastTradeTime', 0),
                    "note": "Analysis unavailable"
                })
        
        enriched_whales.sort(key=lambda x: x['sharpe_ratio'], reverse=True)
        
        return {
            "count": len(enriched_whales),
            "whales": enriched_whales,
            "note": "High-volume traders enriched with Sharpe ratio analysis"
        }

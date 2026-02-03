import json
import time
import os
from typing import List, Dict, Optional, Any
from datetime import datetime

from ..repositories.markets import MarketsRepository
from ..repositories.trades import TradesRepository
from ..repositories.wallets import WalletsRepository
from ..analysis import (
    get_top_traders_by_sharpe,
    TraderMetrics,
    get_top_volume_trades,
    find_consensus_bets,
    analyze_trader
)


class ToolExecutor:
    """Handles execution of all tool functions for the trading bot."""
    
    def __init__(self, bot):
        """
        Initialize tool executor.
        
        Args:
            bot: Reference to parent TradingBot instance
        """
        self.bot = bot
        self.markets_repo = MarketsRepository()
        self.trades_repo = TradesRepository()
        self.wallets_repo = WalletsRepository()
        
        # Cache for top traders
        self.top_traders_cache = None
        self.cache_time = None
    
    def get_available_funds(self) -> Dict[str, Any]:
        """Get current available balance minus open orders."""
        if not self.bot.dry_run and self.bot.polymarket_client:
            try:
                real_balance = self.wallets_repo.get_balance(self.bot.wallet_address)
                if real_balance is not None:
                    self.bot.balance = real_balance
            except Exception as e:
                print(f"  [Warning: Could not refresh balance: {e}]")
        
        # Calculate locked funds in open orders
        locked_in_orders = 0.0
        if not self.bot.dry_run and self.bot.polymarket_client:
            try:
                orders = self.bot.polymarket_client.get_orders()
                for order in orders:
                    if order.get('status') == 'LIVE':
                        original_size = float(order.get('original_size', 0))
                        size_matched = float(order.get('size_matched', 0))
                        price = float(order.get('price', 0))
                        remaining_size = original_size - size_matched
                        locked_in_orders += remaining_size * price
            except Exception as e:
                print(f"  [Warning: Could not fetch open orders: {e}]")
        
        available_balance = self.bot.balance - locked_in_orders
        
        return {
            "balance_usd": round(self.bot.balance, 2),
            "locked_in_orders": round(locked_in_orders, 2),
            "available_balance": round(available_balance, 2),
            "positions_count": len(self.bot.positions),
            "total_invested": round(sum(p['amount'] for p in self.bot.positions), 2),
            "available_for_trading": round(available_balance, 2),
            "max_single_bet": round(available_balance * self.bot.max_single_bet_pct, 2),
            "max_single_bet_pct": f"{int(self.bot.max_single_bet_pct * 100)}%",
            "target_deployment": "100% of balance",
            "mode": "DRY_RUN" if self.bot.dry_run else "LIVE"
        }
    
    def get_current_positions(self) -> List[Dict[str, Any]]:
        """Get all current open positions."""
        if not self.bot.positions:
            return []
        
        positions_list = []
        for i, pos in enumerate(self.bot.positions, 1):
            positions_list.append({
                "position_number": i,
                "market_slug": pos['market_slug'],
                "market_title": pos.get('market_title', pos['market_slug']),
                "outcome": pos['outcome'],
                "amount_invested": round(pos['amount'], 2),
                "reasoning": pos['reasoning'],
                "timestamp": pos['timestamp'],
                "mode": pos.get('mode', 'DRY_RUN')
            })
        
        return positions_list
    
    def get_trade_history(self, limit: int = 10) -> Dict[str, Any]:
        """Get trading history."""
        if self.bot.dry_run:
            if not self.bot.simulated_trades:
                return {
                    "total_trades": 0,
                    "trades": [],
                    "message": "No trades placed yet (dry-run mode)"
                }
            
            recent_trades = self.bot.simulated_trades[-limit:]
            
            return {
                "total_trades": len(self.bot.simulated_trades),
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
            if not self.bot.wallet_address:
                return {
                    "error": "No wallet address configured",
                    "message": "Set POLYMARKET_WALLET in .env file"
                }
            
            print(f"  [Fetching trade history for wallet...]")
            try:
                trades = self.trades_repo.get_active_trades(self.bot.wallet_address, limit=limit)
                
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
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get comprehensive portfolio summary."""
        total_invested = sum(p['amount'] for p in self.bot.positions)
        unique_markets = len(set(p['market_slug'] for p in self.bot.positions))
        avg_position_size = total_invested / len(self.bot.positions) if self.bot.positions else 0
        largest_position = max((p['amount'] for p in self.bot.positions), default=0)
        
        if self.bot.dry_run:
            total_trades_count = len(self.bot.simulated_trades)
        else:
            if self.bot.wallet_address:
                try:
                    trades = self.trades_repo.get_active_trades(self.bot.wallet_address, limit=500)
                    total_trades_count = len(trades)
                except:
                    total_trades_count = 0
            else:
                total_trades_count = 0
        
        return {
            "balance": {
                "available": round(self.bot.balance, 2),
                "invested": round(total_invested, 2),
                "total_capital": round(self.bot.balance + total_invested, 2)
            },
            "positions": {
                "count": len(self.bot.positions),
                "unique_markets": unique_markets,
                "avg_position_size": round(avg_position_size, 2),
                "largest_position": round(largest_position, 2)
            },
            "risk_metrics": {
                "capital_deployed_pct": round((total_invested / (self.bot.balance + total_invested) * 100) if (self.bot.balance + total_invested) > 0 else 0, 2),
                "target_deployment_pct": "100%",
                "diversification_score": f"{unique_markets}/{len(self.bot.positions)}" if self.bot.positions else "N/A",
                "max_single_bet_allowed": round(self.bot.balance * self.bot.max_single_bet_pct, 2),
                "max_single_bet_pct": f"{int(self.bot.max_single_bet_pct * 100)}%"
            },
            "trading_activity": {
                "total_trades": total_trades_count,
                "mode": "DRY_RUN" if self.bot.dry_run else "LIVE"
            }
        }
    
    def get_top_traders(self, n: int = 10) -> List[Dict[str, Any]]:
        """Get top N traders by Sharpe ratio."""
        n = min(n, 50)
        
        # Cache for 5 minutes
        if self.top_traders_cache and self.cache_time:
            if time.time() - self.cache_time < 300:
                return self.top_traders_cache[:n]
        
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
        
        self.top_traders_cache = result
        self.cache_time = time.time()
        
        return result
    
    def get_trader_top_trades(self, wallet: str, n: int = 5) -> List[Dict[str, Any]]:
        """Get top trades for a specific trader."""
        print(f"  [Fetching top {n} trades for wallet...]")
        trades = get_top_volume_trades(wallet, n * 3)
        
        result = []
        for trade in trades:
            if self.markets_repo.is_active(trade.market_slug):
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

    def get_consensus_bets(self, min_traders: int = 2) -> List[Dict[str, Any]]:
        """Find consensus bets among top traders."""
        print(f"  [Finding consensus bets...]")
        
        if not self.top_traders_cache:
            self.get_top_traders(10)
        
        # Convert cache back to TraderMetrics
        traders = []
        for t in self.top_traders_cache:
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
        
        result = []
        for market_slug, outcome, trader_count, avg_volume in consensus:
            if trader_count >= min_traders and self.markets_repo.is_active(market_slug):
                result.append({
                    "market_slug": market_slug,
                    "outcome": outcome,
                    "trader_count": trader_count,
                    "avg_volume_usd": round(avg_volume, 2),
                    "status": "active"
                })
        
        return result[:20]
    
    def get_market_details(self, market_slug: str) -> Optional[Dict[str, Any]]:
        """Get market details."""
        print(f"  [Fetching market details for {market_slug}...]")
        return self.markets_repo.get_market_details(market_slug)
    
    def get_active_markets(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get active markets."""
        print(f"  [Fetching {limit} active markets...]")
        return self.markets_repo.get_active_markets(limit)
    
    def search_news(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Search for recent news."""
        print(f"  [Searching news for: {query}...]")
        try:
            from pygooglenews import GoogleNews
            gn = GoogleNews(lang='en', country='US')
            search = gn.search(query, when='7d')
            articles = [
                {
                    'title': e.title,
                    'source': e.source.get('title', 'Unknown'),
                    'published': e.published,
                    'url': e.link
                }
                for e in search['entries'][:max_results]
            ]
            return {"query": query, "results_count": len(articles), "articles": articles}
        except Exception as e:
            return {"query": query, "error": str(e), "note": "News unavailable"}
    
    def read_knowledge_base(self) -> Dict[str, Any]:
        """Read the trading knowledge base."""
        print(f"  [Reading knowledge base...]")
        
        kb_path = "kb.txt"
        
        try:
            if os.path.exists(kb_path):
                with open(kb_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                return {
                    "available": True,
                    "content": content,
                    "note": "Knowledge base contains 14 proven Polymarket trading strategies"
                }
            else:
                return {
                    "available": False,
                    "error": "Knowledge base file (kb.txt) not found"
                }
        except Exception as e:
            return {"available": False, "error": str(e)}
    
    def get_suggested_whales(self, limit: int = 50) -> Dict[str, Any]:
        """Get recommended whale traders with Sharpe ratio analysis."""
        print(f"  [Fetching {limit} suggested whales...]")
        
        whales = self.wallets_repo.get_suggested_whales(limit)
        
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

import json
import time
import os
from typing import List, Dict, Optional, Any
from datetime import datetime
from decimal import Decimal

from .providers import AIProvider, ChatGPTProvider, ClaudeProvider
from .prompts import get_system_prompt
from .tools import TOOLS
from .repositories.markets import MarketsRepository
from .repositories.trades import TradesRepository
from .repositories.wallets import WalletsRepository
from .analysis import (
    get_top_traders_by_sharpe,
    TraderMetrics,
    get_top_volume_trades,
    find_consensus_bets,
    analyze_trader
)


class TradingBot:
    """AI-powered Polymarket trading bot."""
    
    def __init__(
        self,
        ai_provider: AIProvider,
        initial_balance: float = 100.0,
        dry_run: bool = True,
        polymarket_client=None,
        wallet_address: str = None,
        max_single_bet_pct: float = 1.0
    ):
        """
        Initialize trading bot.
        
        Args:
            ai_provider: AI provider instance (ChatGPT or Claude)
            initial_balance: Starting balance in USD
            dry_run: If True, simulates bets without real execution
            polymarket_client: Polymarket CLOB client for live trading
            wallet_address: Wallet address for fetching real trade history
            max_single_bet_pct: Maximum percentage of available balance for a single bet
        """
        self.ai_provider = ai_provider
        self.dry_run = dry_run
        self.polymarket_client = polymarket_client
        self.wallet_address = wallet_address
        self.max_single_bet_pct = max(0.0, min(1.0, max_single_bet_pct))
        
        # Initialize repositories
        self.markets_repo = MarketsRepository()
        self.trades_repo = TradesRepository()
        self.wallets_repo = WalletsRepository()
        
        # Track positions
        self.positions = []
        self.simulated_trades = []
        
        # Set initial balance
        if dry_run:
            self.balance = 50.0  # Always $50 in dry-run
        else:
            if wallet_address:
                real_balance = self.wallets_repo.get_balance(wallet_address)
                if real_balance is not None:
                    self.balance = real_balance
                    print(f"✅ Fetched real balance: ${self.balance:.2f}")
                else:
                    self.balance = initial_balance
                    print(f"⚠️  Using provided balance: ${self.balance:.2f}")
            else:
                self.balance = initial_balance
        
        # Cache for top traders
        self.top_traders_cache = None
        self.cache_time = None
    
    def get_available_funds(self) -> Dict[str, Any]:
        """Get current available balance minus open orders."""
        if not self.dry_run and self.polymarket_client:
            try:
                real_balance = self.wallets_repo.get_balance(self.wallet_address)
                if real_balance is not None:
                    self.balance = real_balance
            except Exception as e:
                print(f"  [Warning: Could not refresh balance: {e}]")
        
        # Calculate locked funds in open orders
        locked_in_orders = 0.0
        if not self.dry_run and self.polymarket_client:
            try:
                orders = self.polymarket_client.get_orders()
                for order in orders:
                    if order.get('status') == 'LIVE':
                        original_size = float(order.get('original_size', 0))
                        size_matched = float(order.get('size_matched', 0))
                        price = float(order.get('price', 0))
                        remaining_size = original_size - size_matched
                        locked_in_orders += remaining_size * price
            except Exception as e:
                print(f"  [Warning: Could not fetch open orders: {e}]")
        
        available_balance = self.balance - locked_in_orders
        
        return {
            "balance_usd": round(self.balance, 2),
            "locked_in_orders": round(locked_in_orders, 2),
            "available_balance": round(available_balance, 2),
            "positions_count": len(self.positions),
            "total_invested": round(sum(p['amount'] for p in self.positions), 2),
            "available_for_trading": round(available_balance, 2),
            "max_single_bet": round(available_balance * self.max_single_bet_pct, 2),
            "max_single_bet_pct": f"{int(self.max_single_bet_pct * 100)}%",
            "target_deployment": "100% of balance",
            "mode": "DRY_RUN" if self.dry_run else "LIVE"
        }
    
    def get_current_positions(self) -> List[Dict[str, Any]]:
        """Get all current open positions."""
        if not self.positions:
            return []
        
        positions_list = []
        for i, pos in enumerate(self.positions, 1):
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
        if self.dry_run:
            if not self.simulated_trades:
                return {
                    "total_trades": 0,
                    "trades": [],
                    "message": "No trades placed yet (dry-run mode)"
                }
            
            recent_trades = self.simulated_trades[-limit:]
            
            return {
                "total_trades": len(self.simulated_trades),
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
            if not self.wallet_address:
                return {
                    "error": "No wallet address configured",
                    "message": "Set POLYMARKET_WALLET in .env file"
                }
            
            print(f"  [Fetching trade history for wallet...]")
            try:
                trades = self.trades_repo.get_active_trades(self.wallet_address, limit=limit)
                
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
        total_invested = sum(p['amount'] for p in self.positions)
        unique_markets = len(set(p['market_slug'] for p in self.positions))
        avg_position_size = total_invested / len(self.positions) if self.positions else 0
        largest_position = max((p['amount'] for p in self.positions), default=0)
        
        if self.dry_run:
            total_trades_count = len(self.simulated_trades)
        else:
            if self.wallet_address:
                try:
                    trades = self.trades_repo.get_active_trades(self.wallet_address, limit=500)
                    total_trades_count = len(trades)
                except:
                    total_trades_count = 0
            else:
                total_trades_count = 0
        
        return {
            "balance": {
                "available": round(self.balance, 2),
                "invested": round(total_invested, 2),
                "total_capital": round(self.balance + total_invested, 2)
            },
            "positions": {
                "count": len(self.positions),
                "unique_markets": unique_markets,
                "avg_position_size": round(avg_position_size, 2),
                "largest_position": round(largest_position, 2)
            },
            "risk_metrics": {
                "capital_deployed_pct": round((total_invested / (self.balance + total_invested) * 100) if (self.balance + total_invested) > 0 else 0, 2),
                "target_deployment_pct": "100%",
                "diversification_score": f"{unique_markets}/{len(self.positions)}" if self.positions else "N/A",
                "max_single_bet_allowed": round(self.balance * self.max_single_bet_pct, 2),
                "max_single_bet_pct": f"{int(self.max_single_bet_pct * 100)}%"
            },
            "trading_activity": {
                "total_trades": total_trades_count,
                "mode": "DRY_RUN" if self.dry_run else "LIVE"
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
    
    def place_bet(self, market_slug: str, outcome: str, amount_usd: float, reasoning: str) -> Dict[str, Any]:
        """Place a bet (dry-run or live)."""
        if amount_usd > self.balance:
            return {
                "success": False,
                "error": "Insufficient funds",
                "balance": self.balance
            }
        
        market_info = self.get_market_details(market_slug)
        
        print(f"\n  💰 {'[DRY RUN] ' if self.dry_run else ''}PLACING BET:")
        print(f"     Market: {market_info.get('title', market_slug)}")
        print(f"     Description: {market_info.get('description', 'N/A')[:100]}...")
        print(f"     Outcome: {outcome}")
        print(f"     Amount: ${amount_usd:.2f}")
        print(f"     Reasoning: {reasoning}")
        
        if self.dry_run:
            return self._place_bet_dry_run(market_slug, market_info, outcome, amount_usd, reasoning)
        else:
            return self._place_bet_live(market_slug, market_info, outcome, amount_usd, reasoning)
    
    def _place_bet_dry_run(self, market_slug: str, market_info: Dict, outcome: str, amount_usd: float, reasoning: str) -> Dict[str, Any]:
        """Place a simulated bet."""
        self.balance -= amount_usd
        
        position = {
            "market_slug": market_slug,
            "market_title": market_info.get('title', market_slug),
            "outcome": outcome,
            "amount": amount_usd,
            "reasoning": reasoning,
            "timestamp": datetime.now().isoformat(),
            "mode": "DRY_RUN"
        }
        self.positions.append(position)
        self.simulated_trades.append(position)
        
        print(f"     ✅ Simulated bet placed")
        print(f"     New Balance: ${self.balance:.2f}")
        
        return {
            "success": True,
            "market_slug": market_slug,
            "market_title": market_info.get('title', market_slug),
            "outcome": outcome,
            "amount_usd": amount_usd,
            "new_balance": round(self.balance, 2),
            "mode": "DRY_RUN"
        }
    
    def _place_bet_live(self, market_slug: str, market_info: Dict, outcome: str, amount_usd: float, reasoning: str) -> Dict[str, Any]:
        """Place a live bet."""
        if not self.polymarket_client:
            return {
                "success": False,
                "error": "Polymarket client not initialized"
            }
        
        try:
            from py_clob_client.clob_types import OrderArgs, OrderType
            from py_clob_client.order_builder.constants import BUY
            
            # Get token IDs
            clob_token_ids_str = market_info.get('clob_token_ids', '[]')
            outcomes_str = market_info.get('outcomes', '[]')
            
            try:
                token_ids = json.loads(clob_token_ids_str) if isinstance(clob_token_ids_str, str) else clob_token_ids_str
                outcomes = json.loads(outcomes_str) if isinstance(outcomes_str, str) else outcomes_str
            except json.JSONDecodeError:
                return {"success": False, "error": "Invalid token IDs format"}
            
            if not token_ids or not outcomes:
                return {"success": False, "error": "Market does not have valid token IDs"}
            
            # Map outcome to token_id
            outcome_index = None
            for i, outcome_name in enumerate(outcomes):
                if outcome_name.lower() == outcome.lower():
                    outcome_index = i
                    break
            
            if outcome_index is None:
                return {"success": False, "error": f"Outcome '{outcome}' not found. Available: {outcomes}"}
            
            token_id = token_ids[outcome_index]
            
            # Get current price
            current_price = self.markets_repo.get_price(token_id, side='SELL')
            if current_price is None:
                current_price = 0.5
            
            current_price = min(max(current_price, 0.001), 0.998)
            print(f"     [Fetched current price: ${current_price:.4f}]")
            
            # Calculate shares
            shares = amount_usd / current_price
            
            # Create and post order
            order = self.polymarket_client.create_order(
                OrderArgs(
                    price=Decimal(str(current_price)),
                    size=Decimal(str(shares)),
                    side=BUY,
                    token_id=token_id
                )
            )
            
            order_response = self.polymarket_client.post_order(order, OrderType.GTC)
            
            if order_response and order_response.get('success'):
                self.balance -= amount_usd
                
                position = {
                    "market_slug": market_slug,
                    "market_title": market_info.get('title', market_slug),
                    "outcome": outcome,
                    "amount": amount_usd,
                    "reasoning": reasoning,
                    "timestamp": datetime.now().isoformat(),
                    "order_id": order_response.get('orderID', 'N/A'),
                    "token_id": token_id,
                    "price": current_price,
                    "shares": shares,
                    "mode": "LIVE"
                }
                self.positions.append(position)
                
                print(f"     ✅ Live bet placed successfully!")
                print(f"     Order ID: {order_response.get('orderID', 'N/A')}")
                print(f"     New Balance: ${self.balance:.2f}")
                
                return {
                    "success": True,
                    "market_slug": market_slug,
                    "market_title": market_info.get('title', market_slug),
                    "outcome": outcome,
                    "amount_usd": amount_usd,
                    "new_balance": round(self.balance, 2),
                    "order_id": order_response.get('orderID', 'N/A'),
                    "mode": "LIVE"
                }
            else:
                error_msg = order_response.get('errorMsg', 'Unknown error') if order_response else 'No response'
                return {"success": False, "error": f"Order failed: {error_msg}"}
                
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": f"Error placing live bet: {str(e)}",
                "traceback": traceback.format_exc()
            }
    
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
    
    def execute_function(self, function_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a function call from AI."""
        function_map = {
            "get_available_funds": self.get_available_funds,
            "get_current_positions": self.get_current_positions,
            "get_trade_history": self.get_trade_history,
            "get_portfolio_summary": self.get_portfolio_summary,
            "get_top_traders": self.get_top_traders,
            "get_trader_top_trades": self.get_trader_top_trades,
            "get_consensus_bets": self.get_consensus_bets,
            "get_market_details": self.get_market_details,
            "get_active_markets": self.get_active_markets,
            "place_bet": self.place_bet,
            "search_news": self.search_news,
            "read_knowledge_base": self.read_knowledge_base,
            "get_suggested_whales": self.get_suggested_whales
        }
        
        func = function_map.get(function_name)
        if func:
            return func(**arguments)
        else:
            return {"error": f"Unknown function: {function_name}"}
    
    def run_trading_session(self, max_iterations: int = 10):
        """Run an AI trading session."""
        print("=" * 80)
        print("AI-POWERED POLYMARKET TRADING BOT")
        print("=" * 80)
        print(f"Mode: {'DRY RUN (Simulated)' if self.dry_run else 'LIVE TRADING'}")
        print(f"AI Provider: {self.ai_provider.get_name()}")
        print(f"Starting Balance: ${self.balance:.2f}")
        print(f"Risk Profile: AGGRESSIVE")
        print("=" * 80)
        print()
        
        # Get current date/time and inject into system prompt
        current_datetime = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p %Z")
        system_prompt = get_system_prompt(current_datetime)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Analyze Polymarket trading opportunities and EXECUTE trades."}
        ]
        
        for iteration in range(max_iterations):
            print(f"\n{'='*80}")
            print(f"ITERATION {iteration + 1}/{max_iterations}")
            print(f"{'='*80}\n")
            
            # Get AI response
            response = self.ai_provider.chat(messages, TOOLS)
            
            if not response:
                print("Failed to get response from AI")
                break
            
            choice = response['choices'][0]
            message = choice['message']
            
            # Add assistant message to history
            messages.append(message)
            
            # Check if done
            if choice['finish_reason'] == 'stop':
                print("\n🤖 AI Analysis:")
                print(message.get('content', ''))
                break
            
            # Handle tool calls
            if choice['finish_reason'] == 'tool_calls':
                tool_calls = message.get('tool_calls', [])
                
                for tool_call in tool_calls:
                    function_name = tool_call['function']['name']
                    arguments = json.loads(tool_call['function']['arguments'])
                    
                    print(f"🔧 Calling: {function_name}({json.dumps(arguments, indent=2)})")
                    
                    # Execute function
                    result = self.execute_function(function_name, arguments)
                    
                    # Add result to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call['id'],
                        "content": json.dumps(result)
                    })
                    
                    print(f"✓ Result: {json.dumps(result, indent=2)[:200]}...")
            
            time.sleep(1)
        
        # Final summary
        print("\n" + "=" * 80)
        print("TRADING SESSION COMPLETE")
        print("=" * 80)
        print(f"Final Balance: ${self.balance:.2f}")
        print(f"Total Bets Placed: {len(self.positions)}")
        print(f"Total Invested: ${sum(p['amount'] for p in self.positions):.2f}")
        
        if self.positions:
            print("\nPositions:")
            for i, pos in enumerate(self.positions, 1):
                print(f"  {i}. {pos['market_slug']} - {pos['outcome']} (${pos['amount']:.2f})")
                print(f"     Reasoning: {pos['reasoning']}")
        
        print("=" * 80)

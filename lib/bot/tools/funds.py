"""Funds and balance related tools."""
from typing import Dict, Any, List
from .base import BaseTool
from ...repositories.trades import TradesRepository


class GetAvailableFundsTool(BaseTool):
    """Get available funds for trading."""
    
    @property
    def name(self) -> str:
        return "get_available_funds"
    
    @property
    def description(self) -> str:
        return "Get the current available USDC balance for trading, number of open positions, and total invested amount"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }
    
    def execute(self, bot, **kwargs) -> Dict[str, Any]:
        """Get current available balance minus open orders."""
        from ...repositories.wallets import WalletsRepository
        
        if not bot.dry_run and bot.polymarket_client:
            try:
                wallets_repo = WalletsRepository()
                real_balance = wallets_repo.get_balance(bot.wallet_address)
                if real_balance is not None:
                    bot.balance = real_balance
            except Exception as e:
                print(f"  [Warning: Could not refresh balance: {e}]")
        
        # Calculate locked funds in open orders
        locked_in_orders = 0.0
        if not bot.dry_run and bot.polymarket_client:
            try:
                orders = bot.polymarket_client.get_orders()
                for order in orders:
                    if order.get('status') == 'LIVE':
                        original_size = float(order.get('original_size', 0))
                        size_matched = float(order.get('size_matched', 0))
                        price = float(order.get('price', 0))
                        remaining_size = original_size - size_matched
                        locked_in_orders += remaining_size * price
            except Exception as e:
                print(f"  [Warning: Could not fetch open orders: {e}]")
        
        available_balance = bot.balance - locked_in_orders
        
        return {
            "balance_usd": round(bot.balance, 2),
            "locked_in_orders": round(locked_in_orders, 2),
            "available_balance": round(available_balance, 2),
            "positions_count": len(bot.positions),
            "total_invested": round(sum(p['amount'] for p in bot.positions), 2),
            "available_for_trading": round(available_balance, 2),
            "max_single_bet": round(available_balance * bot.max_single_bet_pct, 2),
            "max_single_bet_pct": f"{int(bot.max_single_bet_pct * 100)}%",
            "target_deployment": "100% of balance",
            "mode": "DRY_RUN" if bot.dry_run else "LIVE"
        }


class GetCurrentPositionsTool(BaseTool):
    """Get current open positions."""
    
    @property
    def name(self) -> str:
        return "get_current_positions"
    
    @property
    def description(self) -> str:
        return "Get all currently open trading positions with details including market, outcome, amount invested, reasoning, and timestamp"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }
    
    def execute(self, bot, **kwargs) -> List[Dict[str, Any]]:
        """Get all current open positions."""
        if not bot.positions:
            return []
        
        positions_list = []
        for i, pos in enumerate(bot.positions, 1):
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


class GetPortfolioSummaryTool(BaseTool):
    """Get portfolio summary."""
    
    @property
    def name(self) -> str:
        return "get_portfolio_summary"
    
    @property
    def description(self) -> str:
        return "Get comprehensive portfolio summary including balance, positions, diversification, and risk metrics"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }
    
    def execute(self, bot, **kwargs) -> Dict[str, Any]:
        """Get comprehensive portfolio summary."""
        total_invested = sum(p['amount'] for p in bot.positions)
        unique_markets = len(set(p['market_slug'] for p in bot.positions))
        avg_position_size = total_invested / len(bot.positions) if bot.positions else 0
        largest_position = max((p['amount'] for p in bot.positions), default=0)
        
        if bot.dry_run:
            total_trades_count = len(bot.simulated_trades)
        else:
            if bot.wallet_address:
                try:
                    trades_repo = TradesRepository()
                    trades = trades_repo.get_active_trades(bot.wallet_address, limit=500)
                    total_trades_count = len(trades)
                except:
                    total_trades_count = 0
            else:
                total_trades_count = 0
        
        return {
            "balance": {
                "available": round(bot.balance, 2),
                "invested": round(total_invested, 2),
                "total_capital": round(bot.balance + total_invested, 2)
            },
            "positions": {
                "count": len(bot.positions),
                "unique_markets": unique_markets,
                "avg_position_size": round(avg_position_size, 2),
                "largest_position": round(largest_position, 2)
            },
            "risk_metrics": {
                "capital_deployed_pct": round((total_invested / (bot.balance + total_invested) * 100) if (bot.balance + total_invested) > 0 else 0, 2),
                "target_deployment_pct": "100%",
                "diversification_score": f"{unique_markets}/{len(bot.positions)}" if bot.positions else "N/A",
                "max_single_bet_allowed": round(bot.balance * bot.max_single_bet_pct, 2),
                "max_single_bet_pct": f"{int(bot.max_single_bet_pct * 100)}%"
            },
            "trading_activity": {
                "total_trades": total_trades_count,
                "mode": "DRY_RUN" if bot.dry_run else "LIVE"
            }
        }

"""Bet placement logic for live and dry-run trading."""
import json
from typing import Dict, Any, Optional
from datetime import datetime
from decimal import Decimal


class BetPlacer:
    """Handles bet placement for both dry-run and live trading."""
    
    def __init__(self, bot):
        """
        Initialize bet placer.
        
        Args:
            bot: Reference to parent TradingBot instance
        """
        self.bot = bot
    
    def place_bet(self, market_slug: str, outcome: str, amount_usd: float, reasoning: str) -> Dict[str, Any]:
        """Place a bet (dry-run or live)."""
        if amount_usd > self.bot.balance:
            return {
                "success": False,
                "error": "Insufficient funds",
                "balance": self.bot.balance
            }
        
        # Get market details using the tool
        from .tools.markets import GetMarketDetailsTool
        market_details_tool = GetMarketDetailsTool()
        market_info = market_details_tool.execute(self.bot, market_slug=market_slug)
        
        print(f"\n  💰 {'[DRY RUN] ' if self.bot.dry_run else ''}PLACING BET:")
        print(f"     Market: {market_info.get('title', market_slug)}")
        print(f"     Description: {market_info.get('description', 'N/A')[:100]}...")
        print(f"     Outcome: {outcome}")
        print(f"     Amount: ${amount_usd:.2f}")
        print(f"     Reasoning: {reasoning}")
        
        if self.bot.dry_run:
            return self._place_bet_dry_run(market_slug, market_info, outcome, amount_usd, reasoning)
        else:
            return self._place_bet_live(market_slug, market_info, outcome, amount_usd, reasoning)
    
    def _place_bet_dry_run(self, market_slug: str, market_info: Dict, outcome: str, amount_usd: float, reasoning: str) -> Dict[str, Any]:
        """Place a simulated bet."""
        self.bot.balance -= amount_usd
        
        position = {
            "market_slug": market_slug,
            "market_title": market_info.get('title', market_slug),
            "outcome": outcome,
            "amount": amount_usd,
            "reasoning": reasoning,
            "timestamp": datetime.now().isoformat(),
            "mode": "DRY_RUN"
        }
        self.bot.positions.append(position)
        self.bot.simulated_trades.append(position)
        
        print(f"     ✅ Simulated bet placed")
        print(f"     New Balance: ${self.bot.balance:.2f}")
        
        return {
            "success": True,
            "market_slug": market_slug,
            "market_title": market_info.get('title', market_slug),
            "outcome": outcome,
            "amount_usd": amount_usd,
            "new_balance": round(self.bot.balance, 2),
            "mode": "DRY_RUN"
        }
    
    def _place_bet_live(self, market_slug: str, market_info: Dict, outcome: str, amount_usd: float, reasoning: str) -> Dict[str, Any]:
        """Place a live bet."""
        if not self.bot.polymarket_client:
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
            from ..repositories.markets import MarketsRepository
            markets_repo = MarketsRepository()
            current_price = markets_repo.get_price(token_id, side='SELL')
            if current_price is None:
                current_price = 0.5
            
            current_price = min(max(current_price, 0.001), 0.998)
            print(f"     [Fetched current price: ${current_price:.4f}]")
            
            # Calculate shares
            shares = amount_usd / current_price
            
            # Create and post order
            order = self.bot.polymarket_client.create_order(
                OrderArgs(
                    price=Decimal(str(current_price)),
                    size=Decimal(str(shares)),
                    side=BUY,
                    token_id=token_id
                )
            )
            
            order_response = self.bot.polymarket_client.post_order(order, OrderType.GTC)
            
            if order_response and order_response.get('success'):
                self.bot.balance -= amount_usd
                
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
                self.bot.positions.append(position)
                
                print(f"     ✅ Live bet placed successfully!")
                print(f"     Order ID: {order_response.get('orderID', 'N/A')}")
                print(f"     New Balance: ${self.bot.balance:.2f}")
                
                return {
                    "success": True,
                    "market_slug": market_slug,
                    "market_title": market_info.get('title', market_slug),
                    "outcome": outcome,
                    "amount_usd": amount_usd,
                    "new_balance": round(self.bot.balance, 2),
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

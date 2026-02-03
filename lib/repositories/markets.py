from typing import List, Dict, Optional
from datetime import datetime
from .base import BaseRepository


class MarketsRepository(BaseRepository):
    """Repository for market-related operations."""
    
    GAMMA_URL = "https://gamma-api.polymarket.com"
    CLOB_URL = "https://clob.polymarket.com"
    
    def __init__(self):
        super().__init__(self.GAMMA_URL)
        self.clob_base = self.CLOB_URL
    
    def get_by_slug(self, slug: str) -> Optional[Dict]:
        """Get market details by slug."""
        return self._get(f"/markets/slug/{slug}")
    
    def get_active_markets(self, limit: int = 20) -> List[Dict]:
        """Get active markets."""
        return self._get_list("/markets", params={'limit': limit, 'active': True})
    
    def get_price(self, token_id: str, side: str = 'SELL') -> Optional[float]:
        """
        Get current price for a token from CLOB.
        
        Args:
            token_id: Token ID to get price for
            side: 'SELL' when buying (default), 'BUY' when selling
        
        Returns:
            Price as float, or None if error
        """
        try:
            response = self._get(
                f"{self.clob_base}/price",
                params={'token_id': token_id, 'side': side}
            )
            if response:
                return float(response.get('price', 0.5))
        except Exception as e:
            print(f"Error fetching price: {e}")
        return None
    
    def is_active(self, market_slug: str) -> bool:
        """Check if a market is still active and accepting trades."""
        market = self.get_by_slug(market_slug)
        
        if not market:
            return False
        
        is_active = market.get('active', False)
        is_closed = market.get('closed', True)
        accepting_orders = market.get('acceptingOrders', False)
        
        # Check end date
        end_date = market.get('endDate')
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                now = datetime.now(end_dt.tzinfo)
                if now > end_dt:
                    return False
            except:
                pass
        
        return is_active and not is_closed and accepting_orders
    
    def get_market_details(self, market_slug: str) -> Optional[Dict]:
        """Get comprehensive market details including status and trading info."""
        market = self.get_by_slug(market_slug)
        
        if not market:
            return None
        
        is_active = market.get('active', False)
        is_closed = market.get('closed', True)
        accepting_orders = market.get('acceptingOrders', False)
        tradeable = is_active and not is_closed and accepting_orders
        
        maker_fee = market.get('makerBaseFee', 0)
        taker_fee = market.get('takerBaseFee', 0)
        fee_info = "No fees (0%)" if maker_fee == 0 and taker_fee == 0 else f"Maker: {maker_fee}%, Taker: {taker_fee}%"
        
        return {
            "market_slug": market_slug,
            "title": market.get('question', 'Unknown'),
            "description": market.get('description', 'No description available'),
            "active": is_active,
            "closed": is_closed,
            "accepting_orders": accepting_orders,
            "tradeable": tradeable,
            "end_date": market.get('endDate', 'Unknown'),
            "category": market.get('category', 'Unknown'),
            "volume": round(float(market.get('volume', 0)), 2),
            "liquidity": round(float(market.get('liquidity', 0)), 2),
            "fees": fee_info,
            "outcomes": market.get('outcomes', '[]'),
            "condition_id": market.get('conditionId', ''),
            "clob_token_ids": market.get('clobTokenIds', '[]'),
            "trading_info": {
                "minimum_trade": "No minimum (can trade fractional shares)",
                "settlement": "Shares worth $1 if outcome occurs, $0 otherwise",
                "liquidity": "Can exit position anytime at current market price"
            },
            "warning": "⚠️ Market is CLOSED or not accepting orders - cannot place new bets" if not tradeable else None
        }

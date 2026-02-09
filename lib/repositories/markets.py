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
        """Get active markets using closed=false API parameter."""
        # Use the API's closed parameter to filter at source
        raw_markets = self._get_list("/markets", params={
            'limit': limit,
            'closed': 'false',
            'active': 'true'
        })
        
        if not raw_markets:
            return []
        
        # Additional filtering for quality
        current_year = datetime.now().year
        filtered_markets = []
        
        for market in raw_markets:
            # Skip if not accepting orders
            if not market.get('acceptingOrders', False):
                continue
            
            # Skip if question mentions old years (2020-2023)
            question = market.get('question', '').lower()
            has_old_year = any(str(year) in question for year in range(2020, current_year))
            if has_old_year:
                continue
            
            # Normalize the slug field name for consistency
            if 'slug' in market and 'market_slug' not in market:
                market['market_slug'] = market['slug']
            
            filtered_markets.append(market)
            
            if len(filtered_markets) >= limit:
                break
        
        return filtered_markets
    
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
            # Make direct request to CLOB (not using base_url)
            import requests
            response = requests.get(
                f"{self.clob_base}/price",
                params={'token_id': token_id, 'side': side},
                timeout=10
            )
            if response.ok:
                data = response.json()
                return float(data.get('price', 0.5))
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
        
        # Check end date - reject if already passed
        end_date = market.get('endDate')
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                now = datetime.now(end_dt.tzinfo)
                if now > end_dt:
                    return False
            except:
                pass
        
        # Check if market is too old (created more than 2 years ago)
        created_at = market.get('createdAt')
        if created_at:
            try:
                created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                now = datetime.now(created_dt.tzinfo)
                age_days = (now - created_dt).days
                if age_days > 730:  # More than 2 years old
                    return False
            except:
                pass
        
        # Check if question mentions old dates (like "2020", "2021", "2022", "2023")
        question = market.get('question', '').lower()
        current_year = datetime.now().year
        for year in range(2020, current_year):
            if str(year) in question:
                return False
        
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
        
        # Get current prices for each outcome
        import json
        outcomes_str = market.get('outcomes', '[]')
        token_ids_str = market.get('clobTokenIds', '[]')
        
        try:
            outcomes = json.loads(outcomes_str) if isinstance(outcomes_str, str) else outcomes_str
            token_ids = json.loads(token_ids_str) if isinstance(token_ids_str, str) else token_ids_str
        except:
            outcomes = []
            token_ids = []
        
        # Fetch current prices
        outcome_prices = {}
        if outcomes and token_ids and len(outcomes) == len(token_ids):
            for outcome, token_id in zip(outcomes, token_ids):
                price = self.get_price(token_id, side='SELL')
                if price:
                    outcome_prices[outcome] = {
                        "current_price": round(price, 4),
                        "potential_return": round((1.0 / price - 1.0) * 100, 2) if price > 0 else 0,
                        "implied_probability": round(price * 100, 2),
                        "cost_per_share": round(price, 4),
                        "payout_if_wins": "$1.00 per share"
                    }
        
        result = {
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
            "outcomes": outcomes_str,
            "condition_id": market.get('conditionId', ''),
            "clob_token_ids": token_ids_str,
            "trading_info": {
                "minimum_trade": "No minimum (can trade fractional shares)",
                "settlement": "Shares worth $1 if outcome occurs, $0 otherwise",
                "liquidity": "Can exit position anytime at current market price"
            }
        }
        
        # Add outcome prices if available
        if outcome_prices:
            result["outcome_prices"] = outcome_prices
        
        # Add warning if not tradeable
        if not tradeable:
            result["warning"] = "⚠️ Market is CLOSED or not accepting orders - cannot place new bets"
        
        # Add warning for old markets
        question = market.get('question', '').lower()
        current_year = datetime.now().year
        for year in range(2020, current_year):
            if str(year) in question:
                result["warning"] = f"⚠️ OLD MARKET - Question mentions {year}. This market is likely resolved or outdated."
                break
        
        # Check if market is very old
        created_at = market.get('createdAt')
        if created_at:
            try:
                created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                now = datetime.now(created_dt.tzinfo)
                age_days = (now - created_dt).days
                if age_days > 730:
                    result["warning"] = f"⚠️ VERY OLD MARKET - Created {age_days} days ago. Likely resolved or outdated."
            except:
                pass
        
        return result

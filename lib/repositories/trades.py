from typing import List, Dict
from .base import BaseRepository


class TradesRepository(BaseRepository):
    """Repository for trade-related operations."""
    
    GAMMA_URL = "https://gamma-api.polymarket.com"
    
    def __init__(self):
        super().__init__(self.GAMMA_URL)
    
    def get_by_wallet(self, wallet: str, limit: int = 100) -> List[Dict]:
        """
        Get trades for a specific wallet.
        
        Args:
            wallet: Wallet address
            limit: Maximum number of trades to return
        
        Returns:
            List of trade dicts
        """
        return self._get_list("/trades", params={'wallet': wallet, 'limit': limit})
    
    def get_top_volume_trades(self, wallet: str, n: int = 10) -> List[Dict]:
        """
        Get top N highest volume trades for a wallet.
        
        Args:
            wallet: Wallet address
            n: Number of top trades to return
        
        Returns:
            List of top trades sorted by volume
        """
        trades = self.get_by_wallet(wallet, limit=500)
        
        if not trades:
            return []
        
        # Calculate volume and sort
        for trade in trades:
            trade['volume'] = float(trade.get('size', 0)) * float(trade.get('price', 0))
        
        trades.sort(key=lambda x: x['volume'], reverse=True)
        return trades[:n]
    
    def get_active_trades(self, wallet: str, limit: int = 100) -> List[Dict]:
        """
        Get only trades in active markets.
        
        Args:
            wallet: Wallet address
            limit: Maximum number of trades to check
        
        Returns:
            List of trades in active markets
        """
        from .markets import MarketsRepository
        
        trades = self.get_by_wallet(wallet, limit=limit)
        markets_repo = MarketsRepository()
        
        active_trades = []
        for trade in trades:
            market_slug = trade.get('slug', '')
            if market_slug and markets_repo.is_active(market_slug):
                active_trades.append(trade)
        
        return active_trades

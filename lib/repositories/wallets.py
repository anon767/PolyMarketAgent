from typing import List, Dict, Optional
from .base import BaseRepository


class WalletsRepository(BaseRepository):
    """Repository for wallet-related operations."""
    
    GAMMA_URL = "https://gamma-api.polymarket.com"
    POLYWHALER_URL = "https://www.polywhaler.com"
    
    def __init__(self):
        super().__init__(self.GAMMA_URL)
    
    def get_leaderboard(self, limit: int = 100) -> List[Dict]:
        """
        Get leaderboard data.
        
        Args:
            limit: Maximum number of traders to return
        
        Returns:
            List of leaderboard entries with trader info
        """
        return self._get_list("/leaderboard", params={'limit': limit})
    
    def get_balance(self, wallet_address: str) -> Optional[float]:
        """
        Get USDC balance for a wallet from Polygon blockchain.
        
        Args:
            wallet_address: Wallet address to check
        
        Returns:
            Balance in USDC, or None if error
        """
        try:
            from web3 import Web3
            
            w3 = Web3(Web3.HTTPProvider('https://polygon-rpc.com'))
            
            if not w3.is_connected():
                return None
            
            # USDC contract on Polygon
            usdc_address = Web3.to_checksum_address('0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174')
            
            # ERC20 ABI for balanceOf
            erc20_abi = [{
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            }]
            
            usdc_contract = w3.eth.contract(address=usdc_address, abi=erc20_abi)
            wallet_checksum = Web3.to_checksum_address(wallet_address)
            balance_wei = usdc_contract.functions.balanceOf(wallet_checksum).call()
            
            # USDC has 6 decimals
            return float(balance_wei / 1_000_000)
            
        except Exception as e:
            print(f"  [Could not fetch balance: {e}]")
            return None
    
    def get_suggested_whales(self, limit: int = 50) -> List[Dict]:
        """
        Get recommended whale traders from PolyWhaler.com.
        
        Args:
            limit: Maximum number of whales to return
        
        Returns:
            List of whale trader info
        """
        try:
            response = self._get(
                f"{self.POLYWHALER_URL}/api/suggested-whales",
                params={'limit': limit}
            )
            if response:
                return response.get('suggestions', [])
        except Exception as e:
            print(f"Error fetching suggested whales: {e}")
        return []

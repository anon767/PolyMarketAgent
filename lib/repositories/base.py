import requests
from typing import Optional, Dict, Any


class BaseRepository:
    """Base repository with common request handling."""
    
    def __init__(self, base_url: str, timeout: int = 10):
        self.base_url = base_url
        self.timeout = timeout
    
    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict]:
        """Make GET request and return JSON response."""
        try:
            response = requests.get(
                f"{self.base_url}{endpoint}",
                params=params,
                timeout=self.timeout
            )
            if response.ok:
                return response.json()
        except Exception as e:
            print(f"Error in GET {endpoint}: {e}")
        return None
    
    def _get_list(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> list:
        """Make GET request and return list response."""
        result = self._get(endpoint, params)
        return result if isinstance(result, list) else []

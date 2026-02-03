from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class AIProvider(ABC):
    """Abstract base class for AI providers."""
    
    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], tools: List[Dict], 
             retry_count: int = 0, max_retries: int = 5) -> Optional[Dict]:
        """Send messages and get response."""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get provider name."""
        pass

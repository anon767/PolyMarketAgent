"""Polymarket trading bot library."""
from .bot import TradingBot
from .providers import AIProvider, ChatGPTProvider, ClaudeProvider
from .analysis import get_top_traders_by_sharpe, analyze_trader
from .prompts import get_system_prompt
from .tools import TOOLS

__all__ = [
    'TradingBot',
    'AIProvider',
    'ChatGPTProvider',
    'ClaudeProvider',
    'get_top_traders_by_sharpe',
    'analyze_trader',
    'get_system_prompt',
    'TOOLS'
]

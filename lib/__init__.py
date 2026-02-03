"""Polymarket trading bot library."""
from .bot import TradingBot
from .bot.resources import get_system_prompt, TOOLS
from .providers import AIProvider, ChatGPTProvider, ClaudeProvider
from .analysis import get_top_traders_by_sharpe, analyze_trader

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

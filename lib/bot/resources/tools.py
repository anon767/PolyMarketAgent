TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_available_funds",
            "description": "Get the current available USDC balance for trading, number of open positions, and total invested amount",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_positions",
            "description": "Get all currently open trading positions with details including market, outcome, amount invested, reasoning, and timestamp",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_trade_history",
            "description": "Get complete trading history showing all bets placed during this session with performance metrics",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of trades to return (default: 10)",
                        "default": 10
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_portfolio_summary",
            "description": "Get comprehensive portfolio summary including balance, positions, diversification, and risk metrics",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_traders",
            "description": "Get top N traders ranked by Sharpe ratio (risk-adjusted returns). Returns trader metrics including Sharpe ratio, win rate, max drawdown (percentage loss from peak), P&L, and total trades. Max drawdown shows risk - closer to 0% is better, more negative means higher losses.",
            "parameters": {
                "type": "object",
                "properties": {
                    "n": {
                        "type": "integer",
                        "description": "Number of top traders to return (default: 10, max: 50)",
                        "default": 10
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_trader_top_trades",
            "description": "Get the top N highest volume trades for a specific trader wallet",
            "parameters": {
                "type": "object",
                "properties": {
                    "wallet": {
                        "type": "string",
                        "description": "Trader's wallet address"
                    },
                    "n": {
                        "type": "integer",
                        "description": "Number of top trades to return (default: 5)",
                        "default": 5
                    }
                },
                "required": ["wallet"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_consensus_bets",
            "description": "Find bets where multiple top traders agree (same market and outcome). Returns markets with 2+ traders betting on the same outcome.",
            "parameters": {
                "type": "object",
                "properties": {
                    "min_traders": {
                        "type": "integer",
                        "description": "Minimum number of traders that must agree (default: 2)",
                        "default": 2
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_market_details",
            "description": "Get detailed information about a specific market including title, description, outcomes, and current status. Use this BEFORE placing a bet to understand what you're betting on.",
            "parameters": {
                "type": "object",
                "properties": {
                    "market_slug": {
                        "type": "string",
                        "description": "Market slug identifier"
                    }
                },
                "required": ["market_slug"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_active_markets",
            "description": "Get list of currently active markets on Polymarket",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of markets to return (default: 20)",
                        "default": 20
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "place_bet",
            "description": "Place a bet on a specific market outcome. CRITICAL: You MUST call get_market_details first to understand the market before betting. Use this only after thorough analysis of trader consensus and market conditions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "market_slug": {
                        "type": "string",
                        "description": "Market slug identifier"
                    },
                    "outcome": {
                        "type": "string",
                        "description": "Outcome to bet on (e.g., 'Yes', 'No', or specific option)"
                    },
                    "amount_usd": {
                        "type": "number",
                        "description": "Amount in USD to bet"
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Your detailed reasoning for this bet including: which traders agree, their metrics, consensus strength, and why you believe this is a good opportunity"
                    }
                },
                "required": ["market_slug", "outcome", "amount_usd", "reasoning"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_news",
            "description": "Search for recent news headlines using Google News RSS (no API key required). Useful for understanding current events that might affect prediction markets (politics, sports, crypto, etc.). Returns recent news articles with titles, sources, and publish dates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g., 'Trump election', 'Bitcoin price', 'NFL playoffs', 'Federal Reserve')"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 5)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_knowledge_base",
            "description": "Read the trading knowledge base (kb.txt) which contains 14 proven Polymarket trading strategies and insights from successful traders. Use this to learn advanced strategies like 'Nothing Ever Happens', 'News Scalping', 'Fed Signal Trading', etc.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_suggested_whales",
            "description": "Get recommended whale traders from PolyWhaler.com - these are high-volume traders with recent activity. Returns wallet addresses, names, recent trade counts, volumes, and last trade times. Alternative to get_top_traders for finding active whales.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of suggested whales to return (default: 10)",
                        "default": 50
                    }
                },
                "required": []
            }
        }
    }
]

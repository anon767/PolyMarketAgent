#!/usr/bin/env python3
"""
AI-Powered Polymarket Trading Bot

Uses ChatGPT to analyze top traders and make intelligent trading decisions.
"""

import requests
import json
import time
from typing import List, Dict, Optional, Any
from datetime import datetime
import argparse
from decimal import Decimal
import os
from pathlib import Path

# Import analysis functions
from polymarket_top_traders_analysis import (
    get_top_traders_by_sharpe,
    TraderMetrics,
    PolymarketAPI,
    get_top_volume_trades,
    find_consensus_bets,
    analyze_trader
)


class PolymarketTradingAPI:
    """Extended API for trading operations."""
    
    @staticmethod
    def get_markets(limit: int = 20) -> List[Dict]:
        """Get active markets."""
        try:
            response = requests.get(
                "https://gamma-api.polymarket.com/markets",
                params={'limit': limit, 'active': True},
                timeout=10
            )
            if response.ok:
                return response.json()
        except Exception as e:
            print(f"Error fetching markets: {e}")
        return []
    
    @staticmethod
    def get_market_details(condition_id: str) -> Optional[Dict]:
        """Get detailed market information."""
        try:
            response = requests.get(
                f"https://gamma-api.polymarket.com/markets/{condition_id}",
                timeout=10
            )
            if response.ok:
                return response.json()
        except Exception as e:
            print(f"Error fetching market details: {e}")
        return None
    
    @staticmethod
    def get_market_prices(condition_id: str) -> Optional[Dict]:
        """Get current market prices."""
        try:
            response = requests.get(
                f"https://clob.polymarket.com/prices/{condition_id}",
                timeout=10
            )
            if response.ok:
                return response.json()
        except Exception as e:
            print(f"Error fetching prices: {e}")
        return None


class AITradingBot:
    """AI-powered trading bot using ChatGPT for decision making."""
    
    SYSTEM_PROMPT = """You are an expert Polymarket trading analyst with access to real-time market data and top trader information.

CURRENT DATE AND TIME: {current_datetime}

Your role is to analyze trading opportunities and make intelligent betting decisions based on:
- Top traders' performance metrics (Sharpe ratio, win rate, max drawdown)
- Individual top trader positions (copy trading strategy)
- Consensus bets among successful traders
- Market conditions and prices
- Available funds
- Recent news headlines (always use search_news)
- Trading knowledge base with 14 proven strategies (use read_knowledge_base to learn advanced tactics)
- Get recommended whales!

DECISION FRAMEWORK:
1. Get a number of potential traders:
    a. Recommended whales
    b. Top traders 
    c. Knowledge base
2. Review their recent trades - they have the best risk-adjusted performance
3. ALSO VERY IMPORTANT: review consensus bets where multiple traders agree
4. ALWAYS call get_market_details to understand what you're betting on and use the search news function
5. Check our current orders and positions with get_trade_history() to make a better informed decision based on our current portfolio
6. Evaluate market opportunities with full context
7. Consider risk management (position sizing, diversification)
8. Make informed betting decisions with detailed reasoning

RISK MANAGEMENT RULES - AGGRESSIVE RISK-TAKING:
- Spread across 2-5 different markets for diversification
- For consensus bets: 2+ traders agreeing is sufficient
- For copy trading: prefer traders with Sharpe ratio > 1.0 and win rate > 55%
- Consider both Sharpe ratio AND max drawdown together
- Diversify across different market categories (sports, politics, crypto, etc.)
- Review portfolio summary to ensure you're deploying capital effectively
- TAKE CALCULATED RISKS: Don't only bet on near-certain outcomes
- Consider markets with 40-70% probability where traders show conviction
- Balance safe bets with higher-risk, higher-reward opportunities

IMPORTANT - BE PROACTIVE AND DEPLOY CAPITAL:
- The balance provided is specifically for trading - use it!
- Aim to deploy 80-100% of capital across good opportunities
- If you find 4-5 good bets, place them all (diversification is good)
- Don't just suggest bets - actually place them using place_bet() if it makes sense!
- Always explain your reasoning clearly in the reasoning parameter
- Review your current positions - if you're only 20% deployed, look for more opportunities
- Don't be afraid to be aggressive when the data supports it
- The goal is to follow proven traders and deploy capital efficiently
- AVOID only betting on near-certain outcomes (>90% probability) or markets ending in hours
- Look for opportunities with 40-70% probability where smart traders show conviction

WORKFLOW - FOLLOW THIS EXACTLY:
1. Call get_available_funds() to check balance
2. Call get_trade_history() to understand our portfolio
3. Call read_knowledge_base() to learn 14 proven strategies (REQUIRED - do this!)
4. Call get_top_traders() to see best performers
5. Call get_trader_top_trades() for the #1 trader's recent bets
6. Call get_consensus_bets() to find where multiple traders agree
7. Call get_suggested_whales() to find whales and people with insider knowledge
8. For EACH interesting opportunity:
   a) Call search_news() to check recent developments (REQUIRED for politics/sports/crypto markets)
   b) Call get_market_details() to understand the market
9. Call get_portfolio_summary() to check deployment percentage

CRITICAL: Your job is to EXECUTE trades, not just analyze them!

You have access to these functions to gather information and place bets. Use them wisely."""

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
    
    def __init__(self, ai_provider: str = "chatgpt", openai_api_key: str = None, initial_balance: float = 100.0, dry_run: bool = True, polymarket_client=None, wallet_address: str = None, max_single_bet_pct: float = 1.0):
        """
        Initialize AI trading bot.
        
        Args:
            ai_provider: "chatgpt" or "bedrock"
            openai_api_key: OpenAI API key (only needed for chatgpt)
            initial_balance: Starting balance in USD (ignored in dry_run, uses $50)
            dry_run: If True, simulates bets without real execution
            polymarket_client: Polymarket CLOB client for live trading
            wallet_address: Wallet address for fetching real trade history
            max_single_bet_pct: Maximum percentage of available balance for a single bet (0.0-1.0, default 1.0 = 100%)
        """
        self.ai_provider = ai_provider.lower()
        self.api_key = openai_api_key
        self.dry_run = dry_run
        self.polymarket_client = polymarket_client
        self.wallet_address = wallet_address
        self.max_single_bet_pct = max(0.0, min(1.0, max_single_bet_pct))  # Clamp between 0 and 1
        
        # Initialize Bedrock client if needed
        self.bedrock_client = None
        if self.ai_provider == "bedrock":
            try:
                import boto3
                self.bedrock_client = boto3.client('bedrock-runtime')
                print("✅ Connected to AWS Bedrock")
            except Exception as e:
                print(f"❌ Error connecting to Bedrock: {e}")
                raise
        
        # Track positions (dry-run only)
        self.positions = []
        self.simulated_trades = []  # For dry-run mode only
        
        # Set initial balance
        if dry_run:
            # In dry run mode, always start with $50
            self.balance = 50.0
        else:
            # In live mode, fetch real balance from blockchain
            if wallet_address:
                try:
                    real_balance = self._fetch_real_balance()
                    if real_balance is not None:
                        self.balance = real_balance
                        print(f"✅ Fetched real balance from blockchain: ${self.balance:.2f}")
                    else:
                        print(f"⚠️  Could not fetch balance, using provided: ${initial_balance:.2f}")
                        self.balance = initial_balance
                except Exception as e:
                    print(f"⚠️  Error fetching balance: {e}, using provided: ${initial_balance:.2f}")
                    self.balance = initial_balance
            else:
                self.balance = initial_balance
        
        # Cache for top traders
        self.top_traders_cache = None
        self.cache_time = None
    
    def _fetch_real_balance(self) -> Optional[float]:
        """Fetch real USDC balance from Polygon blockchain."""
        try:
            from web3 import Web3
            
            # Connect to Polygon RPC
            w3 = Web3(Web3.HTTPProvider('https://polygon-rpc.com'))
            
            if not w3.is_connected():
                print(f"  [Could not connect to Polygon RPC]")
                return None
            
            # USDC contract address on Polygon
            usdc_address = Web3.to_checksum_address('0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174')
            
            # ERC20 ABI for balanceOf
            erc20_abi = [
                {
                    "constant": True,
                    "inputs": [{"name": "_owner", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "balance", "type": "uint256"}],
                    "type": "function"
                }
            ]
            
            # Create contract instance
            usdc_contract = w3.eth.contract(address=usdc_address, abi=erc20_abi)
            
            # Get balance - wallet_address should come from env or arg
            wallet_address = Web3.to_checksum_address(self.wallet_address)
            balance_wei = usdc_contract.functions.balanceOf(wallet_address).call()
            
            # USDC has 6 decimals
            balance_usdc = balance_wei / 1_000_000
            
            return float(balance_usdc)
            
        except Exception as e:
            print(f"  [Could not fetch balance from blockchain: {e}]")
            print(f"  [Using initial balance parameter instead]")
            return None
    
    def get_available_funds(self) -> Dict[str, Any]:
        """Get current available balance minus open orders."""
        # In live mode, optionally refresh balance from API
        if not self.dry_run and self.polymarket_client:
            try:
                real_balance = self._fetch_real_balance()
                if real_balance is not None:
                    # Update balance with real value
                    self.balance = real_balance
            except Exception as e:
                print(f"  [Warning: Could not refresh balance: {e}]")
        
        # Calculate locked funds in open orders
        locked_in_orders = 0.0
        if not self.dry_run and self.polymarket_client:
            try:
                orders = self.polymarket_client.get_orders()
                for order in orders:
                    if order.get('status') == 'LIVE':
                        # Calculate locked amount: (original_size - size_matched) * price
                        original_size = float(order.get('original_size', 0))
                        size_matched = float(order.get('size_matched', 0))
                        price = float(order.get('price', 0))
                        remaining_size = original_size - size_matched
                        locked_in_orders += remaining_size * price
            except Exception as e:
                print(f"  [Warning: Could not fetch open orders: {e}]")
        
        available_balance = self.balance - locked_in_orders
        
        return {
            "balance_usd": round(self.balance, 2),
            "locked_in_orders": round(locked_in_orders, 2),
            "available_balance": round(available_balance, 2),
            "positions_count": len(self.positions),
            "total_invested": round(sum(p['amount'] for p in self.positions), 2),
            "available_for_trading": round(available_balance, 2),
            "max_single_bet": round(available_balance * self.max_single_bet_pct, 2),
            "max_single_bet_pct": f"{int(self.max_single_bet_pct * 100)}%",
            "target_deployment": "100% of balance",
            "mode": "DRY_RUN" if self.dry_run else "LIVE"
        }
    
    def get_current_positions(self) -> List[Dict[str, Any]]:
        """Get all current open positions."""
        # In live mode, optionally fetch real positions from API
        if not self.dry_run and self.polymarket_client:
            try:
                real_positions = self._fetch_real_positions()
                if real_positions:
                    print(f"  [Fetched {len(real_positions)} positions from Polymarket API]")
                    return real_positions
            except Exception as e:
                print(f"  [Warning: Could not fetch positions: {e}]")
        
        # Return tracked positions (dry-run or fallback)
        if not self.positions:
            return []
        
        positions_list = []
        for i, pos in enumerate(self.positions, 1):
            positions_list.append({
                "position_number": i,
                "market_slug": pos['market_slug'],
                "market_title": pos.get('market_title', pos['market_slug']),
                "outcome": pos['outcome'],
                "amount_invested": round(pos['amount'], 2),
                "reasoning": pos['reasoning'],
                "timestamp": pos['timestamp'],
                "mode": pos.get('mode', 'DRY_RUN')
            })
        
        return positions_list
    
    def _fetch_real_positions(self) -> Optional[List[Dict[str, Any]]]:
        """Fetch real positions from Polymarket API."""
        try:
            # Try to get positions from CLOB client
            if hasattr(self.polymarket_client, 'get_positions'):
                positions = self.polymarket_client.get_positions()
                
                if positions:
                    formatted_positions = []
                    for i, pos in enumerate(positions, 1):
                        formatted_positions.append({
                            "position_number": i,
                            "market_slug": pos.get('market', 'unknown'),
                            "market_title": pos.get('title', 'Unknown'),
                            "outcome": pos.get('outcome', 'Unknown'),
                            "amount_invested": round(float(pos.get('size', 0)) * float(pos.get('price', 0)), 2),
                            "shares": round(float(pos.get('size', 0)), 2),
                            "avg_price": round(float(pos.get('price', 0)), 4),
                            "mode": "LIVE"
                        })
                    return formatted_positions
            
            return None
            
        except Exception as e:
            print(f"Error fetching positions: {e}")
            return None
    
    def get_trade_history(self, limit: int = 10) -> Dict[str, Any]:
        """Get trading history from Polymarket API (live) or simulated trades (dry-run)."""
        if self.dry_run:
            # Return simulated trades in dry-run mode
            if not self.simulated_trades:
                return {
                    "total_trades": 0,
                    "trades": [],
                    "message": "No trades placed yet (dry-run mode)"
                }
            
            recent_trades = self.simulated_trades[-limit:]
            
            return {
                "total_trades": len(self.simulated_trades),
                "showing": len(recent_trades),
                "mode": "DRY_RUN",
                "trades": [
                    {
                        "market_slug": t['market_slug'],
                        "market_title": t.get('market_title', t['market_slug']),
                        "outcome": t['outcome'],
                        "amount": round(t['amount'], 2),
                        "reasoning": t['reasoning'],
                        "timestamp": t['timestamp']
                    }
                    for t in recent_trades
                ]
            }
        else:
            # Fetch real trades from Polymarket API
            if not self.wallet_address:
                return {
                    "error": "No wallet address configured",
                    "message": "Set POLYMARKET_WALLET in .env file"
                }
            
            print(f"  [Fetching trade history for wallet...]")
            try:
                trades = PolymarketAPI.get_trades(self.wallet_address, limit=limit * 2)  # Get more to filter
                
                # Filter out closed positions (only show open trades)
                open_trades = []
                for trade in trades:
                    market_slug = trade.get('slug', '')
                    if market_slug and self._check_market_active(market_slug):
                        open_trades.append({
                            "market_slug": market_slug,
                            "market_title": trade.get('title', 'Unknown'),
                            "outcome": trade.get('outcome', 'Unknown'),
                            "side": trade.get('side', 'Unknown'),
                            "amount": round(float(trade.get('size', 0)) * float(trade.get('price', 0)), 2),
                            "price": round(float(trade.get('price', 0)), 4),
                            "timestamp": trade.get('timestamp', 0)
                        })
                        
                        if len(open_trades) >= limit:
                            break
                
                return {
                    "total_trades": len(open_trades),
                    "showing": len(open_trades),
                    "mode": "LIVE",
                    "trades": open_trades,
                    "note": "Only showing trades in active markets"
                }
                
            except Exception as e:
                return {
                    "error": str(e),
                    "message": "Could not fetch trade history from Polymarket API"
                }
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get comprehensive portfolio summary."""
        total_invested = sum(p['amount'] for p in self.positions)
        
        # Calculate diversification
        unique_markets = len(set(p['market_slug'] for p in self.positions))
        
        # Calculate risk metrics
        avg_position_size = total_invested / len(self.positions) if self.positions else 0
        largest_position = max((p['amount'] for p in self.positions), default=0)
        
        # Get total trades count
        if self.dry_run:
            total_trades_count = len(self.simulated_trades)
        else:
            # In live mode, fetch active trades from API
            if self.wallet_address:
                try:
                    trades = PolymarketAPI.get_trades(self.wallet_address, limit=500)
                    # Filter only active trades
                    active_trades = [t for t in trades if self._check_market_active(t.get('slug', ''))]
                    total_trades_count = len(active_trades)
                except:
                    total_trades_count = 0
            else:
                total_trades_count = 0
        
        return {
            "balance": {
                "available": round(self.balance, 2),
                "invested": round(total_invested, 2),
                "total_capital": round(self.balance + total_invested, 2)
            },
            "positions": {
                "count": len(self.positions),
                "unique_markets": unique_markets,
                "avg_position_size": round(avg_position_size, 2),
                "largest_position": round(largest_position, 2)
            },
            "risk_metrics": {
                "capital_deployed_pct": round((total_invested / (self.balance + total_invested) * 100) if (self.balance + total_invested) > 0 else 0, 2),
                "target_deployment_pct": "100%",
                "diversification_score": f"{unique_markets}/{len(self.positions)}" if self.positions else "N/A",
                "max_single_bet_allowed": round(self.balance * self.max_single_bet_pct, 2),
                "max_single_bet_pct": f"{int(self.max_single_bet_pct * 100)}%"
            },
            "trading_activity": {
                "total_trades": total_trades_count,
                "mode": "DRY_RUN" if self.dry_run else "LIVE"
            }
        }
    
    def get_top_traders(self, n: int = 10) -> List[Dict[str, Any]]:
        """Get top N traders by Sharpe ratio."""
        # Limit to max 50
        n = min(n, 50)
        
        # Cache for 5 minutes
        if self.top_traders_cache and self.cache_time:
            if time.time() - self.cache_time < 300:
                return self.top_traders_cache[:n]
        
        print(f"  [Analyzing top 50 traders from leaderboard...]")
        # Always analyze 50 traders, then return top N
        traders = get_top_traders_by_sharpe(n=50, sample_size=50)
        
        result = []
        for i, trader in enumerate(traders, 1):
            result.append({
                "rank": i,
                "username": trader.username,
                "wallet": trader.wallet,
                "sharpe_ratio": round(trader.sharpe_ratio, 4),
                "win_rate": round(trader.win_rate, 2),
                "max_drawdown": round(trader.max_drawdown, 2),
                "total_trades": trader.total_trades,
                "leaderboard_rank": trader.leaderboard_rank,
                "pnl": round(trader.leaderboard_pnl, 2)
            })
        
        self.top_traders_cache = result
        self.cache_time = time.time()
        
        return result
    
    def get_trader_top_trades(self, wallet: str, n: int = 5) -> List[Dict[str, Any]]:
        """Get top trades for a specific trader, filtering out closed markets."""
        print(f"  [Fetching top {n} trades for wallet...]")
        trades = get_top_volume_trades(wallet, n * 3)  # Get more to filter
        
        result = []
        for trade in trades:
            # Check if market is still active
            is_active = self._check_market_active(trade.market_slug)
            
            if is_active:
                result.append({
                    "market": trade.market_title,
                    "market_slug": trade.market_slug,
                    "outcome": trade.outcome,
                    "side": trade.side,
                    "volume_usd": round(trade.value, 2),
                    "price": round(trade.price, 4),
                    "shares": round(trade.size, 2),
                    "status": "active"
                })
                
                # Stop once we have enough active trades
                if len(result) >= n:
                    break
            else:
                pass
        
        return result
    
    def get_consensus_bets(self, min_traders: int = 2) -> List[Dict[str, Any]]:
        """Find consensus bets among top traders, filtering out closed markets."""
        print(f"  [Finding consensus bets...]")
        
        if not self.top_traders_cache:
            self.get_top_traders(10)
        
        # Convert cache back to TraderMetrics
        traders = []
        for t in self.top_traders_cache:
            traders.append(TraderMetrics(
                wallet=t['wallet'],
                username=t['username'],
                leaderboard_rank=t['leaderboard_rank'],
                leaderboard_vol=0,
                leaderboard_pnl=t['pnl'],
                total_trades=t['total_trades'],
                sharpe_ratio=t['sharpe_ratio'],
                avg_return=0,
                volatility=0,
                win_rate=t['win_rate'],
                max_drawdown=t['max_drawdown']
            ))
        
        consensus = find_consensus_bets(traders)
        
        # Filter out closed/inactive markets
        result = []
        for market_slug, outcome, trader_count, avg_volume in consensus:
            if trader_count >= min_traders:
                # Check if market is still active
                is_active = self._check_market_active(market_slug)
                
                if is_active:
                    result.append({
                        "market_slug": market_slug,
                        "outcome": outcome,
                        "trader_count": trader_count,
                        "avg_volume_usd": round(avg_volume, 2),
                        "status": "active"
                    })
                else:
                    pass
        
        return result[:20]  # Top 20 active consensus bets
    
    def _check_market_active(self, market_slug: str) -> bool:
        """Check if a market is still active and accepting trades."""
        try:
            # Use the correct gamma API endpoint for market by slug
            response = requests.get(
                f"https://gamma-api.polymarket.com/markets/slug/{market_slug}",
                timeout=5
            )
            
            if response.ok:
                market = response.json()
                
                # Check if market is active, not closed, and accepting orders
                is_active = market.get('active', False)
                is_closed = market.get('closed', True)
                accepting_orders = market.get('acceptingOrders', False)
                
                # Also check end date if available
                end_date = market.get('endDate')
                if end_date:
                    from datetime import datetime
                    try:
                        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                        now = datetime.now(end_dt.tzinfo)
                        if now > end_dt:
                            return False
                    except:
                        pass
                
                # Market must be active, not closed, AND accepting orders
                return is_active and not is_closed and accepting_orders
            
            # If we can't verify, assume it's NOT active (conservative - don't bet on unknown markets)
            return False
            
        except Exception as e:
            print(f"  [Warning: Could not verify market status: {e}]")
            # If we can't check, assume NOT active to avoid betting on closed markets
            return False
    
    def get_market_details(self, market_slug: str) -> Optional[Dict[str, Any]]:
        """Get market details with description, fees, and trading info."""
        print(f"  [Fetching market details for {market_slug}...]")
        
        # Use the correct gamma API endpoint for market by slug
        try:
            response = requests.get(
                f"https://gamma-api.polymarket.com/markets/slug/{market_slug}",
                timeout=10
            )
            
            if response.ok:
                market = response.json()
                
                # Check market status
                is_active = market.get('active', False)
                is_closed = market.get('closed', True)
                accepting_orders = market.get('acceptingOrders', False)
                end_date = market.get('endDate', 'Unknown')
                
                # Determine if tradeable
                tradeable = is_active and not is_closed and accepting_orders
                
                # Get fee information from API
                maker_fee = market.get('makerBaseFee', 0)
                taker_fee = market.get('takerBaseFee', 0)
                
                if maker_fee == 0 and taker_fee == 0:
                    fee_info = "No fees (0%)"
                else:
                    fee_info = f"Maker: {maker_fee}%, Taker: {taker_fee}%"
                
                return {
                    "market_slug": market_slug,
                    "title": market.get('question', 'Unknown'),
                    "description": market.get('description', 'No description available'),
                    "active": is_active,
                    "closed": is_closed,
                    "accepting_orders": accepting_orders,
                    "tradeable": tradeable,
                    "end_date": end_date,
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
        except Exception as e:
            print(f"  [Warning: Could not fetch from gamma API: {e}]")
        
        # Fallback to trade data
        if self.top_traders_cache:
            for t in self.top_traders_cache[:10]:
                trades = PolymarketAPI.get_trades(t['wallet'], limit=100)
                for trade in trades:
                    if trade.get('slug') == market_slug:
                        return {
                            "market_slug": market_slug,
                            "title": trade.get('title', 'Unknown'),
                            "description": trade.get('description', 'No description available'),
                            "outcome": trade.get('outcome', ''),
                            "side": trade.get('side', ''),
                            "recent_price": round(float(trade.get('price', 0)), 4),
                            "active": True,
                            "tradeable": True,
                            "fees": "Unknown (verify before betting)",
                            "note": "Status unknown - verify market is still active before betting",
                            "trading_info": {
                                "minimum_trade": "No minimum (can trade fractional shares)",
                                "settlement": "Shares worth $1 if outcome occurs, $0 otherwise",
                                "liquidity": "Can exit position anytime at current market price"
                            }
                        }
        
        # Final fallback
        title = market_slug.replace('-', ' ').title()
        description = f"Market: {title}. Full details not available. This market may be closed or inactive."
        
        return {
            "market_slug": market_slug,
            "title": title,
            "description": description,
            "active": False,
            "tradeable": False,
            "fees": "Unknown",
            "note": "⚠️ Limited information - market may be closed or inactive. DO NOT BET without verification.",
            "trading_info": {
                "minimum_trade": "No minimum (can trade fractional shares)",
                "settlement": "Shares worth $1 if outcome occurs, $0 otherwise",
                "liquidity": "Can exit position anytime at current market price"
            }
        }
    
    def get_active_markets(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get active markets that are actually accepting orders."""
        print(f"  [Fetching {limit} active markets...]")
        
        try:
            # Get markets from gamma API
            response = requests.get(
                "https://gamma-api.polymarket.com/markets",
                params={'limit': limit * 3, 'active': True},  # Get more to filter
                timeout=10
            )
            
            if not response.ok:
                return []
            
            markets = response.json()
            
            result = []
            for market in markets:
                # Check if market is actually accepting orders
                is_active = market.get('active', False)
                is_closed = market.get('closed', True)
                accepting_orders = market.get('acceptingOrders', False)
                
                # Check end date
                end_date = market.get('endDate')
                is_future = True
                if end_date:
                    from datetime import datetime
                    try:
                        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                        now = datetime.now(end_dt.tzinfo)
                        is_future = now < end_dt
                    except:
                        pass
                
                # Only include markets that are truly tradeable
                if is_active and not is_closed and accepting_orders and is_future:
                    result.append({
                        "market_slug": market.get('slug', ''),
                        "title": market.get('question', ''),
                        "volume": market.get('volume', 0),
                        "liquidity": market.get('liquidity', 0),
                        "end_date": end_date,
                        "active": True,
                        "accepting_orders": True
                    })
                    
                    if len(result) >= limit:
                        break
            
            return result
            
        except Exception as e:
            print(f"  [Error fetching active markets: {e}]")
            return []
    
    def place_bet(self, market_slug: str, outcome: str, amount_usd: float, reasoning: str) -> Dict[str, Any]:
        """Place a bet (dry-run or live based on mode)."""
        if amount_usd > self.balance:
            return {
                "success": False,
                "error": "Insufficient funds",
                "balance": self.balance
            }
        
        # Get market details for the bet
        market_info = self.get_market_details(market_slug)
        
        print(f"\n  💰 {'[DRY RUN] ' if self.dry_run else ''}PLACING BET:")
        print(f"     Market: {market_info.get('title', market_slug)}")
        print(f"     Description: {market_info.get('description', 'N/A')[:100]}...")
        print(f"     Outcome: {outcome}")
        print(f"     Amount: ${amount_usd:.2f}")
        print(f"     Reasoning: {reasoning}")
        
        if self.dry_run:
            # Simulate the bet
            self.balance -= amount_usd
            
            position = {
                "market_slug": market_slug,
                "market_title": market_info.get('title', market_slug),
                "outcome": outcome,
                "amount": amount_usd,
                "reasoning": reasoning,
                "timestamp": datetime.now().isoformat(),
                "mode": "DRY_RUN"
            }
            self.positions.append(position)
            self.simulated_trades.append(position)
            
            print(f"     ✅ Simulated bet placed")
            print(f"     New Balance: ${self.balance:.2f}")
            
            return {
                "success": True,
                "market_slug": market_slug,
                "market_title": market_info.get('title', market_slug),
                "outcome": outcome,
                "amount_usd": amount_usd,
                "new_balance": round(self.balance, 2),
                "mode": "DRY_RUN"
            }
        else:
            # Live trading with Polymarket API
            if not self.polymarket_client:
                return {
                    "success": False,
                    "error": "Polymarket client not initialized. Cannot place live bets."
                }
            
            try:
                from py_clob_client.clob_types import OrderArgs, OrderType
                from py_clob_client.order_builder.constants import BUY
                from decimal import Decimal
                
                # Get market data from gamma API using slug endpoint
                response = requests.get(
                    f"https://gamma-api.polymarket.com/markets/slug/{market_slug}",
                    timeout=10
                )
                
                if not response.ok:
                    return {
                        "success": False,
                        "error": f"Could not fetch market data for {market_slug} (status: {response.status_code})"
                    }
                
                market = response.json()
                
                # Get token IDs from clobTokenIds (it's a JSON string)
                clob_token_ids_str = market.get('clobTokenIds', '[]')
                outcomes_str = market.get('outcomes', '[]')
                
                try:
                    token_ids = json.loads(clob_token_ids_str) if isinstance(clob_token_ids_str, str) else clob_token_ids_str
                    outcomes = json.loads(outcomes_str) if isinstance(outcomes_str, str) else outcomes_str
                except json.JSONDecodeError:
                    return {
                        "success": False,
                        "error": f"Invalid token IDs or outcomes format in market data"
                    }
                
                if not token_ids or not outcomes:
                    return {
                        "success": False,
                        "error": f"Market does not have valid token IDs. clobTokenIds: {clob_token_ids_str}, outcomes: {outcomes_str}"
                    }
                
                # Map outcome to token_id
                outcome_index = None
                for i, outcome_name in enumerate(outcomes):
                    if outcome_name.lower() == outcome.lower():
                        outcome_index = i
                        break
                
                if outcome_index is None:
                    return {
                        "success": False,
                        "error": f"Outcome '{outcome}' not found. Available: {outcomes}"
                    }
                
                token_id = token_ids[outcome_index]
                condition_id = market.get('conditionId')
                
                if not condition_id:
                    return {
                        "success": False,
                        "error": "Market does not have a condition ID"
                    }
                
                # Get current market price - use SELL side because we're buying from sellers
                price_response = requests.get(
                    f"https://clob.polymarket.com/price",
                    params={'token_id': token_id, 'side': 'SELL'},
                    timeout=10
                )
                
                current_price = 0.5  # Default fallback
                if price_response.ok:
                    try:
                        price_data = price_response.json()
                        current_price = float(price_data.get('price', 0.5))
                        # Cap price to stay within CLOB bounds (0.001 - 0.999)
                        current_price = min(max(current_price, 0.001), 0.998)
                        print(f"     [Fetched current price: ${current_price:.4f}]")
                    except (ValueError, KeyError) as e:
                        print(f"     [Warning: Could not parse price: {e}, using fallback]")
                else:
                    print(f"     [Warning: Price API returned {price_response.status_code}, using fallback $0.50]")
                
                # Calculate shares to buy
                shares = amount_usd / current_price
                
                # Create order using py-clob-client
                order = self.polymarket_client.create_order(
                    OrderArgs(
                        price=Decimal(str(current_price)),
                        size=Decimal(str(shares)),
                        side=BUY,
                        token_id=token_id
                    )
                )
                
                # Post order to exchange
                order_response = self.polymarket_client.post_order(order, OrderType.GTC)
                
                if order_response and order_response.get('success'):
                    self.balance -= amount_usd
                    
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
                    self.positions.append(position)
                    
                    print(f"     ✅ Live bet placed successfully!")
                    print(f"     Order ID: {order_response.get('orderID', 'N/A')}")
                    print(f"     Token ID: {token_id}")
                    print(f"     Price: ${current_price:.4f}")
                    print(f"     Shares: {shares:.2f}")
                    print(f"     New Balance: ${self.balance:.2f}")
                    
                    return {
                        "success": True,
                        "market_slug": market_slug,
                        "market_title": market_info.get('title', market_slug),
                        "outcome": outcome,
                        "amount_usd": amount_usd,
                        "new_balance": round(self.balance, 2),
                        "order_id": order_response.get('orderID', 'N/A'),
                        "token_id": token_id,
                        "price": current_price,
                        "shares": shares,
                        "mode": "LIVE"
                    }
                else:
                    error_msg = order_response.get('errorMsg', 'Unknown error') if order_response else 'No response'
                    return {
                        "success": False,
                        "error": f"Order submission failed: {error_msg}",
                        "response": order_response
                    }
                    
            except Exception as e:
                import traceback
                return {
                    "success": False,
                    "error": f"Error placing live bet: {str(e)}",
                    "traceback": traceback.format_exc()
                }
    
    def search_news(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Search for recent news headlines using pygooglenews."""
        print(f"  [Searching news for: {query}...]")
        try:
            from pygooglenews import GoogleNews
            gn = GoogleNews(lang='en', country='US')
            search = gn.search(query, when='7d')
            articles = [{'title': e.title, 'source': e.source.get('title', 'Unknown'), 
                        'published': e.published, 'url': e.link} 
                       for e in search['entries'][:max_results]]
            return {"query": query, "results_count": len(articles), "articles": articles}
        except Exception as e:
            return {"query": query, "error": str(e), "note": "News unavailable, continue with trader data"}
    
    
    def read_knowledge_base(self) -> Dict[str, Any]:
        """Read the trading knowledge base file."""
        print(f"  [Reading knowledge base...]")
        
        kb_path = "kb.txt"
        
        try:
            if os.path.exists(kb_path):
                with open(kb_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                return {
                    "available": True,
                    "content": content,
                    "note": "Knowledge base contains 14 proven Polymarket trading strategies from successful traders"
                }
            else:
                return {
                    "available": False,
                    "error": "Knowledge base file (kb.txt) not found",
                    "note": "Continue with standard analysis using trader data"
                }
                
        except Exception as e:
            return {
                "available": False,
                "error": str(e),
                "note": "Could not read knowledge base. Continue with standard analysis."
            }
    
    def get_suggested_whales(self, limit: int = 50) -> Dict[str, Any]:
        """Get recommended whale traders from PolyWhaler.com with Sharpe ratio and max drawdown analysis."""
        print(f"  [Fetching {limit} suggested whales from PolyWhaler...]")
        try:
            response = requests.get(
                f"https://www.polywhaler.com/api/suggested-whales?limit={limit}",
                timeout=10
            )
            if response.ok:
                data = response.json()
                whales = data.get('suggestions', [])
                
                # Enrich with Sharpe ratio and max drawdown
                print(f"  [Analyzing {len(whales)} whales for risk metrics...]")
                enriched_whales = []
                
                for w in whales:
                    wallet = w['wallet']
                    print(f"    Analyzing {w.get('name', wallet)}...")
                    
                    # Use existing analysis function
                    metrics = analyze_trader(
                        wallet=wallet,
                        username=w.get('name', 'Unknown'),
                        rank=0,  # Not from leaderboard
                        vol=w.get('recentVolume', 0),
                        pnl=0  # Not available from PolyWhaler
                    )
                    
                    if metrics:
                        enriched_whales.append({
                            "wallet": wallet,
                            "name": w.get('name', 'Unknown'),
                            "recent_trades": w.get('recentTradeCount', 0),
                            "recent_volume": round(w.get('recentVolume', 0), 2),
                            "sharpe_ratio": round(metrics.sharpe_ratio, 4),
                            "win_rate": round(metrics.win_rate, 2),
                            "max_drawdown": round(metrics.max_drawdown, 2),
                            "total_trades": metrics.total_trades,
                            "last_trade_time": w.get('lastTradeTime', 0)
                        })
                    else:
                        # Include without metrics if analysis fails
                        enriched_whales.append({
                            "wallet": wallet,
                            "name": w.get('name', 'Unknown'),
                            "recent_trades": w.get('recentTradeCount', 0),
                            "recent_volume": round(w.get('recentVolume', 0), 2),
                            "sharpe_ratio": 0.0,
                            "win_rate": 0.0,
                            "max_drawdown": 0.0,
                            "total_trades": 0,
                            "last_trade_time": w.get('lastTradeTime', 0),
                            "note": "Analysis unavailable"
                        })
                
                # Sort by Sharpe ratio
                enriched_whales.sort(key=lambda x: x['sharpe_ratio'], reverse=True)
                
                return {
                    "count": len(enriched_whales),
                    "whales": enriched_whales,
                    "note": "High-volume traders from PolyWhaler.com enriched with Sharpe ratio and max drawdown analysis"
                }
            else:
                return {"error": f"API returned {response.status_code}", "whales": []}
        except Exception as e:
            return {"error": str(e), "whales": [], "note": "PolyWhaler unavailable, use get_top_traders instead"}
    
    def execute_function(self, function_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a function call from ChatGPT."""
        if function_name == "get_available_funds":
            return self.get_available_funds()
        elif function_name == "get_current_positions":
            return self.get_current_positions()
        elif function_name == "get_trade_history":
            return self.get_trade_history(**arguments)
        elif function_name == "get_portfolio_summary":
            return self.get_portfolio_summary()
        elif function_name == "get_top_traders":
            return self.get_top_traders(**arguments)
        elif function_name == "get_trader_top_trades":
            return self.get_trader_top_trades(**arguments)
        elif function_name == "get_consensus_bets":
            return self.get_consensus_bets(**arguments)
        elif function_name == "get_market_details":
            return self.get_market_details(**arguments)
        elif function_name == "get_active_markets":
            return self.get_active_markets(**arguments)
        elif function_name == "place_bet":
            return self.place_bet(**arguments)
        elif function_name == "search_news":
            return self.search_news(**arguments)
        elif function_name == "read_knowledge_base":
            return self.read_knowledge_base()
        elif function_name == "get_suggested_whales":
            return self.get_suggested_whales(**arguments)
        else:
            return {"error": f"Unknown function: {function_name}"}
    
    def chat_with_gpt(self, messages: List[Dict[str, str]], retry_count: int = 0, max_retries: int = 5) -> Dict[str, Any]:
        """Send messages to AI and get response with exponential backoff retry."""
        if self.ai_provider == "bedrock":
            return self._chat_with_bedrock(messages, retry_count, max_retries)
        else:
            return self._chat_with_openai(messages, retry_count, max_retries)
    
    def _chat_with_openai(self, messages: List[Dict[str, str]], retry_count: int = 0, max_retries: int = 5) -> Dict[str, Any]:
        """Send messages to ChatGPT and get response with exponential backoff retry."""
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": messages,
                    "tools": self.TOOLS,
                    "tool_choice": "auto"
                },
                timeout=60
            )
            
            if response.ok:
                return response.json()
            elif response.status_code == 429 and retry_count < max_retries:
                # Rate limit - exponential backoff
                wait_time = 2 ** retry_count
                print(f"⏳ Rate limited. Retrying in {wait_time}s... (attempt {retry_count + 1}/{max_retries})")
                time.sleep(wait_time)
                return self._chat_with_openai(messages, retry_count + 1, max_retries)
            elif response.status_code >= 500 and retry_count < max_retries:
                # Server error - exponential backoff
                wait_time = 2 ** retry_count
                print(f"⏳ Server error. Retrying in {wait_time}s... (attempt {retry_count + 1}/{max_retries})")
                time.sleep(wait_time)
                return self._chat_with_openai(messages, retry_count + 1, max_retries)
            else:
                print(f"API Error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            if retry_count < max_retries:
                wait_time = 2 ** retry_count
                print(f"⏳ Error: {e}. Retrying in {wait_time}s... (attempt {retry_count + 1}/{max_retries})")
                time.sleep(wait_time)
                return self._chat_with_openai(messages, retry_count + 1, max_retries)
            else:
                print(f"Error calling ChatGPT: {e}")
                return None
    
    def _chat_with_bedrock(self, messages: List[Dict[str, str]], retry_count: int = 0, max_retries: int = 5) -> Dict[str, Any]:
        """Send messages to Claude via Bedrock and get response with exponential backoff retry."""
        try:
            # Convert OpenAI format to Claude format
            claude_messages = []
            system_message = None
            
            for msg in messages:
                if msg['role'] == 'system':
                    system_message = msg['content']
                elif msg['role'] == 'tool':
                    # Convert tool response to user message
                    claude_messages.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": msg['tool_call_id'],
                                "content": msg['content']
                            }
                        ]
                    })
                else:
                    # Handle regular messages and tool calls
                    content = []
                    
                    if msg.get('content'):
                        content.append({"type": "text", "text": msg['content']})
                    
                    if msg.get('tool_calls'):
                        for tool_call in msg['tool_calls']:
                            content.append({
                                "type": "tool_use",
                                "id": tool_call['id'],
                                "name": tool_call['function']['name'],
                                "input": json.loads(tool_call['function']['arguments'])
                            })
                    
                    if content:
                        claude_messages.append({
                            "role": msg['role'] if msg['role'] != 'assistant' else 'assistant',
                            "content": content
                        })
            
            # Convert tools to Claude format
            claude_tools = []
            for tool in self.TOOLS:
                claude_tools.append({
                    "name": tool['function']['name'],
                    "description": tool['function']['description'],
                    "input_schema": tool['function']['parameters']
                })
            
            # Call Bedrock
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "messages": claude_messages,
                "tools": claude_tools
            }
            
            if system_message:
                request_body["system"] = system_message
            
            response = self.bedrock_client.invoke_model(
                modelId="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            
            # Convert Claude response to OpenAI format
            openai_response = {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": []
                    },
                    "finish_reason": response_body.get('stop_reason', 'stop')
                }]
            }
            
            # Extract content and tool calls
            for content_block in response_body.get('content', []):
                if content_block['type'] == 'text':
                    openai_response['choices'][0]['message']['content'] = content_block['text']
                elif content_block['type'] == 'tool_use':
                    openai_response['choices'][0]['message']['tool_calls'].append({
                        "id": content_block['id'],
                        "type": "function",
                        "function": {
                            "name": content_block['name'],
                            "arguments": json.dumps(content_block['input'])
                        }
                    })
            
            # Set finish reason
            if openai_response['choices'][0]['message']['tool_calls']:
                openai_response['choices'][0]['finish_reason'] = 'tool_calls'
            
            return openai_response
            
        except Exception as e:
            if retry_count < max_retries:
                wait_time = 2 ** retry_count
                print(f"⏳ Error: {e}. Retrying in {wait_time}s... (attempt {retry_count + 1}/{max_retries})")
                time.sleep(wait_time)
                return self._chat_with_bedrock(messages, retry_count + 1, max_retries)
            else:
                print(f"Error calling Bedrock: {e}")
                return None
    
    def run_trading_session(self, max_iterations: int = 10):
        """Run an AI trading session."""
        print("=" * 80)
        print("AI-POWERED POLYMARKET TRADING BOT")
        print("=" * 80)
        print(f"Mode: {'DRY RUN (Simulated)' if self.dry_run else 'LIVE TRADING'}")
        print(f"Starting Balance: ${self.balance:.2f}")
        print(f"Risk Profile: AGGRESSIVE ")
        print("=" * 80)
        print()
        
        # Get current date and time
        from datetime import datetime
        current_datetime = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p %Z")
        
        # Inject current date/time into system prompt
        system_prompt = self.SYSTEM_PROMPT.format(current_datetime=current_datetime)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Analyze Polymarket trading opportunities and EXECUTE trades."}
        ]
        
        for iteration in range(max_iterations):
            print(f"\n{'='*80}")
            print(f"ITERATION {iteration + 1}/{max_iterations}")
            print(f"{'='*80}\n")
            
            # Get ChatGPT response
            response = self.chat_with_gpt(messages)
            
            if not response:
                print("Failed to get response from ChatGPT")
                break
            
            choice = response['choices'][0]
            message = choice['message']
            
            # Add assistant message to history
            messages.append(message)
            
            # Check if done
            if choice['finish_reason'] == 'stop':
                print("\n🤖 AI Analysis:")
                print(message.get('content', ''))
                
                # Check if AI suggested bets but didn't place them
                content = message.get('content', '')
                if any(word in content.lower() for word in ['bet', 'suggest', 'consider', 'recommend', 'position']):
                    print("\n⚠️  AI provided analysis but didn't place bets.")
                    print("💡 Tip: The AI should use the place_bet function to execute trades.")
                    print("    It analyzed opportunities but stopped without taking action.")
                
                break
            
            # Handle tool calls
            if choice['finish_reason'] == 'tool_calls':
                tool_calls = message.get('tool_calls', [])
                
                for tool_call in tool_calls:
                    function_name = tool_call['function']['name']
                    arguments = json.loads(tool_call['function']['arguments'])
                    
                    print(f"🔧 Calling: {function_name}({json.dumps(arguments, indent=2)})")
                    
                    # Execute function
                    result = self.execute_function(function_name, arguments)
                    
                    # Add result to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call['id'],
                        "content": json.dumps(result)
                    })
                    
                    print(f"✓ Result: {json.dumps(result, indent=2)[:200]}...")
            
            # Small delay between iterations
            time.sleep(1)
        
        # Final summary
        print("\n" + "=" * 80)
        print("TRADING SESSION COMPLETE")
        print("=" * 80)
        print(f"Final Balance: ${self.balance:.2f}")
        print(f"Total Bets Placed: {len(self.positions)}")
        print(f"Total Invested: ${sum(p['amount'] for p in self.positions):.2f}")
        
        if self.positions:
            print("\nPositions:")
            for i, pos in enumerate(self.positions, 1):
                print(f"  {i}. {pos['market_slug']} - {pos['outcome']} (${pos['amount']:.2f})")
                print(f"     Reasoning: {pos['reasoning']}")
        
        print("=" * 80)


def main():
    # Load environment variables from .env file
    from dotenv import load_dotenv
    load_dotenv()
    
    parser = argparse.ArgumentParser(
        description='AI-powered Polymarket trading bot using ChatGPT'
    )
    
    parser.add_argument(
        '--balance',
        type=float,
        default=100.0,
        help='Starting balance in USD (default: 100, dry-run always uses $50)'
    )
    parser.add_argument(
        '--max-iterations',
        type=int,
        default=20,
        help='Maximum AI iterations (default: 20)'
    )
    parser.add_argument(
        '--api-key',
        help='OpenAI API key (or set OPENAI_API_KEY env var)'
    )
    parser.add_argument(
        '--live',
        action='store_true',
        help='Enable LIVE trading (default is dry-run/simulation)'
    )
    parser.add_argument(
        '--polymarket-key',
        help='Polymarket API key for live trading (or set POLYMARKET_API_KEY env var)'
    )
    parser.add_argument(
        '--polymarket-secret',
        help='Polymarket API secret (or set POLYMARKET_SECRET env var)'
    )
    parser.add_argument(
        '--polymarket-passphrase',
        help='Polymarket API passphrase (or set POLYMARKET_PASSPHRASE env var)'
    )
    parser.add_argument(
        '--max-bet-pct',
        type=float,
        default=1.0,
        help='Maximum percentage of available balance for a single bet (0.0-1.0, default: 1.0 = 100%%)'
    )
    
    args = parser.parse_args()
    
    # Get OpenAI API key
    import os
    ai_provider = os.getenv('AI_PROVIDER', 'chatgpt').lower()
    api_key = args.api_key or os.getenv('OPENAI_API_KEY')
    
    if ai_provider == 'chatgpt' and not api_key:
        print("❌ Error: ChatGPT provider requires OPENAI_API_KEY")
        print("Set AI_PROVIDER=bedrock in .env to use AWS Bedrock instead")
        return
    
    print(f"🤖 Using AI Provider: {ai_provider.upper()}")
    if ai_provider == 'bedrock':
        print("   Model: Claude 3.5 Sonnet via AWS Bedrock")
    else:
        print("   Model: GPT-4o-mini via OpenAI")
    
    # Get wallet address from env
    wallet_address = os.getenv('POLYMARKET_WALLET')
    if not wallet_address:
        print("⚠️  Warning: POLYMARKET_WALLET not set in .env - trade history will be unavailable")
    
    # Determine if live trading
    dry_run = not args.live
    polymarket_client = None
    
    if args.live:
        # Get Polymarket credentials
        pm_key = args.polymarket_key or os.getenv('POLYMARKET_API_KEY')
        pm_secret = args.polymarket_secret or os.getenv('POLYMARKET_SECRET')
        pm_passphrase = args.polymarket_passphrase or os.getenv('POLYMARKET_PASSPHRASE')
        pm_private_key = os.getenv('POLYMARKET_PRIVATE_KEY')
        pm_wallet = os.getenv('POLYMARKET_WALLET')
        pm_builder_address = os.getenv('POLYMARKET_BUILDER_ADDRESS')
        
        if not all([pm_key, pm_secret, pm_passphrase, pm_private_key, pm_wallet]):
            print("❌ Error: Live trading requires Polymarket credentials")
            print("Set: POLYMARKET_API_KEY, POLYMARKET_SECRET, POLYMARKET_PASSPHRASE")
            print("     POLYMARKET_PRIVATE_KEY, POLYMARKET_WALLET")
            return
        
        try:
            from py_clob_client.client import ClobClient
            
            # Initialize client with private key (signer) and funder (proxy wallet)
            polymarket_client = ClobClient(
                host="https://clob.polymarket.com",
                key=pm_private_key,  # Private key of signer EOA
                chain_id=137,  # Polygon
                signature_type=1,  # For Safe/email/magic proxy wallet
                funder=pm_wallet  # Proxy wallet address (where funds are)
            )
            
            # Create or derive API credentials (this is the correct way per Polymarket docs)
            polymarket_client.set_api_creds(polymarket_client.create_or_derive_api_creds())
            
            print("✅ Connected to Polymarket CLOB for LIVE trading")
            print(f"   Proxy Wallet: {pm_wallet}")
            print(f"   Signer: {pm_builder_address if pm_builder_address else 'Derived from private key'}")
            print("⚠️  WARNING: This will place REAL bets with REAL money!")
            print()
            
        except ImportError:
            print("❌ Error: py-clob-client not installed")
            print("Install with: pip install py-clob-client")
            return
        except Exception as e:
            print(f"❌ Error connecting to Polymarket: {e}")
            return
    
    # Create bot
    bot = AITradingBot(
        ai_provider=ai_provider,
        openai_api_key=api_key,
        initial_balance=args.balance,
        dry_run=dry_run,
        polymarket_client=polymarket_client,
        wallet_address=wallet_address,
        max_single_bet_pct=args.max_bet_pct
    )
    
    # Run trading session
    bot.run_trading_session(max_iterations=args.max_iterations)


if __name__ == "__main__":
    main()

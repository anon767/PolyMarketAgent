#!/usr/bin/env python3
"""
Polymarket Top Traders Analysis

Finds top 10 traders by Sharpe ratio, analyzes their highest volume trades,
and identifies consensus bets across all top traders.

The Polymarket leaderboard ranks by:
- Volume (vol): Total trading volume in USD
- P&L (pnl): Profit and Loss in USD

This script calculates our own Sharpe ratio based on trade history.
"""

import requests
import json
import statistics
from typing import List, Dict, Optional, Tuple
from collections import defaultdict, Counter
from dataclasses import dataclass
import argparse
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from datetime import datetime
import numpy as np


@dataclass
class TraderMetrics:
    """Metrics for a trader."""
    wallet: str
    username: str
    leaderboard_rank: int
    leaderboard_vol: float
    leaderboard_pnl: float
    total_trades: int
    sharpe_ratio: float
    avg_return: float
    volatility: float
    win_rate: float
    max_drawdown: float


@dataclass
class TradeInfo:
    """Information about a trade."""
    market_title: str
    market_slug: str
    outcome: str
    side: str
    size: float
    price: float
    value: float
    timestamp: int


class PolymarketAPI:
    """Client for Polymarket Data API."""
    
    BASE_URL = "https://data-api.polymarket.com"
    
    @staticmethod
    def get_leaderboard(limit: int = 100) -> List[Dict]:
        """
        Fetch the trader leaderboard.
        
        Note: API has a hard limit of ~50 traders regardless of requested limit.
        """
        try:
            response = requests.get(
                f"{PolymarketAPI.BASE_URL}/v1/leaderboard",
                params={'limit': limit},
                timeout=10
            )
            if response.ok:
                return response.json()
        except Exception as e:
            print(f"Error fetching leaderboard: {e}")
        return []
    
    @staticmethod
    def get_trades(wallet: str, limit: int = 500) -> List[Dict]:
        """Get trade history for a wallet."""
        try:
            response = requests.get(
                f"{PolymarketAPI.BASE_URL}/trades",
                params={'user': wallet, 'limit': limit},
                timeout=10
            )
            if response.ok:
                return response.json()
        except Exception as e:
            print(f"Error fetching trades: {e}")
        return []


class SharpeCalculator:
    """Calculate Sharpe ratio from trade data."""
    
    @staticmethod
    def calculate_returns_from_trades(trades: List[Dict]) -> List[float]:
        """Calculate returns from matched buy/sell pairs."""
        if not trades:
            return []
        
        # Group trades by market
        from collections import defaultdict
        market_positions = defaultdict(list)
        
        # Reverse to process chronologically
        for trade in reversed(trades):
            condition_id = trade.get('conditionId', '')
            if condition_id:
                market_positions[condition_id].append(trade)
        
        returns = []
        
        # Calculate P&L for each market
        for condition_id, market_trades in market_positions.items():
            position_size = 0
            position_cost = 0
            
            for trade in market_trades:
                try:
                    side = trade.get('side', '')
                    size = float(trade.get('size', 0))
                    price = float(trade.get('price', 0))
                    
                    if side == 'BUY':
                        position_cost += size * price
                        position_size += size
                    elif side == 'SELL':
                        if position_size > 0:
                            avg_cost = position_cost / position_size if position_size > 0 else 0
                            pnl = size * (price - avg_cost)
                            returns.append(pnl)
                            
                            position_cost -= size * avg_cost
                            position_size -= size
                except (ValueError, TypeError, ZeroDivisionError):
                    continue
        
        return returns if returns else [0.0]
    
    @staticmethod
    def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.0) -> float:
        """Calculate Sharpe ratio."""
        if len(returns) < 2:
            return 0.0
        
        try:
            mean_return = statistics.mean(returns)
            std_dev = statistics.stdev(returns)
            
            if std_dev == 0:
                return 0.0
            
            sharpe = (mean_return - risk_free_rate) / std_dev
            return sharpe
        except statistics.StatisticsError:
            return 0.0
    
    @staticmethod
    def calculate_max_drawdown(returns: List[float]) -> float:
        """
        Calculate maximum drawdown.
        
        Args:
            returns: List of returns
            
        Returns:
            Maximum drawdown as a percentage
        """
        if not returns:
            return 0.0
        
        cumulative = [sum(returns[:i+1]) for i in range(len(returns))]
        running_max = [max(cumulative[:i+1]) for i in range(len(cumulative))]
        drawdowns = [(cumulative[i] - running_max[i]) / abs(running_max[i]) if running_max[i] != 0 else 0
                     for i in range(len(cumulative))]
        
        return min(drawdowns) * 100 if drawdowns else 0.0
    
    @staticmethod
    def calculate_win_rate(trades: List[Dict]) -> float:
        """Calculate win rate from trades."""
        if not trades:
            return 0.0
        
        profitable_trades = sum(
            1 for trade in trades
            if trade.get('side') == 'SELL' and float(trade.get('price', 0)) > 0.5
        )
        
        return (profitable_trades / len(trades)) * 100 if trades else 0.0


def analyze_trader(
    wallet: str,
    username: str,
    rank: int,
    vol: float,
    pnl: float
) -> Optional[TraderMetrics]:
    """Analyze a trader and calculate their metrics."""
    trades = PolymarketAPI.get_trades(wallet)
    
    if not trades:
        return None
    
    # Calculate metrics
    returns = SharpeCalculator.calculate_returns_from_trades(trades)
    sharpe_ratio = SharpeCalculator.calculate_sharpe_ratio(returns)
    win_rate = SharpeCalculator.calculate_win_rate(trades)
    max_drawdown = SharpeCalculator.calculate_max_drawdown(returns)
    
    avg_return = statistics.mean(returns) if returns else 0.0
    volatility = statistics.stdev(returns) if len(returns) > 1 else 0.0
    
    return TraderMetrics(
        wallet=wallet,
        username=username,
        leaderboard_rank=rank,
        leaderboard_vol=vol,
        leaderboard_pnl=pnl,
        total_trades=len(trades),
        sharpe_ratio=sharpe_ratio,
        avg_return=avg_return,
        volatility=volatility,
        win_rate=win_rate,
        max_drawdown=max_drawdown
    )


def get_top_traders_by_sharpe(n: int = 10, sample_size: int = 50) -> List[TraderMetrics]:
    """
    Get top N traders by Sharpe ratio.
    
    Args:
        n: Number of top traders to return
        sample_size: Number of traders to request (API limit is ~50)
    """
    print(f"Fetching leaderboard...")
    leaderboard = PolymarketAPI.get_leaderboard(limit=sample_size)
    
    if not leaderboard:
        print("Failed to fetch leaderboard")
        return []
    
    actual_count = len(leaderboard)
    print(f"✓ Received {actual_count} traders from API (API limit: ~50)")
    print(f"Analyzing all {actual_count} traders to calculate Sharpe ratios...")
    print("-" * 80)
    
    traders = []
    
    for i, trader_info in enumerate(leaderboard, 1):
        wallet = trader_info.get('proxyWallet', '')
        username = trader_info.get('userName', 'Unknown')
        vol = float(trader_info.get('vol', 0))
        pnl = float(trader_info.get('pnl', 0))
        
        display_name = username[:30] + "..." if len(username) > 30 else username
        
        print(f"[{i}/{actual_count}] Analyzing {display_name}")
        
        metrics = analyze_trader(wallet, username, i, vol, pnl)
        if metrics and metrics.total_trades > 0:
            traders.append(metrics)
    
    # Sort by Sharpe ratio
    traders.sort(key=lambda x: x.sharpe_ratio, reverse=True)
    
    print(f"\n✓ Analyzed {len(traders)} traders with trade history")
    print(f"✓ Selecting top {n} by Sharpe ratio")
    
    return traders[:n]


def get_top_volume_trades(wallet: str, n: int = 3) -> List[TradeInfo]:
    """Get top N trades by volume for a wallet."""
    trades = PolymarketAPI.get_trades(wallet, limit=500)
    
    trade_infos = []
    for trade in trades:
        try:
            size = float(trade.get('size', 0))
            price = float(trade.get('price', 0))
            value = size * price
            
            trade_infos.append(TradeInfo(
                market_title=trade.get('title', 'Unknown'),
                market_slug=trade.get('slug', ''),
                outcome=trade.get('outcome', 'N/A'),
                side=trade.get('side', 'N/A'),
                size=size,
                price=price,
                value=value,
                timestamp=trade.get('timestamp', 0)
            ))
        except (ValueError, TypeError):
            continue
    
    # Sort by value
    trade_infos.sort(key=lambda x: x.value, reverse=True)
    
    return trade_infos[:n]


def find_consensus_bets(traders: List[TraderMetrics]) -> List[Tuple[str, str, int, float]]:
    """
    Find bets that multiple top traders agree on.
    
    Returns list of (market_slug, outcome, trader_count, avg_volume)
    """
    print("\nAnalyzing consensus bets across top traders...")
    
    # Track (market_slug, outcome) -> list of (wallet, volume)
    bet_tracker = defaultdict(list)
    
    for trader in traders:
        trades = PolymarketAPI.get_trades(trader.wallet, limit=500)
        
        # Group by market and outcome
        market_bets = defaultdict(float)
        
        for trade in trades:
            market_slug = trade.get('slug', '')
            outcome = trade.get('outcome', '')
            side = trade.get('side', '')
            
            if market_slug and outcome and side == 'BUY':
                size = float(trade.get('size', 0))
                price = float(trade.get('price', 0))
                value = size * price
                
                key = (market_slug, outcome)
                market_bets[key] += value
        
        # Add to tracker
        for (market_slug, outcome), volume in market_bets.items():
            bet_tracker[(market_slug, outcome)].append((trader.wallet, volume))
    
    # Find consensus (2+ traders on same bet)
    consensus_bets = []
    
    for (market_slug, outcome), traders_list in bet_tracker.items():
        if len(traders_list) >= 2:
            trader_count = len(traders_list)
            avg_volume = sum(vol for _, vol in traders_list) / trader_count
            consensus_bets.append((market_slug, outcome, trader_count, avg_volume))
    
    # Sort by trader count, then by volume
    consensus_bets.sort(key=lambda x: (x[2], x[3]), reverse=True)
    
    return consensus_bets


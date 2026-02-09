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
    
    # Cache for market resolutions to avoid repeated API calls
    _market_cache = {}
    
    @staticmethod
    def _check_market_resolution_by_clob(asset_id: str) -> bool:
        """Check if market is resolved by checking if it's delisted from CLOB."""
        try:
            response = requests.get(
                'https://clob.polymarket.com/price',
                params={'token_id': asset_id, 'side': 'BUY'},
                timeout=3
            )
            # 404 means market is delisted (resolved)
            return response.status_code == 404
        except Exception:
            return False
    
    @staticmethod
    def _get_market_by_slug(slug: str) -> Optional[Dict]:
        """Get market info by slug from Gamma API."""
        try:
            response = requests.get(
                f'https://gamma-api.polymarket.com/markets/slug/{slug}',
                timeout=3
            )
            if response.ok:
                return response.json()
        except Exception:
            pass
        return None
    
    @staticmethod
    def _get_market_resolution(condition_id: str, asset_id: str = None, slug: str = None) -> Optional[Dict]:
        """Get market resolution status from Gamma API with caching."""
        cache_key = f"{condition_id}:{asset_id}:{slug}" if slug else (f"{condition_id}:{asset_id}" if asset_id else condition_id)
        
        if cache_key in SharpeCalculator._market_cache:
            return SharpeCalculator._market_cache[cache_key]
        
        # First check if market is resolved via CLOB
        is_resolved = False
        if asset_id:
            is_resolved = SharpeCalculator._check_market_resolution_by_clob(asset_id)
        
        # Try slug-based lookup first (more reliable for resolved markets)
        market_info = None
        if slug and is_resolved:
            market_info = SharpeCalculator._get_market_by_slug(slug)
            if market_info:
                market_info['closed'] = True
                SharpeCalculator._market_cache[cache_key] = market_info
                return market_info
        
        # Fallback to condition_id lookup
        try:
            response = requests.get(
                'https://gamma-api.polymarket.com/markets',
                params={'condition_id': condition_id},
                timeout=3
            )
            if response.ok:
                markets = response.json()
                if markets:
                    market_info = markets[0]
                    # Override closed status if CLOB check confirms resolution
                    if is_resolved:
                        market_info['closed'] = True
                    SharpeCalculator._market_cache[cache_key] = market_info
                    return market_info
        except Exception:
            pass
        
        SharpeCalculator._market_cache[cache_key] = None
        return None
    
    @staticmethod
    def calculate_returns_from_trades(trades: List[Dict], check_resolutions: bool = False) -> List[float]:
        """
        Calculate returns from:
        1. Explicit SELL trades (manual exits)
        2. Resolved markets (automatic redemption) - OPTIONAL, slow
        
        Args:
            trades: List of trade dictionaries
            check_resolutions: If True, check market resolutions (slow). Default False for speed.
        
        Note: Setting check_resolutions=True makes API calls to check market resolution status.
        For large trade histories, this may be slow. Use False for faster analysis.
        """
        if not trades:
            return []
        
        # Group trades by market and outcome, storing asset_id and slug for resolution checks
        from collections import defaultdict
        market_positions = defaultdict(lambda: defaultdict(lambda: {
            'size': 0, 
            'cost': 0, 
            'trades': [], 
            'asset_id': None,
            'slug': None
        }))
        
        # Reverse to process chronologically
        for trade in reversed(trades):
            condition_id = trade.get('conditionId', '')
            outcome = trade.get('outcome', '')
            asset_id = trade.get('asset', '')
            slug = trade.get('slug', '')
            if condition_id and outcome:
                market_positions[condition_id][outcome]['trades'].append(trade)
                # Store asset_id and slug for resolution checks
                if asset_id and not market_positions[condition_id][outcome]['asset_id']:
                    market_positions[condition_id][outcome]['asset_id'] = asset_id
                if slug and not market_positions[condition_id][outcome]['slug']:
                    market_positions[condition_id][outcome]['slug'] = slug
        
        returns = []
        
        # Calculate P&L for each market/outcome combination
        for condition_id, outcomes in market_positions.items():
            for outcome, data in outcomes.items():
                position_size = 0
                position_cost = 0
                asset_id = data['asset_id']
                slug = data['slug']
                
                for trade in data['trades']:
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
                
                # Only check resolutions if explicitly requested (slow operation)
                if check_resolutions and position_size > 0:
                    # Check market resolution using condition_id, asset_id, and slug
                    market_info = SharpeCalculator._get_market_resolution(condition_id, asset_id, slug)
                    is_closed = market_info and market_info.get('closed', False)
                    
                    if is_closed and market_info:
                        # Market is resolved - calculate P&L based on outcome
                        outcomes_list = market_info.get('outcomes', [])
                        prices_list = market_info.get('outcomePrices', [])
                        
                        # Parse if they're JSON strings
                        if isinstance(outcomes_list, str):
                            try:
                                outcomes_list = json.loads(outcomes_list)
                            except:
                                outcomes_list = []
                        
                        if isinstance(prices_list, str):
                            try:
                                prices_list = json.loads(prices_list)
                            except:
                                prices_list = []
                        
                        # Find the price for this outcome
                        try:
                            outcome_index = outcomes_list.index(outcome)
                            final_price_str = prices_list[outcome_index]
                            final_price = float(final_price_str) if final_price_str else 0.0
                            
                            # Calculate P&L based on final price
                            # If price is very close to 1.0, outcome won (shares worth $1)
                            # If price is very close to 0.0, outcome lost (shares worth $0)
                            if final_price > 0.95:
                                # Won - shares worth $1 each
                                avg_cost = position_cost / position_size if position_size > 0 else 0
                                pnl = position_size * (1.0 - avg_cost)
                                returns.append(pnl)
                            elif final_price < 0.05:
                                # Check if another outcome clearly won
                                prices_float = [float(p) if p else 0.0 for p in prices_list]
                                if any(p > 0.95 for p in prices_float):
                                    # Lost - shares worth $0
                                    avg_cost = position_cost / position_size if position_size > 0 else 0
                                    pnl = position_size * (0.0 - avg_cost)
                                    returns.append(pnl)
                        except (ValueError, IndexError, TypeError):
                            pass
        
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
        Calculate maximum drawdown from peak equity.
        
        Args:
            returns: List of returns (P&L from each trade/resolution)
            
        Returns:
            Maximum drawdown as a percentage (negative value)
        """
        if not returns or len(returns) == 0:
            return 0.0
        
        # Calculate cumulative equity curve
        cumulative = [sum(returns[:i+1]) for i in range(len(returns))]
        
        # Track peak and max drawdown
        peak = cumulative[0]
        max_dd = 0.0
        
        for value in cumulative:
            # Update peak if we have a new high
            if value > peak:
                peak = value
            
            # Calculate drawdown from peak
            if peak > 0:
                drawdown = ((value - peak) / peak) * 100
                max_dd = min(max_dd, drawdown)
            elif peak < 0:
                # If peak is negative, we're in a loss position
                # Drawdown is still calculated but interpretation differs
                drawdown = ((value - peak) / abs(peak)) * 100
                max_dd = min(max_dd, drawdown)
        
        return max_dd
    
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
    pnl: float,
    recent_trades_window: int = 10,
    check_resolutions: bool = False
) -> Optional[TraderMetrics]:
    """Analyze a trader and calculate their metrics.
    
    Args:
        wallet: Trader's wallet address
        username: Trader's username
        rank: Leaderboard rank
        vol: Trading volume
        pnl: Profit and loss
        recent_trades_window: Number of recent returns to use for Sharpe ratio and max drawdown (default: 10)
        check_resolutions: Check market resolutions (slow, default: False for speed)
    """
    trades = PolymarketAPI.get_trades(wallet)
    
    if not trades:
        return None
    
    # Calculate metrics - skip resolution checks for speed
    returns = SharpeCalculator.calculate_returns_from_trades(trades, check_resolutions=check_resolutions)
    
    # Use only last N returns for Sharpe ratio and max drawdown
    recent_returns = returns[-recent_trades_window:] if len(returns) > recent_trades_window else returns
    
    sharpe_ratio = SharpeCalculator.calculate_sharpe_ratio(recent_returns)
    win_rate = SharpeCalculator.calculate_win_rate(trades)
    max_drawdown = SharpeCalculator.calculate_max_drawdown(recent_returns)
    
    avg_return = statistics.mean(recent_returns) if recent_returns else 0.0
    volatility = statistics.stdev(recent_returns) if len(recent_returns) > 1 else 0.0
    
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
    """Get top N trades by volume for a wallet, filtered to active markets only."""
    from .repositories.markets import MarketsRepository
    
    trades = PolymarketAPI.get_trades(wallet, limit=500)
    markets_repo = MarketsRepository()
    
    trade_infos = []
    for trade in trades:
        try:
            market_slug = trade.get('slug', '')
            
            # Skip if market is not active
            if not market_slug or not markets_repo.is_active(market_slug):
                continue
            
            size = float(trade.get('size', 0))
            price = float(trade.get('price', 0))
            value = size * price
            
            trade_infos.append(TradeInfo(
                market_title=trade.get('title', 'Unknown'),
                market_slug=market_slug,
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
    Find bets that multiple top traders agree on, filtered to active markets only.
    
    Returns list of (market_slug, outcome, trader_count, avg_volume)
    """
    from .repositories.markets import MarketsRepository
    
    print("\nAnalyzing consensus bets across top traders...")
    
    markets_repo = MarketsRepository()
    
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
            
            # Skip if not active market
            if not market_slug or not markets_repo.is_active(market_slug):
                continue
            
            if outcome and side == 'BUY':
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


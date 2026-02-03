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


def create_visualizations(traders: List[TraderMetrics], consensus: List[Tuple[str, str, int, float]]):
    """Create insightful visualizations of the data."""
    
    print("\nGenerating visualizations...")
    
    # Create a figure with multiple subplots - use subplots for better control
    fig, axes = plt.subplots(3, 3, figsize=(24, 18))
    fig.suptitle('Polymarket Top Traders Analysis', fontsize=20, fontweight='bold', y=0.995)
    
    # 1. Sharpe Ratio vs Leaderboard Rank
    ax1 = axes[0, 0]
    ranks = [t.leaderboard_rank for t in traders]
    sharpes = [t.sharpe_ratio for t in traders]
    colors = plt.cm.viridis(np.linspace(0, 1, len(traders)))
    
    scatter = ax1.scatter(ranks, sharpes, c=colors, s=200, alpha=0.6, edgecolors='black', linewidth=2)
    
    for i, trader in enumerate(traders):
        ax1.annotate(f"#{i+1}", (trader.leaderboard_rank, trader.sharpe_ratio),
                    fontsize=8, ha='center', va='center', fontweight='bold')
    
    ax1.set_xlabel('Leaderboard Rank (by P&L)', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Sharpe Ratio', fontsize=12, fontweight='bold')
    ax1.set_title('Sharpe Ratio vs Leaderboard Rank\n(Lower rank = higher P&L)', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.invert_xaxis()  # Lower rank is better
    
    # 2. Sharpe Ratio Distribution
    ax2 = axes[0, 1]
    sharpe_values = [t.sharpe_ratio for t in traders]
    bars = ax2.barh(range(len(traders)), sharpe_values, color=colors, edgecolor='black', linewidth=1.5)
    ax2.set_yticks(range(len(traders)))
    ax2.set_yticklabels([f"#{i+1} {t.username[:15]}" for i, t in enumerate(traders)], fontsize=9)
    ax2.set_xlabel('Sharpe Ratio', fontsize=12, fontweight='bold')
    ax2.set_title('Top 10 Traders by Sharpe Ratio', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='x')
    ax2.axvline(x=0, color='red', linestyle='--', linewidth=2, alpha=0.7)
    
    # 3. Volume vs P&L
    ax3 = axes[0, 2]
    volumes = [t.leaderboard_vol for t in traders]
    pnls = [t.leaderboard_pnl for t in traders]
    
    scatter2 = ax3.scatter(volumes, pnls, c=sharpes, s=300, alpha=0.6, 
                          cmap='RdYlGn', edgecolors='black', linewidth=2)
    
    for i, trader in enumerate(traders):
        ax3.annotate(f"#{i+1}", (trader.leaderboard_vol, trader.leaderboard_pnl),
                    fontsize=8, ha='center', va='center', fontweight='bold')
    
    ax3.set_xlabel('Trading Volume ($)', fontsize=12, fontweight='bold')
    ax3.set_ylabel('Profit & Loss ($)', fontsize=12, fontweight='bold')
    ax3.set_title('Volume vs P&L (colored by Sharpe)', fontsize=14, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    ax3.axhline(y=0, color='red', linestyle='--', linewidth=2, alpha=0.7)
    
    cbar = plt.colorbar(scatter2, ax=ax3)
    cbar.set_label('Sharpe Ratio', fontsize=10, fontweight='bold')
    
    # Format axes
    ax3.ticklabel_format(style='plain', axis='both')
    
    # 4. Win Rate vs Sharpe Ratio
    ax4 = axes[1, 0]
    win_rates = [t.win_rate for t in traders]
    
    scatter3 = ax4.scatter(win_rates, sharpes, c=colors, s=200, alpha=0.6, 
                          edgecolors='black', linewidth=2)
    
    for i, trader in enumerate(traders):
        ax4.annotate(f"#{i+1}", (trader.win_rate, trader.sharpe_ratio),
                    fontsize=8, ha='center', va='center', fontweight='bold')
    
    ax4.set_xlabel('Win Rate (%)', fontsize=12, fontweight='bold')
    ax4.set_ylabel('Sharpe Ratio', fontsize=12, fontweight='bold')
    ax4.set_title('Win Rate vs Sharpe Ratio', fontsize=14, fontweight='bold')
    ax4.grid(True, alpha=0.3)
    
    # 5. Max Drawdown vs Sharpe Ratio
    ax5 = axes[1, 1]
    drawdowns = [t.max_drawdown for t in traders]
    
    scatter4 = ax5.scatter(drawdowns, sharpes, c=colors, s=200, alpha=0.6,
                          edgecolors='black', linewidth=2)
    
    for i, trader in enumerate(traders):
        ax5.annotate(f"#{i+1}", (trader.max_drawdown, trader.sharpe_ratio),
                    fontsize=8, ha='center', va='center', fontweight='bold')
    
    ax5.set_xlabel('Max Drawdown (%)', fontsize=12, fontweight='bold')
    ax5.set_ylabel('Sharpe Ratio', fontsize=12, fontweight='bold')
    ax5.set_title('Max Drawdown vs Sharpe Ratio\n(Lower drawdown = better risk management)', fontsize=14, fontweight='bold')
    ax5.grid(True, alpha=0.3)
    ax5.axvline(x=0, color='green', linestyle='--', linewidth=2, alpha=0.7, label='No Drawdown')
    ax5.legend()
    
    # 6. Risk-Return Profile (Sharpe vs Volatility)
    ax6 = axes[1, 2]
    volatilities = [t.volatility for t in traders]
    
    scatter5 = ax6.scatter(volatilities, sharpes, c=colors, s=200, alpha=0.6,
                          edgecolors='black', linewidth=2)
    
    for i, trader in enumerate(traders):
        ax6.annotate(f"#{i+1}", (trader.volatility, trader.sharpe_ratio),
                    fontsize=8, ha='center', va='center', fontweight='bold')
    
    ax6.set_xlabel('Volatility (Std Dev of Returns)', fontsize=12, fontweight='bold')
    ax6.set_ylabel('Sharpe Ratio', fontsize=12, fontweight='bold')
    ax6.set_title('Risk-Return Profile\n(Higher Sharpe + Lower Vol = Better)', fontsize=14, fontweight='bold')
    ax6.grid(True, alpha=0.3)
    
    # 7. Consensus Bets Distribution
    ax7 = axes[2, 0]
    
    if consensus:
        # Group by trader count
        trader_counts = [c[2] for c in consensus[:20]]
        count_distribution = Counter(trader_counts)
        
        counts = sorted(count_distribution.keys())
        frequencies = [count_distribution[c] for c in counts]
        
        bars = ax7.bar(counts, frequencies, color='steelblue', edgecolor='black', linewidth=1.5, alpha=0.7)
        ax7.set_xlabel('Number of Traders Agreeing', fontsize=12, fontweight='bold')
        ax7.set_ylabel('Number of Consensus Bets', fontsize=12, fontweight='bold')
        ax7.set_title('Consensus Bet Distribution', fontsize=14, fontweight='bold')
        ax7.grid(True, alpha=0.3, axis='y')
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax7.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}',
                    ha='center', va='bottom', fontweight='bold')
    else:
        ax7.text(0.5, 0.5, 'No consensus bets found', ha='center', va='center', 
                fontsize=12, transform=ax7.transAxes)
        ax7.set_title('Consensus Bet Distribution', fontsize=14, fontweight='bold')
    
    # 8. Top Consensus Bets by Volume
    ax8 = axes[2, 1]
    
    if consensus:
        top_consensus = consensus[:10]
        market_labels = [f"{c[0][:30]}..." if len(c[0]) > 30 else c[0] for c in top_consensus]
        avg_volumes = [c[3] for c in top_consensus]
        trader_counts_top = [c[2] for c in top_consensus]
        
        # Color by trader count
        colors_consensus = plt.cm.Reds(np.array(trader_counts_top) / max(trader_counts_top))
        
        bars = ax8.barh(range(len(top_consensus)), avg_volumes, color=colors_consensus, 
                       edgecolor='black', linewidth=1.5)
        ax8.set_yticks(range(len(top_consensus)))
        ax8.set_yticklabels([f"{label} ({count}T)" for label, count in 
                            zip(market_labels, trader_counts_top)], fontsize=8)
        ax8.set_xlabel('Average Volume ($)', fontsize=12, fontweight='bold')
        ax8.set_title('Top 10 Consensus Bets by Volume\n(#T = traders agreeing)', 
                     fontsize=14, fontweight='bold')
        ax8.grid(True, alpha=0.3, axis='x')
        ax8.ticklabel_format(style='plain', axis='x')
    else:
        ax8.text(0.5, 0.5, 'No consensus bets found', ha='center', va='center',
                fontsize=12, transform=ax8.transAxes)
        ax8.set_title('Top 10 Consensus Bets by Volume', fontsize=14, fontweight='bold')
    
    # 9. Trader Performance Heatmap
    ax9 = axes[2, 2]
    
    # Create normalized metrics for heatmap
    metrics_data = []
    metric_names = ['Sharpe\nRatio', 'Win\nRate', 'P&L\nRank', 'Low\nDrawdown']
    
    for trader in traders:
        # Normalize metrics to 0-1 scale
        sharpe_norm = (trader.sharpe_ratio - min(sharpes)) / (max(sharpes) - min(sharpes)) if max(sharpes) != min(sharpes) else 0.5
        win_norm = trader.win_rate / 100
        pnl_norm = 1 - (trader.leaderboard_rank - 1) / 49  # Inverse rank (higher is better)
        drawdown_norm = 1 - abs(trader.max_drawdown) / 100 if trader.max_drawdown < 0 else 1  # Less negative is better
        
        metrics_data.append([sharpe_norm, win_norm, pnl_norm, drawdown_norm])
    
    im = ax9.imshow(metrics_data, cmap='RdYlGn', aspect='auto', vmin=0, vmax=1)
    
    ax9.set_xticks(range(len(metric_names)))
    ax9.set_xticklabels(metric_names, fontsize=10, fontweight='bold')
    ax9.set_yticks(range(len(traders)))
    ax9.set_yticklabels([f"#{i+1}" for i in range(len(traders))], fontsize=9)
    ax9.set_title('Trader Performance Heatmap\n(Green = Better)', fontsize=14, fontweight='bold')
    
    cbar2 = plt.colorbar(im, ax=ax9)
    cbar2.set_label('Normalized Score', fontsize=10, fontweight='bold')
    
    # Verify all 9 subplots are present
    print(f"  Created {len(axes.flat)} subplots")
    for idx, ax in enumerate(axes.flat, 1):
        if ax.get_title():
            print(f"  Plot {idx}: {ax.get_title()}")
    
    # Adjust layout to prevent overlap
    plt.tight_layout(rect=[0, 0, 1, 0.99])
    
    # Save the figure
    filename = f'polymarket_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
    plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"\n✓ Visualizations saved to: {filename}")
    print(f"✓ Generated 9 plots in 3x3 grid")
    
    # Show the plot
    plt.show()
    plt.close()


def main():
    parser = argparse.ArgumentParser(
        description='Analyze top Polymarket traders by Sharpe ratio',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script:
1. Fetches the Polymarket leaderboard (ranked by volume/PnL)
2. Calculates Sharpe ratio for each trader based on trade history
3. Ranks traders by Sharpe ratio (risk-adjusted returns)
4. Shows top 3 highest volume trades for each top trader
5. Identifies consensus bets across all top traders

Examples:
  %(prog)s                           # Analyze top 50 from leaderboard
  %(prog)s --deep-analysis           # Analyze 500+ traders (slower but more accurate)
  %(prog)s --sample-size 200         # Analyze top 200 from leaderboard
  %(prog)s --plot                    # Generate visualizations
  %(prog)s --deep-analysis --plot    # Deep analysis with visualizations
  %(prog)s --json                    # JSON output

Note: The leaderboard API has a limit. --deep-analysis analyzes up to 1000 traders
to find the true top 10 by Sharpe ratio, not just top by volume.
        """
    )
    
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON'
    )
    parser.add_argument(
        '--plot',
        action='store_true',
        help='Generate visualizations (requires matplotlib)'
    )
    parser.add_argument(
        '--deep-analysis',
        action='store_true',
        help='Analyze more traders from leaderboard (500+) before filtering to top 10 by Sharpe'
    )
    parser.add_argument(
        '--sample-size',
        type=int,
        default=50,
        help='Number of traders to analyze from leaderboard (default: 50, max with --deep-analysis: 1000)'
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("POLYMARKET TOP TRADERS ANALYSIS")
    print("=" * 80)
    print()
    print("Note: Polymarket leaderboard ranks by Volume and P&L.")
    print("This script calculates Sharpe ratio (risk-adjusted returns) from trade history.")
    print()
    
    # Determine sample size
    if args.deep_analysis:
        sample_size = min(args.sample_size, 1000)
        print(f"🔍 DEEP ANALYSIS MODE: Analyzing {sample_size} traders from leaderboard")
        print(f"   This will take longer but finds the true top performers by Sharpe ratio")
        print()
    else:
        sample_size = args.sample_size
    
    # Get top 10 traders by Sharpe ratio
    top_traders = get_top_traders_by_sharpe(10, sample_size)
    
    if not top_traders:
        print("No trader data found.")
        return
    
    # Get consensus bets
    consensus = find_consensus_bets(top_traders)
    
    # Generate visualizations if requested
    if args.plot:
        create_visualizations(top_traders, consensus)
        return
    
    if args.json:
        # JSON output
        output = {
            'top_traders': [],
            'consensus_bets': []
        }
        
        for trader in top_traders:
            top_trades = get_top_volume_trades(trader.wallet, 3)
            
            output['top_traders'].append({
                'rank_by_sharpe': top_traders.index(trader) + 1,
                'wallet': trader.wallet,
                'username': trader.username,
                'leaderboard_rank': trader.leaderboard_rank,
                'leaderboard_vol': trader.leaderboard_vol,
                'leaderboard_pnl': trader.leaderboard_pnl,
                'sharpe_ratio': trader.sharpe_ratio,
                'total_trades': trader.total_trades,
                'win_rate': trader.win_rate,
                'max_drawdown': trader.max_drawdown,
                'top_trades': [
                    {
                        'market': t.market_title,
                        'outcome': t.outcome,
                        'side': t.side,
                        'value': t.value
                    }
                    for t in top_trades
                ]
            })
        
        # Get consensus bets
        for market_slug, outcome, count, avg_vol in consensus[:20]:
            output['consensus_bets'].append({
                'market_slug': market_slug,
                'outcome': outcome,
                'trader_count': count,
                'avg_volume': avg_vol
            })
        
        print(json.dumps(output, indent=2))
    else:
        # Human-readable output
        print(f"\n{'='*80}")
        print(f"TOP 10 TRADERS BY SHARPE RATIO")
        print(f"{'='*80}\n")
        
        for i, trader in enumerate(top_traders, 1):
            print(f"#{i} - {trader.username}")
            print(f"  Wallet: {trader.wallet}")
            print(f"  Leaderboard Rank: #{trader.leaderboard_rank}")
            print(f"  Leaderboard Volume: ${trader.leaderboard_vol:,.2f}")
            print(f"  Leaderboard P&L: ${trader.leaderboard_pnl:,.2f}")
            print(f"  Sharpe Ratio: {trader.sharpe_ratio:.4f}")
            print(f"  Total Trades: {trader.total_trades}")
            print(f"  Win Rate: {trader.win_rate:.2f}%")
            print(f"  Max Drawdown: {trader.max_drawdown:.2f}%")
            
            # Get top 3 volume trades
            print(f"\n  Top 3 Highest Volume Trades:")
            top_trades = get_top_volume_trades(trader.wallet, 3)
            
            for j, trade in enumerate(top_trades, 1):
                print(f"    {j}. {trade.market_title}")
                print(f"       Outcome: {trade.outcome} | Side: {trade.side}")
                print(f"       Volume: ${trade.value:,.2f} ({trade.size:,.0f} shares @ ${trade.price:.4f})")
            
            print("-" * 80)
        
        # Find consensus bets
        print(f"\n{'='*80}")
        print(f"CONSENSUS BETS (Agreed by 2+ Top Traders)")
        print(f"{'='*80}\n")
        
        if consensus:
            print(f"Found {len(consensus)} consensus bets\n")
            
            for i, (market_slug, outcome, count, avg_vol) in enumerate(consensus[:20], 1):
                print(f"#{i} - {market_slug}")
                print(f"  Outcome: {outcome}")
                print(f"  Traders: {count}/{len(top_traders)}")
                print(f"  Avg Volume: ${avg_vol:,.2f}")
                print("-" * 80)
        else:
            print("No consensus bets found (no markets with 2+ traders)")


if __name__ == "__main__":
    main()

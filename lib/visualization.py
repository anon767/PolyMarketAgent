import matplotlib.pyplot as plt
import numpy as np
from typing import List, Tuple
from collections import Counter
from datetime import datetime

from .analysis import TraderMetrics


def create_visualizations(traders: List[TraderMetrics], consensus: List[Tuple[str, str, int, float]]):
    """Create insightful visualizations of trader data."""
    
    print("\nGenerating visualizations...")
    
    # Create figure with 3x3 subplots
    fig, axes = plt.subplots(3, 3, figsize=(24, 18))
    fig.suptitle('Polymarket Top Traders Analysis', fontsize=20, fontweight='bold', y=0.995)
    
    # Extract common data
    sharpes = [t.sharpe_ratio for t in traders]
    colors = plt.cm.viridis(np.linspace(0, 1, len(traders)))
    
    # 1. Sharpe Ratio vs Leaderboard Rank
    _plot_sharpe_vs_rank(axes[0, 0], traders, colors)
    
    # 2. Sharpe Ratio Distribution
    _plot_sharpe_distribution(axes[0, 1], traders, colors)
    
    # 3. Volume vs P&L
    _plot_volume_vs_pnl(axes[0, 2], traders, sharpes)
    
    # 4. Win Rate vs Sharpe Ratio
    _plot_win_rate_vs_sharpe(axes[1, 0], traders, colors)
    
    # 5. Max Drawdown vs Sharpe Ratio
    _plot_drawdown_vs_sharpe(axes[1, 1], traders, colors)
    
    # 6. Risk-Return Profile
    _plot_risk_return(axes[1, 2], traders, colors)
    
    # 7. Consensus Bets Distribution
    _plot_consensus_distribution(axes[2, 0], consensus)
    
    # 8. Top Consensus Bets by Volume
    _plot_top_consensus(axes[2, 1], consensus)
    
    # 9. Trader Performance Heatmap
    _plot_performance_heatmap(axes[2, 2], traders, sharpes)
    
    # Verify all subplots
    print(f"  Created {len(axes.flat)} subplots")
    for idx, ax in enumerate(axes.flat, 1):
        if ax.get_title():
            print(f"  Plot {idx}: {ax.get_title()}")
    
    # Adjust layout and save
    plt.tight_layout(rect=[0, 0, 1, 0.99])
    
    filename = f'polymarket_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
    plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"\n✓ Visualizations saved to: {filename}")
    print(f"✓ Generated 9 plots in 3x3 grid")
    
    plt.show()
    plt.close()


def _plot_sharpe_vs_rank(ax, traders: List[TraderMetrics], colors):
    """Plot Sharpe Ratio vs Leaderboard Rank."""
    ranks = [t.leaderboard_rank for t in traders]
    sharpes = [t.sharpe_ratio for t in traders]
    
    ax.scatter(ranks, sharpes, c=colors, s=200, alpha=0.6, edgecolors='black', linewidth=2)
    
    for i, trader in enumerate(traders):
        ax.annotate(f"#{i+1}", (trader.leaderboard_rank, trader.sharpe_ratio),
                   fontsize=8, ha='center', va='center', fontweight='bold')
    
    ax.set_xlabel('Leaderboard Rank (by P&L)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Sharpe Ratio', fontsize=12, fontweight='bold')
    ax.set_title('Sharpe Ratio vs Leaderboard Rank\n(Lower rank = higher P&L)', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.invert_xaxis()


def _plot_sharpe_distribution(ax, traders: List[TraderMetrics], colors):
    """Plot Sharpe Ratio Distribution."""
    sharpe_values = [t.sharpe_ratio for t in traders]
    
    ax.barh(range(len(traders)), sharpe_values, color=colors, edgecolor='black', linewidth=1.5)
    ax.set_yticks(range(len(traders)))
    ax.set_yticklabels([f"#{i+1} {t.username[:15]}" for i, t in enumerate(traders)], fontsize=9)
    ax.set_xlabel('Sharpe Ratio', fontsize=12, fontweight='bold')
    ax.set_title('Top 10 Traders by Sharpe Ratio', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='x')
    ax.axvline(x=0, color='red', linestyle='--', linewidth=2, alpha=0.7)


def _plot_volume_vs_pnl(ax, traders: List[TraderMetrics], sharpes: List[float]):
    """Plot Volume vs P&L."""
    volumes = [t.leaderboard_vol for t in traders]
    pnls = [t.leaderboard_pnl for t in traders]
    
    scatter = ax.scatter(volumes, pnls, c=sharpes, s=300, alpha=0.6,
                        cmap='RdYlGn', edgecolors='black', linewidth=2)
    
    for i, trader in enumerate(traders):
        ax.annotate(f"#{i+1}", (trader.leaderboard_vol, trader.leaderboard_pnl),
                   fontsize=8, ha='center', va='center', fontweight='bold')
    
    ax.set_xlabel('Trading Volume ($)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Profit & Loss ($)', fontsize=12, fontweight='bold')
    ax.set_title('Volume vs P&L (colored by Sharpe)', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color='red', linestyle='--', linewidth=2, alpha=0.7)
    ax.ticklabel_format(style='plain', axis='both')
    
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('Sharpe Ratio', fontsize=10, fontweight='bold')


def _plot_win_rate_vs_sharpe(ax, traders: List[TraderMetrics], colors):
    """Plot Win Rate vs Sharpe Ratio."""
    win_rates = [t.win_rate for t in traders]
    sharpes = [t.sharpe_ratio for t in traders]
    
    ax.scatter(win_rates, sharpes, c=colors, s=200, alpha=0.6, edgecolors='black', linewidth=2)
    
    for i, trader in enumerate(traders):
        ax.annotate(f"#{i+1}", (trader.win_rate, trader.sharpe_ratio),
                   fontsize=8, ha='center', va='center', fontweight='bold')
    
    ax.set_xlabel('Win Rate (%)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Sharpe Ratio', fontsize=12, fontweight='bold')
    ax.set_title('Win Rate vs Sharpe Ratio', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)


def _plot_drawdown_vs_sharpe(ax, traders: List[TraderMetrics], colors):
    """Plot Max Drawdown vs Sharpe Ratio."""
    drawdowns = [t.max_drawdown for t in traders]
    sharpes = [t.sharpe_ratio for t in traders]
    
    ax.scatter(drawdowns, sharpes, c=colors, s=200, alpha=0.6, edgecolors='black', linewidth=2)
    
    for i, trader in enumerate(traders):
        ax.annotate(f"#{i+1}", (trader.max_drawdown, trader.sharpe_ratio),
                   fontsize=8, ha='center', va='center', fontweight='bold')
    
    ax.set_xlabel('Max Drawdown (%)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Sharpe Ratio', fontsize=12, fontweight='bold')
    ax.set_title('Max Drawdown vs Sharpe Ratio\n(Lower drawdown = better risk management)', 
                fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.axvline(x=0, color='green', linestyle='--', linewidth=2, alpha=0.7, label='No Drawdown')
    ax.legend()


def _plot_risk_return(ax, traders: List[TraderMetrics], colors):
    """Plot Risk-Return Profile."""
    volatilities = [t.volatility for t in traders]
    sharpes = [t.sharpe_ratio for t in traders]
    
    ax.scatter(volatilities, sharpes, c=colors, s=200, alpha=0.6, edgecolors='black', linewidth=2)
    
    for i, trader in enumerate(traders):
        ax.annotate(f"#{i+1}", (trader.volatility, trader.sharpe_ratio),
                   fontsize=8, ha='center', va='center', fontweight='bold')
    
    ax.set_xlabel('Volatility (Std Dev of Returns)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Sharpe Ratio', fontsize=12, fontweight='bold')
    ax.set_title('Risk-Return Profile\n(Higher Sharpe + Lower Vol = Better)', 
                fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)


def _plot_consensus_distribution(ax, consensus: List[Tuple[str, str, int, float]]):
    """Plot Consensus Bets Distribution."""
    if consensus:
        trader_counts = [c[2] for c in consensus[:20]]
        count_distribution = Counter(trader_counts)
        
        counts = sorted(count_distribution.keys())
        frequencies = [count_distribution[c] for c in counts]
        
        bars = ax.bar(counts, frequencies, color='steelblue', edgecolor='black', 
                     linewidth=1.5, alpha=0.7)
        ax.set_xlabel('Number of Traders Agreeing', fontsize=12, fontweight='bold')
        ax.set_ylabel('Number of Consensus Bets', fontsize=12, fontweight='bold')
        ax.set_title('Consensus Bet Distribution', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height, f'{int(height)}',
                   ha='center', va='bottom', fontweight='bold')
    else:
        ax.text(0.5, 0.5, 'No consensus bets found', ha='center', va='center',
               fontsize=12, transform=ax.transAxes)
        ax.set_title('Consensus Bet Distribution', fontsize=14, fontweight='bold')


def _plot_top_consensus(ax, consensus: List[Tuple[str, str, int, float]]):
    """Plot Top Consensus Bets by Volume."""
    if consensus:
        top_consensus = consensus[:10]
        market_labels = [f"{c[0][:30]}..." if len(c[0]) > 30 else c[0] for c in top_consensus]
        avg_volumes = [c[3] for c in top_consensus]
        trader_counts = [c[2] for c in top_consensus]
        
        colors = plt.cm.Reds(np.array(trader_counts) / max(trader_counts))
        
        ax.barh(range(len(top_consensus)), avg_volumes, color=colors, 
               edgecolor='black', linewidth=1.5)
        ax.set_yticks(range(len(top_consensus)))
        ax.set_yticklabels([f"{label} ({count}T)" for label, count in 
                           zip(market_labels, trader_counts)], fontsize=8)
        ax.set_xlabel('Average Volume ($)', fontsize=12, fontweight='bold')
        ax.set_title('Top 10 Consensus Bets by Volume\n(#T = traders agreeing)',
                    fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='x')
        ax.ticklabel_format(style='plain', axis='x')
    else:
        ax.text(0.5, 0.5, 'No consensus bets found', ha='center', va='center',
               fontsize=12, transform=ax.transAxes)
        ax.set_title('Top 10 Consensus Bets by Volume', fontsize=14, fontweight='bold')


def _plot_performance_heatmap(ax, traders: List[TraderMetrics], sharpes: List[float]):
    """Plot Trader Performance Heatmap."""
    metrics_data = []
    metric_names = ['Sharpe\nRatio', 'Win\nRate', 'P&L\nRank', 'Low\nDrawdown']
    
    for trader in traders:
        sharpe_norm = (trader.sharpe_ratio - min(sharpes)) / (max(sharpes) - min(sharpes)) if max(sharpes) != min(sharpes) else 0.5
        win_norm = trader.win_rate / 100
        pnl_norm = 1 - (trader.leaderboard_rank - 1) / 49
        drawdown_norm = 1 - abs(trader.max_drawdown) / 100 if trader.max_drawdown < 0 else 1
        
        metrics_data.append([sharpe_norm, win_norm, pnl_norm, drawdown_norm])
    
    im = ax.imshow(metrics_data, cmap='RdYlGn', aspect='auto', vmin=0, vmax=1)
    
    ax.set_xticks(range(len(metric_names)))
    ax.set_xticklabels(metric_names, fontsize=10, fontweight='bold')
    ax.set_yticks(range(len(traders)))
    ax.set_yticklabels([f"#{i+1}" for i in range(len(traders))], fontsize=9)
    ax.set_title('Trader Performance Heatmap\n(Green = Better)', fontsize=14, fontweight='bold')
    
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Normalized Score', fontsize=10, fontweight='bold')

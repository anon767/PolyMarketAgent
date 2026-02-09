#!/usr/bin/env python3
"""
AI-Powered Polymarket Trading Bot - CLI Entry Point
"""
import argparse
import os
from dotenv import load_dotenv

from lib.bot import TradingBot
from lib.providers import ChatGPTProvider, ClaudeProvider
from lib.analysis import get_top_traders_by_sharpe, find_consensus_bets
from lib.visualization import create_visualizations


def run_analysis(args):
    """Run trader analysis and generate visualizations."""
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
    
    # Get top traders
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
    
    # Print results
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
        print("-" * 80)
    
    # Print consensus bets
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


def run_trading(args):
    """Run AI trading bot."""
    # Get AI provider
    ai_provider_name = os.getenv('AI_PROVIDER', 'chatgpt').lower()
    api_key = args.api_key or os.getenv('OPENAI_API_KEY')
    
    print(f"🤖 Using AI Provider: {ai_provider_name.upper()}")
    
    # Initialize AI provider
    if ai_provider_name == 'bedrock':
        try:
            import boto3
            bedrock_client = boto3.client('bedrock-runtime')
            ai_provider = ClaudeProvider(bedrock_client)
            print("   Model: Claude Opus 4 via AWS Bedrock")
            print("✅ Connected to AWS Bedrock")
        except Exception as e:
            print(f"❌ Error connecting to Bedrock: {e}")
            return
    else:
        if not api_key:
            print("❌ Error: ChatGPT provider requires OPENAI_API_KEY")
            print("Set AI_PROVIDER=bedrock in .env to use AWS Bedrock instead")
            return
        ai_provider = ChatGPTProvider(api_key)
        print("   Model: GPT-4o-mini via OpenAI")
    
    # Get wallet address
    wallet_address = os.getenv('POLYMARKET_WALLET')
    if not wallet_address:
        print("⚠️  Warning: POLYMARKET_WALLET not set in .env - trade history will be unavailable")
    
    # Determine if live trading
    dry_run = not args.live
    polymarket_client = None
    
    if args.live:
        # Get Polymarket credentials
        pm_key = os.getenv('POLYMARKET_API_KEY')
        pm_secret = os.getenv('POLYMARKET_SECRET')
        pm_passphrase = os.getenv('POLYMARKET_PASSPHRASE')
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
            
            # Initialize client
            polymarket_client = ClobClient(
                host="https://clob.polymarket.com",
                key=pm_private_key,
                chain_id=137,
                signature_type=1,
                funder=pm_wallet
            )
            
            # Create or derive API credentials
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
    bot = TradingBot(
        ai_provider=ai_provider,
        initial_balance=args.balance,
        dry_run=dry_run,
        polymarket_client=polymarket_client,
        wallet_address=wallet_address,
        max_single_bet_pct=args.max_bet_pct
    )
    
    # Run trading session
    bot.run_trading_session(max_iterations=args.max_iterations)


def main():
    # Load environment variables
    load_dotenv()
    
    parser = argparse.ArgumentParser(
        description='AI-powered Polymarket trading bot and analysis tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run trading bot (dry-run)
  %(prog)s trade
  
  # Run trading bot (live mode)
  %(prog)s trade --live --max-iterations 20
  
  # Analyze top traders
  %(prog)s analyze
  
  # Analyze with visualizations
  %(prog)s analyze --plot
  
  # Deep analysis with more traders
  %(prog)s analyze --deep-analysis --plot
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Trading command
    trade_parser = subparsers.add_parser('trade', help='Run AI trading bot')
    trade_parser.add_argument(
        '--balance',
        type=float,
        default=100.0,
        help='Starting balance in USD (default: 100, dry-run always uses $50)'
    )
    trade_parser.add_argument(
        '--max-iterations',
        type=int,
        default=20,
        help='Maximum AI iterations (default: 20)'
    )
    trade_parser.add_argument(
        '--api-key',
        help='OpenAI API key (or set OPENAI_API_KEY env var)'
    )
    trade_parser.add_argument(
        '--live',
        action='store_true',
        help='Enable LIVE trading (default is dry-run/simulation)'
    )
    trade_parser.add_argument(
        '--max-bet-pct',
        type=float,
        default=1.0,
        help='Maximum percentage of available balance for a single bet (0.0-1.0, default: 1.0 = 100%%)'
    )
    
    # Analysis command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze top traders')
    analyze_parser.add_argument(
        '--plot',
        action='store_true',
        help='Generate visualizations (requires matplotlib)'
    )
    analyze_parser.add_argument(
        '--deep-analysis',
        action='store_true',
        help='Analyze more traders from leaderboard (500+) before filtering to top 10 by Sharpe'
    )
    analyze_parser.add_argument(
        '--sample-size',
        type=int,
        default=50,
        help='Number of traders to analyze from leaderboard (default: 50, max with --deep-analysis: 1000)'
    )
    
    args = parser.parse_args()
    
    # Default to trade if no command specified
    if not args.command:
        args.command = 'trade'
        args.balance = 100.0
        args.max_iterations = 20
        args.api_key = None
        args.live = False
        args.max_bet_pct = 1.0
    
    # Route to appropriate command
    if args.command == 'analyze':
        run_analysis(args)
    elif args.command == 'trade':
        run_trading(args)


if __name__ == "__main__":
    main()

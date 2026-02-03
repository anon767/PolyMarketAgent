"""Main trading bot orchestrator."""
import json
import time
from typing import Dict, Any
from datetime import datetime

from ..providers import AIProvider
from ..repositories.wallets import WalletsRepository
from .resources import get_system_prompt, TOOLS
from .tools import ToolExecutor
from .trading import BetPlacer


class TradingBot:
    """AI-powered Polymarket trading bot."""
    
    def __init__(
        self,
        ai_provider: AIProvider,
        initial_balance: float = 100.0,
        dry_run: bool = True,
        polymarket_client=None,
        wallet_address: str = None,
        max_single_bet_pct: float = 1.0
    ):
        """
        Initialize trading bot.
        
        Args:
            ai_provider: AI provider instance (ChatGPT or Claude)
            initial_balance: Starting balance in USD
            dry_run: If True, simulates bets without real execution
            polymarket_client: Polymarket CLOB client for live trading
            wallet_address: Wallet address for fetching real trade history
            max_single_bet_pct: Maximum percentage of available balance for a single bet
        """
        self.ai_provider = ai_provider
        self.dry_run = dry_run
        self.polymarket_client = polymarket_client
        self.wallet_address = wallet_address
        self.max_single_bet_pct = max(0.0, min(1.0, max_single_bet_pct))
        
        # Track positions
        self.positions = []
        self.simulated_trades = []
        
        # Set initial balance
        if dry_run:
            self.balance = 50.0  # Always $50 in dry-run
        else:
            if wallet_address:
                wallets_repo = WalletsRepository()
                real_balance = wallets_repo.get_balance(wallet_address)
                if real_balance is not None:
                    self.balance = real_balance
                    print(f"✅ Fetched real balance: ${self.balance:.2f}")
                else:
                    self.balance = initial_balance
                    print(f"⚠️  Using provided balance: ${self.balance:.2f}")
            else:
                self.balance = initial_balance
        
        # Initialize tool executor and bet placer
        self.tool_executor = ToolExecutor(self)
        self.bet_placer = BetPlacer(self)
    
    def execute_function(self, function_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a function call from AI."""
        # Map function names to methods
        if function_name == "place_bet":
            return self.bet_placer.place_bet(**arguments)
        
        # All other functions are handled by tool executor
        method = getattr(self.tool_executor, function_name, None)
        if method:
            return method(**arguments)
        else:
            return {"error": f"Unknown function: {function_name}"}
    
    def run_trading_session(self, max_iterations: int = 10):
        """Run an AI trading session."""
        print("=" * 80)
        print("AI-POWERED POLYMARKET TRADING BOT")
        print("=" * 80)
        print(f"Mode: {'DRY RUN (Simulated)' if self.dry_run else 'LIVE TRADING'}")
        print(f"AI Provider: {self.ai_provider.get_name()}")
        print(f"Starting Balance: ${self.balance:.2f}")
        print(f"Risk Profile: AGGRESSIVE")
        print("=" * 80)
        print()
        
        # Get current date/time and inject into system prompt
        current_datetime = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p %Z")
        system_prompt = get_system_prompt(current_datetime)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Analyze Polymarket trading opportunities and EXECUTE trades."}
        ]
        
        for iteration in range(max_iterations):
            print(f"\n{'='*80}")
            print(f"ITERATION {iteration + 1}/{max_iterations}")
            print(f"{'='*80}\n")
            
            # Get AI response
            response = self.ai_provider.chat(messages, TOOLS)
            
            if not response:
                print("Failed to get response from AI")
                break
            
            choice = response['choices'][0]
            message = choice['message']
            
            # Add assistant message to history
            messages.append(message)
            
            # Check if done
            if choice['finish_reason'] == 'stop':
                print("\n🤖 AI Analysis:")
                print(message.get('content', ''))
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
            
            time.sleep(1)
        
        # Final summary
        self._print_summary()
    
    def _print_summary(self):
        """Print final trading session summary."""
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

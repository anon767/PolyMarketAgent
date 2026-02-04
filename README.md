# Polymarket AI Trading Bot

An AI-powered copy-trader bot that analyzes top Polymarket traders and automatically places bets based on consensus signals and proven strategies.

## Setup

1. Install dependencies:
```bash
pip install py-clob-client web3 requests python-dotenv pygooglenews boto3 matplotlib numpy
```

2. Create a `.env` file with your credentials (see `.env.example`):
```bash
# AI Provider (chatgpt or bedrock)
AI_PROVIDER=bedrock

# Polymarket Credentials
POLYMARKET_WALLET=0x...
POLYMARKET_PRIVATE_KEY=0x...
POLYMARKET_API_KEY=...
POLYMARKET_SECRET=...
POLYMARKET_PASSPHRASE=...

# OpenAI (only if using chatgpt)
OPENAI_API_KEY=sk-...
```

## Usage

### Trading Bot

Run in dry-run mode (simulated with $50):
```bash
python bot.py trade
```

Run with live trading:
```bash
python bot.py trade --live --max-iterations 20
```

Adjust risk parameters:
```bash
python bot.py trade --live --max-bet-pct 0.5  # Max 50% per bet
```

### Trader Analysis

Analyze top traders by Sharpe ratio:
```bash
python bot.py analyze
```

Generate visualizations:
```bash
python bot.py analyze --plot
```

Deep analysis (more traders):
```bash
python bot.py analyze --deep-analysis --plot
```
## Example Analysis

![Trader Analysis](polymarket_analysis_20260201_174013.png)

*9-panel visualization showing Sharpe ratios, win rates, drawdowns, consensus bets, and performance heatmaps*

## Example Bot Output

```
================================================================================
TRADING SESSION COMPLETE
================================================================================
Final Balance: $13.92
Total Bets Placed: 2
Total Invested: $6.00

Positions:
  1. nba-bos-dal-2026-02-03 - Celtics ($3.00)
     Reasoning: Strong consensus bet with 5 top traders agreeing on Celtics. Despite missing Tatum, Celtics have shown depth and continued success. Recent news confirms strong team performance. Multiple whale traders including scaffolding (0.87 Sharpe) are backing this position. Using Knowledge Base strategy #2 (Copy Trading Profitable Whales) and following consensus.
  2. nba-nyk-was-2026-02-03 - Knicks ($3.00)
     Reasoning: Highest consensus bet with 6 top traders agreeing on Knicks. Recent news shows Knicks are favored with strong momentum after OG Anunoby acquisition. Multiple whale traders including tsybka (17.2% win rate) and alliswell (28.08% win rate) are backing this position. News indicates favorable matchup against struggling Wizards team. Following Knowledge Base strategies #2 (Copy Trading) and #7 (Trade Reality vs Media Narratives).
================================================================================
```

## License

MIT


# Polymarket AI Trading Bot

An AI-powered trading bot that analyzes top Polymarket traders and automatically places bets based on consensus signals and proven strategies.

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

## License

MIT


# Polymarket AI Trading Bot

An AI-powered trading bot that analyzes top Polymarket traders and automatically places bets based on consensus signals and proven strategies.

## Setup

Install dependencies: `pip install py-clob-client web3 requests python-dotenv pygooglenews boto3`

Create a `.env` file with your Polymarket credentials (wallet address, private key). The bot supports both ChatGPT and AWS Bedrock (Claude) as AI providers. Set `AI_PROVIDER=bedrock` or `AI_PROVIDER=chatgpt` in your `.env` file.

## Usage

Run in dry-run mode (simulated): `python polymarket_copy_trader.py`

Run with live trading: `python polymarket_copy_trader.py --live --max-iterations 15`

The bot analyzes top traders by Sharpe ratio, finds consensus bets where multiple successful traders agree, checks recent news, and executes trades following 14 proven strategies from the knowledge base. It automatically manages risk by diversifying across markets and tracking open orders.

## Example Analysis

![Trader Analysis](polymarket_analysis_20260201_174013.png)

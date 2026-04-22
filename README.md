# Forex Bot Exness $200 DEMO

Multi-agent forex trading bot for Exness demo account with dynamic risk management, asymmetric hybrid strategy, and self-learning capabilities.

## Features

- **5 Independent Agents** - Each with unique perception and strategy
- **Dynamic Risk Management** - Adjusts lot size based on equity curve, drawdown, and consecutive losses
- **Asymmetric Hybrid Strategy** - Combines technical, macro, and sentiment signals with adaptive weighting
- **Noise Filtering** - Filters out losing trades caused by spread spikes, slippage, or market noise
- **Concept Drift Detection** - Detects market regime changes and resets learning
- **Self-Correction Learning** - Learns from filtered losses to improve future decisions
- **Redis Support** - Optional real-time state sharing and event bus
- **Telegram Notifications** - Real-time trade alerts and bot status
- **Streamlit Dashboard** - Visualize performance, agent states, and trades
- **Backtesting Engine** - Test strategies on historical data

## Project Structure

```
forex_bot_exness_200usd_DEMO/
├── src/
│   ├── config/          # Configuration (base, live, paper, backtest)
│   ├── core/            # Core types, utils, logger, exceptions
│   ├── data/            # Data sources, filters, storage
│   ├── agents/          # 5 trading agents with memory and learning
│   ├── execution/       # Brokers (Exness MT5, demo, backtest)
│   ├── orchestrator/    # Main trading loops (live, demo, backtest)
│   ├── notifications/   # Telegram integration
│   └── dashboard/       # Streamlit monitoring dashboard
├── docker/              # Docker and docker-compose
├── scripts/             # Utility scripts
├── tests/               # Unit and integration tests
├── monitoring/          # Monitoring configs
├── logs/                # Application logs
└── data/historical/     # Historical market data
```

## Quick Start

### 1. Clone and Install

```bash
# Clone repository
cd forex_bot_exness_200usd_DEMO

# Install dependencies
bun install

# Copy environment file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

### 2. Database Setup

```bash
# Initialize TimescaleDB
python scripts/init_db.py
```

### 3. Run Demo Mode (No Real Trading)

```bash
# Start with demo broker (simulated trading)
 bun run src/main.py --mode demo
```

### 4. Access Dashboard

```bash
# In another terminal
cd dashboard
streamlit run app.py
```

Open http://localhost:8501

## Configuration

Edit `.env` or config files in `src/config/`:

- `TOTAL_CAPITAL=200` - Starting capital
- `DYNAMIC_RISK=True` - Enable risk scaling based on equity curve
- `MAX_AGENTS=5` - Number of trading agents
- `RISK_BASE=0.01` - Base risk per trade (1%)
- `MAX_RISK=0.02` - Maximum risk (2%)
- `MIN_RISK=0.005` - Minimum risk (0.5%)
- `TRADING_START=7` - Trading starts at 7 AM UTC
- `TRADING_END=22` - Trading ends at 10 PM UTC
- `MAX_CONSECUTIVE_LOSSES=3` - Stop after 3 consecutive losses
- `ENABLE_NOISE_FILTER=True` - Filter losing trades from noise
- `USE_REDIS=False` - Enable Redis for real-time updates

## Risk Management

### Dynamic Risk Calculation

Risk per agent adjusts based on:
- Current equity vs peak (drawdown)
- Consecutive losses
- Market volatility

Formula:
```
risk_dynamic = calculate_dynamic_risk(equity, peak, drawdown_limit, base_risk, min_risk, max_risk)
lot_size = (capital * risk_dynamic) / (sl_pips * pip_value_per_lot)
```

### Loss Controller

Automatically stops the bot after `MAX_CONSECUTIVE_LOSSES` (default: 3) losing trades to preserve capital.

## Agent Architecture

Each agent consists of:

1. **Perception** - Technical indicators, macro events, sentiment analysis
2. **Strategy** - Signal fusion and decision making
3. **Asymmetric Hybrid** - Weight allocation, skew detection, adaptive mixing
4. **Memory** - Trade history and loss memory
5. **Risk** - Per-agent risk calculation
6. **Execution** - Order placement with smart routing
7. **Learning** - Loss minimization and self-correction

## Training & Backtesting

```bash
# Run backtest
python scripts/backtest.py --start 2024-01-01 --end 2024-12-31

# Create and train agents
python scripts/create_agents.py --train

# Monitor deployment
bash scripts/deploy_monitor.sh
```

## Docker Deployment

```bash
# Start all services (PostgreSQL, Redis, bot)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Telegram Alerts

Bot sends notifications for:
- Each trade (entry/exit, P&L, current equity)
- Consecutive loss warnings
- Bot shutdown alerts
- Daily performance reports

## Dashboard

Streamlit dashboard shows:
- Real-time equity curve
- Agent performance breakdown
- Recent trades table
- Risk metrics (drawdown, win rate, Sharpe)
- System status and logs

## Safety Features

- **Demo-first** - Default to demo mode, explicit opt-in for live trading
- **Max risk limits** - Hard caps on per-trade and total risk
- **Trading hours** - Only trade within configured hours
- **Loss limits** - Auto-stop after consecutive losses
- **Noise filter** - Discard losing trades from spreads/slippage before learning
- **Drift detector** - Reset learning when market regime changes

## Requirements

- Python 3.11+
- MetaTrader 5 (for live/demo trading)
- TimescaleDB (PostgreSQL with timescale extension)
- Redis (optional, for real-time features)
- Exness Demo Account ($200)

## Support

For issues or questions, check the logs in `logs/` or open an issue on GitHub.

## Disclaimer

This bot is for educational and demo purposes only. Trading forex involves significant risk. Always test thoroughly on demo before considering live trading. Past performance doesn't guarantee future results.

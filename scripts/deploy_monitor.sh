#!/bin/bash
# Deployment monitor script for forex bot

set -e

echo "=== Forex Bot Deployment Monitor ==="
echo ""

# Check if Docker containers are running
if command -v docker-compose &> /dev/null; then
    echo "Docker Compose Services:"
    docker-compose ps
    echo ""
fi

# Check Python dependencies
echo "Checking Python environment..."
if [ -d "venv" ]; then
    source venv/bin/activate
fi

python -c "import MetaTrader5; print('MT5: OK')" 2>/dev/null || echo "MT5: Not installed"
python -c "import pika; print('RabbitMQ: OK')" 2>/dev/null || echo "RabbitMQ: Not installed"
python -c "import psycopg2; print('PostgreSQL: OK')" 2>/dev/null || echo "PostgreSQL: Not installed"

echo ""
echo "Checking logs..."
if [ -d "logs" ]; then
    echo "Recent system log entries:"
    tail -n 20 logs/system.log 2>/dev/null || echo "No logs found"
fi

echo ""
echo "Bot status: Check running processes"
ps aux | grep -E "python.*main|streamlit" | grep -v grep || echo "No bot processes running"

echo ""
echo "=== Monitor complete ==="

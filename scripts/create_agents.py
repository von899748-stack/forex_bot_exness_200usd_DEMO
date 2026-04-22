#!/usr/bin/env python
"""Create and initialize agent records in database"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from src.config.paper import PaperConfig
from src.agents.factory import AgentFactory
from src.core.logger import setup_logger

logger = setup_logger()


def main():
    config = PaperConfig()
    factory = AgentFactory()
    symbols = config.symbols.symbols

    logger.info(f"Creating up to {config.risk.max_agents} agents for symbols: {symbols}")

    agents = factory.create_standard_agents(config, symbols)
    logger.info(f"Created {len(agents)} agents")

    for agent in agents:
        logger.info(f"  Agent {agent.agent_id}: {agent.__class__.__name__} for {agent.symbol}")


if __name__ == "__main__":
    main()

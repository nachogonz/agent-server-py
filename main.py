#!/usr/bin/env python3
"""
LiveKit Python Agent Server - Main Entry Point

This script starts the LiveKit agent with the appropriate configuration
based on environment variables.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add src directory to the Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from livekit.agents import cli, WorkerOptions
from src.agent import entrypoint, prewarm

# Configure logging - suppress LiveKit warnings
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        # Add file handler if needed
        # logging.FileHandler('agent.log')
    ]
)
# Suppress specific loggers
logging.getLogger("livekit.agents").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def main():
    """Main entry point for the LiveKit Python agent."""
    
    # Log startup information
    agent_mode = os.getenv("MODE", "orders")
    logger.info(f"Starting LiveKit Python Agent in mode: {agent_mode}")
    
    # Verify required environment variables
    required_vars = ["LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
    
    # Create worker options
    worker_options = WorkerOptions(
        entrypoint_fnc=entrypoint,
        prewarm_fnc=prewarm,
    )
    
    # Start the agent using LiveKit CLI
    cli.run_app(worker_options)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
LiveKit Python Agent Server - Main Entry Point

This script starts the LiveKit agent with the appropriate configuration
using the realtime API as shown in the LiveKit documentation.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add src directory to the Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, Agent, JobContext, RoomInputOptions
from livekit.plugins import openai

from src.agent import VoiceAssistant

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def entrypoint(ctx: agents.JobContext):
    """Main entry point for the LiveKit agent using realtime API."""
    
    # Check required environment variables
    required_env_vars = ["LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "OPENAI_API_KEY"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    # Determine agent mode
    agent_mode = os.getenv("MODE", "orders")
    logger.info(f"Starting LiveKit agent in mode: {agent_mode}")

    try:
        # Create the voice assistant
        assistant = VoiceAssistant(mode=agent_mode)
        
        # Create agent session with realtime model
        session = AgentSession(
            llm=openai.realtime.RealtimeModel(
                voice="coral"
            )
        )

        # Start the session
        await session.start(
            room=ctx.room,
            agent=assistant,
        )

        # Generate initial greeting
        await session.generate_reply(
            instructions="Greet the user and offer your assistance."
        )

        logger.info("✅ Agent session started successfully")

    except Exception as error:
        logger.error(f"❌ Error in agent entry: {error}")
        raise


async def prewarm(proc):
    """Prewarm function to initialize models."""
    logger.info("🔄 Prewarming agent models...")
    proc.userdata["prewarmed"] = True
    logger.info("✅ Agent models prewarmed successfully")
    return


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
    worker_options = agents.WorkerOptions(
        entrypoint_fnc=entrypoint,
        prewarm_fnc=prewarm,
    )
    
    # Start the agent using LiveKit CLI
    agents.cli.run_app(worker_options)


if __name__ == "__main__":
    main()
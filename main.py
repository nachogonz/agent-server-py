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
from livekit.agents import AgentSession
from livekit.plugins import openai, elevenlabs, deepgram, silero

from src.agent import VoiceAssistant
from src.agent_tools import build_livekit_tools
from src.config.config_manager import ConfigManager

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def entrypoint(ctx: agents.JobContext):
    """Main entry point for the LiveKit agent using STT-LLM-TTS pipeline."""

    # Check required environment variables  
    required_env_vars = ["LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "OPENAI_API_KEY", "ELEVEN_API_KEY"]
    # ElevenLabs and Deepgram are optional for basic functionality
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]

    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )

    try:
        # Connect to the room first
        await ctx.connect()

        # Initialize configuration manager
        config_manager = ConfigManager()
        
        # Check for agent name in environment variable
        agent_name = os.getenv("AGENT_NAME")
        
        if agent_name:
            logger.info(f"Loading specific agent: {agent_name}")
            # Create the voice assistant with specific agent configuration
            assistant = VoiceAssistant(config_manager=config_manager, agent_name=agent_name)
            logger.info(f"✅ Loaded agent '{assistant.get_agent_name()}' in mode: {assistant.mode}")
        else:
            # Create the voice assistant with default configuration
            assistant = VoiceAssistant(config_manager=config_manager)
            logger.info(f"✅ Loaded default agent '{assistant.get_agent_name()}' in mode: {assistant.mode}")

        # Build and attach function tools to the assistant
        logger.info("🔧 Building and attaching function tools...")
        tools = build_livekit_tools(assistant.function_context)
        await assistant.update_tools(tools)
        logger.info(f"✅ Attached {len(tools)} function tools to assistant")

        # Create configurations using the config manager
        logger.info("🔧 Creating TTS, STT, LLM, and VAD configurations...")
        tts_config = config_manager.create_tts()
        stt_config = config_manager.create_stt()
        llm_config = config_manager.create_llm()
        vad_config = config_manager.create_vad()

        # Create agent session with STT-LLM-TTS pipeline
        session = AgentSession(
            stt=stt_config,
            llm=llm_config,
            tts=tts_config,
            vad=vad_config,
        )

        # Start the session
        await session.start(
            room=ctx.room,
            agent=assistant,
        )

        # Generate initial greeting using configured instructions
        await session.generate_reply(
            instructions=assistant.get_greeting_instructions(),
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

    # Initialize configuration to get mode for logging
    config_manager = ConfigManager()
    
    # Show available agents
    available_agents = config_manager.list_available_agents()
    agent_name = os.getenv("AGENT_NAME")
    
    if available_agents:
        logger.info(f"Available agents: {', '.join(available_agents)}")
        if agent_name:
            if agent_name in available_agents:
                logger.info(f"Using specified agent: {agent_name}")
            else:
                logger.warning(f"⚠️ Agent '{agent_name}' not found, will use default")
        else:
            logger.info(f"No AGENT_NAME specified, using first available agent: {available_agents[0]}")
    else:
        logger.warning("⚠️ No agents found in configuration")
    
    agent_mode = config_manager.get_agent_mode()
    logger.info(f"Starting LiveKit Python Agent in mode: {agent_mode}")

    # Verify required environment variables
    required_vars = ["LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.error(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )
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

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

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def entrypoint(ctx: agents.JobContext):
    """Main entry point for the LiveKit agent using STT-LLM-TTS pipeline."""

    # Check required environment variables  
    required_env_vars = ["LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "OPENAI_API_KEY"]
    # ElevenLabs and Deepgram are optional for basic functionality
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]

    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )

    # Determine agent mode
    agent_mode = os.getenv("MODE", "orders")
    logger.info(f"Starting LiveKit agent in mode: {agent_mode}")

    try:
        # Connect to the room first
        await ctx.connect()
        
        # Create the voice assistant
        assistant = VoiceAssistant(mode=agent_mode)

        # Configure TTS - use ElevenLabs if available, fallback to OpenAI
        tts_config = None
        eleven_api_key = os.getenv("ELEVEN_API_KEY") or os.getenv("ELEVENLABS_API_KEY")
        
        if eleven_api_key:
            try:
                logger.info("Using ElevenLabs TTS")
                # Use a more common voice ID that should exist (Rachel - default female voice)
                voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Rachel voice
                tts_config = elevenlabs.TTS(
                    api_key=eleven_api_key,
                    voice_id=voice_id, 
                    model="eleven_multilingual_v2"
                )
                logger.info(f"✅ ElevenLabs TTS configured with voice: {voice_id}")
            except Exception as e:
                logger.warning(f"⚠️ ElevenLabs TTS failed to initialize: {e}")
                logger.info("Falling back to OpenAI TTS")
                tts_config = openai.TTS(voice="nova")
        else:
            logger.info("Using OpenAI TTS (ElevenLabs API key not found)")
            tts_config = openai.TTS(voice="nova")

        # Configure STT - use Deepgram if available, fallback to OpenAI
        stt_config = None
        deepgram_api_key = os.getenv("DEEPGRAM_API_KEY")
        
        if deepgram_api_key:
            logger.info("Using Deepgram STT")
            stt_config = deepgram.STT(model="nova-2")
        else:
            logger.info("Using OpenAI STT (Deepgram API key not found)")
            stt_config = openai.STT()

        # Create agent session with STT-LLM-TTS pipeline
        session = AgentSession(
            stt=stt_config,
            llm=openai.LLM(model="gpt-4o-mini"),
            tts=tts_config,
            vad=silero.VAD.load(),
        )

        # Start the session
        await session.start(
            room=ctx.room,
            agent=assistant,
        )

        # Generate initial greeting
        await session.generate_reply(
            instructions="Greet the user and offer your assistance.",
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

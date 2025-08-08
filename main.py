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
from livekit.agents import AgentSession, metrics, MetricsCollectedEvent
from livekit.agents.metrics import LLMMetrics, STTMetrics, TTSMetrics, EOUMetrics
from livekit.plugins import openai, elevenlabs, deepgram, silero

from src.agent import VoiceAssistant
from src.agent_tools import build_livekit_tools
from src.config.config_manager import ConfigManager

# LangSmith imports
try:
    from langsmith import Client
    from langsmith.run_helpers import traceable
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    Client = None
    traceable = None

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

        # --- Metrics & Telemetry setup (non-blocking) ---
        usage_collector = metrics.UsageCollector()
        # Track per-speech turn timing to compute total latency
        speech_latency_state: dict[str, dict[str, float]] = {}
        
        # --- LangSmith setup ---
        langsmith_client = None
        # Check for both possible environment variable names
        langsmith_api_key = os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")
        langsmith_project = os.getenv("LANGSMITH_PROJECT") or os.getenv("LANGCHAIN_PROJECT", "livekit-voice-agent")
        
        if LANGSMITH_AVAILABLE and langsmith_api_key:
            try:
                # Set required environment variables for LangSmith
                os.environ["LANGCHAIN_API_KEY"] = langsmith_api_key
                os.environ["LANGCHAIN_PROJECT"] = langsmith_project
                os.environ["LANGCHAIN_TRACING_V2"] = "true"
                
                langsmith_client = Client(
                    api_key=langsmith_api_key,
                    api_url="https://api.smith.langchain.com"
                )
                logger.info(f"✅ LangSmith client initialized for project: {langsmith_project}")
            except Exception as e:
                logger.warning(f"⚠️ LangSmith initialization failed: {e}")
        else:
            if not LANGSMITH_AVAILABLE:
                logger.info("📝 LangSmith not available (langsmith package not installed)")
            if not langsmith_api_key:
                logger.info("📝 LangSmith not configured (set LANGSMITH_API_KEY or LANGCHAIN_API_KEY to enable)")
        
        # Track conversation data for LangSmith
        conversation_data = {
            "session_id": ctx.room.name if hasattr(ctx, 'room') and ctx.room else "unknown",
            "agent_name": assistant.get_agent_name(),
            "turns": [],
            "metrics": []
        }

        async def _handle_llm(m: LLMMetrics):
            try:
                if m.speech_id:
                    state = speech_latency_state.setdefault(m.speech_id, {})
                    state["llm_ttft"] = float(m.ttft or 0.0)
            except Exception as e:
                logger.debug(f"llm metrics handle error: {e}")

        async def _handle_stt(m: STTMetrics):
            try:
                # Nothing to aggregate into latency; still useful for logs/usage
                return
            except Exception as e:
                logger.debug(f"stt metrics handle error: {e}")

        async def _handle_tts(m: TTSMetrics):
            try:
                if m.speech_id:
                    state = speech_latency_state.setdefault(m.speech_id, {})
                    state["tts_ttfb"] = float(m.ttfb or 0.0)
            except Exception as e:
                logger.debug(f"tts metrics handle error: {e}")

        async def _handle_eou(m: EOUMetrics):
            try:
                if m.speech_id:
                    state = speech_latency_state.setdefault(m.speech_id, {})
                    state["eou_delay"] = float(m.end_of_utterance_delay or 0.0)
            except Exception as e:
                logger.debug(f"eou metrics handle error: {e}")

        async def _maybe_log_total_latency(speech_id: str):
            try:
                state = speech_latency_state.get(speech_id)
                if not state:
                    return
                if all(k in state for k in ("eou_delay", "llm_ttft", "tts_ttfb")):
                    total_latency = state["eou_delay"] + state["llm_ttft"] + state["tts_ttfb"]
                    logger.info(
                        f"⚡ TOTAL LATENCY (speech_id={speech_id}): "
                        f"EOU={state['eou_delay']:.3f}s + LLM TTFT={state['llm_ttft']:.3f}s + TTS TTFB={state['tts_ttfb']:.3f}s = "
                        f"{total_latency:.3f}s"
                    )
                    # cleanup to keep memory bounded
                    speech_latency_state.pop(speech_id, None)
            except Exception as e:
                logger.debug(f"latency compute error: {e}")

        async def _process_metrics_event(m):
            try:
                # Log formatted metrics for LLM, STT, TTS, and EOU
                metrics.log_metrics(m)
                
                # Terminal logging for different metric types
                if isinstance(m, LLMMetrics):
                    logger.info(f"📊 LLM Metrics - Duration: {m.duration:.3f}s, Tokens: {m.completion_tokens}/{m.prompt_tokens}, TTFT: {m.ttft:.3f}s, Speech ID: {m.speech_id}")
                elif isinstance(m, STTMetrics):
                    logger.info(f"🎤 STT Metrics - Audio Duration: {m.audio_duration:.3f}s, Processing: {m.duration:.3f}s, Streamed: {m.streamed}")
                elif isinstance(m, TTSMetrics):
                    logger.info(f"🔊 TTS Metrics - Audio Duration: {m.audio_duration:.3f}s, Characters: {m.characters_count}, TTFB: {m.ttfb:.3f}s, Speech ID: {m.speech_id}")
                elif isinstance(m, EOUMetrics):
                    logger.info(f"🎯 EOU Metrics - EOU Delay: {m.end_of_utterance_delay:.3f}s, Transcription Delay: {m.transcription_delay:.3f}s, Speech ID: {m.speech_id}")
                
                # Store metrics in conversation data for LangSmith
                metric_data = {
                    "type": type(m).__name__,
                    "speech_id": getattr(m, "speech_id", None),
                    "timestamp": asyncio.get_event_loop().time(),
                    "data": {
                        "duration": getattr(m, "duration", None),
                        "audio_duration": getattr(m, "audio_duration", None),
                        "completion_tokens": getattr(m, "completion_tokens", None),
                        "prompt_tokens": getattr(m, "prompt_tokens", None),
                        "ttft": getattr(m, "ttft", None),
                        "ttfb": getattr(m, "ttfb", None),
                        "characters_count": getattr(m, "characters_count", None),
                        "end_of_utterance_delay": getattr(m, "end_of_utterance_delay", None),
                        "transcription_delay": getattr(m, "transcription_delay", None),
                        "streamed": getattr(m, "streamed", None),
                    }
                }
                conversation_data["metrics"].append(metric_data)
                
                # Aggregate usage across session
                usage_collector.collect(m)
                
                # Dispatch to per-type handlers concurrently
                tasks = []
                if isinstance(m, LLMMetrics):
                    tasks.append(_handle_llm(m))
                elif isinstance(m, STTMetrics):
                    tasks.append(_handle_stt(m))
                elif isinstance(m, TTSMetrics):
                    tasks.append(_handle_tts(m))
                elif isinstance(m, EOUMetrics):
                    tasks.append(_handle_eou(m))

                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)

                # After handling, check if we can compute total latency for this turn
                speech_id = getattr(m, "speech_id", None)
                if speech_id:
                    await _maybe_log_total_latency(speech_id)
            except Exception as e:
                logger.warning(f"metrics processing error: {e}")

        @session.on("metrics_collected")
        def _on_metrics_collected(ev: MetricsCollectedEvent):
            # Schedule logging/aggregation in background to avoid impacting realtime loop
            asyncio.create_task(_process_metrics_event(ev.metrics))
            logger.info(f"📊 Metrics collected for type: {type(ev.metrics).__name__}")

        async def _log_usage_summary():
            try:
                summary = usage_collector.get_summary()
                logger.info("=" * 60)
                logger.info("📈 SESSION USAGE SUMMARY")
                logger.info("=" * 60)
                logger.info(f"Usage Summary: {summary}")
                logger.info("=" * 60)
                
                # Send conversation data to LangSmith
                if langsmith_client:
                    try:
                        await _send_to_langsmith(conversation_data, summary)
                    except Exception as e:
                        logger.warning(f"LangSmith upload failed: {e}")
            except Exception as e:
                logger.warning(f"usage summary error: {e}")

        # Emit usage summary when worker shuts down
        ctx.add_shutdown_callback(_log_usage_summary)

        # Optional: enable Langfuse telemetry if env is present
        def setup_langfuse_if_configured():
            try:
                if not (
                    os.getenv("LANGFUSE_PUBLIC_KEY")
                    and os.getenv("LANGFUSE_SECRET_KEY")
                    and os.getenv("LANGFUSE_HOST")
                ):
                    return

                import base64  # local import to avoid overhead when unused
                from livekit.agents.telemetry import set_tracer_provider
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                    OTLPSpanExporter,
                )
                from opentelemetry.sdk.trace import TracerProvider
                from opentelemetry.sdk.trace.export import BatchSpanProcessor

                public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
                secret_key = os.getenv("LANGFUSE_SECRET_KEY")
                host = os.getenv("LANGFUSE_HOST")

                langfuse_auth = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()
                os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = f"{host.rstrip('/')}/api/public/otel"
                os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"Authorization=Basic {langfuse_auth}"

                trace_provider = TracerProvider()
                trace_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
                set_tracer_provider(trace_provider)
                logger.info("✅ Langfuse telemetry enabled")
            except Exception as e:
                logger.warning(f"telemetry setup skipped: {e}")

        setup_langfuse_if_configured()
        
        # Test LangSmith connection if available
        if langsmith_client:
            try:
                async def test_langsmith():
                    try:
                        @traceable(name="LiveKit Agent Test")
                        def test_function():
                            return {"test": "connection", "status": "connected"}
                        
                        result = await asyncio.get_event_loop().run_in_executor(None, test_function)
                        logger.info(f"✅ LangSmith connection test successful: {result}")
                    except Exception as e:
                        logger.warning(f"⚠️ LangSmith connection test failed: {e}")
                
                # Run test in background
                asyncio.create_task(test_langsmith())
            except Exception as e:
                logger.warning(f"⚠️ LangSmith test setup failed: {e}")
        
        # Add conversation tracking to session events
        # Note: LiveKit events might have different names, let's try multiple approaches
        def _log_conversation_event(event_type, ev):
            try:
                logger.info(f"🎯 {event_type} event received: {type(ev)}")
                logger.info(f"🎯 Event attributes: {dir(ev)}")
                
                # Try to extract text from various possible attributes
                text = ""
                speech_id = None
                
                # Common attribute names for text
                for attr in ['text', 'message', 'content', 'transcript']:
                    if hasattr(ev, attr):
                        text = getattr(ev, attr, "")
                        logger.info(f"🎯 Found text in {attr}: {text[:50]}...")
                        break
                
                # Common attribute names for speech_id
                for attr in ['speech_id', 'id', 'turn_id', 'session_id']:
                    if hasattr(ev, attr):
                        speech_id = getattr(ev, attr, None)
                        logger.info(f"🎯 Found speech_id in {attr}: {speech_id}")
                        break
                
                turn_data = {
                    "type": event_type,
                    "timestamp": asyncio.get_event_loop().time(),
                    "text": text,
                    "speech_id": speech_id
                }
                conversation_data["turns"].append(turn_data)
                logger.info(f"💬 {event_type} logged to LangSmith: {len(text)} chars")
            except Exception as e:
                logger.error(f"❌ {event_type} logging error: {e}")
                import traceback
                logger.error(f"❌ {event_type} error details: {traceback.format_exc()}")
        
        # Try different possible event names
        try:
            @session.on("user_message")
            def _on_user_message(ev):
                _log_conversation_event("user_message", ev)
        except Exception as e:
            logger.warning(f"⚠️ Could not register user_message event: {e}")
        
        try:
            @session.on("agent_message")
            def _on_agent_message(ev):
                _log_conversation_event("agent_message", ev)
        except Exception as e:
            logger.warning(f"⚠️ Could not register agent_message event: {e}")
        
        # Try alternative event names
        try:
            @session.on("message")
            def _on_message(ev):
                _log_conversation_event("message", ev)
        except Exception as e:
            logger.warning(f"⚠️ Could not register message event: {e}")
        
        try:
            @session.on("transcript")
            def _on_transcript(ev):
                _log_conversation_event("transcript", ev)
        except Exception as e:
            logger.warning(f"⚠️ Could not register transcript event: {e}")
        
        async def _send_to_langsmith(conv_data, usage_summary):
            """Send conversation data and metrics to LangSmith using tracing."""
            try:
                logger.info(f"📤 Sending conversation data to LangSmith...")
                logger.info(f"   - Session: {conv_data['session_id']}")
                logger.info(f"   - Turns: {len(conv_data['turns'])}")
                logger.info(f"   - Metrics: {len(conv_data['metrics'])}")
                
                # Use LangSmith tracing decorator for reliable data sending
                @traceable(name=f"LiveKit Voice Agent - {conv_data['agent_name']}")
                def send_conversation_data():
                    return {
                        "session_id": conv_data["session_id"],
                        "agent_name": conv_data["agent_name"],
                        "conversation_turns": len(conv_data["turns"]),
                        "total_metrics": len(conv_data["metrics"]),
                        "usage_summary": str(usage_summary),
                        "conversation_data": conv_data
                    }
                
                # Send data using tracing
                result = await asyncio.get_event_loop().run_in_executor(None, send_conversation_data)
                logger.info(f"✅ Conversation data sent to LangSmith via tracing (session: {conv_data['session_id']})")
                logger.info(f"✅ Data sent: {result}")
                
            except Exception as e:
                logger.error(f"❌ Failed to send to LangSmith: {e}")
                import traceback
                logger.error(f"❌ LangSmith error details: {traceback.format_exc()}")
                raise

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

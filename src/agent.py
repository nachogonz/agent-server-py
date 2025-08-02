import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

from dotenv import load_dotenv
import httpx

from livekit import agents
from livekit.agents import AgentSession, Agent, JobContext, WorkerOptions, cli

from .functions import FunctionContext
from .prompts.orders import SYSTEM_PROMPT_ORDERS
from .prompts.appointments import SYSTEM_PROMPT_APPOINTMENTS
from .prompts.leads import SYSTEM_PROMPT_LEADS
from .prompts.airline import SYSTEM_PROMPT_AIRLINE
from .prompts.jarvis import SYSTEM_PROMPT_JARVIS
from .health_server import start_health_server, stop_health_server

load_dotenv()

# Configure logging - suppress LiveKit warnings
logging.basicConfig(level=logging.WARNING)
logging.getLogger("livekit.agents").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


class VoiceAssistant(Agent):
    """Voice assistant agent that handles different business scenarios."""
    
    def __init__(self, mode: str = "orders"):
        # Select system prompt based on mode
        instructions_map = {
            "appointments": SYSTEM_PROMPT_APPOINTMENTS,
            "leads": SYSTEM_PROMPT_LEADS,
            "airline": SYSTEM_PROMPT_AIRLINE,
            "jarvis": SYSTEM_PROMPT_JARVIS,
            "orders": SYSTEM_PROMPT_ORDERS  # default
        }
        
        instructions = instructions_map.get(mode, SYSTEM_PROMPT_ORDERS)
        instructions += "\n\nIMPORTANT: Keep responses SHORT (≤ 2 sentences). Speak quickly and get to the point."
        
        super().__init__(instructions=instructions)
        self.mode = mode
        self.function_context = FunctionContext()
        self.session_id = f"livekit-{int(datetime.now().timestamp())}-{os.urandom(4).hex()}"
        self.conversation_items: List[Dict[str, Any]] = []
        self.session_start_time = datetime.now().isoformat()

    def get_system_prompt(self) -> str:
        """Get the system prompt based on the current mode."""
        instructions_map = {
            "appointments": SYSTEM_PROMPT_APPOINTMENTS,
            "leads": SYSTEM_PROMPT_LEADS,
            "airline": SYSTEM_PROMPT_AIRLINE,
            "jarvis": SYSTEM_PROMPT_JARVIS,
            "orders": SYSTEM_PROMPT_ORDERS  # default
        }
        
        instructions = instructions_map.get(self.mode, SYSTEM_PROMPT_ORDERS)
        instructions += "\n\nIMPORTANT: Keep responses SHORT (≤ 2 sentences). Speak quickly and get to the point."
        return instructions
        
    async def capture_conversation_item(self, role: str, content: str):
        """Capture conversation items for analytics."""
        self.conversation_items.append({
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "content": content
        })
        
    async def send_analytics_data(self):
        """Send conversation analytics to backend."""
        try:
            api_base_url = os.getenv("API_BASE_URL", "http://localhost:3001")
            payload = {
                "sessionId": self.session_id,
                "agentId": self.mode,
                "startTime": self.session_start_time,
                "endTime": datetime.now().isoformat(),
                "conversationItems": self.conversation_items
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{api_base_url}/metrics/livekit-complete-session",
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    logger.info("✅ Analytics data sent successfully")
                else:
                    logger.error(f"❌ Failed to send analytics data: {response.status_code}")
                    
        except Exception as error:
            logger.error(f"❌ Error sending analytics data: {error}")

    async def on_chat_message(self, message: str) -> str:
        """Handle chat messages from the console."""
        try:
            # Capture user message
            await self.capture_conversation_item("user", message)

            # Get the system prompt based on mode
            system_prompt = self.get_system_prompt()
            
            # Build conversation history from previous messages
            conversation = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history (last 10 messages to keep context manageable)
            for item in self.conversation_items[-20:]:  # Last 20 items (10 exchanges)
                conversation.append({
                    "role": item["role"],
                    "content": item["content"]
                })
            
            # Add current message
            conversation.append({"role": "user", "content": message})
            
            # Call OpenAI LLM for real response
            import openai
            client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=conversation,
                max_tokens=500,
                temperature=0.7
            )
            
            assistant_response = response.choices[0].message.content

            # Capture assistant response
            await self.capture_conversation_item("assistant", assistant_response)

            return assistant_response
        except Exception as error:
            logger.error(f"Error handling chat message: {error}")
            return "I'm sorry, I encountered an error. Please try again."


async def entrypoint(ctx: JobContext):
    """Main entry point for the LiveKit agent."""
    
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
        
        # For console mode, create interactive chat
        if ctx.room and ctx.room.name == "fake_room":
            logger.info("✅ Starting interactive console chat...")
            await interactive_console_chat(assistant)
        else:
            # Real LiveKit mode - connect to actual room
            # Start health check server (only if not already running)
            try:
                health_runner = await start_health_server()
            except OSError as e:
                if "address already in use" in str(e):
                    logger.info("Health server already running on port 8080")
                    health_runner = None
                else:
                    raise
            
            # Connect to the LiveKit room
            await ctx.connect()
            logger.info(f"Connected to LiveKit room: {ctx.room.name}")
            
            # Wait for participants
            participant = await ctx.wait_for_participant()
            logger.info(f"Participant joined: {participant.identity}")
            
            # Set up cleanup function
            def cleanup():
                async def _cleanup():
                    try:
                        logger.info("🔄 Session ending, sending analytics data...")
                        await assistant.send_analytics_data()
                        if health_runner:
                            await stop_health_server(health_runner)
                        logger.info("✅ Session cleanup completed")
                    except Exception as error:
                        logger.error(f"❌ Error during session cleanup: {error}")
                
                asyncio.create_task(_cleanup())

            # Register cleanup callback
            ctx.add_shutdown_callback(cleanup)
            
            logger.info("✅ Agent connected and ready for LiveKit interaction")

    except Exception as error:
        logger.error(f"❌ Error in agent entry: {error}")
        raise


async def prewarm(proc):
    """Prewarm function to initialize models."""
    # Basic prewarm for the agent - no async operations needed
    proc.userdata["prewarmed"] = True
    return


async def interactive_console_chat(assistant: VoiceAssistant):
    """Interactive console chat interface for testing the agent."""
    print("\n" + "="*60)
    print("🤖 LiveKit Python Agent - Interactive Console")
    print("="*60)
    print(f"Agent Mode: {assistant.mode}")
    print("Type your messages and press Enter to chat with the agent.")
    print("Type 'quit' or 'exit' to end the session.")
    print("="*60)
    
    try:
        while True:
            # Get user input
            user_input = input("\n👤 You: ").strip()
            
            # Check for exit commands
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye! Ending session...")
                break
            
            if not user_input:
                continue
            
            # Get agent response
            print("🤖 Agent: ", end="", flush=True)
            response = await assistant.on_chat_message(user_input)
            print(response)
            
    except KeyboardInterrupt:
        print("\n👋 Session interrupted. Goodbye!")
    except Exception as error:
        print(f"\n❌ Error in console chat: {error}")
    finally:
        print("✅ Console session ended.")





if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        )
    )
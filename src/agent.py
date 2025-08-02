import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

from dotenv import load_dotenv
import httpx

from livekit import agents
from livekit.agents import Agent, JobContext

from .functions import FunctionContext
from .prompts.orders import SYSTEM_PROMPT_ORDERS
from .prompts.appointments import SYSTEM_PROMPT_APPOINTMENTS
from .prompts.leads import SYSTEM_PROMPT_LEADS
from .prompts.airline import SYSTEM_PROMPT_AIRLINE
from .prompts.jarvis import SYSTEM_PROMPT_JARVIS

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VoiceAssistant(Agent):
    """Voice assistant agent that handles different business scenarios using LiveKit realtime API."""
    
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

    async def on_session_end(self):
        """Handle session cleanup when the session ends."""
        try:
            logger.info("🔄 Session ending, sending analytics data...")
            await self.send_analytics_data()
            logger.info("✅ Session cleanup completed")
        except Exception as error:
            logger.error(f"❌ Error during session cleanup: {error}")
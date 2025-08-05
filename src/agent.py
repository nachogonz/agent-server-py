import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

from dotenv import load_dotenv
import httpx
from livekit.agents import Agent

from .functions import FunctionContext
from .config.config_manager import ConfigManager

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VoiceAssistant(Agent):
    """Voice assistant that provides system prompts and handles analytics for VoicePipelineAgent."""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None, mode: Optional[str] = None, agent_name: Optional[str] = None):
        # Initialize configuration manager
        self.config_manager = config_manager or ConfigManager()
        
        # Load specific agent config if agent_name is provided
        if agent_name:
            success = self.config_manager.load_agent_by_name(agent_name)
            if not success:
                logger.warning(f"⚠️ Failed to load agent '{agent_name}', using default config")
        
        # Get mode from config if not provided
        self.mode = mode or self.config_manager.get_agent_mode()
        
        # Get the system prompt from config manager
        instructions = self._get_system_prompt_from_config()
        
        # Initialize the parent Agent class with instructions
        super().__init__(instructions=instructions)
        
        self.function_context = FunctionContext()
        self.session_id = f"livekit-{int(datetime.now().timestamp())}-{os.urandom(4).hex()}"
        self.conversation_items: List[Dict[str, Any]] = []
        self.session_start_time = datetime.now().isoformat()

    def _get_system_prompt_from_config(self) -> str:
        """Get the system prompt from config manager."""
        prompt = self.config_manager.get_agent_prompt()
        
        # If no prompt in config, provide a basic fallback
        if not prompt:
            logger.warning("⚠️ No prompt found in config, using fallback")
            prompt = "You are a helpful voice assistant. Respond in a friendly, conversational manner."
        
        # Add the common instruction for short responses
        prompt += "\n\nIMPORTANT: Keep responses SHORT (≤ 2 sentences). Speak quickly and get to the point."
        return prompt

    def get_system_prompt(self) -> str:
        """Get the system prompt from config manager."""
        return self._get_system_prompt_from_config()

    def get_function_definitions(self) -> List[Dict[str, Any]]:
        """Get function definitions for the agent."""
        return self.function_context.create_function_context()
    
    def get_tts_config(self) -> Dict[str, Any]:
        """Get TTS configuration from config manager."""
        return self.config_manager.get_tts_config()
    
    def get_stt_config(self) -> Dict[str, Any]:
        """Get STT configuration from config manager."""
        return self.config_manager.get_stt_config()
    
    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration from config manager."""
        return self.config_manager.get_llm_config()
    
    def get_vad_config(self) -> Dict[str, Any]:
        """Get VAD configuration from config manager."""
        return self.config_manager.get_vad_config()
    
    def get_greeting_instructions(self) -> str:
        """Get greeting instructions from config manager."""
        return self.config_manager.get_greeting_instructions()
    
    def get_agent_name(self) -> str:
        """Get the agent name from config manager."""
        return self.config_manager.get_agent_name()
    
    def list_available_agents(self) -> List[str]:
        """Get list of available agent names."""
        return self.config_manager.list_available_agents()
    
    def load_agent_by_name(self, agent_name: str) -> bool:
        """Load a specific agent configuration by name."""
        return self.config_manager.load_agent_by_name(agent_name)
        
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
                "agentId": self.get_agent_name(),
                "agentMode": self.mode,
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
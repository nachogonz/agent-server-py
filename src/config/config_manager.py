"""
Configuration Manager for Voice Assistant

This module handles loading configuration from JSON files with future support for database configurations.
It provides a centralized way to manage TTS, STT, LLM, and agent configurations.
"""

import json
import logging
import os
import asyncio
from typing import Dict, Any, Optional, List
from pathlib import Path

import httpx
from livekit.plugins import openai, elevenlabs, deepgram, silero

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages configuration loading from API server with JSON file fallback."""
    
    def __init__(self, config_source: Optional[str] = None, api_base_url: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_source: Path to JSON config file for fallback or None for default
            api_base_url: Base URL for the agents API server
        """
        self.config_source = config_source or self._get_default_config_path()
        self.api_base_url = api_base_url or os.getenv("API_BASE_URL", "http://localhost:3000")
        self.config: Dict[str, Any] = {}
        # Check environment variable for API usage preference
        use_api_env = os.getenv("USE_API_CONFIG", "true").lower()
        self.use_api = use_api_env in ("true", "1", "yes", "on")
        logger.info(f"🔗 API configuration: {'enabled' if self.use_api else 'disabled'} (URL: {self.api_base_url})")
        self._load_config()
    
    def _get_default_config_path(self) -> str:
        """Get the default configuration file path."""
        # Look for config.json in the project root (two levels up from src/config/)
        project_root = Path(__file__).parent.parent.parent
        return str(project_root / "config.json")
    
    def _fetch_agents_from_api(self) -> List[Dict[str, Any]]:
        """Fetch all agents from the API server."""
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{self.api_base_url}/agents")
                response.raise_for_status()
                agents = response.json()
                logger.info(f"✅ Fetched {len(agents)} agents from API")
                return agents
        except httpx.RequestError as e:
            logger.error(f"❌ Request error fetching agents from API: {e}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ HTTP error fetching agents from API: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error fetching agents from API: {e}")
            raise
    
    def _fetch_agent_by_name_from_api(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Fetch a specific agent by name from the API server."""
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{self.api_base_url}/agents/name/{agent_name}")
                if response.status_code == 404:
                    logger.warning(f"⚠️ Agent '{agent_name}' not found in API")
                    return None
                response.raise_for_status()
                agent = response.json()
                logger.info(f"✅ Fetched agent '{agent_name}' from API")
                return agent
        except httpx.RequestError as e:
            logger.error(f"❌ Request error fetching agent '{agent_name}' from API: {e}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ HTTP error fetching agent '{agent_name}' from API: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error fetching agent '{agent_name}' from API: {e}")
            raise
    
    def _load_config(self) -> None:
        """Load configuration from API server or fallback to JSON file."""
        if self.use_api:
            try:
                # Try to load from API server first
                agents = self._fetch_agents_from_api()
                if agents and len(agents) > 0:
                    self.config = agents[0]  # Use first agent as default
                    logger.info(f"✅ Configuration loaded from API: {self.api_base_url} (using first agent config)")
                    return
                else:
                    logger.warning("⚠️ No agents found in API, falling back to JSON file")
            except Exception as e:
                logger.warning(f"⚠️ Failed to load from API: {e}, falling back to JSON file")
        
        # Fallback to JSON file loading
        try:
            if os.path.isfile(self.config_source):
                with open(self.config_source, 'r') as f:
                    raw_config = json.load(f)
                
                # Handle array of configurations - use the first one
                if isinstance(raw_config, list) and len(raw_config) > 0:
                    self.config = raw_config[0]
                    logger.info(f"✅ Configuration loaded from JSON: {self.config_source} (using first agent config)")
                elif isinstance(raw_config, dict):
                    self.config = raw_config
                    logger.info(f"✅ Configuration loaded from JSON: {self.config_source}")
                else:
                    logger.warning(f"⚠️ Invalid config format, using defaults")
                    self.config = self._get_default_config()
            else:
                logger.warning(f"⚠️ Config file not found: {self.config_source}, using defaults")
                self.config = self._get_default_config()
        except Exception as e:
            logger.error(f"❌ Error loading config: {e}, using defaults")
            self.config = self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration if file loading fails."""
        return {
            "tts": {
                "provider": "openai",
                "openai": {"voice": "nova"}
            },
            "stt": {
                "provider": "openai",
                "openai": {}
            },
            "llm": {
                "provider": "openai",
                "openai": {"model": "gpt-4o-mini"}
            },
            "vad": {"provider": "silero"},
            "agent": {
                "mode": "orders",
                "greeting_instructions": "Greet the user and offer your assistance."
            }
        }
    
    def get_tts_config(self) -> Dict[str, Any]:
        """Get TTS configuration."""
        return self.config.get("tts", {})
    
    def get_stt_config(self) -> Dict[str, Any]:
        """Get STT configuration."""
        return self.config.get("stt", {})
    
    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration."""
        return self.config.get("llm", {})
    
    def get_vad_config(self) -> Dict[str, Any]:
        """Get VAD configuration."""
        return self.config.get("vad", {})
    
    def get_agent_config(self) -> Dict[str, Any]:
        """Get agent configuration."""
        return self.config.get("agent", {})
    
    def get_agent_mode(self) -> str:
        """Get the agent mode, with config file taking priority over environment variable."""
        config_mode = self.config.get("agent", {}).get("mode")
        return config_mode or "orders" 
    
    def get_greeting_instructions(self) -> str:
        """Get greeting instructions for the agent."""
        return self.config.get("agent", {}).get("greeting_instructions", "Greet the user and offer your assistance.")
    
    def get_agent_prompt(self) -> str:
        """Get the system prompt for the agent."""
        return self.config.get("agent", {}).get("prompt", "")
    
    def get_agent_name(self) -> str:
        """Get the agent name."""
        return self.config.get("name", "default_agent")
    
    def load_agent_by_name(self, agent_name: str) -> bool:
        """
        Load a specific agent configuration by name.
        
        Args:
            agent_name: Name of the agent to load
            
        Returns:
            True if agent was found and loaded, False otherwise
        """
        if self.use_api:
            try:
                # Try to load from API server first
                agent = self._fetch_agent_by_name_from_api(agent_name)
                if agent:
                    self.config = agent
                    logger.info(f"✅ Loaded agent config from API: {agent_name}")
                    return True
                else:
                    logger.warning(f"⚠️ Agent '{agent_name}' not found in API, trying JSON fallback")
            except Exception as e:
                logger.warning(f"⚠️ Failed to load agent '{agent_name}' from API: {e}, trying JSON fallback")
        
        # Fallback to JSON file loading
        try:
            if os.path.isfile(self.config_source):
                with open(self.config_source, 'r') as f:
                    raw_config = json.load(f)
                
                if isinstance(raw_config, list):
                    for agent_config in raw_config:
                        if agent_config.get("name") == agent_name:
                            self.config = agent_config
                            logger.info(f"✅ Loaded agent config from JSON: {agent_name}")
                            return True
                    
                    logger.warning(f"⚠️ Agent '{agent_name}' not found in JSON")
                    return False
                else:
                    logger.warning("⚠️ Config is not an array, cannot load by name")
                    return False
            else:
                logger.warning(f"⚠️ Config file not found")
                return False
        except Exception as e:
            logger.error(f"❌ Error loading agent config by name: {e}")
            return False
    
    def list_available_agents(self) -> List[str]:
        """
        Get list of available agent names from API or config.
        
        Returns:
            List of agent names
        """
        if self.use_api:
            try:
                # Try to get from API server first
                agents = self._fetch_agents_from_api()
                if agents:
                    return [agent.get("name", f"agent_{i}") for i, agent in enumerate(agents)]
                else:
                    logger.warning("⚠️ No agents found in API, trying JSON fallback")
            except Exception as e:
                logger.warning(f"⚠️ Failed to list agents from API: {e}, trying JSON fallback")
        
        # Fallback to JSON file
        try:
            if os.path.isfile(self.config_source):
                with open(self.config_source, 'r') as f:
                    raw_config = json.load(f)
                
                if isinstance(raw_config, list):
                    return [agent.get("name", f"agent_{i}") for i, agent in enumerate(raw_config)]
                else:
                    return [raw_config.get("name", "default_agent")]
            else:
                return []
        except Exception as e:
            logger.error(f"❌ Error listing agents: {e}")
            return []
    
    def reload_config(self) -> None:
        """Reload configuration from API or fallback source."""
        self._load_config()
        logger.info("🔄 Configuration reloaded")
    
    def set_api_enabled(self, enabled: bool) -> None:
        """Enable or disable API usage for configuration loading."""
        self.use_api = enabled
        if enabled:
            logger.info("✅ API configuration loading enabled")
        else:
            logger.info("📁 Fallback to JSON file configuration loading")
    
    def is_api_enabled(self) -> bool:
        """Check if API configuration loading is enabled."""
        return self.use_api
    
    def get_api_base_url(self) -> str:
        """Get the current API base URL."""
        return self.api_base_url
    
    def set_api_base_url(self, url: str) -> None:
        """Set the API base URL."""
        self.api_base_url = url
        logger.info(f"🔗 API base URL updated to: {url}")
    
    def load_agent_config_by_index(self, agent_index: int = 0) -> None:
        """
        Load a specific agent configuration by index from API or array config.
        
        Args:
            agent_index: Index of the agent config to load (default: 0)
        """
        if self.use_api:
            try:
                # Try to load from API server first
                agents = self._fetch_agents_from_api()
                if agents and len(agents) > agent_index:
                    self.config = agents[agent_index]
                    logger.info(f"✅ Loaded agent config from API at index {agent_index}")
                    return
                else:
                    logger.warning(f"⚠️ Agent index {agent_index} not found in API, trying JSON fallback")
            except Exception as e:
                logger.warning(f"⚠️ Failed to load agent by index from API: {e}, trying JSON fallback")
        
        # Fallback to JSON file loading
        try:
            if os.path.isfile(self.config_source):
                with open(self.config_source, 'r') as f:
                    raw_config = json.load(f)
                
                if isinstance(raw_config, list) and len(raw_config) > agent_index:
                    self.config = raw_config[agent_index]
                    logger.info(f"✅ Loaded agent config from JSON at index {agent_index}")
                else:
                    logger.warning(f"⚠️ Agent index {agent_index} not found in JSON, using first or default")
                    self._load_config()
            else:
                logger.warning(f"⚠️ Config file not found, using defaults")
                self._load_config()
        except Exception as e:
            logger.error(f"❌ Error loading agent config by index: {e}")
            self._load_config()
    
    def create_tts(self) -> Any:
        """Create TTS instance based on configuration."""
        tts_config = self.get_tts_config()
        provider = tts_config.get("provider", "openai")
        
        if provider == "elevenlabs":
            eleven_api_key = os.getenv("ELEVEN_API_KEY")
            if eleven_api_key:
                try:
                    elevenlabs_config = tts_config.get("elevenlabs", {})
                    voice_settings_config = elevenlabs_config.get("voice_settings", {})
                    
                    voice_settings = elevenlabs.VoiceSettings(
                        stability=voice_settings_config.get("stability", 0.7),
                        similarity_boost=voice_settings_config.get("similarity_boost", 0.8),
                        style=voice_settings_config.get("style", 0.3),
                        use_speaker_boost=voice_settings_config.get("use_speaker_boost", True),
                        speed=voice_settings_config.get("speed", 1.1)
                    )
                    
                    tts_instance = elevenlabs.TTS(
                        api_key=eleven_api_key,
                        voice_id=elevenlabs_config.get("voice_id", "21m00Tcm4TlvDq8ikWAM"),
                        model=elevenlabs_config.get("model", "eleven_flash_v2_5"),
                        language=elevenlabs_config.get("language", "es"),
                        voice_settings=voice_settings
                    )
                    
                    logger.info(f"✅ ElevenLabs TTS configured with voice: {elevenlabs_config.get('voice_id')}")
                    return tts_instance
                    
                except Exception as e:
                    logger.warning(f"⚠️ ElevenLabs TTS failed to initialize: {e}")
                    logger.info("Falling back to OpenAI TTS")
            else:
                logger.info("ElevenLabs API key not found, falling back to OpenAI TTS")
        
        # Fallback to OpenAI TTS
        openai_config = tts_config.get("openai", {})
        voice = openai_config.get("voice", "nova")
        logger.info(f"Using OpenAI TTS with voice: {voice}")
        return openai.TTS(voice=voice)
    
    def create_stt(self) -> Any:
        """Create STT instance based on configuration."""
        stt_config = self.get_stt_config()
        provider = stt_config.get("provider", "openai")
        
        if provider == "deepgram":
            deepgram_api_key = os.getenv("DEEPGRAM_API_KEY")
            if deepgram_api_key:
                try:
                    deepgram_config = stt_config.get("deepgram", {})
                    model = deepgram_config.get("model", "nova-2")
                    
                    logger.info(f"Using Deepgram STT with model: {model}")
                    return deepgram.STT(model=model)
                    
                except Exception as e:
                    logger.warning(f"⚠️ Deepgram STT failed to initialize: {e}")
                    logger.info("Falling back to OpenAI STT")
            else:
                logger.info("Deepgram API key not found, falling back to OpenAI STT")
        
        # Fallback to OpenAI STT
        logger.info("Using OpenAI STT")
        return openai.STT()
    
    def create_llm(self) -> Any:
        """Create LLM instance based on configuration."""
        llm_config = self.get_llm_config()
        provider = llm_config.get("provider", "openai")
        
        if provider == "openai":
            openai_config = llm_config.get("openai", {})
            model = openai_config.get("model", "gpt-4o-mini")
            
            logger.info(f"Using OpenAI LLM with model: {model}")
            return openai.LLM(model=model)
        
        # Default fallback
        logger.info("Using default OpenAI LLM")
        return openai.LLM(model="gpt-4o-mini")
    
    def create_vad(self) -> Any:
        """Create VAD instance based on configuration."""
        vad_config = self.get_vad_config()
        provider = vad_config.get("provider", "silero")
        
        if provider == "silero":
            logger.info("Using Silero VAD")
            return silero.VAD.load()
        
        # Default fallback
        logger.info("Using default Silero VAD")
        return silero.VAD.load()
    
    # Future database integration methods
    def _load_from_database(self, config_id: str) -> Dict[str, Any]:
        """
        Future method to load configuration from database.
        
        Args:
            config_id: Database configuration identifier
            
        Returns:
            Configuration dictionary
        """
        # TODO: Implement database loading
        # This will be implemented when migrating to database storage
        pass
    
    def save_to_database(self, config_id: str) -> bool:
        """
        Future method to save current configuration to database.
        
        Args:
            config_id: Database configuration identifier
            
        Returns:
            Success status
        """
        # TODO: Implement database saving
        # This will be implemented when migrating to database storage
        pass
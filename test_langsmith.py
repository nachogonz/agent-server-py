#!/usr/bin/env python3
"""
Test script to verify LangSmith integration
"""

import os
import asyncio
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

async def test_langsmith():
    """Test LangSmith connection and data sending."""
    
    # Check if LangSmith is available
    try:
        from langsmith import Client
        logger.info("✅ LangSmith package is available")
    except ImportError:
        logger.error("❌ LangSmith package not installed. Run: pip install langsmith")
        return False
    
    # Check environment variables
    api_key = os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")
    if not api_key:
        logger.error("❌ LANGSMITH_API_KEY or LANGCHAIN_API_KEY not set")
        return False
    
    logger.info(f"✅ LangSmith API key is set")
    
    # Set required environment variables
    os.environ["LANGCHAIN_API_KEY"] = api_key
    os.environ["LANGCHAIN_PROJECT"] = "livekit-voice-agent"
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    
    # Also set LangSmith specific variables
    os.environ["LANGSMITH_API_KEY"] = api_key
    os.environ["LANGSMITH_PROJECT"] = "livekit-voice-agent"
    os.environ["LANGSMITH_ENDPOINT"] = "https://api.smith.langchain.com"
    
    try:
        # Create client with explicit configuration
        client = Client(
            api_key=api_key,
            api_url="https://api.smith.langchain.com"
        )
        logger.info("✅ LangSmith client created successfully")
        
        # Test data
        test_data = {
            "name": "LiveKit Voice Agent Test",
            "run_type": "chain",
            "inputs": {
                "test": "connection",
                "session_id": "test_session_123",
                "agent_name": "test_agent"
            },
            "outputs": {
                "status": "connected",
                "message": "LangSmith integration is working!"
            },
            "extra": {
                "test_metrics": {
                    "llm_duration": 1.234,
                    "tts_duration": 0.567,
                    "total_latency": 1.801
                }
            }
        }
        
        # Send test data using tracing
        logger.info("📤 Sending test data to LangSmith using tracing...")
        
        try:
            from langsmith.run_helpers import traceable
            
            @traceable(name="LiveKit Voice Agent Test")
            def test_function():
                return {
                    "test": "connection",
                    "session_id": "test_session_123",
                    "agent_name": "test_agent",
                    "status": "connected",
                    "message": "LangSmith integration is working!",
                    "test_metrics": {
                        "llm_duration": 1.234,
                        "tts_duration": 0.567,
                        "total_latency": 1.801
                    }
                }
            
            result = test_function()
            logger.info(f"✅ Test data sent successfully via tracing: {result}")
            logger.info("✅ Check LangSmith dashboard for the trace")
            
        except Exception as e:
            logger.error(f"❌ Tracing test exception: {e}")
            raise
        
        return True
        
    except Exception as e:
        logger.error(f"❌ LangSmith test failed: {e}")
        import traceback
        logger.error(f"❌ Error details: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_langsmith())
    if success:
        logger.info("🎉 LangSmith integration test PASSED!")
    else:
        logger.error("💥 LangSmith integration test FAILED!")
        exit(1)

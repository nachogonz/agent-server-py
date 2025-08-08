#!/usr/bin/env python3
"""
Test LangSmith tracing integration
"""

import os
import asyncio
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

async def test_langsmith_tracing():
    """Test LangSmith tracing integration."""
    
    # Check if LangSmith is available
    try:
        from langsmith import Client
        from langsmith.run_helpers import traceable
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
    
    try:
        # Test with traceable decorator
        @traceable(name="LiveKit Voice Agent Test")
        def test_function():
            logger.info("🔧 Test function called")
            return "Test completed successfully"
        
        # Call the traced function
        result = test_function()
        logger.info(f"✅ Traced function result: {result}")
        
        # Test with async function
        @traceable(name="LiveKit Voice Agent Async Test")
        async def test_async_function():
            logger.info("🔧 Async test function called")
            await asyncio.sleep(0.1)  # Simulate some work
            return "Async test completed successfully"
        
        # Call the async traced function
        async_result = await test_async_function()
        logger.info(f"✅ Async traced function result: {async_result}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ LangSmith tracing test failed: {e}")
        import traceback
        logger.error(f"❌ Error details: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_langsmith_tracing())
    if success:
        logger.info("🎉 LangSmith tracing test PASSED!")
    else:
        logger.error("💥 LangSmith tracing test FAILED!")
        exit(1)

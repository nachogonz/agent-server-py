#!/usr/bin/env python3
"""
Simple test script to verify the LiveKit Python agent components work correctly.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src directory to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

async def test_agent_components():
    """Test that the agent components can be imported and instantiated."""
    print("🧪 Testing LiveKit Python Agent Components")
    print("=" * 50)
    
    try:
        # Test imports
        print("1. Testing imports...")
        from src.agent import VoiceAssistant, entrypoint, prewarm
        from src.functions import FunctionContext
        from src.health_server import start_health_server, stop_health_server
        print("   ✅ All imports successful")
        
        # Test agent creation
        print("2. Testing agent creation...")
        assistant = VoiceAssistant(mode="orders")
        print(f"   ✅ Agent created with mode: {assistant.mode}")
        
        # Test function context
        print("3. Testing function context...")
        function_definitions = assistant.function_context.create_function_context()
        print(f"   ✅ Function context created with {len(function_definitions)} functions")
        
        # Test function handler
        print("4. Testing function handler...")
        result = await assistant.function_context.handle_function_call(
            "checkClientId", 
            {"clientId": "test123"}
        )
        print(f"   ✅ Function call test: {result[:50]}...")
        
        # Test health server
        print("5. Testing health server...")
        health_runner = await start_health_server()
        print("   ✅ Health server started")
        
        await stop_health_server(health_runner)
        print("   ✅ Health server stopped")
        
        print("=" * 50)
        print("🎉 All tests passed! The agent is ready to use.")
        print()
        print("Next steps:")
        print("1. Set up your .env file with LiveKit and OpenAI credentials")
        print("2. Start the backend API server (for function calls)")
        print("3. Run: python main.py console (for testing)")
        print("4. Run: python main.py dev (for LiveKit integration)")
        
    except ImportError as e:
        print(f"   ❌ Import error: {e}")
        print("   💡 Try: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_agent_components())
    sys.exit(0 if success else 1)
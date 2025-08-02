#!/usr/bin/env python3
"""
Standalone console test for LiveKit Python Agent
This bypasses the LiveKit CLI and directly tests the agent functionality
Now with voice-first capabilities!
"""

import asyncio
import os
import logging
import speech_recognition as sr
import pyttsx3
import threading
from dotenv import load_dotenv
from src.agent import VoiceAssistant

# Load environment variables
load_dotenv()

# Set up logging - suppress httpx logs
logging.basicConfig(level=logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

class VoiceConsole:
    def __init__(self, assistant: VoiceAssistant):
        self.assistant = assistant
        self.recognizer = sr.Recognizer()
        self.engine = pyttsx3.init()
        self.voice_mode = True
        
        # Configure TTS
        voices = self.engine.getProperty('voices')
        if voices:
            self.engine.setProperty('voice', voices[0].id)  # Use first available voice
        self.engine.setProperty('rate', 180)  # Speed of speech
        
    def speak(self, text: str):
        """Convert text to speech."""
        print(f"🤖 Agent: {text}")
        self.engine.say(text)
        self.engine.runAndWait()
        
    def listen(self) -> str:
        """Listen for voice input and convert to text."""
        with sr.Microphone() as source:
            print("🎤 Listening... (speak now)")
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            
            try:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                print("🔄 Processing speech...")
                
                text = self.recognizer.recognize_google(audio)
                print(f"👤 You: {text}")
                return text
                
            except sr.WaitTimeoutError:
                print("⏰ No speech detected within timeout")
                return ""
            except sr.UnknownValueError:
                print("❓ Could not understand audio")
                return ""
            except sr.RequestError as e:
                print(f"❌ Error with speech recognition: {e}")
                return ""
                
    def toggle_mode(self):
        """Toggle between voice and text mode."""
        self.voice_mode = not self.voice_mode
        mode = "Voice" if self.voice_mode else "Text"
        print(f"🔄 Switched to {mode} mode")
        self.speak(f"Switched to {mode} mode")

async def main():
    """Main console test function."""
    print("\n" + "="*60)
    print("🤖 LiveKit Python Agent - Voice-First Console")
    print("="*60)
    
    # Check required environment variables
    required_env_vars = ["OPENAI_API_KEY"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set them in your .env file")
        return
    
    # Get agent mode
    agent_mode = os.getenv("MODE", "jarvis")
    print(f"Agent Mode: {agent_mode}")
    print("This console uses real OpenAI LLM integration with voice capabilities!")
    print("Voice mode is ON by default.")
    print("Commands:")
    print("  - Speak naturally to interact")
    print("  - Say 'switch mode' to toggle voice/text")
    print("  - Say 'quit' or 'exit' to end session")
    print("  - Press Ctrl+C to exit")
    print("="*60)
    
    # Create the voice assistant and console
    assistant = VoiceAssistant(mode=agent_mode)
    console = VoiceConsole(assistant)
    
    # Welcome message
    welcome_msg = f"Hello, I'm your {agent_mode} assistant. How can I help you today?"
    console.speak(welcome_msg)
    
    try:
        while True:
            if console.voice_mode:
                # Voice mode
                user_input = console.listen()
                
                if not user_input:
                    continue
                    
                # Check for commands
                if user_input.lower() in ['switch mode', 'toggle mode', 'text mode']:
                    console.toggle_mode()
                    continue
                    
                if user_input.lower() in ['quit', 'exit', 'goodbye']:
                    console.speak("Goodbye! Ending session.")
                    break
                    
                # Get agent response
                response = await assistant.on_chat_message(user_input)
                console.speak(response)
                
            else:
                # Text mode
                user_input = input("\n👤 You: ").strip()
                
                if not user_input:
                    continue
                    
                # Check for commands
                if user_input.lower() in ['switch mode', 'toggle mode', 'voice mode']:
                    console.toggle_mode()
                    continue
                    
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye! Ending session...")
                    break
                    
                # Get agent response
                print("🤖 Agent: ", end="", flush=True)
                response = await assistant.on_chat_message(user_input)
                print(response)
            
    except KeyboardInterrupt:
        print("\n👋 Session interrupted. Goodbye!")
    except Exception as error:
        print(f"\n❌ Error in console chat: {error}")
        logger.error(f"Console error: {error}")
    finally:
        print("✅ Console session ended.")

if __name__ == "__main__":
    asyncio.run(main()) 
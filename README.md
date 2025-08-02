# LiveKit Python Agent Server

This is a Python implementation of a LiveKit voice agent using the realtime API with OpenAI's Realtime Model.

## Features

- Real-time voice conversation using LiveKit Agents with OpenAI's Realtime Model
- Multiple agent modes: orders, appointments, leads, airline, jarvis
- End-to-end voice processing with GPT-4o
- Analytics tracking

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file with the following variables:

```env
# LiveKit Configuration
LIVEKIT_API_KEY=<your LiveKit API key>
LIVEKIT_API_SECRET=<your LiveKit API secret>
LIVEKIT_URL=<your LiveKit server URL>

# AI Provider Keys
OPENAI_API_KEY=<your OpenAI API key>

# Agent Configuration
MODE=orders  # Options: orders, appointments, leads, airline, jarvis

# Optional: Backend API for analytics
API_BASE_URL=http://localhost:3001
```

## Usage

### Development Mode

Start the agent in development mode to connect to LiveKit:

```bash
python main.py dev
```

### Production Mode

Start the agent in production mode:

```bash
python main.py start
```

### Console Mode

For testing, you can run the agent in console mode:

```bash
python main.py console
```

## Agent Modes

- **orders**: Order management and processing
- **appointments**: Appointment scheduling and management
- **leads**: Lead qualification and management
- **airline**: Airline booking and customer service
- **jarvis**: General assistant with multiple capabilities

## Architecture

The agent uses the LiveKit Agents realtime API with OpenAI's Realtime Model:

- **Realtime Model**: OpenAI GPT-4o with "coral" voice for end-to-end voice processing

## File Structure

```
agent-server-py/
├── main.py              # Main entry point with realtime API
├── requirements.txt     # Python dependencies
├── src/
│   ├── agent.py         # VoiceAssistant class
│   ├── functions.py     # Function definitions
│   └── prompts/         # System prompts for different modes
└── README.md           # This file
```

## Troubleshooting

1. **Missing API Keys**: Ensure all required API keys are set in your `.env` file
2. **LiveKit Connection**: Verify your LiveKit server URL and credentials
3. **Audio Issues**: Check microphone permissions and audio device settings

## Development

The agent is built using the LiveKit Agents Python SDK v1.2.2 with OpenAI's Realtime Model. The main entry point is `main.py` which uses the `AgentSession` class with the `openai.realtime.RealtimeModel` for end-to-end voice processing.
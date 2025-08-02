# LiveKit Python Agent Server

A Python implementation of the LiveKit voice agent server, ported from the Node.js version. This agent provides voice-based interactions for multiple business scenarios including orders, appointments, leads, airline services, and AI consultations.

## Features

- **Voice AI Agent**: Text-based LLM integration with OpenAI GPT-4o-mini
- **Multiple Agent Modes**: 
  - `orders`: Product ordering and order management
  - `appointments`: Dental clinic appointment scheduling
  - `leads`: Health insurance lead capture
  - `airline`: Flight booking and customer service
  - `jarvis`: AI consultation scheduling
- **Real-time Communication**: Powered by LiveKit's communication platform
- **Function Calling**: Integrated business functions for each agent mode
- **Analytics**: Conversation tracking and session metrics
- **Extensible**: Easy to add new agent modes and functions

## Requirements

- Python 3.9+
- LiveKit account and API credentials
- OpenAI API key
- Backend API server (for business functions)

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd back/agent-server-py
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your actual credentials
   ```

4. **Configure environment**:
   ```env
   LIVEKIT_API_KEY=your_livekit_api_key
   LIVEKIT_API_SECRET=your_livekit_api_secret
   LIVEKIT_URL=wss://your-project.livekit.cloud
   OPENAI_API_KEY=your_openai_api_key
   MODE=orders  # or appointments, leads, airline, jarvis
   API_BASE_URL=http://localhost:3001
   ```

## Usage

### Local Development

**Console Mode** (for testing):
```bash
python main.py console
```

**Development Mode** (connects to LiveKit):
```bash
python main.py dev
```

**Production Mode**:
```bash
python main.py start
```

### Docker

1. **Build the image**:
   ```bash
   docker build -t livekit-python-agent .
   ```

2. **Run the container**:
   ```bash
   docker run -d \
     --name python-agent \
     -e LIVEKIT_API_KEY=your_key \
     -e LIVEKIT_API_SECRET=your_secret \
     -e OPENAI_API_KEY=your_openai_key \
     -e MODE=orders \
     -e API_BASE_URL=http://host.docker.internal:3001 \
     -p 8080:8080 \
     livekit-python-agent
   ```

## Agent Modes

### Orders Agent (`MODE=orders`)
- Client verification and greeting
- Product search with vector similarity
- Order creation and management
- Delivery scheduling
- Natural conversational ordering flow

### Appointments Agent (`MODE=appointments`)
- Dental appointment scheduling
- Availability checking
- Patient type detection (new/returning)
- Appointment type categorization
- Reminder preferences

### Leads Agent (`MODE=leads`)
- Health insurance lead capture
- Structured sales script flow
- Objection handling
- Data collection and qualification
- Follow-up scheduling

### Airline Agent (`MODE=airline`)
- Flight booking modifications
- Passenger check-in services
- Lost baggage reporting
- Spanish language support
- Comprehensive flight management

### Jarvis Agent (`MODE=jarvis`)
- AI consultation scheduling
- Business discovery and qualification
- Calendar availability checking
- Meeting coordination
- Custom proposal preparation

## Architecture

### Key Components

- **`agent.py`**: Main agent logic and LiveKit integration
- **`functions.py`**: Business function implementations
- **`prompts/`**: Agent personality and instruction prompts
- **`main.py`**: Application entry point

### Function Context

Each agent mode has access to specific business functions:

- **Orders**: `checkClientId`, `searchProducts`, `createOrder`, `finishOrder`
- **Appointments**: `createAppointment`, `checkAppointmentAvailability`
- **Leads**: `captureLead`
- **Airline**: `changeBooking`, `checkInPassenger`, `reportLostBaggage`
- **Consultations**: `scheduleConsultation`, `checkCalendarAvailability`

### Metrics Collection

The agent automatically collects:
- Conversation transcripts
- Usage metrics (tokens, duration)
- Function call analytics
- Session performance data

## Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `LIVEKIT_API_KEY` | LiveKit API key | Yes | - |
| `LIVEKIT_API_SECRET` | LiveKit API secret | Yes | - |
| `OPENAI_API_KEY` | OpenAI API key | Yes | - |
| `MODE` | Agent mode | No | `orders` |
| `API_BASE_URL` | Backend API URL | No | `http://localhost:3001` |
| `PORT` | Health check port | No | `8080` |

### Agent Customization

To modify agent behavior:

1. **Update prompts**: Edit files in `src/prompts/`
2. **Add functions**: Extend `FunctionContext` in `src/functions.py`
3. **Modify conversation flow**: Update agent logic in `src/agent.py`

## API Integration

The agent integrates with backend services for:

- User and client management
- Product catalog and search
- Order processing
- Appointment scheduling
- Lead management
- Calendar operations

Ensure your backend API is running and accessible at the configured `API_BASE_URL`.

## Development

### Project Structure

```
agent-server-py/
├── src/
│   ├── __init__.py
│   ├── agent.py          # Main agent implementation
│   ├── functions.py      # Business function implementations
│   └── prompts/          # Agent instruction prompts
│       ├── __init__.py
│       ├── orders.py
│       ├── appointments.py
│       ├── leads.py
│       ├── airline.py
│       └── jarvis.py
├── main.py               # Application entry point
├── requirements.txt      # Python dependencies
├── Dockerfile           # Container configuration
├── .env.example         # Environment template
└── README.md           # This file
```

### Adding New Agent Modes

1. Create a new prompt file in `src/prompts/`
2. Add mode-specific functions to `src/functions.py`
3. Update the prompt mapping in `src/agent.py`
4. Test the new mode with `MODE=your_new_mode`

## Troubleshooting

### Common Issues

1. **Missing environment variables**: Ensure all required variables are set
2. **Import errors**: Run `pip install -r requirements.txt` to install dependencies
3. **API connection errors**: Verify backend API is running and accessible
4. **LiveKit connection issues**: Check API credentials and network connectivity
5. **Function call errors**: Verify backend API endpoints and data formats

### Testing the Agent

1. **Console Mode**: Test the agent locally without LiveKit connection:
   ```bash
   python main.py console
   ```

2. **Development Mode**: Connect to LiveKit for full testing:
   ```bash
   python main.py dev
   ```

### Debugging

Enable debug logging by setting the log level in `src/agent.py`:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Health Checks

The agent includes a built-in health check server at `http://localhost:8080/health`.

## License

This project is part of the Nova Node AI platform.
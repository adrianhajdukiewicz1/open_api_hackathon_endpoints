# Travel Planning API

This API allows you to interact with an AI-powered travel planning system through HTTP endpoints rather than a console interface.

## Features

- Conversation-based travel planning
- Instagram profile analysis for inspiration
- Session-based conversation management
- Structured travel plan output

## Getting Started

### Prerequisites

- Python 3.8+
- FastAPI
- Uvicorn
- OpenAI Python SDK

### Running the API Server

Execute the following command from the project root:

```bash
cd src
python run_api.py
```

This will start the FastAPI server on port 8000.

## API Endpoints

### POST /conversation

Start or continue a conversation with the travel planning system.

**Request Body**:

```json
{
  "message": "I want to plan a trip to Italy",
  "session_id": "optional-existing-session-id"
}
```

**Response**:

```json
{
  "session_id": "generated-session-id",
  "messages": [
    {
      "agent_name": "TriageAgent",
      "content": "Hi! I'd be happy to help you plan a trip to Italy..."
    }
  ],
  "tool_calls": [],
  "handoffs": [],
  "travel_plan": null
}
```

### DELETE /conversation/{session_id}

Delete a conversation session by ID.

**Response**:

```json
{
  "status": "success",
  "message": "Session abc123 deleted"
}
```

## Example Usage

1. Start a new conversation:

```bash
curl -X POST http://localhost:8000/conversation \
  -H "Content-Type: application/json" \
  -d '{"message": "I want to plan a trip to Italy"}'
```

2. Continue the conversation using the returned session ID:

```bash
curl -X POST http://localhost:8000/conversation \
  -H "Content-Type: application/json" \
  -d '{"message": "I want to explore Rome and Florence", "session_id": "your-session-id"}'
```

3. Provide an Instagram profile for inspiration:

```bash
curl -X POST http://localhost:8000/conversation \
  -H "Content-Type: application/json" \
  -d '{"message": "Check out @italytourism", "session_id": "your-session-id"}'
```

4. When finished, you can delete the session:

```bash
curl -X DELETE http://localhost:8000/conversation/your-session-id
```

## Response Structure

The API returns:

- `session_id`: Your conversation identifier
- `messages`: Text responses from the AI agents
- `tool_calls`: Information about tools that were called (e.g., Instagram analysis)
- `handoffs`: Information about which agent is handling your request
- `travel_plan`: The final structured travel plan (when available)

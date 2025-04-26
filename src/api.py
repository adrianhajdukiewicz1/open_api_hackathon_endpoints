import uuid
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from agents import (
    Runner,
    TResponseInputItem,
    FunctionToolResult,
    ItemHelpers,
    MessageOutputItem,
    HandoffOutputItem,
    ToolCallItem,
    ToolCallOutputItem,
)
from agents_fastapi import TriageAgent, PlanningAgent, TravelPlan, URLAnalysisResult

# Create FastAPI app
app = FastAPI(
    title="Travel Planning API",
    description="API for generating travel plans using AI agents and Instagram profile analysis",
    version="1.0.0",
)

# Storage for conversation histories
# Using a simple in-memory dictionary - in production, use a proper database
conversations: Dict[str, dict] = {}

# --- API Models ---


class ConversationRequest(BaseModel):
    message: str = Field(description="User message to the travel planning agent")
    session_id: Optional[str] = Field(
        default=None,
        description="Session ID for continuing an existing conversation. If not provided, a new conversation will be created.",
    )


class AgentMessage(BaseModel):
    agent_name: str = Field(description="Name of the agent that produced this message")
    content: str = Field(description="Text content of the message")


class ToolCallInfo(BaseModel):
    tool_name: str = Field(description="Name of the tool that was called")
    status: str = Field(
        description="Status of the tool call (started, completed, error)"
    )
    details: Optional[str] = Field(
        default=None, description="Additional details about the tool call"
    )


class HandoffInfo(BaseModel):
    from_agent: str = Field(description="Name of the agent handing off")
    to_agent: str = Field(description="Name of the agent receiving the handoff")


class ConversationResponse(BaseModel):
    session_id: str = Field(description="Unique identifier for this conversation")
    messages: List[AgentMessage] = Field(description="List of agent messages")
    tool_calls: List[ToolCallInfo] = Field(
        description="Information about tools that were called"
    )
    handoffs: List[HandoffInfo] = Field(description="Information about agent handoffs")
    travel_plan: Optional[TravelPlan] = Field(
        default=None, description="The generated travel plan, if available"
    )


# --- API Routes ---


@app.post("/conversation", response_model=ConversationResponse)
async def conversation(request: ConversationRequest):
    """
    Send a message to the travel planning system and get responses from the AI agents.
    """
    # Get or create a session
    session_id = request.session_id or uuid.uuid4().hex[:16]

    # Get or initialize conversation data
    if session_id not in conversations:
        conversations[session_id] = {
            "current_agent": TriageAgent,
            "input_items": [],
            "context": {},
        }

    conversation_data = conversations[session_id]
    current_agent = conversation_data["current_agent"]
    input_items: list[TResponseInputItem] = conversation_data["input_items"]
    context = conversation_data["context"]

    # Add user message to input items
    input_items.append({"content": request.message, "role": "user"})

    # Prepare response objects
    agent_messages = []
    tool_calls = []
    handoffs = []
    travel_plan = None

    try:
        # Run the agent
        result = await Runner.run(current_agent, input_items, context=context)

        # Process the results
        for new_item in result.new_items:
            agent_name = getattr(new_item, "agent", None)
            if agent_name:
                agent_name = agent_name.name
            else:
                agent_name = "System"

            # Handle different types of output items
            if isinstance(new_item, MessageOutputItem):
                text_output = ItemHelpers.text_message_output(new_item)
                agent_messages.append(
                    AgentMessage(agent_name=agent_name, content=text_output)
                )

                # Check for final plan
                if (
                    hasattr(new_item, "agent")
                    and new_item.agent == PlanningAgent
                    and isinstance(result.final_output, TravelPlan)
                ):
                    travel_plan = result.final_output

            elif isinstance(new_item, HandoffOutputItem):
                handoffs.append(
                    HandoffInfo(
                        from_agent=new_item.source_agent.name,
                        to_agent=new_item.target_agent.name,
                    )
                )

            elif isinstance(new_item, ToolCallItem):
                tool_calls.append(
                    ToolCallInfo(
                        tool_name=str(new_item), status="started", details=None
                    )
                )

            elif isinstance(new_item, ToolCallOutputItem):
                tool_status = "completed"
                tool_details = None

                # Handle specific tool outputs
                if (
                    hasattr(new_item, "output")
                    and isinstance(new_item.output, FunctionToolResult)
                    and isinstance(new_item.output.output, URLAnalysisResult)
                ):
                    analysis = new_item.output.output
                    if analysis.error:
                        tool_status = "error"
                        tool_details = f"Error: {analysis.error}"
                    else:
                        tool_details = f"Analyzed Instagram profile: {analysis.url}"

                tool_call_id = getattr(new_item, "tool_call_id", "unknown-tool")
                tool_calls.append(
                    ToolCallInfo(
                        tool_name=tool_call_id, status=tool_status, details=tool_details
                    )
                )

        # Update conversation state for next request
        input_items = result.to_input_list()
        current_agent = result.last_agent

        # Save updated state
        conversations[session_id] = {
            "current_agent": current_agent,
            "input_items": input_items,
            "context": context,
        }

        # Return the response
        return ConversationResponse(
            session_id=session_id,
            messages=agent_messages,
            tool_calls=tool_calls,
            handoffs=handoffs,
            travel_plan=travel_plan,
        )

    except Exception as e:
        # Log the error (in a real application, use proper logging)
        print(f"Error during {current_agent.name} execution: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error processing request: {str(e)}"
        )


@app.delete("/conversation/{session_id}")
async def delete_conversation(session_id: str):
    """
    Delete a conversation session by ID
    """
    if session_id in conversations:
        del conversations[session_id]
        return {"status": "success", "message": f"Session {session_id} deleted"}
    else:
        raise HTTPException(
            status_code=404, detail=f"Session ID {session_id} not found"
        )


@app.get("/")
async def root():
    """
    Root endpoint returning basic API information
    """
    return {
        "api": "Travel Planning API",
        "version": "1.0.0",
        "endpoints": {
            "/conversation": "POST - Send a message to the travel planning system",
            "/conversation/{session_id}": "DELETE - Delete a conversation session",
        },
    }

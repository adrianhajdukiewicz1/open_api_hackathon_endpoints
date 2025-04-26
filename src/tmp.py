# tmp.py
import asyncio
import uuid
from typing import List, Optional

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from agents import (
    Agent,
    FunctionToolResult,
    HandoffOutputItem,
    ItemHelpers,
    MessageOutputItem,
    ModelSettings,
    Runner,
    TResponseInputItem,
    ToolCallItem,
    ToolCallOutputItem,
    function_tool,
    handoff,
    trace,
)
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from instagram_image_extractor import describe_instagram_images

# --- Pydantic Models for Structured Data ---


class ImageDescription(BaseModel):
    image_url: str = Field(description="The URL of the image analyzed.")
    description: str = Field(description="A detailed description of the image content.")


class URLAnalysisResult(BaseModel):
    url: str = Field(description="The URL that was analyzed.")
    image_descriptions: str = Field(
        description="Descriptions of key images found on the page."
    )
    error: Optional[str] = Field(
        default=None, description="Any error encountered during analysis."
    )


class TravelPlan(BaseModel):
    destination: str = Field(description="The primary destination of the trip.")
    dates: Optional[str] = Field(
        default=None, description="Proposed or requested dates for the trip."
    )
    summary: str = Field(description="A brief summary of the proposed trip plan.")
    daily_itinerary: List[str] = Field(
        description="A list of activities or places to visit for each day or key period."
    )
    notes: Optional[str] = Field(
        default=None,
        description="Additional notes, suggestions, or considerations based on the analysis.",
    )


# --- Tool Definition for Instagram Analysis ---

# Configure OpenAI client (used within the tool for image description)
openai_client = AsyncOpenAI()


@function_tool
async def describe_instagram_profile(username_or_url: str) -> URLAnalysisResult:
    """
    Fetches Instagram images for a given username or profile URL and uses a vision model to describe them.

    Args:
        username_or_url: Instagram username or profile URL to fetch images from
    """
    print(f"[Tool] Analyzing Instagram profile: {username_or_url}")

    # Use the Instagram image extractor
    result = await describe_instagram_images(
        username_or_url,
    )

    # Convert the InstagramAnalysisResult to URLAnalysisResult for compatibility
    return URLAnalysisResult(
        url=username_or_url,
        image_descriptions=result.image_descriptions,
        error=result.error,
    )


# --- Agent Definitions ---

# Forward declaration for handoffs
PlanningAgent: Agent
InstagramImagesExtractor: Agent

TriageAgent = Agent(
    name="TriageAgent",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are the first point of contact for planning a user's trip.
    Your goals are:
    1. Greet the user warmly.
    2. Ask for their desired travel destination.
    3. Ask user a Instagram profile they'd like you to analyze for destination inspiration (e.g., a travel influencer, tourism board, or hotel profile).
    4. Once you have the Instagram username or URL from the user, use the `describe_instagram_profile` tool to fetch and get descriptions for key images from that profile.
    5. **After the tool successfully returns the analysis results (image descriptions)**,then hand off the conversation to the **PlanningAgent**. Mention that you are ready to pass the analyzed image details along for planning.
    6. If the tool returns an error, inform the user about the problem and ask if they have a different Instagram profile or if they want to proceed without Instagram analysis (then hand off to PlanningAgent).    """,
    tools=[describe_instagram_profile],
    # Handoff defined after InstagramImagesExtractor is defined
)

InstagramImagesExtractor = Agent(
    name="InstagramImagesExtractor",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You receive the conversation after the TriageAgent has gathered initial details.
    Your specific tasks are:
    1. Once you have the Instagram username or URL from the user, use the `describe_instagram_profile` tool to fetch and get descriptions for key images from that profile.
    2. If the user provided an Instagram profile to the TriageAgent, confirm it. If not, **ask the user to provide a specific Instagram username or URL** related to their desired destination. Explain that analyzing Instagram photos from this location will help create a much better plan.
    3. **After the tool successfully returns the analysis results (image descriptions)**, review the results briefly and then **immediately** hand off the conversation to the **PlanningAgent**. Mention that you are passing the analyzed image details along for planning.
    4. If the tool returns an error, inform the user about the problem and ask if they have a different Instagram profile or if they want to proceed without Instagram analysis (then hand off to PlanningAgent).
    """,
    tools=[describe_instagram_profile],
    # Handoff defined after PlanningAgent is defined
    model_settings=ModelSettings(temperature=0.1),  # Be precise in asking/using tool
)

PlanningAgent = Agent(
    name="PlanningAgent",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are the final step in the travel planning process. You receive the conversation history which includes:
    - The user's initial preferences (destination, dates, interests) from the TriageAgent.
    - The analysis results (image descriptions) from an Instagram profile provided by the user, processed by the InstagramImagesExtractor via the `describe_instagram_profile` tool (check the tool output messages).
    Your task is to synthesize ALL this information into a cohesive travel plan.
    Specifically:
    1. Review the user's initial request and preferences.
    2. Carefully review the image descriptions from the `describe_instagram_profile` tool output. These provide valuable visual inspiration for the plan.
    3. Create a structured travel plan based on *both* the user's preferences *and* the insights from the Instagram image analysis.
    4. The plan should include a destination, proposed dates (if specific enough), a summary, a suggested daily itinerary (or key activities list), and any relevant notes derived from the Instagram content (e.g., mentioning specific sights from images, incorporating themes you observed).
    5. Output the final plan using the structured `TravelPlan` format. Make the itinerary detailed and engaging.
    """,
    output_type=TravelPlan,
    model_settings=ModelSettings(temperature=0.7),  # Allow for creativity in planning
)

# Define handoffs now that all agents are declared
# TriageAgent.handoffs.append(handoff(agent=InstagramImagesExtractor))
TriageAgent.handoffs.append(handoff(agent=PlanningAgent))

# InstagramImagesExtractor.handoffs.append(handoff(agent=PlanningAgent))

# --- Main Execution Logic ---


async def main():
    current_agent: Agent = TriageAgent
    input_items: list[TResponseInputItem] = []
    context = {}  # Add context if needed later

    conversation_id = uuid.uuid4().hex[:16]
    print("Starting travel planning conversation...")
    print(f"Conversation ID: {conversation_id}")
    print("-" * 30)

    while True:
        user_input = input("You: ")
        if user_input.lower() in ["quit", "exit"]:
            print("Ending conversation.")
            break

        with trace(
            f"Travel Planning Turn ({current_agent.name})", group_id=conversation_id
        ):
            input_items.append({"content": user_input, "role": "user"})

            print(f"\n--- Running {current_agent.name} ---")
            try:
                result = await Runner.run(current_agent, input_items, context=context)

                for new_item in result.new_items:
                    agent_name = new_item.agent.name
                    if isinstance(new_item, MessageOutputItem):
                        text_output = ItemHelpers.text_message_output(new_item)
                        print(f"{agent_name}: {text_output}")
                        # Check if this is the final plan output
                        if new_item.agent == PlanningAgent and isinstance(
                            result.final_output, TravelPlan
                        ):
                            print("\n--- Generated Travel Plan ---")
                            # Output is already structured, just print confirmation
                            print(result.final_output.model_dump_json(indent=2))
                            print(
                                "\nPlan generated. You can ask for refinements or type 'quit' to exit."
                            )
                            # Optionally break or change loop condition here
                    elif isinstance(new_item, HandoffOutputItem):
                        print(
                            f"\n[System] Handed off from {new_item.source_agent.name} to {new_item.target_agent.name}\n"
                        )
                    elif isinstance(new_item, ToolCallItem):
                        print(f"{agent_name}: Calling tool '{new_item}'...")
                    elif isinstance(new_item, ToolCallOutputItem):
                        # Don't print the full tool output by default, it can be large
                        # Check if it's our specific tool and maybe print a summary
                        if isinstance(
                            new_item.output, FunctionToolResult
                        ) and isinstance(new_item.output.output, URLAnalysisResult):
                            analysis: URLAnalysisResult = new_item.output.output
                            status = (
                                "successfully"
                                if not analysis.error
                                else f"with error: {analysis.error}"
                            )
                            print(
                                f"{agent_name}: Tool 'describe_instagram_profile' finished {status}."
                            )
                            print(
                                f"  - Extracted ~{len(analysis.extracted_text)} chars of text."
                            )
                            print(
                                f"  - Described {len(analysis.image_descriptions)} images."
                            )
                        else:
                            # Generic tool output confirmation
                            print(f"{agent_name}: Tool call finished.")
                    else:
                        # Catch other item types if necessary
                        pass

                input_items = result.to_input_list()
                current_agent = result.last_agent  # Update agent after handoff

            except Exception as e:
                print(f"\n--- An Error Occurred ---")
                print(f"Error during {current_agent.name} execution: {e}")
                # Optionally reset or break
                break


if __name__ == "__main__":
    asyncio.run(main())

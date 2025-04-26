# filepath: /Users/yuriybabyak/repo/hackaton/open_api_hackathon_endpoints/src/agents_fastapi.py
"""
This module contains agent definitions for the travel planning system.
"""

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
    # For compatibility with the original code
    extracted_text: Optional[str] = Field(
        default="", description="Extracted text from the page"
    )


class TravelPlan(BaseModel):
    destination: str = Field(description="The primary destination of the trip.")
    geo_location: List[str] = Field(description="Destination attitudes and longitude")
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
        extracted_text="",  # Add this field for compatibility
        error=result.error,
    )


class MockLocationResult(BaseModel):
    """Result containing mock locations mapped from a profile."""

    profile_source: str = Field(description="The Instagram profile used as the source.")
    mapped_locations: List[str] = Field(
        description="A list of mock travel destinations inspired by the profile."
    )


@function_tool
async def get_locations_attitude_for_destinations(
    username_or_url: str,
) -> MockLocationResult:
    """
    Gets a list of *mock* travel locations potentially inspired by an Instagram profile.
    It simulates analyzing the profile for places visited and returns a predefined list
    of interesting destinations. Use this when the user asks for location ideas or
    places visited based on a profile, rather than image descriptions.

    Args:
        username_or_url: The Instagram username or profile URL to simulate analyzing.
    """
    print(f"[Tool] Getting mock locations inspired by: {username_or_url}")


# --- Agent Definitions ---

# Forward declaration for handoffs
PlanningAgent: Agent

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
TriageAgent.handoffs.append(handoff(agent=PlanningAgent))

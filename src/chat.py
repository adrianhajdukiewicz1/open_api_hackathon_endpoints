import asyncio
import re
import json
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin
from contextlib import asynccontextmanager
from collections import defaultdict
import uuid  # To generate session IDs if needed
from bs4 import BeautifulSoup

import aiohttp
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Body

# --- Agents SDK Imports ---
from agents import (
    Agent,
    Runner,
    TResponseInputItem,
    trace,
    function_tool,
    ToolCallOutputItem,
    ItemHelpers,
)


# --- Pydantic Models for API ---


class ChatMessage(BaseModel):
    session_id: str = Field(
        description="Unique identifier for the conversation session."
    )
    message: str = Field(description="The user's message.")


class ChatResponse(BaseModel):
    session_id: str
    response: str
    status: str = "ok"  # Could add 'analyzing', 'synthesizing' for more detail


class ClearRequest(BaseModel):
    session_id: str


class ClearResponse(BaseModel):
    session_id: str
    status: str


# --- Agent and Tool Definitions (Copied from previous example) ---


# ImageAnalysis Model
class ImageAnalysis(BaseModel):
    description: str = Field(
        description="A detailed description of the location, which may include historical, cultural, or geographical context. Location like on the hills, on the beach, etc. Probable city, country, etc."
    )
    overview: str = Field(
        description="A brief overview of the specific location depicted in the image."
    )
    location: Optional[str] = Field(
        default=None,
        description="The specific location depicted in the image (e.g., city, landmark, country), if identifiable.",
    )
    error: Optional[str] = Field(
        default=None, description="Any error encountered during analysis."
    )
    is_image: bool = Field(
        default=False,  # Default to False
        description="Whether the URL successfully resolved to an image and was analyzed.",
    )


# UserProfile Model
class UserProfile(BaseModel):
    summary: str = Field(
        description="A summary of the user's likely interests, hobbies, and travel patterns based on the analyzed image URLs."
    )
    analysis_details: List[ImageAnalysis] = Field(
        description="List of analysis results for each URL."
    )


# image_analyzer_agent
image_analyzer_agent = Agent(
    name="Image_Analyzer",
    instructions=(
        "You are an expert image analyst. Analyze the provided image URL. "
        "Describe the main subject and scene concisely. Include context like landscape type (beach, mountain, city), potential activities, and overall vibe. "
        "If a specific location is identifiable (city, landmark, country), state it clearly. "
        "If the URL is not an image or an error occurs, indicate that by setting is_image to false and providing an error message. "
        "Respond ONLY with the JSON object matching the ImageAnalysis schema."
    ),
    model="gpt-4o",
    tools=[get_image_urls_from_source],
    output_type=ImageAnalysis,
)

# profile_synthesizer_agent
profile_synthesizer_agent = Agent(
    name="Profile Synthesizer",
    instructions=(
        "You are an expert profiler specializing in travel preferences. You will be given a list of analysis results from various image URLs. "
        "Each result contains a description, an overview, and potentially a location. "
        "Based *only* on the provided descriptions, overviews, and locations from the successful image analyses (where is_image is true), "
        "infer the person's likely travel interests (e.g., adventure, relaxation, culture, nature, urban exploration), preferred environments (e.g., beaches, mountains, cities), and potential hobbies reflected (e.g., photography, hiking, surfing). "
        "Create a concise summary profile highlighting these inferred preferences. Ignore URLs that were not images or resulted in errors. "
        "Respond ONLY with the JSON object matching the UserProfile schema, including all original analysis details provided in the input."
    ),
    model="gpt-4o-mini",
    output_type=UserProfile,
)


# is_valid_url helper
def is_valid_url(url: str) -> bool:
    regex = re.compile(
        r"^(?:http|ftp)s?://"
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"
        r"localhost|"
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
        r"(?::\d+)?"
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )
    return re.match(regex, url) is not None


# analyze_single_url helper (Requires global http_session)
async def analyze_single_url(session: aiohttp.ClientSession, url: str) -> ImageAnalysis:
    if not is_valid_url(url):
        return ImageAnalysis(
            description="",
            overview="",
            error=f"Invalid URL format: {url}",
            is_image=False,
        )

    # Construct input using TResponseInputItem format expected by Runner.run
    input_message: List[TResponseInputItem] = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": url, "detail": "auto"},
                },  # Correct structure
                {
                    "type": "text",
                    "text": "Analyze this image based on your instructions.",
                },
            ],
        }
    ]
    analysis_result: Optional[ImageAnalysis] = None

    try:
        # Optional HEAD request - might be better handled by the model's error reporting
        # ... (HEAD request code omitted for brevity, rely on agent failure) ...

        print(f"Analyzing image URL: {url}")
        # Make sure to pass an empty context dict or None if analyze_single_url doesn't need specific context
        result = await Runner.run(image_analyzer_agent, input_message, context=None)
        # The Runner.run() result doesn't seem to have an error attribute
        # Instead, check if final_output is empty or if new_items is empty
        if not result.final_output:
            print(f"Error during agent run for {url}: No output produced")
            return ImageAnalysis(
                description="",
                overview="",
                error="Agent run failed: No output produced",
                is_image=False,
            )

        analysis_result = result.final_output_as(ImageAnalysis)

        if not analysis_result:
            return ImageAnalysis(
                description="",
                overview="",
                error="Analysis returned unexpected empty result",
                is_image=False,
            )

        # Model should set is_image and error based on instructions.
        # If the model produced output but didn't explicitly set error, assume it's an image *unless* it set is_image=False.
        if analysis_result.error is None and analysis_result.is_image is None:
            analysis_result.is_image = True
        elif analysis_result.error:
            analysis_result.is_image = False  # Ensure consistency

        return analysis_result

    except aiohttp.ClientError as e:
        print(f"Network error accessing URL {url}: {e}")
        return ImageAnalysis(
            description="", overview="", error=f"Network error: {e}", is_image=False
        )
    except asyncio.TimeoutError:
        print(f"Timeout accessing URL {url}")
        return ImageAnalysis(
            description="", overview="", error="Timeout accessing URL", is_image=False
        )
    except Exception as e:
        # Catch potential validation errors or other issues during Runner.run or output processing
        print(f"General error analyzing URL {url}: {e}")
        # Check if it's a validation error from Pydantic
        if "validation error" in str(e).lower():
            error_detail = f"Model output validation failed: {e}"
        else:
            error_detail = f"Analysis failed: {e}"
        return ImageAnalysis(
            description="", overview="", error=error_detail, is_image=False
        )


# get_image_urls_from_source tool
@function_tool
async def get_image_urls_from_source(source_url: str) -> List[str]:
    """
    Fetches a webpage URL and extracts all valid image URLs found within <img> tags,
    or returns the URL directly if it points to an image file.

    Args:
        source_url: The URL of the webpage to scrape for images or a direct image URL. Must be a valid HTTP/HTTPS URL.

    Returns:
        A list of absolute image URLs found on the page or the direct image URL if provided. Returns an empty list on error.
    """
    print(f"Attempting to process URL: {source_url}")
    # Strict URL validation
    if not is_valid_url(source_url):
        print(f"Invalid source URL provided: {source_url}")
        return []

    # Ensure source_url starts with http:// or https://
    if not source_url.startswith(("http://", "https://")):
        print(f"URL must start with http:// or https://: {source_url}")
        return []

    # Check if the URL is a direct image URL
    if any(
        source_url.lower().endswith(ext)
        for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"]
    ):
        print(f"Direct image URL detected: {source_url}")
        return [source_url]

    image_urls: List[str] = []
    try:
        # Create a new session for this specific request
        async with aiohttp.ClientSession() as session:
            async with session.get(source_url, timeout=10) as response:
                response.raise_for_status()
                content_type = response.headers.get("Content-Type", "").lower()

                # Check if the response is an image
                if content_type.startswith("image/"):
                    print(
                        f"URL {source_url} is an image with content type: {content_type}"
                    )
                    return [source_url]

                # Check if the response is HTML
                elif "text/html" in content_type:
                    html_content = await response.text()
                    soup = BeautifulSoup(html_content, "html.parser")

                    img_tags = soup.find_all("img")
                    for img in img_tags:
                        src = img.get("src")
                        if src:
                            absolute_src = urljoin(source_url, src)
                            if is_valid_url(absolute_src) and any(
                                absolute_src.lower().endswith(ext)
                                for ext in [
                                    ".jpg",
                                    ".jpeg",
                                    ".png",
                                    ".webp",
                                    ".gif",
                                    ".avif",
                                ]
                            ):
                                if absolute_src not in image_urls:
                                    image_urls.append(absolute_src)
                else:
                    print(
                        f"URL {source_url} has unsupported content type: {content_type}"
                    )
                    return []

                print(f"Found {len(image_urls)} potential image URLs.")
                return image_urls

    except aiohttp.ClientError as e:
        print(f"Error fetching source URL {source_url}: {e}")
        return []
    except Exception as e:
        print(f"Error parsing HTML or extracting images from {source_url}: {e}")
        return []


# travel_profiler_agent
travel_profiler_agent = Agent(
    name="Travel Profiler Assistant",
    instructions=(
        "You are a friendly travel planning assistant. Your goal is to understand the user's visual preferences for travel. "
        "1. Start by asking the user what kind of travel experiences they enjoy (e.g., relaxing beaches, adventurous mountains, cultural cities). "
        "2. Then, ask the user to provide a URL. This can be either: "
        "   - A direct link to an image (e.g., https://example.com/image.jpg) "
        "   - A webpage URL (like a blog post, social media profile - e.g., public Instagram, Pinterest board) that contains images. "
        "   Make it clear you need a single, specific URL. "
        "3. Once the user provides a URL, confirm you will analyze it and use the 'Image_Analyzer' agent to extract images and their details. "
        "4. The system will then analyze the images and generate a profile. You will be informed of the profile summary. "
        "5. Present the profile summary you are given back to the user conversationally. Ask follow-up questions based on the profile to continue the conversation."
    ),
    handoffs=[image_analyzer_agent],
    model="gpt-4o-mini",
)

# --- Global State (In-Memory) ---
# Store conversation history per session_id
# Use defaultdict for easier initialization
# Add locks for basic concurrency control per session
conversation_histories: Dict[str, List[TResponseInputItem]] = defaultdict(list)
session_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
http_session: Optional[aiohttp.ClientSession] = None


# --- FastAPI Lifespan Management for aiohttp session ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global http_session
    # Startup: Create the session
    http_session = aiohttp.ClientSession()
    print("AIOHTTP ClientSession started.")
    yield
    # Shutdown: Close the session
    if http_session:
        await http_session.close()
        print("AIOHTTP ClientSession closed.")


# --- FastAPI App Initialization ---
app = FastAPI(lifespan=lifespan, title="Travel Profiler Agent API")

# --- API Endpoints ---


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatMessage = Body(...)):
    """Handles incoming user messages and orchestrates the agent workflow."""
    global http_session  # Ensure we use the global session

    session_id = payload.session_id
    user_message = payload.message

    if not http_session:
        raise HTTPException(status_code=500, detail="HTTP session not initialized")

    # Acquire lock for this session to prevent race conditions
    async with session_locks[session_id]:
        # Retrieve or initialize history
        current_history = conversation_histories[session_id]

        # Add user message to history
        current_history.append({"role": "user", "content": user_message})

        extracted_urls: Optional[List[str]] = None
        agent_response_text = ""
        final_status = "ok"

        try:
            print(f"Running agent for session {session_id}...")
            with trace(f"Chat Turn - Session: {session_id}"):
                tool_context = {"http_session": http_session}
                result = await Runner.run(
                    travel_profiler_agent, current_history, context=tool_context
                )  # current_history includes the latest user message here

                # Initialize the final history based on the agent's run result
                # This includes the user message and the agent's direct output/tool calls
                final_updated_history = result.to_input_list()

                # Process new items from the agent run specifically to find tool output
                # Note: result.to_input_list() already incorporates these items correctly formatted
                # We only need to iterate here to *detect* if the tool was called and get its output.
                agent_response_text = ""  # Reset agent response text
                extracted_urls = None
                print(final_updated_history)
                for item in result.new_items:
                    if item.type == "message_output_item":
                        text = ItemHelpers.text_message_output(item)
                        if text:
                            agent_response_text += text.strip() + "\n"
                    elif (
                        item.type == "tool_call_item"
                        and item.raw_item.name == "get_image_urls_from_source"
                    ):
                        if isinstance(item.output, list):
                            extracted_urls = item.output
                        else:
                            print(
                                f"Warning: Tool {item.raw_item.tool_name} output was not a list: {type(item.output)}"
                            )

                # --- Orchestration: Analyze and Synthesize if URLs were extracted ---
                if extracted_urls is not None:
                    print(
                        f"Session {session_id}: Tool extracted {len(extracted_urls)} URLs."
                    )
                    final_status = "analyzing"
                    # The agent's initial conversational text is captured above

                    # --- Analysis ---
                    all_analysis_results: List[ImageAnalysis] = []
                    if extracted_urls:
                        analysis_tasks = [
                            analyze_single_url(http_session, url)
                            for url in extracted_urls
                        ]
                        results_analysis = await asyncio.gather(*analysis_tasks)
                        all_analysis_results.extend(
                            [
                                res
                                for res in results_analysis
                                if isinstance(res, ImageAnalysis)
                            ]
                        )
                        successful_analyses = [
                            res
                            for res in all_analysis_results
                            if res.is_image and not res.error
                        ]
                        print(
                            f"Session {session_id}: Successfully analyzed {len(successful_analyses)} images."
                        )

                        # --- Synthesis ---
                        if successful_analyses:
                            final_status = "synthesizing"
                            synthesizer_input_data = [
                                analysis.model_dump()
                                for analysis in successful_analyses
                            ]
                            synthesizer_input_message: TResponseInputItem = {
                                "role": "user",
                                "content": (
                                    "Here are the analysis results for the user's images:\n"
                                    f"{json.dumps(synthesizer_input_data, indent=2)}\n\n"
                                    "Please generate the user profile based ONLY on these results."
                                ),
                            }
                            print(f"Session {session_id}: Running synthesizer...")
                            synthesizer_result = await Runner.run(
                                profile_synthesizer_agent, [synthesizer_input_message]
                            )

                            if synthesizer_result.final_output:
                                user_profile = synthesizer_result.final_output_as(
                                    UserProfile
                                )
                                summary_for_user = (
                                    f"Okay, I've analyzed the images from the URL you provided! "
                                    f"Based on what I saw, here's a little summary of your visual travel preferences:\n\n{user_profile.summary}\n\n"
                                    "What do you think? Does that sound like you? We can explore destinations based on this!"
                                )
                                agent_response_text = summary_for_user  # This is the final response for this turn
                                final_status = "profile_generated"

                                # ** CORRECTED HISTORY APPEND **
                                # Add the synthesizer's result (tool role) and the summary (assistant role)
                                # to the history list we got from result.to_input_list()
                                synthesizer_tool_message: TResponseInputItem = {
                                    "role": "tool",
                                    "tool_call_id": "profile_synthesizer_result",  # Placeholder ID
                                    "content": user_profile.model_dump_json(),
                                }
                                final_updated_history.append(
                                    synthesizer_tool_message
                                )  # Append to the list from to_input_list()

                                final_updated_history.append(
                                    {"role": "assistant", "content": summary_for_user}
                                )  # Append the final summary message

                            else:  # Synthesizer failed
                                error_message = "I analyzed the images, but had trouble creating a profile summary."
                                agent_response_text = error_message
                                final_status = "synthesis_failed"
                                final_updated_history.append(
                                    {"role": "assistant", "content": error_message}
                                )  # Append error message
                        else:  # No successful analyses
                            no_images_message = "I tried fetching images from that URL, but couldn't successfully analyze any. Could you provide a different URL, perhaps one from a public Instagram profile, Pinterest board, or a travel blog post with clear images?"
                            agent_response_text = no_images_message
                            final_status = "analysis_failed"
                            final_updated_history.append(
                                {"role": "assistant", "content": no_images_message}
                            )  # Append clarification message
                    else:  # Tool returned no URLs
                        no_urls_found_msg = "I checked the page, but couldn't find any image URLs to analyze. Please provide a different URL with visible images."
                        agent_response_text = no_urls_found_msg
                        final_status = "no_urls_found"
                        final_updated_history.append(
                            {"role": "assistant", "content": no_urls_found_msg}
                        )  # Append clarification message

                # Handle direct agent run error
                elif hasattr(result, "error") and result.error:
                    print(f"Session {session_id}: Agent run failed: {result.error}")
                    agent_response_text = "Sorry, I encountered an internal error. Could you please rephrase?"
                    final_status = "agent_error"
                    # Overwrite history with just the error message for this turn
                    final_updated_history = (
                        current_history  # Start from history before this failed run
                    )
                    final_updated_history.append(
                        {"role": "assistant", "content": agent_response_text}
                    )

                # Ensure we have response text if nothing else was set
                if not agent_response_text.strip():
                    # This might happen if the agent only called a tool and we didn't generate a summary yet
                    # or if the agent simply didn't produce text output.
                    # Provide a generic holding response or look deeper into why no text was generated.
                    agent_response_text = (
                        "Okay, I'm processing that..."
                        if extracted_urls is not None
                        else "How can I help you further?"
                    )

                # ** FINAL HISTORY UPDATE **
                conversation_histories[session_id] = (
                    final_updated_history  # Assign the final list
                )

        except Exception as e:
            print(f"Error in chat endpoint for session {session_id}: {e}")
            # Log traceback
            raise HTTPException(
                status_code=500, detail=f"An internal server error occurred: {e}"
            )

        return ChatResponse(
            session_id=session_id,
            response=agent_response_text.strip(),
            status=final_status,
        )


@app.post("/clear", response_model=ClearResponse)
async def clear_endpoint(payload: ClearRequest):
    """Clears the conversation history for a given session ID."""
    session_id = payload.session_id
    async with session_locks[session_id]:  # Lock while modifying
        if session_id in conversation_histories:
            del conversation_histories[session_id]
            # Also remove the lock itself if no longer needed (optional, defaultdict handles creation)
            if session_id in session_locks:
                del session_locks[session_id]
            print(f"Cleared history for session: {session_id}")
            return ClearResponse(session_id=session_id, status="cleared")
        else:
            print(f"Session ID not found for clearing: {session_id}")
            # Return success even if not found, as the state is desired (no history)
            return ClearResponse(
                session_id=session_id, status="not_found_or_already_cleared"
            )


@app.get("/generate_session_id")
async def generate_session_id_endpoint():
    """Generates a new unique session ID."""
    return {"session_id": str(uuid.uuid4())}


# --- Run the app ---
if __name__ == "__main__":
    import uvicorn

    print("Starting FastAPI server...")
    print("Endpoints:")
    print("  POST /chat - Send messages to the agent")
    print("  POST /clear - Clear conversation history")
    print("  GET  /generate_session_id - Get a new session ID")
    print("Access API docs at http://127.0.0.1:8000/docs")
    uvicorn.run(app, host="127.0.0.1", port=8000)

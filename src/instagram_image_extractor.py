"""
Instagram image extractor using the Apify service.
This module provides functionality to retrieve Instagram images and analyze them.
"""

import asyncio
import base64
import os
from typing import List, Optional

import httpx
from apify_client import ApifyClient
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel, Field

from src.url_data_extractor import generate_markdown_from_urls

# Configure OpenAI client
openai_client = AsyncOpenAI()

# --- Pydantic Models ---


class ImageDescription(BaseModel):
    image_url: str = Field(description="The URL of the image analyzed.")
    description: str = Field(description="A detailed description of the image content.")


class InstagramAnalysisResult(BaseModel):
    username: str = Field(description="The Instagram username that was analyzed.")
    image_descriptions: str = Field(
        description="Descriptions of images found on the Instagram profile."
    )
    error: Optional[str] = Field(
        default=None, description="Any error encountered during analysis."
    )


def get_instagram_images_urls(username: str, imgs_limit: int = 10) -> List[str]:
    """
    Retrieve Instagram image URLs for a given username.

    Args:
        username: Instagram username to fetch images from
        imgs_limit: Maximum number of images to return (default: 10)

    Returns:
        A list of image URLs
    """
    return get_instagram_data(username=username, limit=imgs_limit, search_type="user")


def get_instagram_data(
    username: str,
    limit: int = 10,
    search_type: str = "user",
    results_type: str = "posts",
    add_parent_data: bool = False,
) -> List[str]:
    """
    Generic function to retrieve Instagram data of various types.

    Args:
        username: Username
        limit: Maximum number of results to return
        search_type: Type of search to perform ('user', 'hashtag', or 'url')
        results_type: Type of results to get ('posts', 'comments', 'profiles')
        add_parent_data: Whether to include parent data in results

    Returns:
        A list of image URLs
    """
    # Use provided token or fallback to default
    token = os.environ.get("APIFY_API_KEY")

    # Initialize the ApifyClient with API token
    client = ApifyClient(token)

    # Prepare the search URL based on search type
    if search_type == "user":
        direct_urls = [f"https://www.instagram.com/{username}"]
    elif search_type == "hashtag":
        direct_urls = [f"https://www.instagram.com/explore/tags/{username}"]
    elif search_type == "url":
        direct_urls = [username] if isinstance(username, str) else username
    else:
        raise ValueError(
            f"Invalid search_type: {search_type}. Must be 'user', 'hashtag', or 'url'"
        )

    # Prepare the Actor input
    run_input = {
        "directUrls": direct_urls,
        "resultsType": results_type,
        "resultsLimit": limit,
        "searchType": "hashtag" if search_type == "hashtag" else "user",
        "searchLimit": limit,
        "addParentData": add_parent_data,
    }

    # Run the Actor and wait for it to finish
    run = client.actor("shu8hvrXbJbY3Eb9W").call(run_input=run_input)

    # Fetch images from the results
    all_imgs = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        if "images" in item:
            all_imgs.extend(item["images"])

    return all_imgs


async def describe_instagram_images(
    username_or_url: str, max_images: int = 10
) -> InstagramAnalysisResult:
    """
    Fetches Instagram images for a given username or profile URL and uses a vision model to describe them.

    Args:
        username_or_url: Instagram username or profile URL to fetch images from
        max_images: Maximum number of images to fetch and describe (default: 10)
    """
    print(f"[Tool] Analyzing Instagram profile: {username_or_url}")
    error_message: Optional[str] = None

    try:
        # Extract username if a URL was provided
        username = username_or_url

        print(f"[Tool] Using Instagram username: {username}")

        # Get Instagram images using the Apify client
        image_urls = get_instagram_images_urls(username, max_images)
        print(f"[Tool] Found {len(image_urls)} Instagram images")

        if not image_urls:
            error_message = f"No images found for Instagram profile: {username}"
            print(f"[Tool] {error_message}")
            return InstagramAnalysisResult(
                username=username,
                image_descriptions=[],
                error=error_message,
            )

        image_descriptions_list = await generate_markdown_from_urls(image_urls)

    except Exception as e:
        error_message = f"An error occurred while fetching Instagram images: {e}"
        print(f"[Tool*] {error_message}")

    return InstagramAnalysisResult(
        username=username,
        image_descriptions=image_descriptions_list,
        error=error_message,
    )

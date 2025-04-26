import asyncio
import re
from typing import List, Optional

import aiohttp
from pydantic import BaseModel, Field

from agents import Agent, Runner, TResponseInputItem, trace
from clients.instagram.client import get_instagram_data


class ImageAnalysis(BaseModel):
    """Structured output for image analysis."""

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
        description="Whether the URL successfully resolved to an image and was analyzed."
    )


image_analyzer_agent = Agent(
    name="Image Analyzer",
    instructions=(
        "You are an expert image analyst. Analyze the provided image URL. "
        "Describe the main subject and scene concisely. "
        "If a specific location is identifiable (city, landmark, country), state it clearly. "
        "If the URL is not an image or an error occurs, indicate that. "
        "Respond ONLY with the JSON object matching the ImageAnalysis schema."
    ),
    model="o3",
    output_type=ImageAnalysis,
)


def is_valid_url(url: str) -> bool:
    """Basic check for URL validity."""
    # Simple regex for basic validation, not exhaustive
    regex = re.compile(
        r"^(?:http|ftp)s?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # domain...
        r"localhost|"  # localhost...
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )
    return re.match(regex, url) is not None


async def analyze_single_url(session: aiohttp.ClientSession, url: str) -> ImageAnalysis:
    """Analyzes a single URL using the image_analyzer_agent."""
    if not is_valid_url(url):
        return ImageAnalysis(
            description="",
            overview="",
            location=None,
            error=f"Invalid URL format: {url}",
            is_image=False,
        )

    # Construct the input message for the vision model
    input_message: List[TResponseInputItem] = [
        {
            "role": "user",
            "content": [
                {
                    "type": "input_image",
                    "image_url": url,
                    "detail": "auto",
                },
                {
                    "type": "input_text",
                    "text": "Analyze this image based on your instructions.",
                },
            ],
        }
    ]

    try:
        # Optionally, perform a quick HEAD request to check Content-Type first
        # This saves costs if the URL is clearly not an image (e.g., text/html)
        # Using aiohttp session passed from main
        async with session.head(url, allow_redirects=True, timeout=5) as response:
            content_type = response.headers.get("Content-Type", "").lower()
            if not content_type.startswith("image/"):
                return ImageAnalysis(
                    description="",
                    overview="",
                    location=None,
                    error=f"URL content type is '{content_type}', not an image.",
                    is_image=False,
                )
            # If it might be an image, proceed with analysis

        print(f"Analyzing image URL: {url}")
        result = await Runner.run(image_analyzer_agent, input_message)
        analysis = result.final_output_as(ImageAnalysis)
        # Ensure is_image is set correctly even if model doesn't explicitly set it
        analysis.is_image = True
        analysis.error = None  # Clear any default error if analysis succeeded
        return analysis

    except aiohttp.ClientError as e:
        print(f"Network error accessing URL {url}: {e}")
        return ImageAnalysis(
            description="",
            overview="",
            location=None,
            error=f"Network error: {e}",
            is_image=False,
        )
    except asyncio.TimeoutError:
        print(f"Timeout accessing URL {url}")
        return ImageAnalysis(
            description="",
            overview="",
            location=None,
            error="Timeout accessing URL",
            is_image=False,
        )
    except Exception as e:
        print(f"Error analyzing URL {url}: {e}")
        # Check if it's an OpenAI API error related to content
        error_str = str(e)
        if (
            "Input image may contain content that is not allowed" in error_str
            or "Invalid image url" in error_str
        ):
            return ImageAnalysis(
                description="",
                overview="",
                location=None,
                error=f"Analysis error: {error_str}",
                is_image=False,
            )
        # Assume other errors mean analysis failed
        return ImageAnalysis(
            description="",
            overview="",
            location=None,
            error=f"Analysis failed: {e}",
            is_image=False,
        )


async def process_urls(urls: List[str]) -> List[ImageAnalysis]:
    """
    Process a list of URLs to analyze images.

    Args:
        urls: List of image URLs to analyze

    Returns:
        List of ImageAnalysis results for each URL
    """
    if not urls:
        print("No valid URLs provided.")
        return []

    all_analysis_results: List[ImageAnalysis] = []

    # Use a single aiohttp session for efficiency
    async with aiohttp.ClientSession() as session:
        # Run analysis for all URLs concurrently
        analysis_tasks = [analyze_single_url(session, url) for url in urls]

        print(f"\nStarting analysis for {len(urls)} URLs...")
        # Use a trace for the entire workflow
        with trace("URL Analysis Workflow"):
            results = await asyncio.gather(*analysis_tasks)
            all_analysis_results.extend(results)

            return all_analysis_results


async def generate_markdown_from_urls(urls: List[str]) -> str:
    """
    Process a list of URLs and generate markdown with image descriptions.

    Args:
        urls: List of image URLs to analyze

    Returns:
        A formatted markdown string with image analysis results
    """
    all_analysis_results = await process_urls(urls)

    markdown_output = "# Image Analysis Results\n\n"

    for i, (url, analysis) in enumerate(zip(urls, all_analysis_results), 1):
        if analysis.is_image:
            # Add to markdown output
            markdown_output += f"## Image {i}\n\n"
            if analysis.location:
                markdown_output += f"**Location:** {analysis.location}\n\n"
            markdown_output += f"{analysis.description}\n\n"
        else:
            markdown_output += f"## Image {i}\n\n"
            markdown_output += f"**Error:** {analysis.error or 'Unknown error'}\n\n"

    return markdown_output

async def main():
    urls = [
        "https://scontent-waw2-2.cdninstagram.com/v/t51.29350-15/248951567_1668035853399331_1015357667300622163_n.webp?stp=dst-jpg_e35_tt6&efg=eyJ2ZW5jb2RlX3RhZyI6IkNBUk9VU0VMX0lURU0uaW1hZ2VfdXJsZ2VuLjE0NDB4MTgwMC5zZHIuZjI5MzUwLmRlZmF1bHRfaW1hZ2UifQ&_nc_ht=scontent-waw2-2.cdninstagram.com&_nc_cat=107&_nc_oc=Q6cZ2QGcriQjbYsoPru8nxnhUr2bHb7ad_0XwEYKsT7EhpRONOCnSRNQQJIecu8wbS1ZGUg&_nc_ohc=8EVN3DPiIM8Q7kNvwFpfI0p&_nc_gid=6_uYBzi--I5aJnYSJ57oLA&edm=AP4sbd4BAAAA&ccb=7-5&ig_cache_key=MjY5MzI3MDYxMDIwMjY5MjMxOQ%3D%3D.3-ccb7-5&oh=00_AfHEMFlfcTxNwKdIbgkvygPdOYZb_iEDuL7AkA37iHoRIg&oe=6811E167&_nc_sid=7a9f4b",
        "https://scontent-waw2-2.cdninstagram.com/v/t51.29350-15/260151702_116903297466432_8625987194443257014_n.webp?stp=dst-jpg_e35_tt6&efg=eyJ2ZW5jb2RlX3RhZyI6IkNBUk9VU0VMX0lURU0uaW1hZ2VfdXJsZ2VuLjE0NDB4MTgwMC5zZHIuZjI5MzUwLmRlZmF1bHRfaW1hZ2UifQ&_nc_ht=scontent-waw2-2.cdninstagram.com&_nc_cat=100&_nc_oc=Q6cZ2QGcriQjbYsoPru8nxnhUr2bHb7ad_0XwEYKsT7EhpRONOCnSRNQQJIecu8wbS1ZGUg&_nc_ohc=LLMff1JPJ-8Q7kNvwE1rZdN&_nc_gid=6_uYBzi--I5aJnYSJ57oLA&edm=AP4sbd4BAAAA&ccb=7-5&ig_cache_key=MjcxMjAyNjc2NzUzMzMyNTA0OQ%3D%3D.3-ccb7-5&oh=00_AfGNRAA3H2P4qcYXUSxq36qniKanc3qxy3lzhNy4oruNpA&oe=6811ECB8&_nc_sid=7a9f4b",
    ]

    # Use the new function to generate markdown
    markdown_output = await generate_markdown_from_urls(urls)    

    print("\n--- Individual URL Analysis Results ---")
    # Print detailed results for each URL
    all_analysis_results = await process_urls(urls)
    for i, (url, analysis) in enumerate(zip(urls, all_analysis_results), 1):
        print(f"\nURL: {url}")
        print(f"  Is Image: {analysis.is_image}")

        if analysis.is_image:
            print(f"  Description: {analysis.description}")
            print(f"  Location: {analysis.location or 'Not identified'}")
        else:
            print(f"  Error: {analysis.error}")

    print("\n--- Markdown Output ---")
    print(markdown_output)


if __name__ == "__main__":
    asyncio.run(main())


def generate_markdown_for_urls(urls: List[str]) -> str:
    """
    A synchronous function that processes a list of URLs and returns markdown with descriptions.
    This is a convenience wrapper around the asynchronous function.

    Args:
        urls: List of image URLs to analyze

    Returns:
        A formatted markdown string with image analysis results
    """
    return asyncio.run(generate_markdown_from_urls(urls))

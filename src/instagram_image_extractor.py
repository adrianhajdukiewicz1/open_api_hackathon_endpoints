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

    return [
        "https://instagram.fltn3-2.fna.fbcdn.net/v/t51.29350-15/223390606_3042042959360602_7440794659899633636_n.jpg?stp=dst-jpg_e35_s1080x1080_tt6&_nc_ht=instagram.fltn3-2.fna.fbcdn.net&_nc_cat=110&_nc_oc=Q6cZ2QE_sH98rUJkNzmRaeo5Oi7wm7qXX5CA0wS7ERQGIo98pMyhVy6xjdkh0iKqn5_9eMIszwTMO5UUGTqTKNtG9qx3&_nc_ohc=O3jBH4dUiPMQ7kNvwGI4gPf&_nc_gid=5jTbcYFyTX93vYC0ooOoqQ&edm=APs17CUBAAAA&ccb=7-5&oh=00_AfFagM-f-twYLgc6b9m9P964F1Yr_2DRBog9FK_k7R-S6w&oe=681294A0&_nc_sid=10d13b",
        "https://instagram.fltn3-1.fna.fbcdn.net/v/t51.29350-15/225043600_173495351388663_3417796725639752925_n.jpg?stp=dst-jpg_e35_s1080x1080_tt6&_nc_ht=instagram.fltn3-1.fna.fbcdn.net&_nc_cat=103&_nc_oc=Q6cZ2QE_sH98rUJkNzmRaeo5Oi7wm7qXX5CA0wS7ERQGIo98pMyhVy6xjdkh0iKqn5_9eMIszwTMO5UUGTqTKNtG9qx3&_nc_ohc=RDiu4cMv9xgQ7kNvwEaEWD6&_nc_gid=5jTbcYFyTX93vYC0ooOoqQ&edm=APs17CUBAAAA&ccb=7-5&oh=00_AfExl5ru5ASicfzNWmdCqwQE_Am2-I_8e7ThUcSoOiUi4w&oe=6812889D&_nc_sid=10d13b",
        "https://instagram.fltn3-2.fna.fbcdn.net/v/t51.29350-15/224472678_4288250224530438_1333112829596207137_n.jpg?stp=dst-jpg_e35_s1080x1080_tt6&_nc_ht=instagram.fltn3-2.fna.fbcdn.net&_nc_cat=106&_nc_oc=Q6cZ2QE_sH98rUJkNzmRaeo5Oi7wm7qXX5CA0wS7ERQGIo98pMyhVy6xjdkh0iKqn5_9eMIszwTMO5UUGTqTKNtG9qx3&_nc_ohc=LCnlXimCGRwQ7kNvwEYjl3C&_nc_gid=5jTbcYFyTX93vYC0ooOoqQ&edm=APs17CUBAAAA&ccb=7-5&oh=00_AfGytr1zM-Vf_iyaVdcM4hjdiXZk26csqPcqnplnCka9aQ&oe=68128906&_nc_sid=10d13b",
        "https://instagram.fltn3-1.fna.fbcdn.net/v/t51.29350-15/222873170_1040313216741624_6871161088862286710_n.jpg?stp=dst-jpg_e35_s1080x1080_tt6&_nc_ht=instagram.fltn3-1.fna.fbcdn.net&_nc_cat=100&_nc_oc=Q6cZ2QE_sH98rUJkNzmRaeo5Oi7wm7qXX5CA0wS7ERQGIo98pMyhVy6xjdkh0iKqn5_9eMIszwTMO5UUGTqTKNtG9qx3&_nc_ohc=mub3PihTr8IQ7kNvwFnCpq0&_nc_gid=5jTbcYFyTX93vYC0ooOoqQ&edm=APs17CUBAAAA&ccb=7-5&oh=00_AfFuDx3acQ1tWZiC0KRmMrf3yJnH6c84BLSUfR8eZF7hKA&oe=68129754&_nc_sid=10d13b",
        "https://instagram.fltn3-2.fna.fbcdn.net/v/t51.29350-15/224059418_510976860008382_2544112052215191453_n.jpg?stp=dst-jpg_e35_s1080x1080_tt6&_nc_ht=instagram.fltn3-2.fna.fbcdn.net&_nc_cat=106&_nc_oc=Q6cZ2QE_sH98rUJkNzmRaeo5Oi7wm7qXX5CA0wS7ERQGIo98pMyhVy6xjdkh0iKqn5_9eMIszwTMO5UUGTqTKNtG9qx3&_nc_ohc=Tz8rDJpBTeIQ7kNvwFmiusE&_nc_gid=5jTbcYFyTX93vYC0ooOoqQ&edm=APs17CUBAAAA&ccb=7-5&oh=00_AfEcCYXmqT3b1jzRk_C5Ro-xhai2kBAEIr_7y2IWrIZeCw&oe=68127C74&_nc_sid=10d13b",
        "https://instagram.fltn3-1.fna.fbcdn.net/v/t51.29350-15/224103566_347797140251385_8895094865939233394_n.jpg?stp=dst-jpg_e35_s1080x1080_tt6&_nc_ht=instagram.fltn3-1.fna.fbcdn.net&_nc_cat=109&_nc_oc=Q6cZ2QE_sH98rUJkNzmRaeo5Oi7wm7qXX5CA0wS7ERQGIo98pMyhVy6xjdkh0iKqn5_9eMIszwTMO5UUGTqTKNtG9qx3&_nc_ohc=r8m5_aXGQQ0Q7kNvwFFxxqa&_nc_gid=5jTbcYFyTX93vYC0ooOoqQ&edm=APs17CUBAAAA&ccb=7-5&oh=00_AfFsMd6vkCPAW8c32mUme8Kj4MGL3_Ic6EnmegmTtSw-Uw&oe=6812867A&_nc_sid=10d13b",
        "https://instagram.fltn3-1.fna.fbcdn.net/v/t51.29350-15/222795842_1604430873096371_3712226091082577865_n.jpg?stp=dst-jpg_e35_s1080x1080_tt6&_nc_ht=instagram.fltn3-1.fna.fbcdn.net&_nc_cat=111&_nc_oc=Q6cZ2QE_sH98rUJkNzmRaeo5Oi7wm7qXX5CA0wS7ERQGIo98pMyhVy6xjdkh0iKqn5_9eMIszwTMO5UUGTqTKNtG9qx3&_nc_ohc=j9ND2_5aFhIQ7kNvwE9Gio0&_nc_gid=5jTbcYFyTX93vYC0ooOoqQ&edm=APs17CUBAAAA&ccb=7-5&oh=00_AfE4PxbGoJtVZGVILsak_Yap5zqEjluP2BUpArPDP0oQ7A&oe=68128E09&_nc_sid=10d13b",
        "https://instagram.fltn3-1.fna.fbcdn.net/v/t51.29350-15/222495093_4329049450495067_3257865335139794392_n.jpg?stp=dst-jpg_e35_s1080x1080_tt6&_nc_ht=instagram.fltn3-1.fna.fbcdn.net&_nc_cat=111&_nc_oc=Q6cZ2QE_sH98rUJkNzmRaeo5Oi7wm7qXX5CA0wS7ERQGIo98pMyhVy6xjdkh0iKqn5_9eMIszwTMO5UUGTqTKNtG9qx3&_nc_ohc=E0fOymf0CwwQ7kNvwG36eMd&_nc_gid=5jTbcYFyTX93vYC0ooOoqQ&edm=APs17CUBAAAA&ccb=7-5&oh=00_AfHrmjA-OR8vaZuKRRL0LL-9Iy8vfLL9JBsCuBd3bVCb7g&oe=68128E3D&_nc_sid=10d13b",
        "https://instagram.fltn3-2.fna.fbcdn.net/v/t51.29350-15/225603682_353019579726016_3031052545333368688_n.jpg?stp=dst-jpg_e35_s1080x1080_tt6&_nc_ht=instagram.fltn3-2.fna.fbcdn.net&_nc_cat=104&_nc_oc=Q6cZ2QE_sH98rUJkNzmRaeo5Oi7wm7qXX5CA0wS7ERQGIo98pMyhVy6xjdkh0iKqn5_9eMIszwTMO5UUGTqTKNtG9qx3&_nc_ohc=nIGh9JvsQy8Q7kNvwEJCsaY&_nc_gid=5jTbcYFyTX93vYC0ooOoqQ&edm=APs17CUBAAAA&ccb=7-5&oh=00_AfG_6WVPiD2Fpx1HpX7wFJArzuaMIkc9wyYp9gYghwme8w&oe=681281B1&_nc_sid=10d13b",
        "https://instagram.fltn3-2.fna.fbcdn.net/v/t51.29350-15/223055821_772089190131776_9022304724914632422_n.jpg?stp=dst-jpg_e35_s1080x1080_tt6&_nc_ht=instagram.fltn3-2.fna.fbcdn.net&_nc_cat=108&_nc_oc=Q6cZ2QE_sH98rUJkNzmRaeo5Oi7wm7qXX5CA0wS7ERQGIo98pMyhVy6xjdkh0iKqn5_9eMIszwTMO5UUGTqTKNtG9qx3&_nc_ohc=w00oWvTKGLcQ7kNvwFqyg2f&_nc_gid=5jTbcYFyTX93vYC0ooOoqQ&edm=APs17CUBAAAA&ccb=7-5&oh=00_AfEsF0j2IYFGCd1ipi_P9kDz3xeDFHA-Vl1hxtm23-D2bw&oe=68128945&_nc_sid=10d13b",
        "https://scontent-man2-1.cdninstagram.com/v/t51.29350-15/263434775_326324875679222_4966329092414923646_n.webp?stp=dst-jpg_e35_p1080x1080_tt6&_nc_ht=scontent-man2-1.cdninstagram.com&_nc_cat=102&_nc_oc=Q6cZ2QG75Lhi8uvFG7iSmkK5kyjzl7mqBiHGISqn0Nu-coFOSsA029axfs6PB4-NhbJWRDY&_nc_ohc=qU3R6spP9hkQ7kNvwGchxZg&_nc_gid=W1zhJjQIIcifEZF6vLUgwg&edm=APs17CUBAAAA&ccb=7-5&oh=00_AfHkT1rtNjVnNUHszT5lslLptjM3KsjuKvL-B6K2iDxgNA&oe=68127C3F&_nc_sid=10d13b",
        "https://scontent-man2-1.cdninstagram.com/v/t51.29350-15/263175223_667655547727545_5155513412274334419_n.webp?stp=dst-jpg_e35_p1080x1080_tt6&_nc_ht=scontent-man2-1.cdninstagram.com&_nc_cat=109&_nc_oc=Q6cZ2QG75Lhi8uvFG7iSmkK5kyjzl7mqBiHGISqn0Nu-coFOSsA029axfs6PB4-NhbJWRDY&_nc_ohc=BQlCy75B2BEQ7kNvwGvK34Y&_nc_gid=W1zhJjQIIcifEZF6vLUgwg&edm=APs17CUBAAAA&ccb=7-5&oh=00_AfGpX65wsk_g4N-_6pn03n4PDoHjfJLoHNF5YCIHSvQD4g&oe=68128744&_nc_sid=10d13b",
        "https://scontent-man2-1.cdninstagram.com/v/t51.29350-15/263737150_1252800688478634_7778634919652907228_n.webp?stp=dst-jpg_e35_p1080x1080_tt6&_nc_ht=scontent-man2-1.cdninstagram.com&_nc_cat=106&_nc_oc=Q6cZ2QG75Lhi8uvFG7iSmkK5kyjzl7mqBiHGISqn0Nu-coFOSsA029axfs6PB4-NhbJWRDY&_nc_ohc=ndyac_i4uMgQ7kNvwHzx_Fs&_nc_gid=W1zhJjQIIcifEZF6vLUgwg&edm=APs17CUBAAAA&ccb=7-5&oh=00_AfHudSIYQS2RhnAHGLCUUtQ-UKNP0gXsiB62f5DWT77sbg&oe=68129312&_nc_sid=10d13b",
        "https://scontent-man2-1.cdninstagram.com/v/t51.29350-15/264193519_915547845743240_6180188134341037371_n.webp?stp=dst-jpg_e35_p1080x1080_tt6&_nc_ht=scontent-man2-1.cdninstagram.com&_nc_cat=108&_nc_oc=Q6cZ2QG75Lhi8uvFG7iSmkK5kyjzl7mqBiHGISqn0Nu-coFOSsA029axfs6PB4-NhbJWRDY&_nc_ohc=vhZ3VzhEbiMQ7kNvwFGtX97&_nc_gid=W1zhJjQIIcifEZF6vLUgwg&edm=APs17CUBAAAA&ccb=7-5&oh=00_AfEUYdfoBADX2uhmfqplXyFOZqo1yP_f1Khx1piBNrqC0A&oe=68128A55&_nc_sid=10d13b",
        "https://scontent-man2-1.cdninstagram.com/v/t51.29350-15/263666626_295218352615398_7847555531909550126_n.webp?stp=dst-jpg_e35_p1080x1080_tt6&_nc_ht=scontent-man2-1.cdninstagram.com&_nc_cat=106&_nc_oc=Q6cZ2QG75Lhi8uvFG7iSmkK5kyjzl7mqBiHGISqn0Nu-coFOSsA029axfs6PB4-NhbJWRDY&_nc_ohc=YdA0T-z-aRsQ7kNvwEjzyWJ&_nc_gid=W1zhJjQIIcifEZF6vLUgwg&edm=APs17CUBAAAA&ccb=7-5&oh=00_AfGDHFj_00zxj5Xc5tPGRSRCecJ_1X8O8di2gMhdk_7qMA&oe=68129056&_nc_sid=10d13b",
        "https://scontent-man2-1.cdninstagram.com/v/t51.29350-15/263442993_604535390758805_7827531428325428452_n.webp?stp=dst-jpg_e35_p1080x1080_tt6&_nc_ht=scontent-man2-1.cdninstagram.com&_nc_cat=105&_nc_oc=Q6cZ2QG75Lhi8uvFG7iSmkK5kyjzl7mqBiHGISqn0Nu-coFOSsA029axfs6PB4-NhbJWRDY&_nc_ohc=Tsi6g73Kg9kQ7kNvwG7_ekX&_nc_gid=W1zhJjQIIcifEZF6vLUgwg&edm=APs17CUBAAAA&ccb=7-5&oh=00_AfH5DO_bmQWNp5wBLx0f-h1tb3orQmbpOBDT-hyjo32TQg&oe=68129364&_nc_sid=10d13b",
    ]
    # Prepare the Actor input
    # run_input = {
    #     "directUrls": direct_urls,
    #     "resultsType": results_type,
    #     "resultsLimit": limit,
    #     "searchType": "hashtag" if search_type == "hashtag" else "user",
    #     "searchLimit": limit,
    #     "addParentData": add_parent_data,
    # }

    # # Run the Actor and wait for it to finish
    # run = client.actor("shu8hvrXbJbY3Eb9W").call(run_input=run_input)

    # # Fetch images from the results
    # all_imgs = []
    # for item in client.dataset(run["defaultDatasetId"]).iterate_items():
    #     if "images" in item:
    #         all_imgs.extend(item["images"])

    # return all_imgs


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
        if "/" in username_or_url:
            # Try to extract username from URL patterns like instagram.com/username
            url_parts = username_or_url.split("/")
            for part in url_parts:
                if (
                    part
                    and part != "www.instagram.com"
                    and part != "instagram.com"
                    and "." not in part
                ):
                    username = part
                    break

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

        # Process each image
    #     for img_url in image_urls:
    #         print(f"[Tool] Attempting to fetch and describe image: {img_url}")
    #         try:
    #             async with httpx.AsyncClient(timeout=20.0) as client:
    #                 img_response = await client.get(img_url, timeout=10.0)
    #                 img_response.raise_for_status()
    #                 img_content_type = img_response.headers.get(
    #                     "content-type", ""
    #                 ).lower()

    #                 if "image" not in img_content_type:
    #                     print(f"[Tool] Skipped non-image URL: {img_url}")
    #                     continue

    #                 img_data = await img_response.aread()
    #                 base64_image = base64.b64encode(img_data).decode("utf-8")

    #                 # Use OpenAI Vision API
    #                 vision_messages: List[ChatCompletionMessageParam] = [
    #                     {
    #                         "role": "user",
    #                         "content": [
    #                             {
    #                                 "type": "text",
    #                                 "text": "Describe this image in detail, focusing on elements relevant to travel planning (landmarks, activities, scenery, atmosphere).",
    #                             },
    #                             {
    #                                 "type": "image_url",
    #                                 "image_url": {
    #                                     "url": f"data:{img_content_type};base64,{base64_image}",
    #                                     "detail": "low",
    #                                 },
    #                             },
    #                         ],
    #                     }
    #                 ]

    #                 vision_response = await openai_client.chat.completions.create(
    #                     model="gpt-4o",  # Or another capable vision model
    #                     messages=vision_messages,
    #                     max_tokens=350,
    #                 )

    #                 description = (
    #                     vision_response.choices[0].message.content
    #                     or "No description generated."
    #                 )
    #                 print(f"[Tool] Image description: {description}")
    #                 image_descriptions.append(
    #                     ImageDescription(image_url=img_url, description=description)
    #                 )

    #         except httpx.RequestError as e:
    #             print(f"[Tool] Error fetching image {img_url}: {e}")
    #         except Exception as e:
    #             print(f"[Tool] Error describing image {img_url}: {e}")
    #         # Give a small break to avoid overwhelming servers
    #         await asyncio.sleep(0.1)

    except Exception as e:
        error_message = f"An error occurred while fetching Instagram images: {e}"
        print(f"[Tool*] {error_message}")

    return InstagramAnalysisResult(
        username=username,
        image_descriptions=image_descriptions_list,
        error=error_message,
    )

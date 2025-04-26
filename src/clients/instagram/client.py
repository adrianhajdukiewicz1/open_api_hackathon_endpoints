import os
from apify_client import ApifyClient
from typing import List, Dict, Any, Optional

def get_instagram_images_urls(username: str, imgs_limit: int = 10):
    """
    Retrieve Instagram image URLs for a given username.
    
    Args:
        username: Instagram username to fetch images from
        imgs_limit: Maximum number of images to return (default: 10)
    
    Returns:
        A list of image URLs
    """
    return get_instagram_data(
        target=username,
        limit=imgs_limit,
        search_type="user"
    )

def get_instagram_data(
    target: str,
    limit: int = 10,
    search_type: str = "user",
    results_type: str = "posts",
    add_parent_data: bool = False,
) -> List[str]:
    """
    Generic function to retrieve Instagram data of various types.
    
    Args:
        target: Username, hashtag, or URL to fetch data from
        limit: Maximum number of results to return
        search_type: Type of search to perform ('user', 'hashtag', or 'url')
        results_type: Type of results to get ('posts', 'comments', 'profiles')
        add_parent_data: Whether to include parent data in results
        api_token: Apify API token (uses default if not provided)
    
    Returns:
        A list of image URLs
    """
    # Use provided token or fallback to default
    token = os.environ.get("APIFY_API_KEY")

    # Initialize the ApifyClient with API token
    client = ApifyClient(token)
    
    # Prepare the search URL based on search type
    if search_type == "user":
        direct_urls = [f"https://www.instagram.com/{target}"]
    elif search_type == "hashtag":
        direct_urls = [f"https://www.instagram.com/explore/tags/{target}"]
    elif search_type == "url":
        direct_urls = [target] if isinstance(target, str) else target
    else:
        raise ValueError(f"Invalid search_type: {search_type}. Must be 'user', 'hashtag', or 'url'")

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
import requests
from typing import Optional
import json
def get_web_content(url: str, headers: Optional[dict] = None) -> Optional[str]:
    """
    Fetches the content from a given URL.
    Args:
        url: The URL to fetch.
        headers: Optional headers to include in the request.
    Returns:
        The content of the URL as a string, or None on error.
    """
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {url}: {e}")
        return None

def search_internet(query: str, num_results: int = 5) -> Optional[list[str]]:
    """
    Performs a basic internet search using a simple approach.  For real production
    use, you'd want to use a proper search API (like the Google Custom Search
    API) which requires an API key.  This is a simplified example for demonstration.
    Args:
        query: The search query.
        num_results: The number of search results to return (simplified).
    Returns:
        A list of search result snippets, or None on error.
    """
    #  Simplified search URL (This will NOT work reliably and is just for illustration)
    search_url = f"https://www.google.com/search?q={query}&hl=en"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'} # add user agent
    try:
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()
        text = response.text
        # Very basic and unreliable parsing of search results (DO NOT USE IN PRODUCTION)
        results = []
        start_pos = text.find('<div class="VwiC3b yXK7be">')  # Start of result description
        while start_pos != -1 and len(results) < num_results:
            start_pos = text.find('<div class="VwiC3b yXK7be">', start_pos + 1)
            if start_pos == -1:
                break
            end_pos = text.find('</div>', start_pos)
            if end_pos == -1:
                break
            snippet = text[start_pos + len('<div class="VwiC3b yXK7be">'):end_pos]
            snippet = snippet.replace('<span class="ILfuVd">', '').replace('</span>', '') # remove span
            results.append(snippet)
        return results
    except requests.exceptions.RequestException as e:
        print(f"Error performing search for '{query}': {e}")
        return None

def get_current_date() -> Optional[str]:
    """
    Gets the current date.
    Returns:
        The current date as a string (e.g., "2024-07-24"), or None on error.
    """
    try:
        response = requests.get("https://time.now.sh/")  # A simple time service
        response.raise_for_status()
        data = response.json()
        return data.get("datetime")[:10]  # Extract the date part
    except requests.exceptions.RequestException as e:
        print(f"Error getting current date: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response: {e}")
        return None

if __name__ == "__main__":
    # Example usage
    print(get_current_date())
    print(search_internet("What is the weather in London?"))
    url_content = get_web_content("https://www.example.com")
    if url_content:
        print(f"Successfully fetched content from example.com. First 200 chars: {url_content[:200]}")
    else:
        print("Failed to fetch content from example.com")
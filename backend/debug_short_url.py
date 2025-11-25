import asyncio
import httpx
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def expand_url(url: str):
    print(f"Testing expansion for: {url}")
    if "amzn.to" in url:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            async with httpx.AsyncClient(follow_redirects=True, headers=headers) as client:
                response = await client.get(url, timeout=10)
                expanded_url = str(response.url)
                print(f"Success! Expanded to: {expanded_url}")
                return expanded_url
        except Exception as e:
            print(f"Error expanding URL: {e}")
            return None
    else:
        print("Not an amzn.to URL")
        return url

if __name__ == "__main__":
    # Example amzn.to link (Found via search, hopefully active)
    test_url = "https://amzn.to/2WEYqLu" 
    asyncio.run(expand_url(test_url))

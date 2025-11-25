import asyncio
import unittest
from unittest.mock import MagicMock, patch, AsyncMock
from affiliate_service import AffiliateService

async def test_short_url_expansion():
    print("Testing Short URL Expansion...")
    
    service = AffiliateService()
    
    # Mock httpx.AsyncClient
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        
        # Setup mock response
        mock_response = MagicMock()
        mock_response.url = "https://www.amazon.ca/dp/B0C8X?tag=geocheapest-20"
        mock_client.get.return_value = mock_response
        
        # Mock _add_amazon_from_url to avoid further processing
        service._add_amazon_from_url = AsyncMock(return_value={"id": "test_id", "url": mock_response.url})
        
        short_url = "https://amzn.to/3XYZ"
        
        try:
            await service.add_product_from_url(short_url)
            print("Short URL Expansion Logic Executed")
            
            # Verify client was called with correct headers
            call_kwargs = mock_client_cls.call_args.kwargs
            headers = call_kwargs.get("headers", {})
            if "User-Agent" in headers:
                print("User-Agent Header Present")
            else:
                print("User-Agent Header Missing")
                
            # Verify get was called
            mock_client.get.assert_called_with(short_url)
            print("HTTP Get Called Correctly")
            
            # Verify _add_amazon_from_url was called with EXPANDED URL
            service._add_amazon_from_url.assert_called_with(str(mock_response.url))
            print("Called _add_amazon_from_url with Expanded URL")
            
        except Exception as e:
            print(f"Test Failed with Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_short_url_expansion())

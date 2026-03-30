import pytest
import httpx
from unittest.mock import AsyncMock
from docmost_mcp.client import DocmostClient
from docmost_mcp.config import DocmostConfig

@pytest.fixture
def mock_config():
    return DocmostConfig(
        DOCMOST_BASE_URL="https://docs.example.com",
        DOCMOST_API_TOKEN="token-123"
    )

@pytest.fixture
def client(mock_config):
    return DocmostClient(mock_config)

@pytest.mark.asyncio
async def test_client_get_page_success(client):
    # Mock the internal _request method
    client._request = AsyncMock(return_value={"id": "page-1", "title": "Test Page"})
    
    result = await client.get_page("page-1")
    assert result["id"] == "page-1"
    assert result["title"] == "Test Page"
    client._request.assert_called_once_with(
        "POST", "/pages/info", json_body={
            "pageId": "page-1",
            "includeContent": True,
            "includeSpace": True,
        }
    )

@pytest.mark.asyncio
async def test_client_search_success(client):
    client._request = AsyncMock(return_value={"items": [{"id": "r1"}]})
    
    result = await client.search("query")
    assert result["items"][0]["id"] == "r1"
    client._request.assert_called_once_with(
        "POST", "/search", json_body={"query": "query", "limit": 10, "offset": 0}
    )

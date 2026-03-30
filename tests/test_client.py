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

@pytest.mark.asyncio
async def test_client_import_page_create_success(client):
    client._request = AsyncMock(return_value={"id": "new-page"})
    
    result = await client.import_page("space-1", "New Title", "# Content")
    assert result["id"] == "new-page"
    
    # Check that it called /pages/import with files and data
    args, kwargs = client._request.call_args
    assert args == ("POST", "/pages/import")
    assert "files" in kwargs
    assert "data" in kwargs
    assert kwargs["data"]["spaceId"] == "space-1"
    assert kwargs["files"]["file"][0] == "New Title.md"

@pytest.mark.asyncio
async def test_client_import_page_replace_success(client):
    client._request = AsyncMock(return_value={"id": "page-1"})
    
    result = await client.import_page("space-1", "Ignored Title", "# New Content", page_id="page-1")
    assert result["id"] == "page-1"
    
    # Check that it called /pages/update with json_body
    client._request.assert_called_once_with(
        "POST", "/pages/update", json_body={
            "pageId": "page-1",
            "content": "# New Content",
            "format": "markdown",
            "operation": "replace",
        }
    )

"""
MCP server definition with all Docmost tool registrations.

**Architecture note — separation of concerns:**

This module is the "exhibition curator".  It decides *which* operations
to expose as MCP tools and *how* to present them to the LLM (descriptive
docstrings, parameter names, return formatting).

It does **not** contain HTTP logic, auth logic, or error translation —
all of that lives in ``client.py``.  Each tool function is a thin wrapper:

1. Accept parameters from the LLM.
2. Delegate to ``DocmostClient``.
3. Format the result as a human/LLM-readable string.
4. Catch ``DocmostError`` and return a clear error message.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

from docmost_mcp.client import DocmostClient
from docmost_mcp.config import DocmostConfig
from docmost_mcp.exceptions import DocmostError

logger: logging.Logger = logging.getLogger(__name__)

# ── Initialise config, client, and server ───────────────────────────

# Validate configuration at import time — fail fast.
try:
    _config: DocmostConfig = DocmostConfig()  # type: ignore[call-arg]
except Exception as exc:
    # Write to stderr so it doesn't corrupt the MCP stdio transport.
    print(f"[docmost-mcp] Configuration error: {exc}", file=sys.stderr)
    sys.exit(1)

_client: DocmostClient = DocmostClient(_config)

mcp: FastMCP = FastMCP(
    "docmost-mcp",
    instructions=(
        "Docmost MCP server — provides tools to search, read, create, update, "
        "and delete documentation pages in a Docmost wiki workspace. "
        "Use 'list_spaces' first to discover available spaces, then use other "
        "tools to interact with pages within those spaces."
    ),
)


# ── Helper ──────────────────────────────────────────────────────────

def _format_json(data: Any) -> str:
    """Pretty-print a dict/list as indented JSON for LLM readability.

    Args:
        data: The Python object to serialise.

    Returns:
        A nicely formatted JSON string.
    """
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


# ══════════════════════════════════════════════════════════════════════
#  TOOL 1: SEARCH
# ══════════════════════════════════════════════════════════════════════

@mcp.tool()
async def search_docmost(
    query: str,
    space_id: str | None = None,
    limit: int = 10,
    offset: int = 0,
) -> str:
    """Search the Docmost workspace for pages by keyword.

    Performs a full-text search across all page titles and content
    in spaces the authenticated user can access.

    Args:
        query: The search keywords.
        space_id: Optional space UUID to restrict results to one space.
        limit: Maximum number of results (default 10).
        offset: Number of results to skip (default 0).

    Returns:
        A JSON list of matching pages with titles and space info.
    """
    try:
        result: dict[str, Any] = await _client.search(
            query, space_id=space_id, limit=limit, offset=offset,
        )
        items: list[dict[str, Any]] = result.get("items", [])
        if not items:
            return f"No results found for '{query}'."
        return _format_json(items)
    except DocmostError as exc:
        return f"Search failed: {exc}"


# ══════════════════════════════════════════════════════════════════════
#  TOOL 2: GET PAGE
# ══════════════════════════════════════════════════════════════════════

@mcp.tool()
async def get_page(
    page_id: str,
    include_content: bool = True,
    include_space: bool = True,
) -> str:
    """Retrieve a page's details and content from Docmost.

    Use this to read the full content of a documentation page.
    Note: Page content is returned as ProseMirror JSON.

    Args:
        page_id: The UUID or slug ID of the page.
        include_content: Whether to include the page body (default True).
        include_space: Whether to include parent space info (default True).

    Returns:
        The page data including title, content, space info, and metadata.
    """
    try:
        result: dict[str, Any] = await _client.get_page(
            page_id,
            include_content=include_content,
            include_space=include_space,
        )
        return _format_json(result)
    except DocmostError as exc:
        return f"Failed to retrieve page '{page_id}': {exc}"


# ══════════════════════════════════════════════════════════════════════
#  TOOL 3: CREATE PAGE
# ══════════════════════════════════════════════════════════════════════

@mcp.tool()
async def create_page(
    space_id: str,
    title: str = "Untitled",
    parent_page_id: str | None = None,
    icon: str = "📄",
) -> str:
    """Initialize a new (blank) documentation page skeleton.

    IMPORTANT: This tool only creates the page metadata and hierarchy.
    To add content to the page, you MUST follow up with 'import_page'.

    Args:
        space_id: UUID of the target space.
        title: Page title.
        parent_page_id: Optional parent page UUID to create a sub-page.
        icon: Optional emoji icon for the page (default "📄").

    Returns:
        The created page's ID and metadata.
    """
    try:
        result: dict[str, Any] = await _client.create_page(
            space_id,
            title=title,
            parent_page_id=parent_page_id,
            icon=icon,
        )
        page_id: str = result.get("id", "unknown")
        return (
            f"✅ Blank page created successfully!\n"
            f"  • Title: {title}\n"
            f"  • Page ID: {page_id}\n"
            f"  • Space: {space_id}\n"
            f"👉 NEXT STEP: Use 'import_page' with this Page ID to add content."
        )
    except DocmostError as exc:
        return f"Failed to create page: {exc}"


# ══════════════════════════════════════════════════════════════════════
#  TOOL 4: UPDATE PAGE
# ══════════════════════════════════════════════════════════════════════

@mcp.tool()
async def update_page(
    page_id: str,
    title: str | None = None,
    icon: str | None = None,
) -> str:
    """Update a page's title or icon (metadata only).

    Note: This tool does NOT update page content. To replace page content,
    use the 'import_page' tool with a 'page_id'.

    Args:
        page_id: UUID of the page to update.
        title: New title (omit to keep current).
        icon: New emoji icon (omit to keep current).

    Returns:
        Confirmation with the updated page's metadata.
    """
    try:
        result: dict[str, Any] = await _client.update_page(
            page_id,
            title=title,
            icon=icon,
        )
        return (
            f"✅ Page metadata updated successfully!\n"
            f"  • Page ID: {page_id}\n"
            f"  • Title: {result.get('title', 'N/A')}\n"
            f"  • Last Updated: {result.get('updatedAt', 'N/A')}"
        )
    except DocmostError as exc:
        return f"Failed to update page '{page_id}': {exc}"


# ══════════════════════════════════════════════════════════════════════
#  TOOL 5: DELETE PAGE
# ══════════════════════════════════════════════════════════════════════

@mcp.tool()
async def delete_page(
    page_id: str,
    permanently: bool = False,
) -> str:
    """Delete a page from Docmost.

    By default, pages are soft-deleted (moved to trash and can be restored).
    Set permanently=True to irreversibly remove the page.

    Args:
        page_id: UUID of the page to delete.
        permanently: If True, permanently deletes the page (cannot be undone).
            If False (default), soft-deletes to trash.

    Returns:
        Confirmation of the deletion.
    """
    try:
        await _client.delete_page(page_id, permanently=permanently)
        action: str = "permanently deleted" if permanently else "moved to trash"
        return f"✅ Page '{page_id}' has been {action}."
    except DocmostError as exc:
        return f"Failed to delete page '{page_id}': {exc}"


# ══════════════════════════════════════════════════════════════════════
#  TOOL 6: LIST SPACES
# ══════════════════════════════════════════════════════════════════════

@mcp.tool()
async def list_spaces(page: int = 1, per_page: int = 50) -> str:
    """List all Docmost spaces the authenticated user can access.

    Spaces are top-level containers for teams/projects. Use this to
    discover space IDs before creating or listing pages.

    Args:
        page: Page number to retrieve (default 1).
        per_page: Number of spaces per page (default 50, max 100).

    Returns:
        A JSON list of spaces with names and IDs.
    """
    try:
        result: dict[str, Any] = await _client.list_spaces(page=page, per_page=per_page)
        items: list[dict[str, Any]] = result.get("items", [])
        if not items:
            return "No spaces found."

        summary: list[dict[str, Any]] = [
            {
                "id": s.get("id"),
                "name": s.get("name"),
                "slug": s.get("slug"),
                "description": s.get("description"),
            }
            for s in items
        ]
        return _format_json(summary)
    except DocmostError as exc:
        return f"Failed to list spaces: {exc}"


# ══════════════════════════════════════════════════════════════════════
#  TOOL 7: GET SPACE INFO
# ══════════════════════════════════════════════════════════════════════

@mcp.tool()
async def get_space_info(space_id: str) -> str:
    """Get detailed information about a specific Docmost space.

    Returns the space's name, description, member count, and the
    authenticated user's role/permissions within the space.

    Args:
        space_id: UUID of the space.

    Returns:
        Space details including membership and permission info.
    """
    try:
        result: dict[str, Any] = await _client.get_space(space_id)
        return _format_json(result)
    except DocmostError as exc:
        return f"Failed to get space info for '{space_id}': {exc}"


# ══════════════════════════════════════════════════════════════════════
#  TOOL 8: LIST SPACE PAGES
# ══════════════════════════════════════════════════════════════════════

@mcp.tool()
async def list_space_pages(
    space_id: str,
    page_id: str | None = None,
    limit: int = 50,
) -> str:
    """List pages within a Docmost space (sidebar navigation tree).

    Returns root-level pages by default.  Provide a page_id to list
    its child pages (useful for navigating the page hierarchy).

    Args:
        space_id: UUID of the space.
        page_id: Optional parent page UUID to list children of.
        limit: Maximum pages to return (default 50, max 100).

    Returns:
        A JSON list of pages with titles, icons, and hierarchy info.
    """
    try:
        result: dict[str, Any] = await _client.list_space_pages(
            space_id, page_id=page_id, limit=limit,
        )
        items: list[dict[str, Any]] = result.get("items", [])
        if not items:
            context: str = f"under page '{page_id}'" if page_id else "at root level"
            return f"No pages found {context} in space '{space_id}'."
        return _format_json(items)
    except DocmostError as exc:
        return f"Failed to list pages: {exc}"


# ══════════════════════════════════════════════════════════════════════
#  TOOL 9: IMPORT PAGE
# ══════════════════════════════════════════════════════════════════════

@mcp.tool()
async def import_page(
    space_id: str,
    title: str,
    content: str,
    page_id: str | None = None,
) -> str:
    """Import Markdown content as a new page or replace an existing page.

    This is the RECOMMENDED method for creating a page with content in Docmost.
    If 'page_id' is provided, the content of that specific page will be replaced.
    Otherwise, a new page will be created.

    Args:
        space_id: UUID of the target space.
        title: Title/Filename for the imported content.
        content: The full Markdown content to import.
        page_id: Optional UUID of an existing page to replace its content.

    Returns:
        Confirmation of the import.
    """
    try:
        await _client.import_page(space_id, title, content, page_id=page_id)
        target: str = f"page '{page_id}'" if page_id else f"new page '{title}'"
        return (
            f"✅ Successfully imported content into {target} in space '{space_id}'.\n"
            f"  Use 'list_space_pages' to confirm."
        )
    except DocmostError as exc:
        return f"Failed to import content: {exc}"


# ══════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════

def main() -> None:
    """Start the Docmost MCP server on stdio transport.

    This is called by:
    - ``python -m docmost_mcp``
    - The ``docmost-mcp`` console script
    """
    # Configure logging to stderr (stdout is reserved for MCP stdio transport).
    logging.basicConfig(
        level=logging.INFO,
        format="[docmost-mcp] %(levelname)s: %(message)s",
        stream=sys.stderr,
    )

    logger.info(
        "Starting Docmost MCP server (target: %s)",
        _config.normalised_base_url,
    )
    mcp.run()

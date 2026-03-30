"""
Async HTTP client for the Docmost REST API.

**Why a centralised client class?**

Think of it like a well-calibrated lens system on a professional camera.
You don't swap your entire camera body for every shot — you mount different
lenses on *one* body that handles autofocus, metering, and exposure
consistently.

``DocmostClient`` is that camera body.  It owns:

- A single ``httpx.AsyncClient`` with connection pooling and timeouts.
- The authentication header (Bearer token *or* session cookie).
- Automatic login and token refresh for Community-edition users.
- Consistent error translation: HTTP status codes → custom exceptions.

Every MCP tool in ``server.py`` delegates to a method on this class.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from docmost_mcp.config import DocmostConfig
from docmost_mcp.exceptions import (
    DocmostAPIError,
    DocmostAuthError,
    DocmostConnectionError,
    DocmostNotFoundError,
    DocmostValidationError,
)

logger: logging.Logger = logging.getLogger(__name__)


class DocmostClient:
    """Async client for the Docmost REST API.

    Supports two authentication strategies:

    1. **Bearer token** (Enterprise / Business editions):
       Sends ``Authorization: Bearer <token>`` on every request.

    2. **Email / password login** (Community edition):
       Calls ``POST /api/auth/login`` once, then attaches the returned
       ``authToken`` cookie to every subsequent request.  If a 401 is
       received, the client automatically re-authenticates.

    Args:
        config: Validated ``DocmostConfig`` instance.
    """

    def __init__(self, config: DocmostConfig) -> None:
        self._config: DocmostConfig = config
        self._base_api: str = f"{config.normalised_base_url}/api"
        self._auth_cookie: str | None = None

        # Build default headers — Bearer token if available.
        headers: dict[str, str] = {
            "Accept": "application/json",
        }
        if config.uses_bearer_token:
            headers["Authorization"] = f"Bearer {config.api_token}"

        self._client: httpx.AsyncClient = httpx.AsyncClient(
            base_url=self._base_api,
            headers=headers,
            timeout=httpx.Timeout(30.0, connect=10.0),
        )

    # ── Lifecycle ───────────────────────────────────────────────────────

    async def close(self) -> None:
        """Close the underlying HTTP connection pool.

        Call this when the server is shutting down to release resources.
        """
        await self._client.aclose()

    # ── Authentication ──────────────────────────────────────────────────

    async def _login(self) -> None:
        """Authenticate via email/password and cache the session cookie.

        This hits ``POST /api/auth/login`` — available on all Docmost
        editions, no API key required.

        Raises:
            DocmostAuthError: If login fails (bad credentials, SSO enforced, etc.).
            DocmostConnectionError: If the server is unreachable.
        """
        try:
            response: httpx.Response = await self._client.post(
                "/auth/login",
                json={
                    "email": self._config.email,
                    "password": self._config.password,
                },
            )
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise DocmostConnectionError(
                f"Cannot reach Docmost at {self._config.normalised_base_url}. "
                f"Please verify the URL is correct and the server is running. "
                f"Details: {exc}"
            ) from exc

        if response.status_code == 401:
            raise DocmostAuthError(
                "Login failed: invalid email or password. "
                "Check your DOCMOST_EMAIL and DOCMOST_PASSWORD environment variables."
            )

        if response.status_code == 400:
            body: dict[str, Any] = response.json()
            raise DocmostAuthError(
                f"Login rejected by Docmost: {body.get('message', response.text[:300])}. "
                "This may mean SSO is enforced — try using DOCMOST_API_TOKEN instead."
            )

        if response.status_code != 200:
            raise DocmostAPIError(
                f"Unexpected login response (HTTP {response.status_code}).",
                status_code=response.status_code,
                response_text=response.text[:500],
            )

        # Extract the authToken from the Set-Cookie header.
        token: str | None = response.cookies.get("authToken")

        # Fallback: some Docmost deployments return the token in the response body.
        if not token:
            body = response.json()
            token = body.get("data", {}).get("token") or body.get("token")

        if not token:
            raise DocmostAuthError(
                "Login succeeded but no authToken was returned. "
                "This is unexpected — please check your Docmost version."
            )

        self._auth_cookie = token
        logger.info("Successfully authenticated with Docmost via email/password.")

    async def _ensure_authenticated(self) -> None:
        """Ensure we have valid credentials before making an API call.

        For Bearer-token auth, this is a no-op (the token is in the headers).
        For email/password auth, this triggers ``_login()`` if we haven't
        logged in yet.
        """
        if self._config.uses_bearer_token:
            return  # Bearer token is always in the default headers.

        if self._auth_cookie is None:
            await self._login()

    def _inject_cookie(self, headers: dict[str, str] | None = None) -> dict[str, str]:
        """Inject the session cookie into request headers if using login auth.

        Args:
            headers: Optional extra headers to merge.

        Returns:
            A headers dict ready for use in a request.
        """
        result: dict[str, str] = dict(headers) if headers else {}
        if not self._config.uses_bearer_token and self._auth_cookie:
            result["Cookie"] = f"authToken={self._auth_cookie}"
        return result

    # ── Core request method ─────────────────────────────────────────────

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        json_body: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Send an HTTP request to the Docmost API with automatic retries.

        This is the single bottleneck through which **every** API call flows.
        It handles:

        - Ensuring authentication is established.
        - Injecting cookies for Community-edition auth.
        - Automatic re-login on 401 (token expired).
        - Translating HTTP errors into typed exceptions.

        Args:
            method: HTTP method (``GET``, ``POST``).
            endpoint: API path relative to ``/api/`` (e.g., ``/pages/info``).
            json_body: JSON payload for the request body.
            files: Multipart file uploads.
            data: Form data fields (used alongside ``files``).
            extra_headers: Additional headers to merge.

        Returns:
            Parsed JSON response body as a dict.

        Raises:
            DocmostAuthError: On 401/403 after retry.
            DocmostNotFoundError: On 404.
            DocmostValidationError: On 400.
            DocmostAPIError: On unexpected status codes.
            DocmostConnectionError: On network failures.
        """
        await self._ensure_authenticated()

        for attempt in range(2):  # At most one retry after re-login.
            try:
                # Build request kwargs.
                kwargs: dict[str, Any] = {
                    "headers": self._inject_cookie(extra_headers)
                }

                if files is not None:
                    # Multipart upload — don't set Content-Type (httpx does it).
                    kwargs["files"] = files
                    if data is not None:
                        kwargs["data"] = data
                elif json_body is not None:
                    kwargs["json"] = json_body

                response: httpx.Response = await self._client.request(
                    method, endpoint, **kwargs
                )

            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                raise DocmostConnectionError(
                    f"Cannot reach Docmost at {self._config.normalised_base_url}. "
                    f"Please verify the server is running. Details: {exc}"
                ) from exc

            # ── Handle 401: auto-refresh on first attempt ───────────
            if response.status_code == 401 and attempt == 0:
                if not self._config.uses_bearer_token:
                    logger.info("Session expired. Re-authenticating…")
                    self._auth_cookie = None
                    await self._login()
                    continue  # Retry with fresh cookie.

                raise DocmostAuthError(
                    "API token is invalid or expired. "
                    "Please generate a new token in your Docmost admin panel."
                )

            break  # Success or non-retryable error.

        # ── Translate HTTP errors to exceptions ─────────────────────
        return self._handle_response(response)

    @staticmethod
    def _handle_response(response: httpx.Response) -> dict[str, Any]:
        """Parse a Docmost API response and raise on errors.

        Docmost wraps all responses as ``{ success, status, data }``.
        We return only the inner ``data`` value when available.

        Args:
            response: The raw httpx response.

        Returns:
            The ``data`` field from the response, or the full body.

        Raises:
            DocmostAuthError: On 401 or 403.
            DocmostNotFoundError: On 404.
            DocmostValidationError: On 400.
            DocmostAPIError: On any other non-2xx status.
        """
        status: int = response.status_code

        if status == 401 or status == 403:
            raise DocmostAuthError(
                f"Docmost returned HTTP {status}: access denied. "
                f"Details: {response.text[:300]}"
            )

        if status == 404:
            raise DocmostNotFoundError(
                f"Resource not found (HTTP 404). "
                f"Details: {response.text[:300]}"
            )

        if status == 400:
            raise DocmostValidationError(
                f"Bad request (HTTP 400). "
                f"Details: {response.text[:300]}"
            )

        if status >= 400:
            raise DocmostAPIError(
                f"Docmost API error (HTTP {status}).",
                status_code=status,
                response_text=response.text[:500],
            )

        # ── Parse successful response ───────────────────────────────
        try:
            body: dict[str, Any] = response.json()
        except (json.JSONDecodeError, ValueError):
            return {"raw": response.text[:2000]}

        # Docmost wraps responses as { data, success, status }.
        # Return the inner 'data' if present, else the full body.
        if "data" in body:
            return body["data"]
        return body

    # ══════════════════════════════════════════════════════════════════
    #  PUBLIC API — PAGES
    # ══════════════════════════════════════════════════════════════════

    async def get_page(
        self,
        page_id: str,
        *,
        include_content: bool = True,
        include_space: bool = True,
    ) -> dict[str, Any]:
        """Retrieve a page's details and optionally its content.

        Args:
            page_id: UUID or slug ID of the page.
            include_content: If ``True``, include the page body.
            include_space: If ``True``, include the parent space info.

        Returns:
            Page data dict with nested creator, space, and content fields.
        """
        return await self._request("POST", "/pages/info", json_body={
            "pageId": page_id,
            "includeContent": include_content,
            "includeSpace": include_space,
        })

    async def create_page(
        self,
        space_id: str,
        *,
        title: str = "Untitled",
        parent_page_id: str | None = None,
        icon: str | None = "📄",
    ) -> dict[str, Any]:
        """Initialize a new page skeleton in a space.

        Args:
            space_id: UUID of the target space.
            title: Page title.
            parent_page_id: Optional parent page UUID for nesting.
            icon: Optional emoji icon string (e.g. "📄").

        Returns:
            The created page data dict.
        """
        payload: dict[str, Any] = {"spaceId": space_id, "title": title}

        if parent_page_id:
            payload["parentPageId"] = parent_page_id
        if icon:
            payload["icon"] = icon

        return await self._request("POST", "/pages/create", json_body=payload)

    async def update_page(
        self,
        page_id: str,
        *,
        title: str | None = None,
        icon: str | None = None,
    ) -> dict[str, Any]:
        """Update a page's metadata (title or icon).

        Args:
            page_id: UUID of the page to update.
            title: New title (or ``None`` to keep current).
            icon: New emoji icon (or ``None`` to keep current).

        Returns:
            The updated page data dict.
        """
        payload: dict[str, Any] = {"pageId": page_id}

        if title is not None:
            payload["title"] = title
        if icon is not None:
            payload["icon"] = icon

        return await self._request("POST", "/pages/update", json_body=payload)

    async def delete_page(
        self,
        page_id: str,
        *,
        permanently: bool = False,
    ) -> dict[str, Any]:
        """Delete a page (soft-delete by default).

        Args:
            page_id: UUID of the page to delete.
            permanently: If ``True``, permanently removes the page.
                If ``False`` (default), soft-deletes it to the trash.

        Returns:
            Confirmation dict.
        """
        return await self._request("POST", "/pages/delete", json_body={
            "pageId": page_id,
            "permanentlyDelete": permanently,
        })

    async def list_space_pages(
        self,
        space_id: str,
        *,
        page_id: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """List pages in a space for sidebar navigation.

        Args:
            space_id: UUID of the space.
            page_id: Optional parent page ID to list children of.
            limit: Maximum pages to return (1–100).

        Returns:
            Dict with ``items`` (list of sidebar pages) and ``meta`` (pagination).
        """
        payload: dict[str, Any] = {"spaceId": space_id, "limit": limit}
        if page_id:
            payload["pageId"] = page_id

        return await self._request(
            "POST", "/pages/sidebar-pages", json_body=payload
        )

    async def import_page(
        self,
        space_id: str,
        title: str,
        markdown_content: str,
        *,
        page_id: str | None = None,
    ) -> dict[str, Any]:
        """Import a Markdown document as a new page or replace an existing one.

        Args:
            space_id: UUID of the target space.
            title: Document title (used as the filename).
            markdown_content: The Markdown content to import.
            page_id: Optional UUID. If provided, replaces the content of this page.

        Returns:
            The import result dict.
        """
        files: dict[str, tuple[str, str, str]] = {
            "file": (f"{title}.md", markdown_content, "text/markdown"),
        }
        data: dict[str, str] = {"spaceId": space_id}
        if page_id:
            data["pageId"] = page_id

        return await self._request(
            "POST", "/pages/import", files=files, data=data,
        )

    # ══════════════════════════════════════════════════════════════════
    #  PUBLIC API — SPACES
    # ══════════════════════════════════════════════════════════════════

    async def list_spaces(
        self,
        *,
        page: int = 1,
        per_page: int = 50,
    ) -> dict[str, Any]:
        """List all spaces the authenticated user can access.

        Args:
            page: Numeric page number (starts at 1).
            per_page: Number of spaces per page (1–100).

        Returns:
            Dict with ``items`` (list of spaces) and ``meta`` (pagination).
        """
        payload: dict[str, Any] = {"page": page, "perPage": per_page}
        return await self._request("POST", "/spaces/", json_body=payload)

    async def get_space(self, space_id: str) -> dict[str, Any]:
        """Get details for a specific space.

        Args:
            space_id: UUID of the space.

        Returns:
            Space data dict with member count and membership info.
        """
        return await self._request(
            "POST", "/spaces/info", json_body={"spaceId": space_id}
        )

    # ══════════════════════════════════════════════════════════════════
    #  PUBLIC API — SEARCH
    # ══════════════════════════════════════════════════════════════════

    async def search(
        self,
        query: str,
        *,
        space_id: str | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Full-text search across all accessible pages.

        Args:
            query: Search keywords.
            space_id: Optional space filter.
            limit: Max results to return.
            offset: Number of items to skip for pagination.

        Returns:
            Dict with ``items`` (list of search results with highlights).
        """
        payload: dict[str, Any] = {"query": query, "limit": limit, "offset": offset}
        if space_id:
            payload["spaceId"] = space_id

        return await self._request("POST", "/search", json_body=payload)

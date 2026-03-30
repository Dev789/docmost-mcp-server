"""
Configuration management for the Docmost MCP server.

**Why Pydantic ``BaseSettings`` instead of raw ``os.getenv()``?**

Using ``os.getenv()`` is like loading a camera without checking the film:
you only discover the problem when you press the shutter — i.e., deep
inside a tool call, where it's too late to give the user a clear diagnosis.

``BaseSettings`` validates *all* config at startup time.  If
``DOCMOST_BASE_URL`` is missing, the server dies immediately with a clean
error, rather than halfway through an API call five minutes later.

**Dual auth strategy (Community vs Enterprise):**

- **Community edition:** No API keys available.  Provide
  ``DOCMOST_EMAIL`` + ``DOCMOST_PASSWORD`` → the client will call
  ``POST /auth/login`` to obtain a session cookie automatically.
- **Enterprise / Business:** Provide ``DOCMOST_API_TOKEN`` → the client
  uses ``Authorization: Bearer <token>`` directly.

If *both* are set, the API token takes precedence (it's faster —
no login round-trip).
"""

from __future__ import annotations

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from docmost_mcp.exceptions import DocmostConfigError


class DocmostConfig(BaseSettings):
    """Validated configuration sourced from environment variables.

    Environment variables are loaded automatically.  A ``.env`` file in the
    working directory is also read if present (useful for local dev).

    Attributes:
        base_url: Root URL of the Docmost instance (no trailing slash).
        api_token: Bearer token for EE/Business editions.  Optional.
        email: Login email for Community edition.  Optional.
        password: Login password for Community edition.  Optional.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    base_url: str = Field(
        alias="DOCMOST_BASE_URL",
        description="Root URL of the Docmost instance, e.g. https://docs.example.com",
    )

    api_token: str | None = Field(
        default=None,
        alias="DOCMOST_API_TOKEN",
        description="Bearer API token (Enterprise / Business editions only).",
    )

    email: str | None = Field(
        default=None,
        alias="DOCMOST_EMAIL",
        description="Login email for Community edition (used with DOCMOST_PASSWORD).",
    )

    password: str | None = Field(
        default=None,
        alias="DOCMOST_PASSWORD",
        description="Login password for Community edition (used with DOCMOST_EMAIL).",
    )

    # ── Validation ──────────────────────────────────────────────────────

    @model_validator(mode="after")
    def _check_auth_credentials(self) -> "DocmostConfig":
        """Ensure at least one complete auth strategy is configured.

        Raises:
            DocmostConfigError: If neither an API token nor an email/password
                pair is provided.
        """
        has_token: bool = self.api_token is not None
        has_login: bool = self.email is not None and self.password is not None

        if not has_token and not has_login:
            raise DocmostConfigError(
                "Authentication not configured. Please set one of:\n"
                "  • DOCMOST_API_TOKEN (for Enterprise / Business editions)\n"
                "  • DOCMOST_EMAIL + DOCMOST_PASSWORD (for Community edition)\n"
                "in your environment or .env file."
            )

        return self

    # ── Helpers ──────────────────────────────────────────────────────────

    @property
    def uses_bearer_token(self) -> bool:
        """Return ``True`` if Bearer-token auth should be used."""
        return self.api_token is not None

    @property
    def normalised_base_url(self) -> str:
        """Return the base URL with any trailing slash removed."""
        return self.base_url.rstrip("/")

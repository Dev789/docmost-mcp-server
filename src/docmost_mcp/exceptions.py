"""
Custom exception hierarchy for the Docmost MCP server.

**Why a hierarchy instead of bare ``Exception``?**

Imagine you're a war photographer and your camera jams.  You need to know
*instantly* whether it's a dead battery (fixable in the field), a cracked
lens (mission-aborted), or a corrupt memory card (data lost).  A single
generic "camera error" tells you nothing.

The same principle applies here.  Each exception class maps to a specific
failure mode so that the MCP tool layer can translate it into a clear,
LLM-readable message — not a raw Python traceback that confuses the model.
"""


class DocmostError(Exception):
    """Base exception for all Docmost-related errors.

    Every custom exception in this module inherits from ``DocmostError``,
    so callers can catch the entire family with a single ``except`` clause
    when they don't need fine-grained handling.
    """


class DocmostConfigError(DocmostError):
    """Raised when required configuration is missing or invalid.

    Common triggers:
    - ``DOCMOST_BASE_URL`` not set
    - Neither ``DOCMOST_API_TOKEN`` nor ``DOCMOST_EMAIL``/``DOCMOST_PASSWORD`` provided
    """


class DocmostAuthError(DocmostError):
    """Raised on authentication or authorisation failures (HTTP 401 / 403).

    This signals that the credentials are invalid, expired, or lack the
    required permissions for the requested operation.
    """


class DocmostNotFoundError(DocmostError):
    """Raised when the requested resource does not exist (HTTP 404).

    Examples: page not found, space not found, comment not found.
    """


class DocmostValidationError(DocmostError):
    """Raised when the Docmost API rejects a request due to validation (HTTP 400).

    Examples: missing required field, slug already exists, invalid format.
    """


class DocmostAPIError(DocmostError):
    """Raised for unexpected API errors (HTTP 5xx or non-standard responses).

    Carries the raw ``status_code`` and ``response_text`` so the tool layer
    can surface useful debugging context to the LLM.
    """

    def __init__(self, message: str, status_code: int, response_text: str = "") -> None:
        self.status_code: int = status_code
        self.response_text: str = response_text
        super().__init__(message)


class DocmostConnectionError(DocmostError):
    """Raised when the Docmost instance is unreachable.

    Network timeouts, DNS failures, and connection refused errors all
    get wrapped into this single class so the LLM receives a clear
    "server is down" message instead of a low-level socket traceback.
    """

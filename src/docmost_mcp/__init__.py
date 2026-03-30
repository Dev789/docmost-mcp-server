"""
docmost_mcp — A Model Context Protocol server for Docmost.

This package exposes Docmost wiki operations (search, page CRUD, space
management) as MCP tools that any LLM client can invoke.

Typical usage via the CLI entry-point::

    $ docmost-mcp

Or as a Python module::

    $ python -m docmost_mcp
"""

__version__: str = "1.1.1"
__all__: list[str] = ["__version__"]

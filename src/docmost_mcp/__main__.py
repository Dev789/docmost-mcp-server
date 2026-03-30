"""
Entry-point for ``python -m docmost_mcp`` and the ``docmost-mcp`` console script.

This module wires the three layers together — config → client → server —
and starts the MCP transport.  Think of it as opening the gallery door:
everything behind it has already been hung on the walls.
"""

from docmost_mcp.server import main


if __name__ == "__main__":
    main()

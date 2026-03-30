# Docmost MCP Server

An implementation of the [Model Context Protocol (MCP)](https://modelcontextprotocol.io) that allows LLM-based tools (like Claude, Cursor, or Windsurf) to interact with a [Docmost](https://docmost.com) wiki.

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/docmost-mcp.svg)](https://pypi.org/project/docmost-mcp/)

## Features

The server enables the following documentation management capabilities:

### Space Management
*   **Space Discovery**: List and browse all accessible spaces where teams and projects store their documentation.
*   **Space Details**: Retrieve comprehensive information about specific spaces, including member counts and user permissions.

### Page Discovery
*   **Global Search**: Perform full-text searches across all page titles and content in the workspace.
*   **Hierarchical Navigation**: Browse pages in a structured sidebar format, supporting both root-level and nested child pages.

### Content & Metadata
*   **Reading Content**: Retrieve full page details, including content formatted for modern web editors.
*   **Importing & Creating**: Seamlessly create new pages or update existing ones by importing Markdown content.
*   **Metadata Management**: Manage page titles and icons to keep documentation organized and visually distinct.
*   **Page Lifecycle**: Support for creating blank page skeletons and permanently deleting or trashing unwanted content.


## Integration with MCP Clients

Add the server to your `mcpServers` configuration:

```json
{
  "mcpServers": {
    "docmost": {
      "command": "docmost-mcp",
      "env": {
        "DOCMOST_BASE_URL": "https://your-docmost-url.com",
        "DOCMOST_API_TOKEN": "your-api-token"
      }
    }
  }
}
```

> **Note:** If `docmost-mcp` is not in your system PATH, use the full path to the executable (e.g., the output of `where docmost-mcp` on Windows or `which docmost-mcp` on Linux).

## Technical Details

*   **Architecture**: Built with `FastMCP` for the server layer and `httpx` for asynchronous API communication.
*   **Validation**: Uses Pydantic for environment variable validation, ensuring failures happen at startup if the configuration is invalid.
*   **Auth Lifecycle**: Automatically manages session persistence for Community Edition and token-based authentication for Enterprise.
*   **Error Handling**: Specifically catches API errors (404s, 401s) and returns human-readable summaries to the LLM instead of raw crash data.

## Development

```bash
# Clone and setup
git clone https://github.com/Dev789/docmost-mcp-server.git
cd docmost-mcp-server
python -m venv venv
source venv/bin/activate  # venv\Scripts\activate on Windows

# Editable install
pip install -e .
```

## License
[MIT](LICENSE)

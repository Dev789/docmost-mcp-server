# 📚 Docmost MCP Server

A **Model Context Protocol (MCP)** server that connects any LLM client to your [Docmost](https://docmost.com) wiki. Search, read, create, update, and delete documentation pages — all through natural language.

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/docmost-mcp.svg)](https://pypi.org/project/docmost-mcp/)

---

## ✨ Features

| Tool | Description |
|---|---|
| `search_docmost` | Full-text search with offset pagination |
| `get_page` | Read page data (returns ProseMirror JSON) |
| `create_page` | Create a blank page skeleton (metadata only) |
| `update_page` | Update page title or icon (metadata only) |
| `delete_page` | Soft-delete or permanently remove a page |
| `list_spaces` | List all accessible spaces with pagination |
| `get_space_info` | Get space details and permissions |
| `list_space_pages` | Browse the page hierarchy in a space |
| `import_page` | Import Markdown or replace page content (Recommended) |

---

## 🚀 Quick Start

### 1. Install

```bash
pip install docmost-mcp
```

### 2. Configure

Create a `.env` file (or set environment variables):

**Community Edition** (email/password login):
```env
DOCMOST_BASE_URL=https://docmost.example.com
DOCMOST_EMAIL=your@email.com
DOCMOST_PASSWORD=your-password
```

**Enterprise / Business Edition** (API token):
```env
DOCMOST_BASE_URL=https://docmost.example.com
DOCMOST_API_TOKEN=dk_live_xxxxxxxxxxxxx
```

### 3. Run

```bash
docmost-mcp
```

Or as a Python module:

```bash
python -m docmost_mcp
```

---

## 🔌 Integration with MCP Clients

### Claude Desktop / Cursor / Windsurf

Add this to your MCP client configuration:

```json
{
  "mcpServers": {
    "docmost": {
      "command": "docmost-mcp",
      "env": {
        "DOCMOST_BASE_URL": "https://docmost.example.com",
        "DOCMOST_API_TOKEN": "your-api-token"
      }
    }
  }
}
```

> **Tip:** If you installed with `pip`, use the full path to the `docmost-mcp` executable. Find it with: `which docmost-mcp` (macOS/Linux) or `where docmost-mcp` (Windows).

---

## 🛠️ Usage Guidelines

### Creating Pages with Content
Docmost v1 REST API separates metadata from content. To create a page with initial content:
1. Call `create_page` to initialize the skeleton and get a `page_id`.
2. Call `import_page` providing the `page_id` and your Markdown `content`.

*Alternatively*, use `import_page` directly to create a new page from Markdown if you don't need to specify an icon or parent first.

### Updating Content
The `update_page` tool is for metadata (title/icon) only. To update or replace the content of an existing page, use `import_page` with the target `page_id`.

---

## 🏗️ Architecture

```
src/docmost_mcp/
├── __init__.py         # Package metadata and version
├── __main__.py         # CLI entry point
├── config.py           # Environment validation (Pydantic BaseSettings)
├── exceptions.py       # Custom exception hierarchy
├── client.py           # Async Docmost API client (httpx)
└── server.py           # MCP tool definitions (FastMCP)
```

### Design Principles

1. **Fail Fast** — Configuration is validated at startup. Missing env vars crash immediately with a clear error, not mid-request.
2. **One Client, Many Tools** — A single `DocmostClient` with connection pooling handles all API calls. No per-request client creation.
3. **Typed Exceptions** — Every failure mode has its own exception class (`DocmostAuthError`, `DocmostNotFoundError`, etc.) for precise error messages.
4. **LLM-Friendly Errors** — MCP tools catch exceptions and return descriptive strings, never raw tracebacks.
5. **Dual Auth** — Supports both API token (Enterprise) and email/password login (Community) with automatic session refresh.

---

## 🔐 Authentication

### Community Edition

Uses `POST /api/auth/login` to obtain a session cookie. The server automatically re-authenticates on 401 (session expired).

Required env vars: `DOCMOST_BASE_URL`, `DOCMOST_EMAIL`, `DOCMOST_PASSWORD`

### Enterprise / Business Edition

Uses `Authorization: Bearer <token>` header. Generate an API token from your Docmost admin panel.

Required env vars: `DOCMOST_BASE_URL`, `DOCMOST_API_TOKEN`

> If **both** are configured, the API token takes precedence (no login round-trip needed).

---

## 🛠️ Development

```bash
# Clone the repo
git clone https://github.com/Dev789/docmost-mcp-server.git
cd docmost-mcp-server

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install in editable mode
pip install -e .

# Run
docmost-mcp
```

---

## 📄 License

[MIT](LICENSE) — free to use, modify, and distribute.

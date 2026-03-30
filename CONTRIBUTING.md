# Contributing to Docmost MCP Server

First off, thank you for considering contributing to the Docmost MCP Server! It's people like you that make the open-source community such a great place.

## How Can I Contribute?

### Reporting Bugs
- Before creating a bug report, please check that it hasn't already been reported.
- Use a clear and descriptive title for the issue.
- Describe the exact steps which reproduce the problem in as many details as possible.

### Suggesting Enhancements
- Check if there's already a similar idea in the issues.
- Explain why this enhancement would be useful to most users.

### Pull Requests
- Fork the repository.
- Create a new branch for your feature or bug fix.
- Ensure your code follows the existing style (type hints are encouraged!).
- Add tests if possible.
- Submit a pull request.

## Local Development Setup

1. **Clone the repo**:
   ```bash
   git clone https://github.com/Dev789/docmost-mcp-server.git
   cd docmost-mcp-server
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **Install in editable mode with dev dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```
   *(Note: Add `pytest` to your project dev dependencies if you plan to run tests).*

4. **Run tests**:
   ```bash
   pytest
   ```

## License
By contributing, you agree that your contributions will be licensed under its [MIT License](LICENSE).

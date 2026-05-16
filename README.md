# Review Mode MCP Server
[![Version](https://img.shields.io/pypi/v/review-mode-mcp.svg?maxAge=3600)](https://pypi.org/project/review-mode-mcp/)
[![Downloads](https://pepy.tech/badge/review-mode-mcp)](https://pepy.tech/project/review-mode-mcp)

MCP server for **[Review Mode](https://marketplace.visualstudio.com/items?itemName=aurelio-amerio.review-mode)** — manage review annotations from any AI agent.

For full documentation, see the [Review Mode GitHub page](https://github.com/aurelio-amerio/review-mode).

## Installation

```bash
# Install globally
uv tool install review-mode-mcp

# Or run directly (no install needed)
uvx review-mode-mcp
```

## MCP Configuration

Add to your MCP client config:

```json
{
  "mcpServers": {
    "review-mode-mcp": {
      "command": "review-mode-mcp"
    }
  }
}
```

## Tools

| Tool | Description |
|------|-------------|
| `open_review` | Open a file in Review Mode inside the editor |
| `list_reviewed_files` | List all files with reviews in the workspace |
| `get_review_summary` | Get revision count and comment status counts for a file |
| `get_annotations` | Get the full annotation array from a file's latest revision |
| `update_annotation` | Update status and/or add a reply to annotations |
| `create_annotation` | Create a new annotation on a specific line |

## Requirements

- Python 3.10+
- [Review Mode VS Code extension](https://marketplace.visualstudio.com/items?itemName=aurelio-amerio.review-mode) (for `open_review` and UI)

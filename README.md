# Review Mode MCP Server
[![Version](https://img.shields.io/pypi/v/review-mode-mcp.svg?maxAge=3600)](https://pypi.org/project/review-mode-mcp/)
[![Downloads](https://pepy.tech/badge/review-mode-mcp)](https://pepy.tech/project/review-mode-mcp)

MCP server for **[Review Mode](https://marketplace.visualstudio.com/items?itemName=aurelio-amerio.review-mode)** — manage review annotations from any AI agent.

Instead of loading skill files, running CLI scripts, or understanding JSON formats, any MCP-capable agent gets 6 structured tools to work with review annotations.

## Installation

```bash

# Install globally
uv tool install review-mode-mcp

# Or run directly (no install needed)
uvx review-mode-mcp
```

## MCP Configuration

Add to your MCP client config (Claude Code, Cline, Cursor, Windsurf, Antigravity, etc.):

```json
{
  "mcpServers": {
    "review-mode-mcp": {
      "command": "review-mode-mcp"
    }
  }
}
```

### CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `--revisions-dir` | `.revisions` | Name of the revisions directory |

## Tools

| Tool | Description |
|------|-------------|
| `open_review` | Open a file in Review Mode inside the editor |
| `list_reviewed_files` | List all files with reviews in the workspace |
| `get_review_summary` | Get revision count and comment status counts for a file |
| `get_annotations` | Get the full annotation array from a file's latest revision |
| `update_annotation` | Update status and/or add a reply to annotations |
| `create_annotation` | Create a new annotation on a specific line |

## How It Works

The server reads and writes the `.revisions/` directory — the same files the VS Code extension watches. When the server modifies annotations, the extension detects the filesystem changes and updates its UI automatically.

```
.revisions/
└── docs_plans_my-plan_md/    # normalized path
    ├── revisions.json         # revision index
    ├── my-plan.rev0.md        # snapshot
    ├── rev0.json              # annotations for rev0
    ├── my-plan.rev1.md
    └── rev1.json
```

## Requirements

- Python 3.10+
- [Review Mode VS Code extension](https://marketplace.visualstudio.com/items?itemName=aurelio-amerio.review-mode) (for `open_review` and UI)

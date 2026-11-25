---
title: How to build a remote MCP server in Python for Claude
description: A step-by-step guide to a remote Model Context Protocol server in Python with the official SDK and streamable HTTP, connected to Claude Code and Claude Desktop, plus what you need before putting it on the internet.
kit: mcp
date: 2026-11-25
---

The Model Context Protocol (MCP) is how you give Claude access to your own data and systems: your database, your CRM, your internal API. You write a small server that exposes **tools**, and Claude Code, Claude Desktop or the Claude API connect to it and call those tools when they need them.

This guide builds a **remote** MCP server in Python, the kind that runs over HTTP and that several people or apps can connect to, not only a local script. It uses the official MCP Python SDK and the streamable HTTP transport. The whole server is about 150 lines.

The finished code is free on GitHub: [claude-mcp-server-starter](https://github.com/{{owner}}/claude-mcp-server-starter).

## Local (stdio) vs remote (HTTP) servers

- A **stdio** server is started by the client as a child process. Fine for a personal tool on your laptop.
- A **remote** server listens on a URL like `https://mcp.example.com/mcp`. Teammates, a Claude API app and Claude Code on several machines can all use the same server, and it can sit next to the database it needs.

Our server supports both: `python server.py` for HTTP, `python server.py --stdio` for stdio.

## Step 1: install

```bash
pip install "mcp==2.3.0" uvicorn
```

## Step 2: create the server and a tool

```python
from typing import Annotated
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

server = MCPServer("notes", instructions="Tools for the user's personal notes.")
READ = ToolAnnotations(read_only_hint=True, idempotent_hint=True)

@server.tool(title="Search notes", annotations=READ)
def search_notes(query: Annotated[str, Field(description="Words to look for in titles and text")]) -> list[dict]:
    """Find notes whose title or text contains every word in the query (case-insensitive)."""
    words = query.lower().split()
    return [summary(n) for n in load() if all(w in f"{n['title']} {n['text']}".lower() for w in words)]
```

The SDK turns the type hints, `Field` descriptions and docstring into the tool's JSON schema. **That text is all Claude knows about your tool**, so write it for Claude: what it returns and when to use it.

`read_only_hint` tells clients this tool only looks things up. Clients can use that to skip confirmation prompts for safe calls and ask before changes.

## Step 3: errors Claude can recover from

```python
@server.tool(title="Read a note", annotations=READ)
def get_note(note_id: int) -> dict:
    """Return one note in full."""
    for n in load():
        if n["id"] == note_id:
            return n
    raise ToolError(f"No note with id {note_id}. Use search_notes or list_notes to find ids.")
```

A stack trace teaches Claude nothing. A sentence that says what went wrong and what to do next lets it fix its own mistake in the next call.

## Step 4: serve it over streamable HTTP

```python
app = server.streamable_http_app(stateless_http=True, json_response=True, host="127.0.0.1")
uvicorn.run(app, host="127.0.0.1", port=8000)
```

**Stateless mode** means every request stands alone. You can restart, redeploy or run several workers, and connected clients never notice. For tool servers that don't push notifications, it's the simplest choice.

## Step 5: connect Claude

Claude Code:

```bash
claude mcp add --transport http notes http://localhost:8000/mcp
```

Then ask "What notes do I have about goals?" and watch Claude call `search_notes` and `get_note`.

Claude Desktop (local, stdio), in `claude_desktop_config.json`:

```json
{"mcpServers": {"notes": {"command": "/path/to/.venv/bin/python", "args": ["/path/to/server.py", "--stdio"]}}}
```

## Before you put it on the internet

The server above has **no authentication**. On a public URL, anyone who finds it can call your tools. A production MCP server needs:

1. **API keys per person or app**, stored hashed, shown once, revocable one at a time.
2. **Scopes.** A key made for reading must never be able to change data, however Claude is prompted. Enforce it in code on every tool call.
3. **Rules in code, not in the prompt.** For example, an order can move from paid to shipped but never from cancelled to paid.
4. **Rate limits per key**, so a runaway agent loop can't hammer your database or your API bill.
5. **An audit log** of every call: which key, which tool, the arguments, success or error, duration.
6. **DNS rebinding protection** (only answer for your own host name) and **HTTPS**.
7. A way to **wrap an existing REST API** without giving Claude your API token.
8. A repeatable deploy, backups, and a check that the server works end to end after each deploy.

## Get the full kit

The **[MCP Server Starter Kit]({{kit_url}})** ({{kit_price}}) is all of that, built and tested: API keys with read and write scopes, a rate limit and audit log on every tool, a usage report, 8 example tools over a demo shop database, a template for wrapping any REST API, Docker with Caddy HTTPS, and a one-command AWS deploy that prints your URL and first key. It includes guides for Claude Code, Claude Desktop and the Claude API MCP connector.

Or start free with the [lite server on GitHub](https://github.com/{{owner}}/claude-mcp-server-starter).

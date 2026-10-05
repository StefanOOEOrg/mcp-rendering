"""Shared MCPServer instance that tool modules register themselves against."""
from mcp.server.mcpserver import MCPServer

server = MCPServer(name="mcp-rendering")

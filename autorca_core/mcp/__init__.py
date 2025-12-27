"""
MCP server module for AutoRCA-Core.

Exposes AutoRCA-Core functionality as MCP tools for integration with
Claude Desktop, Claude Code, and other MCP-compatible clients.
"""

from autorca_core.mcp.server import create_mcp_server, start_mcp_server

__all__ = ["create_mcp_server", "start_mcp_server"]


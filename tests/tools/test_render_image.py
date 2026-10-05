"""Tests for the render_image tool: success message and ToolError mapping."""
import httpx2
import pytest
from mcp.server.mcpserver.exceptions import ToolError

from tools.render_image import render_image


def test_render_image_confirms_delivery(http):
    """On success the agent only gets a short confirmation."""
    assert render_image("  a lighthouse at dawn ", "Leuchtturm") == "Bild per Telegram gesendet."
    assert http.calls[0][1]["json"]["prompt"] == "a lighthouse at dawn"


def test_render_image_rejects_empty_text(http):
    """An empty prompt never reaches the backend."""
    with pytest.raises(ToolError, match="leer"):
        render_image("   ")
    assert not http.calls


def test_render_image_turns_backend_errors_into_tool_errors(http):
    """Network errors surface as ToolError so the agent can report them."""
    http.backend = httpx2.ConnectError("connection refused")
    with pytest.raises(ToolError, match="ConnectError"):
        render_image("a fox")

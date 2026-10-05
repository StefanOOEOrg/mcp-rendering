"""render_image: draw a picture on the GX10 and send it to the user's Telegram chat."""
import httpx2
from mcp.server.mcpserver.exceptions import ToolError

from renderer import RenderError, render_and_send
from server_instance import server


@server.tool()
def render_image(text: str, caption: str = "") -> str:
    """Render an image locally on the GX10 and send it straight to Stefan's Telegram chat.

    Use it to visualise something, e.g. "fass unsere Unterhaltung als Bild zusammen".

    - text: the image prompt in ENGLISH, concrete and visual: subject, composition,
      style, lighting, colours (e.g. "flat vector illustration, isometric, pastel colors").
      Image models cannot render longer text: turn topics into symbols/scenes, at most
      1-3 short words inside the image.
    - caption: optional German caption (max. 1024 characters); this is where the actual
      summary goes.

    The image is delivered by this tool; afterwards only confirm briefly in the chat and
    do not repeat the caption. Takes about 5-60 seconds.
    """
    if not text.strip():
        raise ToolError("text ist leer.")
    try:
        render_and_send(text.strip(), caption.strip())
    except (RenderError, httpx2.HTTPError) as exc:
        raise ToolError(f"{type(exc).__name__}: {exc}") from exc
    return "Bild per Telegram gesendet."

"""Render an image on the GX10 and deliver it to Telegram without keeping it.

The PNG is written to a temp file only for the duration of the Telegram upload
and removed in a finally block, whether the upload succeeds or not. Leftovers
from a crash between writing and removing are swept by cleanup_orphans().
"""
import logging
import os
import tempfile
import time
from pathlib import Path

import httpx2

import config

log = logging.getLogger(__name__)

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class RenderError(RuntimeError):
    """Rendering or delivery failed; the message is safe to show to the agent."""


def generate_image(prompt: str, width: int = 1024, height: int = 1024) -> Path:
    """Render prompt on the backend and return the path of a temp PNG.

    The caller MUST remove the file right after delivering it (try/finally).
    Timeouts, connection errors and non-200 responses propagate; in that case
    no file is created.
    """
    resp = httpx2.post(
        f"{config.RENDER_BACKEND}/generate",
        json={"prompt": prompt, "width": width, "height": height},
        timeout=httpx2.Timeout(config.RENDER_TIMEOUT, connect=10),
    )
    if resp.status_code != 200:
        raise RenderError(f"Backend antwortete mit HTTP {resp.status_code}: {resp.text[:200]}")
    if not resp.content.startswith(PNG_SIGNATURE):
        raise RenderError(f"Backend lieferte kein PNG ({resp.headers.get('content-type')})")

    handle, name = tempfile.mkstemp(prefix=config.TMP_PREFIX, suffix=".png", dir=config.TMP_DIR)
    try:
        with os.fdopen(handle, "wb") as out:
            out.write(resp.content)
    except BaseException:
        os.remove(name)
        raise
    return Path(name)


def send_photo(path: Path, caption: str = "") -> None:
    """Upload path as a photo to the configured Telegram chat."""
    token = config.TELEGRAM_BOT_TOKEN
    if not token or not config.TELEGRAM_CHAT_ID:
        raise RenderError("TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID sind nicht konfiguriert.")
    data = {"chat_id": config.TELEGRAM_CHAT_ID}
    if caption:
        data["caption"] = caption[:1024]
    if config.TELEGRAM_THREAD_ID:
        data["message_thread_id"] = config.TELEGRAM_THREAD_ID
    try:
        with open(path, "rb") as photo:
            resp = httpx2.post(
                f"https://api.telegram.org/bot{token}/sendPhoto",
                data=data,
                files={"photo": (path.name, photo, "image/png")},
                timeout=config.TELEGRAM_TIMEOUT,
            )
    except httpx2.HTTPError as exc:
        # httpx names the request URL, which contains the bot token
        raise RenderError(f"Telegram sendPhoto: {str(exc).replace(token, '***')}") from None
    if resp.status_code != 200:
        try:
            desc = resp.json().get("description", "")
        except ValueError:
            desc = ""
        raise RenderError(f"Telegram sendPhoto: HTTP {resp.status_code} {desc}".strip())


def cleanup_orphans(max_age: int | None = None) -> list[Path]:
    """Remove this server's temp PNGs that are older than max_age seconds."""
    max_age = config.ORPHAN_MAX_AGE if max_age is None else max_age
    cutoff = time.time() - max_age
    removed = []
    for path in config.TMP_DIR.glob(f"{config.TMP_PREFIX}*.png"):
        try:
            if path.is_file() and not path.is_symlink() and path.stat().st_mtime < cutoff:
                path.unlink()
                removed.append(path)
        except FileNotFoundError:
            pass
    if removed:
        log.warning("Removed %d orphaned temp PNG(s)", len(removed))
    return removed


def render_and_send(prompt: str, caption: str = "", width: int = 1024, height: int = 1024) -> None:
    """Render, deliver to Telegram and remove the temp file in every case."""
    cleanup_orphans()
    path = generate_image(prompt, width, height)
    try:
        send_photo(path, caption)
    finally:
        os.remove(path)

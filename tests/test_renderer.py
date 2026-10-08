"""Tests for renderer: temp file lifecycle, error paths and the orphan sweep."""
import os
import time

import httpx2
import pytest

import config
import renderer
from tests.conftest import TOKEN


def temp_pngs(tmp):
    """All temp PNGs this server could have left behind."""
    return list(tmp.glob("mcp-rendering-*.png"))


def test_render_and_send_uploads_the_png_and_removes_it(http, isolated_config):
    """The file exists during the upload and is gone afterwards."""
    renderer.render_and_send("a fox", "Ein Fuchs")
    assert len(http.files_seen_during_upload) == 1
    assert not temp_pngs(isolated_config)
    backend_url, backend_kwargs = http.calls[0]
    assert backend_url.endswith("/generate")
    assert backend_kwargs["json"] == {"prompt": "a fox", **config.RENDER_DEFAULTS}
    assert http.calls[1][1]["data"] == {"chat_id": "42", "caption": "Ein Fuchs"}


def test_failed_telegram_upload_still_removes_the_file(http, isolated_config):
    """A Telegram error is reported and leaves no file behind."""
    http.telegram = httpx2.Response(400, json={"ok": False, "description": "chat not found"})
    with pytest.raises(renderer.RenderError, match="chat not found"):
        renderer.render_and_send("a fox")
    assert not temp_pngs(isolated_config)


def test_telegram_network_error_hides_the_bot_token(http, isolated_config):
    """httpx puts the URL (with the token) into its message; it must be masked."""
    http.telegram = httpx2.ConnectError(
        f"cannot reach https://api.telegram.org/bot{TOKEN}/sendPhoto")
    with pytest.raises(renderer.RenderError) as exc:
        renderer.render_and_send("a fox")
    assert TOKEN not in str(exc.value)
    assert not temp_pngs(isolated_config)


@pytest.mark.parametrize("backend", [
    httpx2.ConnectError("connection refused"),
    httpx2.ReadTimeout("timed out"),
])
def test_backend_network_errors_propagate_without_a_file(http, isolated_config, backend):
    """Timeouts and refused connections pass through; nothing is written."""
    http.backend = backend
    with pytest.raises(type(backend)):
        renderer.generate_image("a fox")
    assert not temp_pngs(isolated_config)


@pytest.mark.parametrize("response, match", [
    (httpx2.Response(500, text="comfyui down"), "HTTP 500"),
    (httpx2.Response(200, content=b"<html>", headers={"content-type": "text/html"}), "kein PNG"),
])
def test_bad_backend_responses_raise_without_a_file(http, isolated_config, response, match):
    """Non-200 or non-PNG answers raise; nothing is written and nothing is sent."""
    http.backend = response
    with pytest.raises(renderer.RenderError, match=match):
        renderer.render_and_send("a fox")
    assert not temp_pngs(isolated_config)
    assert not http.files_seen_during_upload


@pytest.mark.usefixtures("http")
def test_missing_telegram_config_is_reported(isolated_config, monkeypatch):
    """Without a bot token the render is not delivered and the file is removed."""
    monkeypatch.setattr(renderer.config, "TELEGRAM_BOT_TOKEN", "")
    with pytest.raises(renderer.RenderError, match="nicht konfiguriert"):
        renderer.render_and_send("a fox")
    assert not temp_pngs(isolated_config)


def test_cleanup_removes_only_old_files_with_the_prefix(isolated_config):
    """Fresh files of a running render and foreign files survive the sweep."""
    old = isolated_config / "mcp-rendering-old.png"
    fresh = isolated_config / "mcp-rendering-fresh.png"
    foreign = isolated_config / "other-old.png"
    for path in (old, fresh, foreign):
        path.write_bytes(b"x")
    past = time.time() - 3600
    os.utime(old, (past, past))
    os.utime(foreign, (past, past))
    assert renderer.cleanup_orphans() == [old]
    assert fresh.exists() and foreign.exists()


def test_overrides_replace_single_defaults_and_none_keeps_them():
    """Only non-None overrides change the request; everything else stays default."""
    payload = renderer.build_payload("a fox", {"model": "qwen", "width": 1344, "seed": 7,
                                               "hires": False, "steps": None})
    assert payload["model"] == "qwen" and payload["width"] == 1344 and payload["seed"] == 7
    assert payload["hires"] is False
    assert payload["steps"] == config.RENDER_DEFAULTS["steps"]
    assert payload["height"] == config.RENDER_DEFAULTS["height"]


def test_default_payload_leaves_seed_to_the_backend():
    """Without a seed the bridge picks a random one."""
    assert "seed" not in renderer.build_payload("a fox")

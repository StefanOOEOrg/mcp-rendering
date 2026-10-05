"""Shared fixtures: an isolated temp dir, fake Telegram settings and a fake HTTP layer."""
import httpx2
import pytest

import config
import renderer

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
TOKEN = "123456:SECRET-TOKEN"


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """Point temp files into tmp_path and configure a fake bot so no test touches real data."""
    monkeypatch.setattr(config, "TMP_DIR", tmp_path)
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", TOKEN)
    monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "42")
    monkeypatch.setattr(config, "TELEGRAM_THREAD_ID", "")
    return tmp_path


class FakeHttp:
    """Stands in for httpx2.post: answers backend and Telegram calls, records what it saw."""

    def __init__(self):
        self.backend = httpx2.Response(200, content=PNG, headers={"content-type": "image/png"})
        self.telegram = httpx2.Response(200, json={"ok": True})
        self.calls = []
        self.files_seen_during_upload = []

    def __call__(self, url, **kwargs):
        self.calls.append((url, kwargs))
        result = self.telegram if "api.telegram.org" in url else self.backend
        if "api.telegram.org" in url:
            self.files_seen_during_upload.append(kwargs["files"]["photo"][1].name)
        if isinstance(result, Exception):
            raise result
        return result


@pytest.fixture
def http(monkeypatch):
    """Replace every outgoing HTTP call with a FakeHttp instance."""
    fake = FakeHttp()
    monkeypatch.setattr(renderer.httpx2, "post", fake)
    return fake

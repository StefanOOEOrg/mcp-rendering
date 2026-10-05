"""Central configuration for the mcp-rendering project.

Environment variables are read once here so the rest of the codebase can rely
on validated, well-known settings instead of scattering os.getenv() calls
across modules.
"""
import os
import tempfile
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# === LOGGING ===
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# === RENDER BACKEND (ComfyUI wrapper on the GX10) ===
RENDER_BACKEND = os.getenv("RENDER_BACKEND", "http://192.168.178.87:8002").rstrip("/")
# Generation usually takes 5-60 s; generous so a busy GPU does not fail the call.
RENDER_TIMEOUT = float(os.getenv("RENDER_TIMEOUT", "300"))

# === TELEGRAM (the calling Hermes profile's own bot) ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_THREAD_ID = os.getenv("TELEGRAM_THREAD_ID", "")
TELEGRAM_TIMEOUT = float(os.getenv("TELEGRAM_TIMEOUT", "60"))

# === TEMP FILES ===
# A rendered PNG only exists while it is being delivered. Files with this prefix
# that are older than ORPHAN_MAX_AGE seconds are leftovers of a crash and get swept.
TMP_DIR = Path(os.getenv("RENDER_TMP_DIR", tempfile.gettempdir()))
TMP_PREFIX = "mcp-rendering-"
ORPHAN_MAX_AGE = int(os.getenv("RENDER_ORPHAN_MAX_AGE", "600"))

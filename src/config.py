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
# The default settings below (flux-lora, hires + face/hand fix) take ~2-3 min per image,
# a model switch on the GX10 adds to that; generous so a busy GPU does not fail the call.
RENDER_TIMEOUT = float(os.getenv("RENDER_TIMEOUT", "600"))

# Request fields sent with every render unless the caller overrides them (bridge API of
# gb10-rendering, see llm repo comfyui/bridge.py). Fields left out here (seed, cfg) are chosen
# by the bridge: random seed, cfg 1 (or 3 when a negative prompt is given).
RENDER_DEFAULTS = {
    "model": "flux-lora",       # "qwen" | "flux" | "flux-lora" (+ Heartsync LoRA)
    "preset": "realistic",      # "realistic" | "final" | "fast" | "anime"
    "width": 1024,
    "height": 1024,
    "steps": 32,
    "guidance": 1.85,           # FLUX prompt adherence
    "sampler": "dpmpp_2m",
    "scheduler": "beta",
    "hires": {"scale": 1.5, "denoise": 0.4, "steps": 25},
    "face_fix": {"steps": 25, "denoise": 0.4},
    "hand_fix": True,
    "negative": "",             # non-empty switches to real CFG 3 (~1.5x time)
    "lora_strength": 0.2,       # Heartsync LoRA 0-2, only used with flux-lora
    "lora2": 1.33,              # second LoRA (Lustly, anatomy) 0-2 / true / false
}

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

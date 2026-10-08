"""render_image: draw a picture on the GX10 and send it to the user's Telegram chat."""
from typing import Annotated, Literal

import httpx2
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from renderer import RenderError, render_and_send
from server_instance import server

# Every render setting is optional: None keeps the default from config.RENDER_DEFAULTS
# (flux-lora, preset realistic, 1024x1024, 32 steps, guidance 1.85, hires + face/hand fix).
Stage = bool | dict


def _doc(text: str):
    """Field with a description for the tool schema (keeps the signature readable)."""
    return Field(description=text)


@server.tool()
def render_image(  # pylint: disable=too-many-arguments,too-many-locals
    text: Annotated[str, _doc("Image prompt in ENGLISH, concrete and visual.")],
    caption: Annotated[str, _doc("Optional German caption, max. 1024 characters.")] = "",
    *,
    model: Annotated[Literal["qwen", "flux", "flux-lora"] | None,
                     _doc("Render engine; default flux-lora.")] = None,
    preset: Annotated[Literal["realistic", "final", "fast", "anime"] | None,
                      _doc("Base settings; default realistic. Explicit fields "
                           "below win over the preset.")] = None,
    width: Annotated[int | None, _doc("Width in px (multiple of 64); default 1024.")] = None,
    height: Annotated[int | None, _doc("Height in px (multiple of 64); default 1024.")] = None,
    seed: Annotated[int | None, _doc("Fixed number = reproducible; default random.")] = None,
    steps: Annotated[int | None, _doc("Sampling steps (flux); default 32.")] = None,
    guidance: Annotated[float | None, _doc("FLUX prompt adherence; default 1.85.")] = None,
    sampler: Annotated[str | None, _doc("Sampler (flux); default dpmpp_2m.")] = None,
    scheduler: Annotated[str | None, _doc("Scheduler (flux); default beta.")] = None,
    hires: Annotated[Stage | None, _doc("Upscale pass: true/false or {scale, denoise, steps}; "
                                        "default on.")] = None,
    face_fix: Annotated[Stage | None, _doc("Face detailer: true/false or {steps, denoise}; "
                                           "default on.")] = None,
    hand_fix: Annotated[Stage | None, _doc("Hand detailer: true/false or "
                                           "{steps, denoise}; default on.")] = None,
    negative: Annotated[str | None, _doc("What must NOT appear; non-empty "
                                         "switches to real CFG (~1.5x time).")] = None,
    lora_strength: Annotated[float | None, _doc("Heartsync LoRA 0-2, only with "
                                                "flux-lora; default 0.2.")] = None,
    lora2: Annotated[float | bool | None, _doc("Second LoRA (anatomy) 0-2 or "
                                               "true/false; default 1.33.")] = None,
) -> str:
    """Render an image locally on the GX10 and send it straight to Stefan's Telegram chat.

    Use it to visualise something, e.g. "fass unsere Unterhaltung als Bild zusammen".
    Image models cannot render longer text: turn topics into symbols/scenes, at most
    1-3 short words inside the image; the actual summary goes into the caption.

    All settings are optional and well tuned by default -- only override them when the
    user asks for something specific (format, style, speed, a reproducible seed).
    The image is delivered by this tool; afterwards only confirm briefly in the chat and
    do not repeat the caption. Takes about 2-3 minutes with the default settings.
    """
    if not text.strip():
        raise ToolError("text ist leer.")
    overrides = {
        "model": model, "preset": preset, "width": width, "height": height, "seed": seed,
        "steps": steps, "guidance": guidance, "sampler": sampler, "scheduler": scheduler,
        "hires": hires, "face_fix": face_fix, "hand_fix": hand_fix, "negative": negative,
        "lora_strength": lora_strength, "lora2": lora2,
    }
    try:
        render_and_send(text.strip(), caption.strip(), overrides)
    except (RenderError, httpx2.HTTPError) as exc:
        raise ToolError(f"{type(exc).__name__}: {exc}") from exc
    return "Bild per Telegram gesendet."

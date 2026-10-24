# Changelog

## 0.1.0 — 2026-10-24

Initial release.

- `render_image(text, caption="", **settings)` — renders a prompt on the ComfyUI wrapper and delivers
  the PNG straight to a Telegram chat, with an optional caption (max. 1024 characters).
- Every render setting can be overridden per call (`model`, `preset`, `width`, `height`, `seed`,
  `steps`, `guidance`, `sampler`, `scheduler`, `hires`, `face_fix`, `hand_fix`, `negative`,
  `lora_strength`, `lora2`); the defaults live in `src/config.py` and are documented in the README.
- No image is kept: the PNG is a temp file only for the upload window and is removed in a `finally`
  block. Orphans from a crash are swept before every render and by `src/cleanup.py`.
- Errors are `ToolError`s with readable text (backend down, timeout, invalid setting, Telegram
  failure); the bot token is masked in every message.
- Configuration via `.env` (`TELEGRAM_BOT_TOKEN`, `_CHAT_ID`, `_THREAD_ID`, `RENDER_BACKEND`,
  `RENDER_TIMEOUT`, `LOG_LEVEL`); `.env.template` ships the template.
- CI: pytest + pylint on Python 3.11 and 3.14.

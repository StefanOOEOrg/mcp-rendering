# MCP Server for image rendering (mcp-rendering)

[![CI](https://github.com/StefanOOEOrg/mcp-rendering/actions/workflows/ci.yml/badge.svg)](https://github.com/StefanOOEOrg/mcp-rendering/actions/workflows/ci.yml)

An MCP server with a single tool, `render_image`: it renders a picture on the LLM server (ComfyUI wrapper, `POST /generate` → PNG) and sends it straight to the user's Telegram chat. Typical use: the user asks for an image of the conversation so far — the agent turns the topics into an English image prompt and puts the actual summary into the caption.

**No image is kept.** The PNG is written to a temp file (`/tmp/mcp-rendering-*.png`) only for the duration of the Telegram upload and is removed in a `finally` block, also when the upload fails. There is no output directory and no history. Leftovers from a crash between writing and removing are swept before every render and by a systemd timer (files older than 10 minutes).

## Requirements

- **Python 3.11 or newer** (the CI runs 3.11 and 3.14).
- A reachable render backend: the ComfyUI wrapper on the LLM server (`POST /generate` → PNG),
  configured via `RENDER_BACKEND`.
- A Telegram bot plus the chat id the picture should go to (`TELEGRAM_BOT_TOKEN`,
  `TELEGRAM_CHAT_ID`, optional `TELEGRAM_THREAD_ID`).

## Installation

```bash
git clone https://github.com/StefanOOEOrg/mcp-rendering.git
cd mcp-rendering
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
cp .env.template .env       # fill in the Telegram bot and RENDER_BACKEND
```

Then register it in your MCP client (see [Deployment (Hermes)](#deployment-hermes)) — note the long
tool timeout, a render takes minutes.

## Project Structure

```
mcp-rendering/
├── src/
│   ├── config.py            # Central config: env vars, read once
│   ├── server_instance.py   # Creates the shared MCPServer instance
│   ├── mcp_server.py        # Composition root: wires up the server + tools
│   ├── main.py              # Entry point (stdio)
│   ├── renderer.py          # Backend call, Telegram upload, temp file lifecycle, sweep
│   ├── cleanup.py           # CLI for the periodic orphan sweep
│   └── tools/
│       └── render_image.py
└── tests/
```

## Available Tools

| Tool | Description |
|------|-------------|
| `render_image(text, caption="", **settings)` | Renders `text` (English image prompt) and sends it as a photo to the configured Telegram chat with an optional `caption` (max. 1024 characters). Returns a short confirmation; errors (backend down, timeout, invalid setting, Telegram) are raised as `ToolError`. |

**Render settings:** every field of the render bridge can be overridden per call (`model`, `preset`, `width`, `height`, `seed`, `steps`, `guidance`, `sampler`, `scheduler`, `hires`, `face_fix`, `hand_fix`, `negative`, `lora_strength`, `lora2`). Anything not given uses `RENDER_DEFAULTS` in `src/config.py`:

```python
{"model": "flux-lora", "preset": "realistic", "width": 1024, "height": 1024,
 "steps": 32, "guidance": 1.85, "sampler": "dpmpp_2m", "scheduler": "beta",
 "hires": {"scale": 1.5, "denoise": 0.4, "steps": 25}, "face_fix": {"steps": 25, "denoise": 0.4},
 "hand_fix": True, "negative": "", "lora_strength": 0.2, "lora2": 1.33}
```
`seed` is left to the bridge (random). With these defaults a render takes ~2-3 minutes (output 1536×1536 after hires), so the server waits up to `RENDER_TIMEOUT` = 600 s and Hermes needs a longer MCP tool timeout (`timeout: 900` in the `mcp_servers` entry).

Error behaviour: timeouts, refused connections and non-200 / non-PNG answers of the backend create no file. The bot token is masked in every error message.

## Setup (development)

```bash
uv venv venv --python 3.12
uv pip install --python venv/bin/python -r requirements-dev.txt
cp .env.template .env        # fill in the bot token and chat id
venv/bin/python -m pytest
```

## Deployment (Hermes)

Install it with its own venv and `.env` (see `.env.template`).

Hermes registration (`mcp_servers` in the profile's `config.yaml`). Every profile sends through **its own** bot:

```yaml
mcp-rendering:
  command: /path/to/mcp-rendering/.venv/bin/python
  args: [/path/to/mcp-rendering/src/main.py]
  env:
    TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN}
    TELEGRAM_CHAT_ID: ${TELEGRAM_HOME_CHANNEL}
    TELEGRAM_THREAD_ID: ${TELEGRAM_HOME_CHANNEL_THREAD_ID}   # only where the profile has one
  timeout: 900   # a render with the default settings takes ~2-3 min (Hermes default: 300 s)
```

Orphan sweep (e.g. a systemd user timer every 10 minutes):

```ini
ExecStart=/path/to/mcp-rendering/.venv/bin/python /path/to/mcp-rendering/src/cleanup.py
```

## Scope / Limitations

- A single-user tool, not a service: it runs locally over stdio — no port of its own, no
  authentication, no multi-user support.
- It needs a working render backend and a Telegram bot; without them `render_image` fails with a
  readable `ToolError`.
- Renders are slow (minutes, see the defaults above) — the tool timeout in the MCP client has to be
  raised, otherwise the call is cut off while the backend still renders.
- Images are not stored: the PNG lives in a temp file only for the Telegram upload and is deleted
  afterwards. There is no gallery, no history and no way to re-send an old render.
- The bot token is masked in error messages, but it still lives in plain text in `.env` — keep that
  file out of the repo and out of logs.

## License

[MIT](LICENSE)

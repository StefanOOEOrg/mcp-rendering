# MCP Server for image rendering (mcp-rendering)

An MCP server with a single tool, `render_image`: it renders a picture on the GX10 (ComfyUI wrapper, `POST /generate` → PNG) and sends it straight to the user's Telegram chat. Typical use: "fass unsere Unterhaltung als Bild zusammen" — the agent turns the topics into an English image prompt and puts the actual summary into the caption.

**No image is kept.** The PNG is written to a temp file (`/tmp/mcp-rendering-*.png`) only for the duration of the Telegram upload and is removed in a `finally` block, also when the upload fails. There is no output directory and no history. Leftovers from a crash between writing and removing are swept before every render and by a systemd timer (files older than 10 minutes).

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
| `render_image(text, caption="")` | Renders `text` (English image prompt, 1024×1024) and sends it as a photo to the configured Telegram chat with an optional German `caption` (max. 1024 characters). Returns a short confirmation; errors (backend down, timeout, Telegram) are raised as `ToolError`. |

Error behaviour: timeouts, refused connections and non-200 / non-PNG answers of the backend create no file. The bot token is masked in every error message.

## Setup (development)

```bash
uv venv venv --python 3.12
uv pip install --python venv/bin/python -r requirements-dev.txt
cp .env.template .env        # fill in the bot token and chat id
venv/bin/python -m pytest
```

## Deployment (Hermes on the ThinkCentre)

This repo is a development repo only — nothing runs from it. Hermes runs the server from a read-only release built from a **committed** ref:

```bash
git commit …                                  # changes must be committed to be deployable
sudo hermes-deploy mcp-rendering --restart    # → /opt/hermes-apps/mcp-rendering/releases/<sha>, restarts the gateways
sudo hermes-deploy --rollback mcp-rendering   # back to the previous release
```

Hermes registration (`mcp_servers` in the profile's `config.yaml`, runs as user `hermes`). Every profile sends through **its own** bot:

```yaml
mcp-rendering:
  command: /opt/hermes-apps/mcp-rendering/current/.venv/bin/python
  args: [/opt/hermes-apps/mcp-rendering/current/src/main.py]
  env:
    TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN}
    TELEGRAM_CHAT_ID: ${TELEGRAM_HOME_CHANNEL}
    TELEGRAM_THREAD_ID: ${TELEGRAM_HOME_CHANNEL_THREAD_ID}   # only where the profile has one
```

Orphan sweep (user `hermes`, `~/.config/systemd/user/mcp-rendering-sweep.{service,timer}`, every 10 minutes):

```ini
ExecStart=/opt/hermes-apps/mcp-rendering/current/.venv/bin/python /opt/hermes-apps/mcp-rendering/current/src/cleanup.py
```

`hermes-deploy` and the overall layout are documented in the `tc-ops` repo.

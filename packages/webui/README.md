# comfyui-webui

Local web UI for the ComfyUI toolchain.

- **Generate** — every parametric workflow in `workflows/mcp/` becomes a form
  (built from its `.meta.json` schema): pick, fill, queue, watch progress,
  browse outputs.
- **Create** — clone an existing workflow, edit the JSON, validate it against
  the live install's node catalog, and register it; or queue a
  natural-language request for a Claude Code session to build with
  `/comfy-create-workflow` (the interactive bridge — requests land in
  `.omc/webui-requests/`).

## Run

```bash
pip install -e packages/webui
comfyui-webui            # http://127.0.0.1:5055
comfyui-webui --port 8080
```

Requires ComfyUI running (default `http://localhost:8188`, override with
`COMFYUI_URL`). Workflow directory follows `COMFY_MCP_WORKFLOW_DIR`.

## API

| Endpoint | Purpose |
|---|---|
| `GET /api/status` | ComfyUI connection, queue depth, workflow count |
| `GET /api/workflows` | catalog with parameter schemas |
| `POST /api/generate` | `{workflow_id, params}` → `{prompt_id}` |
| `GET /api/job/<id>` | status, progress, outputs (with `/api/view` URLs) |
| `GET /api/view?...` | proxies ComfyUI output files |
| `POST /api/upload` | multipart `image` → ComfyUI input name |
| `GET /api/author/workflow/<id>` | raw workflow + meta for cloning |
| `POST /api/author/validate` | `{workflow, meta?}` → errors/warnings |
| `POST /api/author/save` | validate-gated register of `{id, workflow, meta}` |
| `POST /api/author/request` | queue NL spec for Claude (`.omc/webui-requests/`) |
| `GET /api/author/requests` | list pending bridge requests |

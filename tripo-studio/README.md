# Tripo Studio via browser automation

Tripo has to be driven through **Tripo Studio in a browser** (no API). This folder holds the
pieces that let an agent (Claude, or later local Qwen) do that.

| File | What it is |
|---|---|
| `mcp-playwright.json` | MCP config for `@playwright/mcp@0.0.83`, driving real Chrome with the dedicated profile below. Load it with `claude --mcp-config tripo-studio/mcp-playwright.json` (it is not registered globally). |
| `chrome-profile/` | **Gitignored.** A separate Chrome profile holding the Tripo Studio login (cookies). Never commit or share it. Sign in once in the Chrome window this profile opens, then close the window. |
| `pw-out/` | **Gitignored.** Screenshots/downloads written by the Playwright MCP. |
| `enable_tripo.py` | Blender script: enables the `Tripo3d_Blender_Bridge` add-on for the session and logs the result to `enable_tripo.log`. Run: `blender --python tripo-studio/enable_tripo.py`. |
| `start_blender_mcp.py` | Blender script: enables Tripo for the session, enables `blender_mcp` and saves it to preferences, then starts the BlenderMCP server; logs to `start_blender_mcp.log`. |
| `probe.py` | One-shot probe: local Qwen (Ollama on :11435) writes a FLUX prompt, ComfyUI renders it, then Qwen drives Tripo Studio through the Playwright MCP to make a GLB. Safety limits live in its `Guard` class (one generation, no buy/upgrade/sign-out clicks, tripo3d.ai only). Modes: `--resume-in <run dir>` (skip the render), `--export-url <model page> [--scripted-export]` (download an existing model; no generation possible). |
| `out/` | **Gitignored.** One folder per probe run: image, step log, screenshots, GLBs, bakes, `.blend`. |

## What the 2026-11-02 run showed

Qwen picked the right controls (Choose File, upload, Generate, Export) but does not notice when
a click had no effect: it toggled the Export menu 15 times and reported "done". Script the fixed
clicks and keep Qwen for reading the page. One generation = 65 credits; export is free.

## Machine prerequisites (done 2026-11-02)

- Port **60600** (the Tripo Blender bridge) reserved for applications, because Windows' NAT
  service had put it inside an automatic exclusion range (60519–60618). Run once as admin:
  `net stop winnat`, `netsh int ipv4 add excludedportrange protocol=tcp startport=60600 numberofports=1 store=persistent`, `net start winnat`.
- GPU-heavy runs (ComfyUI generation, a 27B Qwen) wait for Dan's go-ahead and a card power cap
  (`nvidia-smi -pl 350`, admin): this PC has lost power under sustained GPU load before.

Moved here from a temporary session scratchpad on 2026-11-02.

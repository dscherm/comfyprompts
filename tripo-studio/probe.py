"""One-shot probe: local Qwen writes a FLUX prompt -> ComfyUI renders -> Qwen drives
Tripo Studio (via @playwright/mcp over stdio) to turn the image into a GLB.

Stdlib only. Run from anywhere:
    python tripo-studio/probe.py            # full run
    python tripo-studio/probe.py --explore  # read-only: open Tripo, dump snapshot, close
    python tripo-studio/probe.py --skip-render out/<ts>/chest.png   # reuse an image

Safety limits are enforced in code (see Guard), never delegated to the model.
"""
import base64
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLCHAIN = HERE.parent
WORKFLOW = TOOLCHAIN / "workflows" / "mcp" / "generate_image_flux2.json"
MCP_CFG = HERE / "mcp-playwright.json"
PW_OUT = HERE / "pw-out"

OLLAMA = "http://127.0.0.1:11435"
MODEL = "qwen3.8:27b"
COMFY = "http://127.0.0.1:8188"
SEED = 424242
START_URL = "https://studio.tripo3d.ai/workspace/generate"
MAX_STEPS = 30
MAX_SECONDS = 20 * 60
SNAP_CHARS = 9000

SUBJECT = ("a single stylised wooden treasure chest, game prop, centred, plain light-grey "
           "background, soft studio light, no text")

FORBIDDEN = re.compile(r"buy|purchase|upgrade|subscribe|\bpay|credit card|checkout|\bplan|"
                       r"pricing|delete|log ?out|sign ?out|account settings", re.I)
GENERATE = re.compile(r"generat|create", re.I)
SECRET_FIELD = re.compile(r"password|card|cvc|cvv|payment|billing|expir", re.I)
LOGIN_HINT = re.compile(r"/(login|signin|sign-in|auth)\b", re.I)


# ---------------------------------------------------------------- utilities
def http_json(url, payload=None, timeout=600):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read()
    return json.loads(body) if body.strip() else {}


def unload_qwen():
    try:
        http_json(f"{OLLAMA}/api/generate", {"model": MODEL, "keep_alive": 0}, timeout=60)
    except Exception as e:  # noqa: BLE001
        print(f"[warn] unload qwen: {e}")


def comfy_free():
    try:
        http_json(f"{COMFY}/free", {"unload_models": True, "free_memory": True}, timeout=60)
    except Exception as e:  # noqa: BLE001
        print(f"[warn] comfy free: {e}")


class VramSampler(threading.Thread):
    """Samples nvidia-smi every 2 s; keeps the max of the largest (24 GB) card."""

    def __init__(self):
        super().__init__(daemon=True)
        self.peak = 0
        self.stop_evt = threading.Event()

    def run(self):
        while not self.stop_evt.is_set():
            try:
                out = subprocess.run(
                    ["nvidia-smi", "--query-gpu=memory.used,memory.total",
                     "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=10
                ).stdout
                rows = [tuple(int(x) for x in ln.split(",")) for ln in out.strip().splitlines()]
                used = max(rows, key=lambda r: r[1])[0]
                self.peak = max(self.peak, used)
            except Exception:  # noqa: BLE001
                pass
            self.stop_evt.wait(2)


# ---------------------------------------------------------------- stage 1
def qwen_chat(messages, tools=None, temperature=0.3, num_ctx=32768, timeout=900):
    payload = {"model": MODEL, "messages": messages, "stream": False, "think": False,
               "options": {"temperature": temperature, "num_ctx": num_ctx}, "keep_alive": "30m"}
    if tools:
        payload["tools"] = tools
    return http_json(f"{OLLAMA}/api/chat", payload, timeout=timeout)["message"]


def stage1(outdir, log, reuse_prompt=None):
    t0 = time.time()
    msg = {"content": reuse_prompt} if reuse_prompt else qwen_chat([
        {"role": "system", "content": "You write prompts for the FLUX text-to-image model. "
         "Reply with the prompt only: one paragraph, no preamble, no quotes."},
        {"role": "user", "content": "Write a FLUX prompt for: " + SUBJECT + ". The image will be "
         "fed to an image-to-3D model, so the whole object must be visible, unoccluded, "
         "three-quarter view, with no cast-shadow clutter or extra objects."},
    ])
    prompt = msg["content"].strip().strip('"')
    qwen_s = time.time() - t0
    log(f"[stage1] qwen prompt ({qwen_s:.1f}s): {prompt}")

    unload_qwen()
    time.sleep(3)
    wf = WORKFLOW
    if "--workflow" in sys.argv:
        wf = TOOLCHAIN / "workflows" / "mcp" / sys.argv[sys.argv.index("--workflow") + 1]
    log(f"[stage1] workflow {wf.name}")
    graph = json.loads(wf.read_text(encoding="utf-8"))
    subs = {"PARAM_PROMPT": prompt, "PARAM_NEGATIVE_PROMPT": "", "PARAM_INT_SEED": SEED,
            "PARAM_INT_WIDTH": 1024, "PARAM_INT_HEIGHT": 1024}
    fallback = {"PARAM_INT_STEPS": 20, "PARAM_FLOAT_CFG": 1.0, "PARAM_STR_SAMPLER_NAME": "euler",
                "PARAM_STR_SCHEDULER": "simple", "PARAM_FLOAT_DENOISE": 1.0}
    for node in graph.values():
        defaults = node.pop("_defaults", {})
        for k, v in node["inputs"].items():
            if isinstance(v, str) and v.startswith("PARAM_"):
                node["inputs"][k] = subs.get(v, defaults.get(v, fallback.get(v)))
                if node["inputs"][k] is None:
                    raise ValueError(f"no value for {v}")
    t1 = time.time()
    pid = http_json(f"{COMFY}/prompt", {"prompt": graph, "client_id": "tripo-probe"})["prompt_id"]
    while True:
        h = http_json(f"{COMFY}/history/{pid}")
        if pid in h and h[pid].get("status", {}).get("completed"):
            break
        if pid in h and h[pid].get("status", {}).get("status_str") == "error":
            raise RuntimeError(f"comfy error: {h[pid]['status']}")
        if time.time() - t1 > 1200:
            raise TimeoutError("render > 20 min")
        time.sleep(2)
    render_s = time.time() - t1
    img = next(o["images"][0] for o in h[pid]["outputs"].values() if o.get("images"))
    q = urllib.parse.urlencode({"filename": img["filename"], "subfolder": img["subfolder"],
                                "type": img["type"]})
    dest = outdir / "chest.png"
    with urllib.request.urlopen(f"{COMFY}/view?{q}", timeout=60) as r:
        dest.write_bytes(r.read())
    log(f"[stage1] rendered {dest} in {render_s:.1f}s")
    comfy_free()
    time.sleep(3)
    return {"workflow": wf.name, "prompt": prompt, "qwen_s": round(qwen_s, 1), "render_s": round(render_s, 1),
            "path": str(dest), "seed": SEED}


# ---------------------------------------------------------------- MCP client
class MCP:
    def __init__(self, roots):
        cfg = json.loads(MCP_CFG.read_text(encoding="utf-8"))["mcpServers"]["playwright"]
        cmd = cfg["command"] + (".cmd" if os.name == "nt" else "")
        self.roots = roots
        self.proc = subprocess.Popen([cmd] + cfg["args"], stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.q = queue.Queue()
        self.next_id = 0
        self.lock = threading.Lock()
        threading.Thread(target=self._reader, daemon=True).start()
        threading.Thread(target=self._drain_err, daemon=True).start()

    def _drain_err(self):
        for _ in self.proc.stderr:
            pass

    def _send(self, obj):
        with self.lock:
            self.proc.stdin.write((json.dumps(obj) + "\n").encode())
            self.proc.stdin.flush()

    def _reader(self):
        for raw in self.proc.stdout:
            try:
                msg = json.loads(raw)
            except ValueError:
                continue
            if "method" in msg and "id" in msg:  # server -> client request
                if msg["method"] == "roots/list":
                    self._send({"jsonrpc": "2.0", "id": msg["id"], "result": {"roots": [
                        {"uri": Path(r).as_uri(), "name": Path(r).name} for r in self.roots]}})
                else:
                    self._send({"jsonrpc": "2.0", "id": msg["id"], "result": {}})
            elif "id" in msg:
                self.q.put(msg)

    def request(self, method, params=None, timeout=180):
        self.next_id += 1
        rid = self.next_id
        self._send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}})
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                msg = self.q.get(timeout=1)
            except queue.Empty:
                if self.proc.poll() is not None:
                    raise RuntimeError("MCP server exited")
                continue
            if msg.get("id") == rid:
                if "error" in msg:
                    raise RuntimeError(f"MCP error: {msg['error']}")
                return msg["result"]
        raise TimeoutError(f"MCP {method} timed out")

    def start(self):
        self.request("initialize", {"protocolVersion": "2025-06-18",
                                    "capabilities": {"roots": {"listChanged": False}},
                                    "clientInfo": {"name": "tripo-probe", "version": "0.1"}})
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return [t["name"] for t in self.request("tools/list")["tools"]]

    def call(self, name, args=None, timeout=180):
        res = self.request("tools/call", {"name": name, "arguments": args or {}}, timeout)
        text = "\n".join(c.get("text", "") for c in res.get("content", []) if c["type"] == "text")
        imgs = [c for c in res.get("content", []) if c["type"] == "image"]
        return text, imgs, bool(res.get("isError"))

    def close(self):
        try:
            self.call("browser_close", timeout=30)
        except Exception as e:  # noqa: BLE001
            print(f"[warn] browser_close: {e}")
        try:
            self.proc.stdin.close()
            self.proc.wait(timeout=15)
        except Exception:  # noqa: BLE001
            self.proc.kill()


def snapshot_text(mcp):
    text, _, _ = mcp.call("browser_snapshot")
    return text


def page_url(snap):
    m = re.search(r"Page URL:\s*(\S+)", snap)
    return m.group(1) if m else ""


def ref_line(snap, ref):
    for ln in snap.splitlines():
        if f"[ref={ref}]" in ln:
            return ln.strip()
    return ""


def trim_snapshot(snap):
    """Keep the page header + YAML; drop noise lines (generic wrappers w/o names)."""
    keep = []
    for ln in snap.splitlines():
        s = ln.strip()
        if re.fullmatch(r"- (generic|group|list|listitem|none)( \[ref=\w+\])?:?", s):
            continue
        if s.startswith("- img") and '"' not in s:
            continue
        keep.append(ln.rstrip())
    out = "\n".join(keep)
    return out if len(out) <= SNAP_CHARS else out[:SNAP_CHARS] + "\n... [snapshot trimmed]"


def ref_context(snap, ref, max_children=6):
    """The ref's own line plus its first few deeper-indented child lines (an unnamed
    `button [ref=e203]` carries its label, e.g. `text: Generate`, on a child line)."""
    lines = snap.splitlines()
    for i, ln in enumerate(lines):
        if f"[ref={ref}]" in ln:
            ind = len(ln) - len(ln.lstrip())
            out = [ln.strip()]
            for nxt in lines[i + 1:i + 1 + max_children]:
                if len(nxt) - len(nxt.lstrip()) <= ind:
                    break
                out.append(nxt.strip())
            return " | ".join(out)
    return ""


NOT_A_GENERATION = re.compile(r"generate in parts", re.I)
OTHER_PAID_GENERATION = re.compile(r"generate image for 3d|generate-image", re.I)


# ---------------------------------------------------------------- guard
EXPORT_ONLY_FORBIDDEN = re.compile(r"smart mesh|retopo|segment|smart uv|texture|rig|"
                                   r"multi-views|retry generat|regenerat|free retry", re.I)


class Guard:
    def __init__(self, image_path, export_only=False):
        self.image = str(Path(image_path).resolve())
        self.export_only = export_only
        self.generation_started = False
        self.uploaded = False
        self.fired = []

    def _refuse(self, why):
        self.fired.append(why)
        return why

    def check(self, tool, args, snap):
        if tool == "click":
            line = ref_context(snap, args.get("ref", ""))
            if not line:
                return self._refuse(f"ref {args.get('ref')} not in current snapshot")
            text = f"{args.get('element', '')} {line}"
            if FORBIDDEN.search(text):
                return self._refuse(f"forbidden click target: {line[:160]}")
            if OTHER_PAID_GENERATION.search(text):
                return self._refuse(f"text-to-image generation refused: {line[:160]}")
            if self.export_only and (GENERATE.search(text) or EXPORT_ONLY_FORBIDDEN.search(text)):
                return self._refuse(f"export-only run: generation/post-process refused: {line[:160]}")
            if GENERATE.search(text) and not NOT_A_GENERATION.search(text):
                if self.generation_started:
                    return self._refuse("second generate/create click refused (1 generation max)")
                if not self.uploaded:
                    return self._refuse("generate/create click refused before the image upload")
        elif tool == "type":
            line = ref_context(snap, args.get("ref", ""))
            if SECRET_FIELD.search(f"{args.get('element', '')} {line}"):
                return self._refuse(f"typing into secret/payment field refused: {line[:120]}")
        elif tool == "upload" and self.export_only:
            return self._refuse("export-only run: upload refused")
        elif tool == "upload":
            paths = args.get("paths") or []
            if not paths or any(str(Path(p).resolve()) != self.image for p in paths):
                return self._refuse(f"upload of non-allowed path refused: {paths}")
        elif tool == "navigate":
            host = urllib.parse.urlparse(args.get("url", "")).hostname or ""
            if not (host == "tripo3d.ai" or host.endswith(".tripo3d.ai")):
                return self._refuse(f"navigation off tripo3d.ai refused: {args.get('url')}")
        return None

    def after_click(self, args, snap):
        text = f"{args.get('element', '')} {ref_context(snap, args.get('ref', ''))}"
        if GENERATE.search(text) and not NOT_A_GENERATION.search(text):
            self.generation_started = True


TOOLS = [
    {"type": "function", "function": {"name": n, "description": d, "parameters": {
        "type": "object", "properties": p, "required": list(p)}}}
    for n, d, p in [
        ("click", "Click an element. ref is the [ref=...] id from the snapshot; element is its "
         "visible text.", {"ref": {"type": "string"}, "element": {"type": "string"}}),
        ("type", "Type text into an input.", {"ref": {"type": "string"},
                                              "element": {"type": "string"},
                                              "text": {"type": "string"}}),
        ("upload", "Upload files into the file chooser that is CURRENTLY OPEN (open it first by "
         "clicking the upload area).", {"paths": {"type": "array", "items": {"type": "string"}}}),
        ("wait", "Wait N seconds (max 20) for the page to change.", {"seconds": {"type": "number"}}),
        ("navigate", "Go to a URL on tripo3d.ai.", {"url": {"type": "string"}}),
        ("done", "The GLB download has started/finished. Summarise.", {"summary": {"type": "string"}}),
        ("give_up", "You cannot proceed. Explain why.", {"reason": {"type": "string"}}),
    ]
]


def parse_tool_call(msg):
    calls = msg.get("tool_calls") or []
    if calls:
        fn = calls[0]["function"]
        args = fn.get("arguments") or {}
        if isinstance(args, str):
            args = json.loads(args)
        return fn["name"], args
    m = re.search(r"\{.*\}", msg.get("content") or "", re.S)  # fallback: JSON in content
    if m:
        try:
            obj = json.loads(m.group(0))
            name = obj.get("name") or obj.get("tool")
            if name:
                return name, obj.get("arguments") or obj.get("args") or {}
        except ValueError:
            pass
    return None, {"raw": (msg.get("content") or "")[:400]}


def find_glbs(since):
    dirs = [PW_OUT, Path.home() / "Downloads"]
    hits = []
    for d in dirs:
        if d.exists():
            for p in [q for ext in ("*.glb", "*.zip", "*.fbx") for q in d.rglob(ext)]:
                if p.stat().st_mtime >= since:
                    hits.append(p)
    return hits


# ---------------------------------------------------------------- stage 2
def stage2(outdir, image_path, log, export_url=None):
    steps_f = (outdir / "steps.jsonl").open("a", encoding="utf-8")
    shots = outdir / "shots"
    shots.mkdir(exist_ok=True)
    guard = Guard(image_path, export_only=bool(export_url))
    t0 = time.time()
    result = {"steps": 0, "stop": None, "generation_started": False, "uploaded": False}
    mcp = MCP(roots=[str(HERE), str(outdir)])
    try:
        tools = mcp.start()
        log(f"[stage2] MCP tools: {tools}")
        text, _, err = mcp.call("browser_navigate", {"url": export_url or START_URL}, timeout=120)
        log(f"[stage2] navigate -> err={err} {text[:200]!r}")
        mcp.call("browser_wait_for", {"time": 15 if export_url else 5})
        if export_url:
            dismiss_tutorial(mcp, log)
        if export_url and "--scripted-export" in sys.argv:
            result.update(scripted_export(mcp, log, t0))
            return result
        history = []
        goal = (f"Goal: on Tripo Studio, upload the image file {guard.image} as an IMAGE-TO-3D "
                "job, start exactly ONE generation, wait until the 3D model is finished, then "
                "download the result in GLB format. Do NOT buy, upgrade or change account "
                "settings. Uploading works in two steps: first click the upload area/button so "
                "a file chooser opens, then call upload with the file path. Generation can take "
                "several minutes: use wait(20) repeatedly while it runs. Call done once the GLB "
                "download has been triggered; call give_up if you are blocked (e.g. login "
                "required, out of credits).")
        if export_url:
            goal = ("Goal: the 3D model on this Tripo Studio page is ALREADY generated. Download it "
                    "in GLB format: click Export, choose GLB if a format is offered, then confirm "
                    "the download. Do NOT generate, retry, retopologise, rig, texture or upload "
                    "anything. If the 3D view says it failed to load, its Retry button only "
                    "reloads the view and is fine to click. If a pop-up covers the page, close it "
                    "(OK or X) first. Element refs change every step: only use refs that appear "
                    "in the CURRENT snapshot, never ones from previous actions. Call done once "
                    "the download has been triggered; call give_up if you are blocked.")
        last_err, err_repeats = "", 0
        for step in range(1, MAX_STEPS + 1):
            if time.time() - t0 > MAX_SECONDS:
                result["stop"] = "time cap (20 min)"
                break
            snap = snapshot_text(mcp)
            url = page_url(snap)
            if LOGIN_HINT.search(url) or (re.search(r"textbox \"[^\"]*password", snap, re.I)
                                          and re.search(r"log ?in|sign ?in", snap, re.I)):
                result["stop"] = f"login page detected at {url}"
                log(f"[stage2] {result['stop']}")
                break
            stext, simgs, _ = mcp.call("browser_take_screenshot", {"type": "jpeg"})
            shot_file = None
            img_b64 = None
            if simgs:
                img_b64 = simgs[0]["data"]
                ext = "jpg" if "jpeg" in simgs[0].get("mimeType", "") else "png"
                shot_file = shots / f"step_{step:02d}.{ext}"
                shot_file.write_bytes(base64.b64decode(img_b64))
            hist_txt = "\n".join(history[-12:]) or "(none yet)"
            user = (f"{goal}\n\nState flags: image_uploaded={guard.uploaded}, "
                    f"generation_started={guard.generation_started}.\n\n"
                    f"Previous actions (most recent last):\n{hist_txt}\n\n"
                    f"Current page accessibility snapshot:\n{trim_snapshot(snap)}\n\n"
                    "The screenshot of the current page is attached. Choose exactly ONE tool "
                    "call for the next action.")
            m = {"role": "user", "content": user}
            if img_b64:
                m["images"] = [img_b64]
            tq = time.time()
            try:
                reply = qwen_chat([{"role": "system", "content": "You are a careful browser "
                                    "agent. You act only through the provided tools, one call "
                                    "per turn. Refs must come from the current snapshot."}, m],
                                  tools=TOOLS, temperature=0.3, num_ctx=32768)
            except Exception as e:  # noqa: BLE001
                result["stop"] = f"qwen error: {e}"
                break
            q_s = time.time() - tq
            name, args = parse_tool_call(reply)
            rec = {"step": step, "t": round(time.time() - t0, 1), "qwen_s": round(q_s, 1),
                   "url": url, "tool": name, "args": args, "screenshot": str(shot_file)}
            refusal = guard.check(name, args, snap) if name else None
            res_text = ""
            if name is None:
                res_text = "no tool call returned"
            elif refusal:
                res_text = f"REFUSED by probe: {refusal}"
            elif name == "click":
                res_text, _, err = mcp.call("browser_click", {"target": args["ref"],
                                                              "element": args.get("element", "")})
                if not err:
                    guard.after_click(args, snap)
            elif name == "type":
                res_text, _, err = mcp.call("browser_type", {"target": args["ref"],
                                                             "element": args.get("element", ""),
                                                             "text": args.get("text", "")})
            elif name == "upload":
                res_text, _, err = mcp.call("browser_file_upload", {"paths": [guard.image]})
                if not err and "rror" not in res_text[:200]:
                    guard.uploaded = True
            elif name == "wait":
                secs = max(1, min(20, float(args.get("seconds", 5))))
                res_text, _, err = mcp.call("browser_wait_for", {"time": secs})
            elif name == "navigate":
                res_text, _, err = mcp.call("browser_navigate", {"url": args["url"]})
            elif name in ("done", "give_up"):
                res_text = args.get("summary") or args.get("reason") or ""
            else:
                res_text = f"unknown tool {name}"
            res_short = re.sub(r"\s+", " ", res_text)[:600]
            rec["result"] = res_short
            rec["refused"] = refusal
            steps_f.write(json.dumps(rec) + "\n")
            steps_f.flush()
            log(f"[step {step:02d}] {q_s:5.1f}s {name} {json.dumps(args)[:160]} -> "
                f"{res_short[:200]}")
            history.append(f"{step}. {name}({json.dumps(args)[:150]}) -> {res_short[:220]}")
            result["steps"] = step
            if name in ("done", "give_up"):
                result["stop"] = f"{name}: {res_text[:300]}"
                break
            same_err = res_short.startswith("### Error") and res_short == last_err
            err_repeats = err_repeats + 1 if same_err else 0
            last_err = res_short if res_short.startswith("### Error") else ""
            if err_repeats >= 2:
                result["stop"] = f"same tool error 3x in a row: {res_short[:200]}"
                break
            if find_glbs(t0):
                log("[stage2] GLB appeared on disk")
        else:
            result["stop"] = result["stop"] or "step cap (30)"
    finally:
        result["generation_started"] = guard.generation_started
        result["uploaded"] = guard.uploaded
        result["refusals"] = guard.fired
        result["elapsed_s"] = round(time.time() - t0, 1)
        time.sleep(3)
        result["glbs"] = [str(p) for p in find_glbs(t0)]
        mcp.close()
        steps_f.close()
    return result


def credit_balance(snap):
    """The credit counter sits just before the Upgrade button in the header."""
    head = snap[:snap.find("Upgrade")] if "Upgrade" in snap else ""
    nums = re.findall(r"\b\d{1,3}(?:,\d{3})+\b|\b\d{3,7}\b", head)
    return nums[-1].replace(",", "") if nums else None


def scripted_export(mcp, log, t0):
    """No model in the loop: open the Export menu, check it says GLB, click its confirm button,
    then wait for the download. Stops if the credit balance moves."""
    out = {"scripted_export": True}
    snap = snapshot_text(mcp)
    out["credits_before"] = credit_balance(snap)
    refs = re.findall(r'button "Export"[^\n]*\[ref=(\w+)\]', snap)
    if not refs:
        out["stop"] = "no Export button on the page"
        return out
    trigger = refs[0]
    text, _, err = mcp.call("browser_click", {"target": trigger, "element": "Export (toolbar)"})
    log(f"[export] open menu ({trigger}) -> err={err}")
    mcp.call("browser_wait_for", {"time": 3})
    snap = snapshot_text(mcp)
    confirm = [r for r in re.findall(r'button "Export"[^\n]*\[ref=(\w+)\]', snap) if r != trigger]
    if "GLB" not in snap or not confirm:
        out["stop"] = f"export menu not as expected (GLB shown={'GLB' in snap}, confirm={confirm})"
        (Path(PW_OUT) / "export_menu_snapshot.txt").write_text(snap, encoding="utf-8")
        return out
    text, _, err = mcp.call("browser_click", {"target": confirm[0], "element": "Export (confirm)"},
                            timeout=300)
    flat = re.sub(r"\s+", " ", text)[:300]
    log(f"[export] confirm ({confirm[0]}) -> err={err} {flat!r}")
    for _ in range(30):
        if find_glbs(t0):
            break
        mcp.call("browser_wait_for", {"time": 10})
    snap = snapshot_text(mcp)
    out["credits_after"] = credit_balance(snap)
    if out["credits_before"] != out["credits_after"]:
        log(f"[export] WARNING credit balance moved: {out['credits_before']} -> {out['credits_after']}")
    out["stop"] = "scripted export finished" if find_glbs(t0) else "no file after 5 min"
    return out


def dismiss_tutorial(mcp, log):
    """Scripted: close Tripo's first-load 'View Your Model' pop-up, which covers Export."""
    for _ in range(3):
        snap = snapshot_text(mcp)
        if "View Your Model" not in snap:
            log("[stage2] no tutorial pop-up")
            return
        tail = snap[snap.index("View Your Model"):]
        m = re.search(r'button "OK"[^\n]*\[ref=(\w+)\]', tail)
        if not m:
            log("[stage2] tutorial pop-up seen but no OK button ref")
            return
        text, _, err = mcp.call("browser_click", {"target": m.group(1),
                                                  "element": "OK on View Your Model pop-up"})
        log(f"[stage2] dismiss tutorial ({m.group(1)}) -> err={err} {text[:120]!r}")
        mcp.call("browser_wait_for", {"time": 2})


def explore(outdir):
    mcp = MCP(roots=[str(HERE), str(outdir)])
    try:
        tools = mcp.start()
        print("TOOLS:", tools)
        text, _, err = mcp.call("browser_navigate", {"url": START_URL}, timeout=120)
        mcp.call("browser_wait_for", {"time": 6})
        snap = snapshot_text(mcp)
        (outdir / "explore_snapshot.txt").write_text(snap, encoding="utf-8")
        _, imgs, _ = mcp.call("browser_take_screenshot", {"type": "jpeg"})
        if imgs:
            (outdir / "explore.jpg").write_bytes(base64.b64decode(imgs[0]["data"]))
        print("URL:", page_url(snap), "snapshot chars:", len(snap))
    finally:
        mcp.close()


def main():
    ts = time.strftime("%Y%m%d-%H%M%S")
    outdir = HERE / "out" / ts
    if "--resume-in" in sys.argv:  # stage 2 only, in an existing run folder with chest.png
        outdir = Path(sys.argv[sys.argv.index("--resume-in") + 1]).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    logf = (outdir / "probe.log").open("a", encoding="utf-8")

    def log(s):
        print(s, flush=True)
        logf.write(s + "\n")
        logf.flush()

    if "--explore" in sys.argv:
        explore(outdir)
        print("explore output:", outdir)
        return
    vram = VramSampler()
    vram.start()
    t0 = time.time()
    summary = {"outdir": str(outdir)}
    try:
        if "--resume-in" in sys.argv:
            summary["stage1"] = {"resumed": True, "path": str(outdir / "chest.png")}
        elif "--skip-render" in sys.argv:
            src = Path(sys.argv[sys.argv.index("--skip-render") + 1])
            shutil.copy(src, outdir / "chest.png")
            summary["stage1"] = {"reused": str(src), "path": str(outdir / "chest.png")}
        else:
            reuse = None
            if "--prompt-file" in sys.argv:
                reuse = Path(sys.argv[sys.argv.index("--prompt-file") + 1]).read_text(
                    encoding="utf-8").strip()
            summary["stage1"] = stage1(outdir, log, reuse)
            summary["stage1"]["prompt_reused_from_earlier_qwen_call"] = bool(reuse)
        export_url = None
        if "--export-url" in sys.argv:
            export_url = sys.argv[sys.argv.index("--export-url") + 1]
            host = urllib.parse.urlparse(export_url).hostname or ""
            assert host == "tripo3d.ai" or host.endswith(".tripo3d.ai"), export_url
            summary["export_only"] = export_url
        summary["stage2"] = stage2(outdir, outdir / "chest.png", log, export_url)
        glbs = summary["stage2"].get("glbs") or []
        if glbs:
            dest = outdir / ("chest" + Path(glbs[0]).suffix)
            shutil.move(glbs[0], dest)
            summary["stage3"] = {"glb": str(dest), "bytes": dest.stat().st_size}
        else:
            summary["stage3"] = {"glb": None}
    finally:
        unload_qwen()
        vram.stop_evt.set()
        summary["peak_vram_mib"] = vram.peak
        summary["wall_s"] = round(time.time() - t0, 1)
        (outdir / f"summary_{ts}.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        log(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

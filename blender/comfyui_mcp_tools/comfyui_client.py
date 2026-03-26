"""Direct ComfyUI HTTP client using only urllib (Blender-compatible).

Talks directly to ComfyUI's REST API at localhost:8188 for:
- Image upload (multipart form data)
- Workflow submission (queue prompt)
- Job status polling (history)
- Output image download
- Model/checkpoint listing
"""

import json
import os
import tempfile
import uuid
import urllib.error
import urllib.parse
import urllib.request


class ComfyUIDirectClient:
    """Lightweight HTTP client for ComfyUI's native API."""

    def __init__(self, base_url="http://127.0.0.1:8188"):
        self.base_url = base_url.rstrip("/")
        self.client_id = uuid.uuid4().hex
        self.timeout = 30

    # ------------------------------------------------------------------
    # Low-level HTTP helpers
    # ------------------------------------------------------------------

    def _get_json(self, endpoint, timeout=None):
        """GET request returning parsed JSON. Returns (ok, data)."""
        url = f"{self.base_url}{endpoint}"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:
                return True, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return False, {"error": f"HTTP {e.code}: {e.reason}"}
        except urllib.error.URLError as e:
            return False, {"error": f"Connection failed: {e.reason}"}
        except Exception as e:
            return False, {"error": str(e)}

    def _post_json(self, endpoint, data, timeout=None):
        """POST JSON request. Returns (ok, data)."""
        url = f"{self.base_url}{endpoint}"
        try:
            body = json.dumps(data).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:
                return True, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                err = json.loads(e.read().decode("utf-8"))
                return False, {"error": err.get("error", str(e))}
            except Exception:
                return False, {"error": f"HTTP {e.code}: {e.reason}"}
        except urllib.error.URLError as e:
            return False, {"error": f"Connection failed: {e.reason}"}
        except Exception as e:
            return False, {"error": str(e)}

    def _get_bytes(self, endpoint, timeout=None):
        """GET request returning raw bytes. Returns (ok, bytes|error_dict)."""
        url = f"{self.base_url}{endpoint}"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:
                return True, resp.read()
        except urllib.error.HTTPError as e:
            return False, {"error": f"HTTP {e.code}: {e.reason}"}
        except urllib.error.URLError as e:
            return False, {"error": f"Connection failed: {e.reason}"}
        except Exception as e:
            return False, {"error": str(e)}

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def check_connection(self):
        """Check if ComfyUI is reachable. Returns (ok, info_dict)."""
        return self._get_json("/system_stats")

    # ------------------------------------------------------------------
    # Image upload (multipart/form-data via urllib)
    # ------------------------------------------------------------------

    def upload_image(self, filepath, subfolder="", overwrite=True):
        """Upload an image file to ComfyUI's /upload/image endpoint.

        Returns (ok, {"name": ..., "subfolder": ..., "type": ...}).
        """
        filename = os.path.basename(filepath)
        boundary = uuid.uuid4().hex

        with open(filepath, "rb") as f:
            image_bytes = f.read()

        # Build multipart body
        parts = []

        # Image file part
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(
            f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'
            f"Content-Type: image/png\r\n\r\n".encode()
        )
        parts.append(image_bytes)
        parts.append(b"\r\n")

        # Overwrite flag
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(
            b'Content-Disposition: form-data; name="overwrite"\r\n\r\n'
        )
        parts.append(b"true" if overwrite else b"false")
        parts.append(b"\r\n")

        # Subfolder (if provided)
        if subfolder:
            parts.append(f"--{boundary}\r\n".encode())
            parts.append(
                b'Content-Disposition: form-data; name="subfolder"\r\n\r\n'
            )
            parts.append(subfolder.encode())
            parts.append(b"\r\n")

        # End boundary
        parts.append(f"--{boundary}--\r\n".encode())

        body = b"".join(parts)
        url = f"{self.base_url}/upload/image"

        try:
            req = urllib.request.Request(
                url,
                data=body,
                headers={
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                    "Content-Length": str(len(body)),
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return True, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                err = json.loads(e.read().decode("utf-8"))
                return False, {"error": err.get("error", str(e))}
            except Exception:
                return False, {"error": f"HTTP {e.code}: {e.reason}"}
        except urllib.error.URLError as e:
            return False, {"error": f"Connection failed: {e.reason}"}
        except Exception as e:
            return False, {"error": str(e)}

    # ------------------------------------------------------------------
    # Prompt queue
    # ------------------------------------------------------------------

    def queue_prompt(self, workflow):
        """Submit a workflow to ComfyUI. Returns (ok, {"prompt_id": ...})."""
        payload = {
            "prompt": workflow,
            "client_id": self.client_id,
        }
        return self._post_json("/prompt", payload)

    # ------------------------------------------------------------------
    # History / job status
    # ------------------------------------------------------------------

    def get_history(self, prompt_id):
        """Get execution history for a prompt. Returns (ok, history_dict)."""
        return self._get_json(f"/history/{prompt_id}")

    def get_job_status(self, prompt_id):
        """Parse history into a simple status dict.

        Returns (ok, {"status": str, "outputs": dict|None, "error": str|None}).
        """
        ok, data = self.get_history(prompt_id)
        if not ok:
            return False, data

        if prompt_id not in data:
            return True, {"status": "pending", "outputs": None, "error": None}

        entry = data[prompt_id]
        status_info = entry.get("status", {})
        status_str = status_info.get("status_str", "unknown")

        if status_str == "error":
            messages = status_info.get("messages", [])
            error_msg = "; ".join(str(m) for m in messages) if messages else "Unknown error"
            return True, {"status": "error", "outputs": None, "error": error_msg}

        outputs = entry.get("outputs", {})
        if outputs:
            return True, {"status": "completed", "outputs": outputs, "error": None}

        return True, {"status": "running", "outputs": None, "error": None}

    # ------------------------------------------------------------------
    # Queue management
    # ------------------------------------------------------------------

    def get_queue(self):
        """Get current queue state. Returns (ok, queue_dict)."""
        return self._get_json("/queue")

    def interrupt(self):
        """Interrupt the currently executing prompt."""
        return self._post_json("/interrupt", {})

    # ------------------------------------------------------------------
    # Output image download
    # ------------------------------------------------------------------

    def download_image(self, filename, subfolder="", folder_type="output"):
        """Download a generated image from ComfyUI.

        Returns (ok, image_bytes | error_dict).
        """
        params = urllib.parse.urlencode({
            "filename": filename,
            "subfolder": subfolder,
            "type": folder_type,
        })
        return self._get_bytes(f"/view?{params}")

    def download_image_to_file(self, filename, output_path, subfolder="", folder_type="output"):
        """Download a generated image and save to disk.

        Returns (ok, output_path | error_dict).
        """
        ok, data = self.download_image(filename, subfolder, folder_type)
        if not ok:
            return False, data
        with open(output_path, "wb") as f:
            f.write(data)
        return True, output_path

    # ------------------------------------------------------------------
    # Model listing
    # ------------------------------------------------------------------

    def get_checkpoints(self):
        """List available checkpoint models. Returns (ok, [name, ...])."""
        ok, data = self._get_json("/object_info/CheckpointLoaderSimple")
        if not ok:
            return False, data
        try:
            inputs = data["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"]
            return True, inputs[0]  # First element is the list of names
        except (KeyError, IndexError):
            return False, {"error": "Could not parse checkpoint list"}

    def get_samplers(self):
        """List available sampler names. Returns (ok, [name, ...])."""
        ok, data = self._get_json("/object_info/KSampler")
        if not ok:
            return False, data
        try:
            inputs = data["KSampler"]["input"]["required"]["sampler_name"]
            return True, inputs[0]
        except (KeyError, IndexError):
            return False, {"error": "Could not parse sampler list"}

    def get_schedulers(self):
        """List available scheduler names. Returns (ok, [name, ...])."""
        ok, data = self._get_json("/object_info/KSampler")
        if not ok:
            return False, data
        try:
            inputs = data["KSampler"]["input"]["required"]["scheduler"]
            return True, inputs[0]
        except (KeyError, IndexError):
            return False, {"error": "Could not parse scheduler list"}

    # ------------------------------------------------------------------
    # Output extraction helpers
    # ------------------------------------------------------------------

    @staticmethod
    def extract_output_images(outputs):
        """Extract image filenames from workflow outputs.

        Returns list of {"filename": ..., "subfolder": ..., "type": ...}.
        """
        images = []
        for node_id, node_output in outputs.items():
            if "images" in node_output:
                for img in node_output["images"]:
                    images.append({
                        "filename": img["filename"],
                        "subfolder": img.get("subfolder", ""),
                        "type": img.get("type", "output"),
                    })
        return images


# Singleton
_client = None


def get_comfyui_client(base_url=None):
    """Get or create the ComfyUI client singleton."""
    global _client
    if _client is None or (base_url and _client.base_url != base_url.rstrip("/")):
        _client = ComfyUIDirectClient(base_url or "http://127.0.0.1:8188")
    return _client

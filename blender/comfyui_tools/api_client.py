"""HTTP client for ComfyUI Prompter API.

Uses urllib instead of requests for Blender compatibility (Blender's
embedded Python does not ship with the requests library).
"""

import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, Optional, Tuple


class APIClient:
    """HTTP client for ComfyUI Prompter API server."""

    def __init__(self, base_url: str = "http://127.0.0.1:5050"):
        self.base_url = base_url.rstrip('/')
        self.timeout = 30

    def _make_request(self, method: str, endpoint: str,
                      data: Optional[Dict] = None) -> Tuple[bool, Dict]:
        url = f"{self.base_url}{endpoint}"
        try:
            if data:
                json_data = json.dumps(data).encode('utf-8')
                req = urllib.request.Request(
                    url,
                    data=json_data,
                    headers={'Content-Type': 'application/json'},
                    method=method,
                )
            else:
                req = urllib.request.Request(url, method=method)

            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                response_data = json.loads(response.read().decode('utf-8'))
                return True, response_data

        except urllib.error.HTTPError as e:
            try:
                error_data = json.loads(e.read().decode('utf-8'))
                return False, {"error": error_data.get("error", str(e))}
            except Exception:
                return False, {"error": f"HTTP {e.code}: {e.reason}"}
        except urllib.error.URLError as e:
            return False, {"error": f"Connection failed: {e.reason}"}
        except Exception as e:
            return False, {"error": str(e)}

    def check_status(self) -> Tuple[bool, Dict]:
        """Check API and ComfyUI status."""
        return self._make_request('GET', '/api/status')

    def analyze_prompt(self, prompt: str) -> Tuple[bool, Dict]:
        """Get AI workflow recommendation for a prompt."""
        return self._make_request('POST', '/api/analyze', {"prompt": prompt})

    def get_workflows(self, workflow_type: Optional[str] = None) -> Tuple[bool, Dict]:
        """Get available workflows."""
        endpoint = '/api/workflows'
        if workflow_type:
            endpoint += f'?type={workflow_type}'
        return self._make_request('GET', endpoint)

    def generate_from_image(self, workflow: str, image_path: str) -> Tuple[bool, Dict]:
        """Start a 3D generation job from an image file path."""
        return self._make_request('POST', '/api/generate', {
            "workflow": workflow,
            "image_path": image_path,
            "mode": "image_to_3d",
        })

    def generate_from_image_data(self, workflow: str, image_data: bytes) -> Tuple[bool, Dict]:
        """Start a 3D generation job from image bytes."""
        base64_data = base64.b64encode(image_data).decode('utf-8')
        return self._make_request('POST', '/api/generate', {
            "workflow": workflow,
            "image_data": f"data:image/png;base64,{base64_data}",
            "mode": "image_to_3d",
        })

    def generate_from_text(self, workflow: str, prompt: str) -> Tuple[bool, Dict]:
        """Start a text-to-3D generation job."""
        return self._make_request('POST', '/api/generate', {
            "workflow": workflow,
            "prompt": prompt,
            "mode": "text_to_3d",
        })

    def get_job_status(self, job_id: str) -> Tuple[bool, Dict]:
        """Get status of a generation job."""
        return self._make_request('GET', f'/api/job/{job_id}')

    def upload_image(self, image_path: str) -> Tuple[bool, Dict]:
        """Upload an image to the server."""
        try:
            with open(image_path, 'rb') as f:
                image_data = f.read()
            base64_data = base64.b64encode(image_data).decode('utf-8')
            return self._make_request('POST', '/api/upload', {
                "image_data": base64_data,
            })
        except Exception as e:
            return False, {"error": str(e)}

    # --- Queue management ---

    def get_queue(self) -> Tuple[bool, Dict]:
        """Get current ComfyUI queue status."""
        return self._make_request('GET', '/api/queue')

    def clear_queue(self) -> Tuple[bool, Dict]:
        """Clear all pending jobs from the queue."""
        return self._make_request('POST', '/api/queue/clear')

    def interrupt_execution(self) -> Tuple[bool, Dict]:
        """Interrupt the currently running generation."""
        return self._make_request('POST', '/api/interrupt')

    # --- Output browsing ---

    def list_outputs(self, output_type: str = "3d", limit: int = 20) -> Tuple[bool, Dict]:
        """List recent output files from ComfyUI."""
        return self._make_request('GET', f'/api/outputs?type={output_type}&limit={limit}')

    # --- Workflow validation ---

    def validate_workflow(self, workflow: str) -> Tuple[bool, Dict]:
        """Validate a workflow before running it."""
        return self._make_request('POST', '/api/validate', {"workflow": workflow})


# Singleton
_client = None


def get_client(base_url: str = None) -> APIClient:
    """Get or create the API client singleton."""
    global _client
    if _client is None or (base_url and _client.base_url != base_url):
        _client = APIClient(base_url or "http://127.0.0.1:5050")
    return _client

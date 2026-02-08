# mcp_server.py - MCP Server for Claude Code integration
# Allows Claude to directly generate images/videos through ComfyUI

import json
import sys
import asyncio
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from ollama_recommender import OllamaRecommender
from workflow_manager import WorkflowManager
from comfyui_agent_sdk.client import ComfyUIClient
from comfyui_agent_sdk.config import ComfyUIConfig
from config import WORKFLOWS, CHECKPOINTS, COMFYUI_PATH, COMFYUI_URL, OLLAMA_URL, API_SERVER_HOST, API_SERVER_PORT

# Initialize components
recommender = OllamaRecommender()
workflow_manager = WorkflowManager()
_config = ComfyUIConfig(comfyui_url=COMFYUI_URL, comfyui_path=str(COMFYUI_PATH))
comfyui_api = ComfyUIClient(config=_config)

# Store active jobs
active_jobs = {}


def handle_request(request: dict) -> dict:
    """Handle incoming MCP request"""
    method = request.get("method", "")
    params = request.get("params", {})
    request_id = request.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "comfyui-prompter",
                    "version": "1.0.0"
                }
            }
        }

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": [
                    {
                        "name": "analyze_prompt",
                        "description": "Analyze a text prompt and get AI-recommended workflow and checkpoint for generation. Use this first before generating.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "prompt": {
                                    "type": "string",
                                    "description": "The text prompt describing what to generate (image, video, 3D model, etc.)"
                                }
                            },
                            "required": ["prompt"]
                        }
                    },
                    {
                        "name": "generate",
                        "description": "Generate content (image/video/3D) using ComfyUI. Queues the workflow and returns a job ID.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "prompt": {
                                    "type": "string",
                                    "description": "The text prompt for generation"
                                },
                                "workflow": {
                                    "type": "string",
                                    "description": "Workflow filename (e.g., 'text_to_video_wan.json'). Use analyze_prompt to get recommendations."
                                },
                                "checkpoint": {
                                    "type": "string",
                                    "description": "Checkpoint/model name (optional, uses workflow default if not specified)"
                                },
                                "mode": {
                                    "type": "string",
                                    "enum": ["standard", "text_to_3d"],
                                    "description": "Generation mode: 'standard' for direct workflow, 'text_to_3d' for text->image->3D pipeline"
                                },
                                "image_path": {
                                    "type": "string",
                                    "description": "Path to input image (for image-to-3D or image-to-video workflows)"
                                }
                            },
                            "required": ["workflow"]
                        }
                    },
                    {
                        "name": "check_job",
                        "description": "Check the status of a generation job",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "job_id": {
                                    "type": "string",
                                    "description": "The job/prompt ID returned from generate"
                                }
                            },
                            "required": ["job_id"]
                        }
                    },
                    {
                        "name": "list_workflows",
                        "description": "List all available workflows with their descriptions and use cases",
                        "inputSchema": {
                            "type": "object",
                            "properties": {}
                        }
                    },
                    {
                        "name": "check_status",
                        "description": "Check if ComfyUI and Ollama are running and available",
                        "inputSchema": {
                            "type": "object",
                            "properties": {}
                        }
                    }
                ]
            }
        }

    elif method == "tools/call":
        tool_name = params.get("name", "")
        tool_args = params.get("arguments", {})

        try:
            result = call_tool(tool_name, tool_args)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                }
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps({"error": str(e)})
                        }
                    ],
                    "isError": True
                }
            }

    elif method == "notifications/initialized":
        # This is a notification, no response needed
        return None

    else:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        }


def call_tool(tool_name: str, args: dict) -> dict:
    """Execute a tool and return results"""

    if tool_name == "analyze_prompt":
        prompt = args.get("prompt", "")
        if not prompt:
            return {"error": "No prompt provided"}

        recommendation = recommender.analyze_prompt(prompt)
        return {
            "recommended_workflow": recommendation.get("recommended_workflow"),
            "recommended_checkpoint": recommendation.get("recommended_checkpoint"),
            "reasoning": recommendation.get("reasoning"),
            "workflow_description": WORKFLOWS.get(recommendation.get("recommended_workflow"), {}).get("description", ""),
            "workflow_type": WORKFLOWS.get(recommendation.get("recommended_workflow"), {}).get("type", "")
        }

    elif tool_name == "generate":
        prompt = args.get("prompt", "")
        workflow_name = args.get("workflow", "")
        checkpoint = args.get("checkpoint")
        mode = args.get("mode", "standard")
        image_path = args.get("image_path")

        if not workflow_name:
            return {"error": "No workflow specified. Use analyze_prompt first to get a recommendation."}

        # Check ComfyUI connection
        if not comfyui_api.is_available():
            return {"error": "ComfyUI is not running. Please start ComfyUI first."}

        # Check for required models
        model_check = workflow_manager.check_required_models(workflow_name)
        if not model_check['has_checkpoint'] and model_check['missing_models']:
            missing = ', '.join(model_check['missing_models'])
            return {"error": f"Missing required models: {missing}. Please download them first."}

        # Handle text-to-3D mode (uses API server for two-step pipeline)
        if mode == "text_to_3d":
            if not prompt:
                return {"error": "text_to_3d mode requires a prompt"}
            import requests
            try:
                response = requests.post(
                    f"http://{API_SERVER_HOST}:{API_SERVER_PORT}/api/generate",
                    json={
                        "workflow": workflow_name,
                        "mode": "text_to_3d",
                        "prompt": prompt
                    },
                    timeout=30
                )
                return response.json()
            except Exception as e:
                return {"error": f"Failed to call API server: {e}. Make sure api_server.py is running."}

        # Standard generation mode
        # Load workflow
        workflow_data = workflow_manager.load_workflow(workflow_name)
        if not workflow_data:
            return {"error": f"Failed to load workflow: {workflow_name}"}

        # Set generation defaults for placeholder workflows
        workflow_data = workflow_manager.set_generation_defaults(
            workflow_data,
            checkpoint=checkpoint if checkpoint else "flux1-dev-fp8.safetensors"
        )

        # Modify checkpoint if specified
        if checkpoint:
            workflow_data = workflow_manager.modify_checkpoint(workflow_data, checkpoint)

        # Modify prompt if provided
        if prompt:
            workflow_data = workflow_manager.modify_prompt(workflow_data, prompt)

        # Handle image input for image-based workflows
        if image_path:
            import shutil
            from pathlib import Path
            from config import COMFYUI_PATH
            input_folder = COMFYUI_PATH / "input"
            src_path = Path(image_path)
            if src_path.exists():
                dest_path = input_folder / src_path.name
                shutil.copy2(src_path, dest_path)
                workflow_data = workflow_manager.modify_image_input(workflow_data, src_path.name)

        # Convert to API format
        api_workflow = workflow_manager.convert_to_api_format(workflow_data)
        if not api_workflow:
            return {"error": "Failed to convert workflow to API format"}

        # Queue in ComfyUI
        result = comfyui_api.queue_prompt(api_workflow)

        if result:
            prompt_id = result.get("prompt_id")
            active_jobs[prompt_id] = {
                "prompt": prompt,
                "workflow": workflow_name,
                "status": "queued"
            }
            return {
                "success": True,
                "job_id": prompt_id,
                "message": f"Generation queued successfully. Use check_job with job_id '{prompt_id}' to monitor progress.",
                "workflow": workflow_name,
                "prompt": prompt
            }
        else:
            return {"error": "Failed to queue prompt in ComfyUI"}

    elif tool_name == "check_job":
        job_id = args.get("job_id", "")
        if not job_id:
            return {"error": "No job_id provided"}

        status = comfyui_api.get_job_status(job_id)

        if status.get("status") == "completed":
            outputs = status.get("outputs", {})
            output_files = []

            # Extract output file paths
            for node_id, node_output in outputs.items():
                if "images" in node_output:
                    for img in node_output["images"]:
                        output_dir = str(COMFYUI_PATH / "output")
                        subfolder = img.get("subfolder", "")
                        filename = img.get("filename", "")
                        img_path = f"{output_dir}/{subfolder}/{filename}" if subfolder else f"{output_dir}/{filename}"
                        output_files.append({
                            "type": "image",
                            "filename": filename,
                            "subfolder": subfolder,
                            "path": img_path
                        })
                if "gltfFilename" in node_output:
                    output_files.append({
                        "type": "3d_model",
                        "filename": node_output["gltfFilename"],
                        "path": str(COMFYUI_PATH / "output" / node_output["gltfFilename"])
                    })
                if "video" in node_output:
                    for vid in node_output["video"]:
                        output_files.append({
                            "type": "video",
                            "filename": vid.get("filename"),
                            "path": str(COMFYUI_PATH / "output" / vid.get("filename", ""))
                        })

            return {
                "status": "completed",
                "job_id": job_id,
                "outputs": output_files,
                "message": "Generation complete!" if output_files else "Generation complete but no output files found."
            }

        elif status.get("status") == "running":
            return {
                "status": "running",
                "job_id": job_id,
                "progress": status.get("progress", "unknown"),
                "message": "Generation in progress..."
            }

        elif status.get("status") == "pending":
            return {
                "status": "pending",
                "job_id": job_id,
                "queue_position": status.get("queue_position", "unknown"),
                "message": "Job is queued, waiting to start..."
            }

        else:
            return {
                "status": status.get("status", "unknown"),
                "job_id": job_id,
                "message": "Unable to determine job status"
            }

    elif tool_name == "list_workflows":
        workflows = []
        for name, info in WORKFLOWS.items():
            workflows.append({
                "name": name,
                "description": info.get("description", ""),
                "type": info.get("type", ""),
                "use_case": info.get("use_case", ""),
                "checkpoint": info.get("checkpoint", "None")
            })
        return {
            "workflows": workflows,
            "count": len(workflows)
        }

    elif tool_name == "check_status":
        ollama_ok = recommender.check_ollama_available()
        comfyui_ok = comfyui_api.is_available()

        return {
            "ollama": {
                "status": "running" if ollama_ok else "not available",
                "url": OLLAMA_URL
            },
            "comfyui": {
                "status": "running" if comfyui_ok else "not available",
                "url": COMFYUI_URL
            },
            "ready": ollama_ok and comfyui_ok,
            "message": "All systems ready!" if (ollama_ok and comfyui_ok) else "Some services are not available"
        }

    else:
        return {"error": f"Unknown tool: {tool_name}"}


def main():
    """Main loop - reads JSON-RPC from stdin, writes to stdout"""
    # Ensure we're using unbuffered binary mode for stdin/stdout
    if sys.platform == 'win32':
        import msvcrt
        msvcrt.setmode(sys.stdin.fileno(), 0)  # Binary mode
        msvcrt.setmode(sys.stdout.fileno(), 0)

    while True:
        try:
            # Read Content-Length header
            header = ""
            while True:
                char = sys.stdin.read(1)
                if not char:
                    return  # EOF
                header += char
                if header.endswith("\r\n\r\n"):
                    break

            # Parse Content-Length
            content_length = 0
            for line in header.split("\r\n"):
                if line.startswith("Content-Length:"):
                    content_length = int(line.split(":")[1].strip())
                    break

            if content_length == 0:
                continue

            # Read content
            content = sys.stdin.read(content_length)
            request = json.loads(content)

            # Handle request
            response = handle_request(request)

            # Send response (if not a notification)
            if response is not None:
                response_json = json.dumps(response)
                response_bytes = response_json.encode('utf-8')
                sys.stdout.write(f"Content-Length: {len(response_bytes)}\r\n\r\n")
                sys.stdout.write(response_json)
                sys.stdout.flush()

        except json.JSONDecodeError as e:
            sys.stderr.write(f"JSON decode error: {e}\n")
            sys.stderr.flush()
        except Exception as e:
            sys.stderr.write(f"Error: {e}\n")
            sys.stderr.flush()


if __name__ == "__main__":
    main()

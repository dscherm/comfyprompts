# api_server.py - Flask REST API server for ComfyUI Prompter
# Provides endpoints for Blender addon integration

import os
import sys
import io
import base64
import uuid
import shutil
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from config import (
    API_SERVER_HOST, API_SERVER_PORT, COMFYUI_URL, OLLAMA_URL,
    COMFYUI_PATH, OUTPUT_3D_PATH, WORKFLOWS,
    DEFAULT_TEXT_TO_IMAGE_WORKFLOW, DEFAULT_3D_WORKFLOW
)
from comfyui_agent_sdk.client import ComfyUIClient
from comfyui_agent_sdk.config import ComfyUIConfig
from workflow_manager import WorkflowManager
from ollama_recommender import OllamaRecommender
from thumbnail_generator import get_thumbnail_generator

app = Flask(__name__)
CORS(app)  # Enable CORS for Blender addon requests

# Initialize components
_config = ComfyUIConfig(comfyui_url=COMFYUI_URL, comfyui_path=str(COMFYUI_PATH))
comfyui = ComfyUIClient(config=_config)
workflow_manager = WorkflowManager()
recommender = OllamaRecommender()

# Store active jobs
active_jobs = {}


@app.route('/api/status', methods=['GET'])
def get_status():
    """Check ComfyUI and Ollama connectivity"""
    return jsonify({
        "comfyui": {
            "connected": comfyui.is_available(),
            "url": COMFYUI_URL
        },
        "ollama": {
            "connected": recommender.check_ollama_available(),
            "url": OLLAMA_URL
        },
        "api_version": "1.0.0"
    })


@app.route('/api/analyze', methods=['POST'])
def analyze_prompt():
    """Get AI workflow recommendation from prompt"""
    data = request.get_json()

    if not data or 'prompt' not in data:
        return jsonify({"error": "Missing 'prompt' in request body"}), 400

    prompt = data['prompt']
    recommendation = recommender.analyze_prompt(prompt)

    return jsonify({
        "success": True,
        "recommendation": recommendation
    })


@app.route('/api/workflows', methods=['GET'])
def get_workflows():
    """List available workflows"""
    workflow_type = request.args.get('type', None)

    if workflow_type == '3d':
        workflows = workflow_manager.get_3d_workflows()
    elif workflow_type == 'image':
        workflows = workflow_manager.get_image_generation_workflows()
    else:
        workflows = WORKFLOWS

    return jsonify({
        "workflows": workflows,
        "count": len(workflows)
    })


@app.route('/api/generate', methods=['POST'])
def generate():
    """
    Queue a 3D generation job

    Request body:
    {
        "workflow": "workflow_filename.json",
        "image_data": "base64_encoded_image" (optional),
        "image_path": "/path/to/image.png" (optional),
        "prompt": "text prompt for text-to-3D" (optional),
        "mode": "image_to_3d" | "text_to_3d"
    }
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "Missing request body"}), 400

    workflow_name = data.get('workflow')
    mode = data.get('mode', 'image_to_3d')
    image_data = data.get('image_data')
    image_path = data.get('image_path')
    text_prompt = data.get('prompt', '')

    if not workflow_name:
        return jsonify({"error": "Missing 'workflow' in request"}), 400

    # Check if required models are available
    model_check = workflow_manager.check_required_models(workflow_name)
    if not model_check['has_checkpoint'] and model_check['missing_models']:
        missing = ', '.join(model_check['missing_models'])
        return jsonify({
            "error": f"Missing required models: {missing}",
            "missing_models": model_check['missing_models'],
            "suggestion": "Download the required models or choose a different workflow"
        }), 400

    # Load the workflow
    workflow_data = workflow_manager.load_workflow(workflow_name)
    if not workflow_data:
        return jsonify({"error": f"Failed to load workflow: {workflow_name}"}), 400

    # Handle image input
    input_image_name = None
    if mode == 'image_to_3d':
        if image_data:
            # Save base64 image to ComfyUI input folder
            input_image_name = _save_base64_image(image_data)
            if not input_image_name:
                return jsonify({"error": "Failed to save input image"}), 500
        elif image_path:
            # Copy image to ComfyUI input folder
            input_image_name = _copy_image_to_input(image_path)
            if not input_image_name:
                return jsonify({"error": "Failed to copy input image"}), 500
        else:
            return jsonify({"error": "image_to_3d mode requires image_data or image_path"}), 400

        # Modify workflow to use the input image
        workflow_data = workflow_manager.modify_image_input(workflow_data, input_image_name)

    elif mode == 'text_to_3d':
        # Two-step pipeline: text-to-image, then image-to-3D
        if not text_prompt:
            return jsonify({"error": "text_to_3d mode requires 'prompt'"}), 400

        # Step 1: Generate image from text
        t2i_workflow = data.get('text_to_image_workflow')  # Optional override
        t2i_result = _run_text_to_image(text_prompt, t2i_workflow)

        if not t2i_result["success"]:
            return jsonify({"error": f"Text-to-image failed: {t2i_result['error']}"}), 500

        # Step 2: Copy generated image to input folder for 3D workflow
        generated_image_path = t2i_result["image_path"]
        input_image_name = _copy_image_to_input(generated_image_path)

        if not input_image_name:
            return jsonify({"error": "Failed to copy generated image for 3D processing"}), 500

        # Modify 3D workflow to use the generated image
        workflow_data = workflow_manager.modify_image_input(workflow_data, input_image_name)
        print(f"[Text-to-3D] Using generated image: {input_image_name}")

    # Fetch object_info from ComfyUI for accurate widget mapping
    object_info = comfyui.get_object_info()
    if object_info:
        workflow_manager.set_object_info(object_info)
        print(f"Loaded {len(object_info)} node definitions from ComfyUI")
    else:
        print("Warning: Could not fetch object_info from ComfyUI, using fallback mappings")

    # Convert workflow from UI format to API format
    api_workflow = workflow_manager.convert_to_api_format(workflow_data)
    if not api_workflow:
        return jsonify({"error": "Failed to convert workflow to API format"}), 500

    print(f"Converted workflow has {len(api_workflow)} nodes")

    # Queue the workflow
    result = comfyui.queue_prompt(api_workflow)

    if not result:
        return jsonify({"error": "Failed to queue workflow in ComfyUI"}), 500

    prompt_id = result.get('prompt_id')

    # Store job info
    job_id = str(uuid.uuid4())
    active_jobs[job_id] = {
        "prompt_id": prompt_id,
        "workflow": workflow_name,
        "mode": mode,
        "status": "queued",
        "created_at": datetime.now().isoformat(),
        "input_image": input_image_name,
        "text_prompt": text_prompt if mode == 'text_to_3d' else None,
        "output_path": None
    }

    return jsonify({
        "success": True,
        "job_id": job_id,
        "prompt_id": prompt_id,
        "message": f"Job queued successfully"
    })


@app.route('/api/batch', methods=['POST'])
def batch_generate():
    """
    Generate multiple variations with different seeds

    Request:
    {
        "workflow": "workflow_filename.json",
        "prompt": "text prompt",
        "count": 4,  # Number of variations (1-10)
        "seeds": [123, 456, ...],  # Optional specific seeds
        "mode": "image_to_3d" | "text_to_3d" | "text_to_image",
        "image_path": "/path/to/image.png" (optional)
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing request body"}), 400

    workflow_name = data.get('workflow')
    prompt = data.get('prompt', '')
    count = min(data.get('count', 1), 10)  # Max 10 at a time
    seeds = data.get('seeds', [])
    mode = data.get('mode', 'text_to_image')
    image_path = data.get('image_path')

    if not workflow_name:
        return jsonify({"error": "Missing 'workflow' in request"}), 400

    # Generate random seeds if not provided
    import random
    while len(seeds) < count:
        seeds.append(random.randint(0, 2**32 - 1))

    batch_id = str(uuid.uuid4())
    batch_jobs = []

    for i, seed in enumerate(seeds[:count]):
        # Load workflow
        workflow_data = workflow_manager.load_workflow(workflow_name)
        if not workflow_data:
            continue

        # Set the seed
        workflow_data = workflow_manager.set_generation_defaults(
            workflow_data,
            seed=seed
        )

        # Modify prompt if provided
        if prompt:
            workflow_data = workflow_manager.modify_prompt(workflow_data, prompt)

        # Handle image input
        if image_path:
            input_image_name = _copy_image_to_input(image_path)
            if input_image_name:
                workflow_data = workflow_manager.modify_image_input(workflow_data, input_image_name)

        # Fetch object_info for proper conversion
        object_info = comfyui.get_object_info()
        if object_info:
            workflow_manager.set_object_info(object_info)

        # Convert and queue
        api_workflow = workflow_manager.convert_to_api_format(workflow_data)
        if not api_workflow:
            continue

        result = comfyui.queue_prompt(api_workflow)
        if result:
            job_id = str(uuid.uuid4())
            prompt_id = result.get('prompt_id')

            active_jobs[job_id] = {
                "prompt_id": prompt_id,
                "workflow": workflow_name,
                "mode": mode,
                "status": "queued",
                "seed": seed,
                "batch_id": batch_id,
                "batch_index": i,
                "created_at": datetime.now().isoformat()
            }

            batch_jobs.append({
                "job_id": job_id,
                "prompt_id": prompt_id,
                "seed": seed,
                "index": i
            })

    return jsonify({
        "success": True,
        "batch_id": batch_id,
        "jobs": batch_jobs,
        "count": len(batch_jobs),
        "message": f"Queued {len(batch_jobs)} jobs"
    })


@app.route('/api/queue', methods=['GET'])
def get_queue():
    """Get current queue status"""
    queue_info = comfyui.get_queue_info()
    return jsonify(queue_info)


@app.route('/api/queue/clear', methods=['POST'])
def clear_queue():
    """Clear all pending jobs from queue"""
    if comfyui.clear_queue():
        return jsonify({"success": True, "message": "Queue cleared"})
    return jsonify({"success": False, "error": "Failed to clear queue"}), 500


@app.route('/api/queue/<prompt_id>', methods=['DELETE'])
def delete_from_queue(prompt_id):
    """Delete a specific job from queue"""
    try:
        comfyui.cancel_prompt(prompt_id)
        return jsonify({"success": True, "message": f"Removed {prompt_id} from queue"})
    except Exception:
        return jsonify({"success": False, "error": "Failed to remove from queue"}), 500


@app.route('/api/interrupt', methods=['POST'])
def interrupt_current():
    """Interrupt currently running generation"""
    if comfyui.interrupt_execution():
        return jsonify({"success": True, "message": "Execution interrupted"})
    return jsonify({"success": False, "error": "Failed to interrupt"}), 500


@app.route('/api/validate', methods=['POST'])
def validate_workflow():
    """
    Validate a workflow before running

    Request:
    {
        "workflow": "workflow_filename.json"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing request body"}), 400

    workflow_name = data.get('workflow')
    if not workflow_name:
        return jsonify({"error": "Missing 'workflow' in request"}), 400

    # Fetch object_info for node validation
    object_info = comfyui.get_object_info()
    if object_info:
        workflow_manager.set_object_info(object_info)

    result = workflow_manager.validate_workflow(workflow_name)
    return jsonify(result)


@app.route('/api/job/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """Poll job status and get output path"""

    # First check our local job store
    if job_id in active_jobs:
        job = active_jobs[job_id]
        prompt_id = job['prompt_id']
        job_start_time = job.get('created_at')
    else:
        # Try treating job_id as a prompt_id directly
        prompt_id = job_id
        job = None
        job_start_time = None

    # Get status from ComfyUI
    status = comfyui.get_job_status(prompt_id)

    # Get output path if completed
    output_path = None
    if status['status'] == 'completed':
        # Pass job start time to filter out old files
        output_path = _get_output_glb_path(prompt_id, job_start_time)

        # If no output found with timestamp filter, log the issue
        if not output_path:
            print(f"[WARNING] Job {job_id} completed but no output file found newer than {job_start_time}")

        # Update job record
        if job:
            job['status'] = 'completed'
            job['output_path'] = output_path

    return jsonify({
        "job_id": job_id,
        "prompt_id": prompt_id,
        "status": status['status'],
        "progress": status.get('progress', 0),
        "output_path": output_path,
        "outputs": status.get('outputs', []),
        "error": status.get('error')
    })


@app.route('/api/jobs', methods=['GET'])
def list_jobs():
    """List all tracked jobs"""
    return jsonify({
        "jobs": active_jobs,
        "count": len(active_jobs)
    })


@app.route('/api/upload', methods=['POST'])
def upload_image():
    """
    Upload an image to ComfyUI input folder

    Accepts:
    - multipart/form-data with 'image' file
    - JSON with 'image_data' (base64)
    """
    if request.content_type and 'multipart/form-data' in request.content_type:
        # File upload
        if 'image' not in request.files:
            return jsonify({"error": "No image file provided"}), 400

        file = request.files['image']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        # Save to ComfyUI input folder
        filename = _generate_unique_filename(file.filename)
        input_path = COMFYUI_PATH / "input" / filename

        try:
            file.save(str(input_path))
            return jsonify({
                "success": True,
                "filename": filename,
                "path": str(input_path)
            })
        except Exception as e:
            return jsonify({"error": f"Failed to save file: {e}"}), 500

    else:
        # JSON with base64
        data = request.get_json()
        if not data or 'image_data' not in data:
            return jsonify({"error": "Missing 'image_data' in request"}), 400

        filename = _save_base64_image(data['image_data'])
        if filename:
            return jsonify({
                "success": True,
                "filename": filename
            })
        else:
            return jsonify({"error": "Failed to save image"}), 500


@app.route('/api/inpaint', methods=['POST'])
def inpaint():
    """
    Run inpainting workflow

    Request body:
    {
        "workflow": "EP19 SDXL INPAINT.json" (optional, uses default if not provided),
        "image_path": "/path/to/image_with_mask.png",
        "prompt": "what to generate in masked area",
        "negative_prompt": "what to avoid" (optional),
        "denoise": 0.75 (optional, 0.0-1.0)
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing request body"}), 400

    workflow_name = data.get('workflow', 'EP19 SDXL INPAINT.json')
    image_path = data.get('image_path')
    prompt = data.get('prompt', '')
    negative_prompt = data.get('negative_prompt', 'ugly, text, watermark')
    denoise = data.get('denoise', 0.75)

    if not image_path:
        return jsonify({"error": "Missing 'image_path'"}), 400

    # Load workflow
    workflow_data = workflow_manager.load_workflow(workflow_name)
    if not workflow_data:
        return jsonify({"error": f"Failed to load workflow: {workflow_name}"}), 400

    # Copy image to input folder
    input_image_name = _copy_image_to_input(image_path)
    if not input_image_name:
        return jsonify({"error": "Failed to copy input image"}), 500

    # Modify workflow
    workflow_data = workflow_manager.modify_image_input(workflow_data, input_image_name)
    workflow_data = workflow_manager.modify_prompt(workflow_data, prompt, negative_prompt)
    workflow_data = workflow_manager.modify_inpaint_settings(workflow_data, denoise)

    # Convert to API format
    api_workflow = workflow_manager.convert_to_api_format(workflow_data)
    if not api_workflow:
        return jsonify({"error": "Failed to convert workflow to API format"}), 500

    # Queue in ComfyUI
    result = comfyui.queue_prompt(api_workflow)
    if not result:
        return jsonify({"error": "Failed to queue inpainting workflow"}), 500

    prompt_id = result.get('prompt_id')
    job_id = str(uuid.uuid4())
    active_jobs[job_id] = {
        "prompt_id": prompt_id,
        "workflow": workflow_name,
        "type": "inpainting",
        "status": "queued"
    }

    return jsonify({
        "success": True,
        "job_id": job_id,
        "prompt_id": prompt_id,
        "message": "Inpainting job queued successfully"
    })


@app.route('/api/sketch-to-image', methods=['POST'])
def sketch_to_image():
    """
    Run sketch-to-image workflow

    Request body:
    {
        "workflow": "EP20 Flux Dev Q8 Sketch 2 Image.json" (optional),
        "image_path": "/path/to/sketch.png",
        "prompt": "description of what to generate",
        "negative_prompt": "what to avoid" (optional),
        "controlnet_strength": 0.8 (optional),
        "controlnet_end": 0.3 (optional)
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing request body"}), 400

    workflow_name = data.get('workflow', 'EP20 Flux Dev Q8 Sketch 2 Image.json')
    image_path = data.get('image_path')
    prompt = data.get('prompt', '')
    negative_prompt = data.get('negative_prompt', '')
    strength = data.get('controlnet_strength', 0.8)
    end_percent = data.get('controlnet_end', 0.3)

    if not image_path:
        return jsonify({"error": "Missing 'image_path'"}), 400
    if not prompt:
        return jsonify({"error": "Missing 'prompt'"}), 400

    # Load workflow
    workflow_data = workflow_manager.load_workflow(workflow_name)
    if not workflow_data:
        return jsonify({"error": f"Failed to load workflow: {workflow_name}"}), 400

    # Copy image to input folder
    input_image_name = _copy_image_to_input(image_path)
    if not input_image_name:
        return jsonify({"error": "Failed to copy input image"}), 500

    # Modify workflow
    workflow_data = workflow_manager.modify_image_input(workflow_data, input_image_name)
    workflow_data = workflow_manager.modify_prompt(workflow_data, prompt, negative_prompt)
    workflow_data = workflow_manager.set_generation_defaults(workflow_data)
    workflow_data = workflow_manager.modify_controlnet_settings(workflow_data, strength, 0.0, end_percent)

    # Convert to API format
    api_workflow = workflow_manager.convert_to_api_format(workflow_data)
    if not api_workflow:
        return jsonify({"error": "Failed to convert workflow to API format"}), 500

    # Queue in ComfyUI
    result = comfyui.queue_prompt(api_workflow)
    if not result:
        return jsonify({"error": "Failed to queue sketch-to-image workflow"}), 500

    prompt_id = result.get('prompt_id')
    job_id = str(uuid.uuid4())
    active_jobs[job_id] = {
        "prompt_id": prompt_id,
        "workflow": workflow_name,
        "type": "sketch_to_image",
        "status": "queued"
    }

    return jsonify({
        "success": True,
        "job_id": job_id,
        "prompt_id": prompt_id,
        "message": "Sketch-to-image job queued successfully"
    })


def _run_text_to_image(prompt: str, t2i_workflow: str = None) -> dict:
    """
    Run text-to-image workflow and wait for completion.

    Args:
        prompt: Text prompt for image generation
        t2i_workflow: Optional workflow name, defaults to DEFAULT_TEXT_TO_IMAGE_WORKFLOW

    Returns:
        dict with 'success', 'image_path' or 'error'
    """
    workflow_name = t2i_workflow or DEFAULT_TEXT_TO_IMAGE_WORKFLOW

    print(f"[Text-to-Image] Starting with workflow: {workflow_name}")
    print(f"[Text-to-Image] Prompt: {prompt[:100]}...")

    # Load the text-to-image workflow
    t2i_workflow_data = workflow_manager.load_workflow(workflow_name)
    if not t2i_workflow_data:
        return {"success": False, "error": f"Failed to load text-to-image workflow: {workflow_name}"}

    # Set default generation parameters (handles placeholder workflows like %model%, %sampler%)
    t2i_workflow_data = workflow_manager.set_generation_defaults(t2i_workflow_data)

    # Modify the prompt in the workflow
    t2i_workflow_data = workflow_manager.modify_prompt(t2i_workflow_data, prompt)

    # Note: Don't use object_info for widget mapping - the order doesn't match workflow JSON
    # The fallback mapping in _get_widget_inputs is correct for template workflows
    # object_info = comfyui.get_object_info()
    # if object_info:
    #     workflow_manager.set_object_info(object_info)

    # Convert to API format
    api_workflow = workflow_manager.convert_to_api_format(t2i_workflow_data)
    if not api_workflow:
        return {"success": False, "error": "Failed to convert text-to-image workflow to API format"}

    # Queue the workflow
    result = comfyui.queue_prompt(api_workflow)
    if not result:
        return {"success": False, "error": "Failed to queue text-to-image workflow"}

    prompt_id = result.get('prompt_id')
    print(f"[Text-to-Image] Queued with prompt_id: {prompt_id}")

    # Wait for completion (5 minute timeout for image generation)
    if not comfyui.wait_for_completion(prompt_id, timeout=300):
        return {"success": False, "error": "Text-to-image generation timed out"}

    print(f"[Text-to-Image] Generation completed")

    # Get the output image path
    status = comfyui.get_job_status(prompt_id)
    if status["status"] != "completed":
        return {"success": False, "error": f"Text-to-image job failed: {status.get('error')}"}

    # Find the output image
    output_images = [p for p in status.get("outputs", []) if p.endswith(('.png', '.jpg', '.jpeg', '.webp'))]

    if not output_images:
        # Try to find the most recent image in ComfyUI output folder
        output_folder = COMFYUI_PATH / "output"
        if output_folder.exists():
            # Find recent PNG files
            import glob
            recent_images = sorted(
                output_folder.glob("ComfyUI_*.png"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            if recent_images:
                output_images = [str(recent_images[0])]

    if not output_images:
        return {"success": False, "error": "No output image found from text-to-image generation"}

    # Get the first/primary output image
    image_path = output_images[0]

    # If it's a relative path, make it absolute
    if not Path(image_path).is_absolute():
        image_path = str(COMFYUI_PATH / "output" / image_path)

    print(f"[Text-to-Image] Output image: {image_path}")

    return {"success": True, "image_path": image_path}


def _save_base64_image(base64_data: str) -> str:
    """Save base64 encoded image to ComfyUI input folder"""
    try:
        # Remove data URL prefix if present
        if ',' in base64_data:
            base64_data = base64_data.split(',')[1]

        # Decode
        image_data = base64.b64decode(base64_data)

        # Generate filename
        filename = f"blender_input_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        input_path = COMFYUI_PATH / "input" / filename

        # Ensure input folder exists
        input_path.parent.mkdir(parents=True, exist_ok=True)

        # Save
        with open(input_path, 'wb') as f:
            f.write(image_data)

        print(f"Saved input image: {input_path}")
        return filename

    except Exception as e:
        print(f"Error saving base64 image: {e}")
        return None


def _copy_image_to_input(source_path: str) -> str:
    """Copy an image file to ComfyUI input folder"""
    try:
        source = Path(source_path)
        if not source.exists():
            print(f"Source image not found: {source_path}")
            return None

        # Generate filename
        filename = f"blender_input_{datetime.now().strftime('%Y%m%d_%H%M%S')}{source.suffix}"
        input_path = COMFYUI_PATH / "input" / filename

        # Ensure input folder exists
        input_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy
        shutil.copy2(source, input_path)

        print(f"Copied input image to: {input_path}")
        return filename

    except Exception as e:
        print(f"Error copying image: {e}")
        return None


def _generate_unique_filename(original_filename: str) -> str:
    """Generate a unique filename"""
    ext = Path(original_filename).suffix
    return f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}{ext}"


@app.route('/api/thumbnail', methods=['POST'])
def get_thumbnail():
    """
    Generate a thumbnail for a file

    Request:
    {
        "path": "/path/to/file.glb",
        "width": 256,  # optional
        "height": 256  # optional
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing request body"}), 400

    file_path = data.get('path')
    if not file_path:
        return jsonify({"error": "Missing 'path' in request"}), 400

    width = data.get('width', 256)
    height = data.get('height', 256)

    generator = get_thumbnail_generator()
    thumbnail = generator.get_thumbnail(file_path, (width, height))

    if thumbnail:
        return jsonify({
            "success": True,
            "thumbnail": thumbnail,
            "mime_type": "image/jpeg"
        })
    else:
        return jsonify({"error": "Failed to generate thumbnail"}), 500


@app.route('/api/outputs', methods=['GET'])
def list_outputs():
    """
    List recent output files with thumbnails

    Query params:
    - type: "image" | "3d" | "video" | "all" (default: all)
    - limit: max results (default: 20)
    """
    output_type = request.args.get('type', 'all')
    limit = int(request.args.get('limit', 20))

    output_dir = COMFYUI_PATH / "output"
    outputs = []

    # Define patterns for each type
    patterns = {
        'image': ['*.png', '*.jpg', '*.jpeg', '*.webp'],
        '3d': ['**/*.glb', '**/*.gltf'],
        'video': ['*.mp4', '*.webm', '*.mov']
    }

    if output_type == 'all':
        search_patterns = patterns['image'] + patterns['3d'] + patterns['video']
    else:
        search_patterns = patterns.get(output_type, [])

    # Collect files
    files = []
    for pattern in search_patterns:
        files.extend(output_dir.glob(pattern))

    # Sort by modification time (newest first)
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

    # Limit results
    files = files[:limit]

    # Generate response with thumbnails
    generator = get_thumbnail_generator()
    for f in files:
        file_info = {
            "path": str(f),
            "name": f.name,
            "size": f.stat().st_size,
            "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            "type": _get_file_type(f.suffix)
        }

        # Optionally include thumbnail (can be slow for many files)
        # thumbnail = generator.get_thumbnail(str(f), (128, 128))
        # if thumbnail:
        #     file_info["thumbnail"] = thumbnail

        outputs.append(file_info)

    return jsonify({
        "outputs": outputs,
        "count": len(outputs)
    })


def _get_output_glb_path(prompt_id: str, job_start_time: str = None) -> str:
    """
    Get the GLB output path for a completed job.

    Args:
        prompt_id: The ComfyUI prompt ID
        job_start_time: ISO format timestamp of when job was created.

    Returns the full path to the GLB file or None if not found.
    """
    status = comfyui.get_job_status(prompt_id)

    if status["status"] != "completed":
        return None

    # Convert job_start_time to unix timestamp for filtering
    min_mtime = None
    if job_start_time:
        try:
            dt = datetime.fromisoformat(job_start_time.replace('Z', '+00:00'))
            min_mtime = dt.timestamp() - 5  # 5 second buffer
        except Exception:
            pass

    # Look for GLB files in outputs
    for output in status["outputs"]:
        if output.endswith('.glb') or output.endswith('.gltf'):
            if not Path(output).is_absolute():
                full_path = OUTPUT_3D_PATH / output
                if full_path.exists():
                    if min_mtime and full_path.stat().st_mtime < min_mtime:
                        continue
                    return str(full_path)
                full_path = COMFYUI_PATH / "output" / output
                if full_path.exists():
                    if min_mtime and full_path.stat().st_mtime < min_mtime:
                        continue
                    return str(full_path)
            else:
                if Path(output).exists():
                    if min_mtime and Path(output).stat().st_mtime < min_mtime:
                        continue
                    return output

    # If no outputs found, try to find the file from the workflow
    try:
        history = comfyui.get_history(prompt_id)
    except Exception:
        history = {}
    if history and prompt_id in history:
        prompt_data = history[prompt_id].get('prompt', [])
        if len(prompt_data) >= 3:
            workflow = prompt_data[2]
            glb_path = _find_glb_from_workflow(workflow, min_mtime)
            if glb_path:
                return glb_path

    return None


def _find_glb_from_workflow(workflow: dict, min_mtime: float = None) -> str:
    """Find the GLB file based on export node settings in workflow."""
    for node_id, node_data in workflow.items():
        class_type = node_data.get('class_type', '')
        inputs = node_data.get('inputs', {})

        if class_type in ['TripoSGExportMesh', 'Hy3DExportMesh', 'SaveGLB', 'ExportMesh',
                          'Hy3DExportGLB', 'ExportGLB', 'Save3DModel']:
            filename_prefix = inputs.get('filename_prefix', '3D/output')
            file_format = inputs.get('file_format', inputs.get('format', 'glb'))

            search_dir = COMFYUI_PATH / "output"
            if '/' in filename_prefix:
                subdir = filename_prefix.rsplit('/', 1)[0]
                search_dir = search_dir / subdir
                prefix = filename_prefix.rsplit('/', 1)[1]
            else:
                prefix = filename_prefix

            if search_dir.exists():
                pattern = f"{prefix}_*.{file_format}"
                matching_files = list(search_dir.glob(pattern))

                if min_mtime and matching_files:
                    matching_files = [
                        f for f in matching_files
                        if f.stat().st_mtime >= min_mtime
                    ]

                if matching_files:
                    newest = max(matching_files, key=lambda p: p.stat().st_mtime)
                    return str(newest)

    return None


def _get_file_type(suffix: str) -> str:
    """Get the file type from extension"""
    suffix = suffix.lower()
    if suffix in ['.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif']:
        return 'image'
    elif suffix in ['.glb', '.gltf']:
        return '3d'
    elif suffix in ['.mp4', '.webm', '.mov', '.avi']:
        return 'video'
    return 'unknown'


if __name__ == '__main__':
    print(f"Starting ComfyUI Prompter API Server on {API_SERVER_HOST}:{API_SERVER_PORT}")
    print(f"ComfyUI URL: {COMFYUI_URL}")
    print(f"Output 3D Path: {OUTPUT_3D_PATH}")

    # Check connections on startup
    if comfyui.is_available():
        print("ComfyUI: Connected")
    else:
        print("ComfyUI: NOT CONNECTED - Please start ComfyUI first")

    if recommender.check_ollama_available():
        print("Ollama: Connected")
    else:
        print("Ollama: NOT CONNECTED - AI recommendations will use fallback mode")

    print("\nAPI Endpoints:")
    print("  GET  /api/status         - Check connectivity")
    print("  POST /api/analyze        - Get AI recommendation")
    print("  GET  /api/workflows      - List workflows")
    print("  POST /api/generate       - Start generation (3D, text-to-3D)")
    print("  POST /api/inpaint        - Run inpainting workflow")
    print("  POST /api/sketch-to-image - Run sketch-to-image workflow")
    print("  GET  /api/job/<id>       - Get job status")
    print("  POST /api/upload         - Upload image")

    app.run(host=API_SERVER_HOST, port=API_SERVER_PORT, debug=True)

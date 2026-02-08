# workflow_manager.py - Handles loading and modifying ComfyUI workflow JSON files

import json
from pathlib import Path
from typing import Dict, Optional, List
from config import COMFYUI_WORKFLOWS_PATH, WORKFLOWS


class WorkflowManager:
    """Manages ComfyUI workflow JSON files"""
    
    def __init__(self, workflows_path: Path = COMFYUI_WORKFLOWS_PATH):
        self.workflows_path = Path(workflows_path)
        
    def load_workflow(self, workflow_filename: str) -> Optional[Dict]:
        """Load a workflow JSON file"""
        workflow_path = self.workflows_path / workflow_filename
        
        if not workflow_path.exists():
            print(f"Workflow not found: {workflow_path}")
            return None
        
        try:
            with open(workflow_path, 'r', encoding='utf-8') as f:
                workflow_data = json.load(f)
            return workflow_data
        except Exception as e:
            print(f"Error loading workflow {workflow_filename}: {e}")
            return None
    
    def modify_checkpoint(self, workflow_data: Dict, checkpoint_name: str) -> Dict:
        """
        Modify the workflow to use a different checkpoint
        
        This is the tricky part - we need to find where checkpoints are referenced
        in the workflow and update them. Different workflows have different structures.
        """
        if workflow_data is None:
            return None
        
        # Make a deep copy to avoid modifying the original
        import copy
        modified_workflow = copy.deepcopy(workflow_data)
        
        # Look for checkpoint loaders in the nodes
        nodes = modified_workflow.get('nodes', [])
        
        for node in nodes:
            node_type = node.get('type', '')
            
            # Common checkpoint loader node types
            if node_type in ['CheckpointLoaderSimple', 'CheckpointLoader']:
                # Update the checkpoint in widgets_values
                if 'widgets_values' in node and len(node['widgets_values']) > 0:
                    print(f"Found checkpoint loader: {node_type}, updating checkpoint to {checkpoint_name}")
                    node['widgets_values'][0] = checkpoint_name
            
            # For image-only checkpoint loaders (used in 3D workflows)
            elif node_type == 'ImageOnlyCheckpointLoader':
                if 'widgets_values' in node and len(node['widgets_values']) > 0:
                    print(f"Found ImageOnlyCheckpointLoader, updating to {checkpoint_name}")
                    node['widgets_values'][0] = checkpoint_name
            
            # For UNET loaders (used in some video workflows)
            elif node_type == 'UNETLoader':
                if 'widgets_values' in node and len(node['widgets_values']) > 0:
                    print(f"Found UNETLoader, updating to {checkpoint_name}")
                    node['widgets_values'][0] = checkpoint_name
        
        return modified_workflow
    
    def modify_prompt(self, workflow_data: Dict, positive_prompt: str, negative_prompt: str = "") -> Dict:
        """
        Modify the positive and negative prompts in the workflow

        Handles multiple workflow formats:
        1. Nodes with 'positive'/'negative' in title
        2. Nodes with placeholder strings like %prompt%, %negative_prompt%
        3. First CLIPTextEncode as positive, second as negative (fallback)
        """
        if workflow_data is None:
            return None

        import copy
        modified_workflow = copy.deepcopy(workflow_data)

        nodes = modified_workflow.get('nodes', [])

        # Track which nodes we've updated
        positive_updated = False
        negative_updated = False
        clip_encode_nodes = []

        for node in nodes:
            node_type = node.get('type', '')

            # Look for CLIP text encode nodes
            if node_type == 'CLIPTextEncode':
                clip_encode_nodes.append(node)
                title = node.get('title', '').lower()

                # Method 1: Check title for positive/negative
                if 'positive' in title:
                    if 'widgets_values' in node and len(node['widgets_values']) > 0:
                        print(f"Updating positive prompt (by title)")
                        node['widgets_values'][0] = positive_prompt
                        positive_updated = True

                elif 'negative' in title:
                    if 'widgets_values' in node and len(node['widgets_values']) > 0:
                        print(f"Updating negative prompt (by title)")
                        node['widgets_values'][0] = negative_prompt if negative_prompt else "ugly, blurry, low quality"
                        negative_updated = True

                # Method 2: Check for placeholder strings
                elif 'widgets_values' in node and len(node['widgets_values']) > 0:
                    current_value = str(node['widgets_values'][0])

                    if '%prompt%' in current_value or current_value == '%prompt%':
                        print(f"Updating positive prompt (placeholder)")
                        node['widgets_values'][0] = positive_prompt
                        positive_updated = True

                    elif '%negative_prompt%' in current_value or '%negative%' in current_value:
                        print(f"Updating negative prompt (placeholder)")
                        node['widgets_values'][0] = negative_prompt if negative_prompt else "ugly, blurry, low quality"
                        negative_updated = True

        # Method 3: Fallback - use node order (first = positive, second = negative)
        if not positive_updated and len(clip_encode_nodes) >= 1:
            node = clip_encode_nodes[0]
            if 'widgets_values' in node and len(node['widgets_values']) > 0:
                print(f"Updating positive prompt (by order - first CLIPTextEncode)")
                node['widgets_values'][0] = positive_prompt
                positive_updated = True

        if not negative_updated and len(clip_encode_nodes) >= 2:
            node = clip_encode_nodes[1]
            if 'widgets_values' in node and len(node['widgets_values']) > 0:
                print(f"Updating negative prompt (by order - second CLIPTextEncode)")
                node['widgets_values'][0] = negative_prompt if negative_prompt else "ugly, blurry, low quality"
                negative_updated = True

        return modified_workflow
    
    def set_generation_defaults(self, workflow_data: Dict,
                                  checkpoint: str = "flux1-dev-fp8.safetensors",
                                  width: int = 1024,
                                  height: int = 1024,
                                  steps: int = 20,
                                  cfg: float = 7.0,
                                  seed: int = None,
                                  sampler: str = "euler",
                                  scheduler: str = "normal",
                                  denoise: float = 1.0) -> Dict:
        """
        Set default generation parameters for placeholder-based workflows.

        Handles workflows that use placeholders like %model%, %sampler%, etc.
        and fills in null values with sensible defaults.
        """
        if workflow_data is None:
            return None

        import copy
        import random
        modified_workflow = copy.deepcopy(workflow_data)

        # Generate random seed if not provided
        if seed is None:
            seed = random.randint(0, 2**32 - 1)

        nodes = modified_workflow.get('nodes', [])

        for node in nodes:
            node_type = node.get('type', '')
            widgets = node.get('widgets_values', [])

            # CheckpointLoaderSimple - set checkpoint name
            if node_type in ['CheckpointLoaderSimple', 'CheckpointLoader']:
                if widgets and len(widgets) > 0:
                    if widgets[0] == '%model%' or widgets[0] is None:
                        print(f"Setting checkpoint to {checkpoint}")
                        node['widgets_values'][0] = checkpoint

            # EmptyLatentImage - set width, height, batch_size
            elif node_type == 'EmptyLatentImage':
                if widgets:
                    # widgets_values: [width, height, batch_size]
                    if len(widgets) >= 1 and (widgets[0] is None or widgets[0] == '%width%'):
                        node['widgets_values'][0] = width
                    if len(widgets) >= 2 and (widgets[1] is None or widgets[1] == '%height%'):
                        node['widgets_values'][1] = height
                    if len(widgets) >= 3 and widgets[2] is None:
                        node['widgets_values'][2] = 1  # batch_size
                    print(f"Setting image size to {width}x{height}")

            # KSampler - set seed, steps, cfg, sampler, scheduler, denoise
            elif node_type == 'KSampler':
                if widgets and len(widgets) >= 7:
                    # widgets_values: [seed, control_after_generate, steps, cfg, sampler_name, scheduler, denoise]
                    new_widgets = list(widgets)

                    # Position 0: seed
                    if new_widgets[0] is None or new_widgets[0] == '%seed%':
                        new_widgets[0] = seed

                    # Position 1: control_after_generate - keep as is ("randomize" or "fixed")

                    # Position 2: steps
                    if new_widgets[2] is None or new_widgets[2] == '%steps%':
                        new_widgets[2] = steps

                    # Position 3: cfg
                    if new_widgets[3] is None or new_widgets[3] == '%cfg%':
                        new_widgets[3] = cfg

                    # Position 4: sampler_name
                    if new_widgets[4] is None or (isinstance(new_widgets[4], str) and '%' in new_widgets[4]):
                        new_widgets[4] = sampler

                    # Position 5: scheduler
                    if new_widgets[5] is None or (isinstance(new_widgets[5], str) and '%' in new_widgets[5]):
                        new_widgets[5] = scheduler

                    # Position 6: denoise (usually 1.0 for text-to-image)
                    if new_widgets[6] is None or new_widgets[6] == '%denoise%':
                        new_widgets[6] = denoise

                    node['widgets_values'] = new_widgets
                    print(f"Setting KSampler: seed={seed}, steps={steps}, cfg={cfg}, sampler={sampler}, scheduler={scheduler}")

        return modified_workflow

    def modify_image_input(self, workflow_data: Dict, image_filename: str) -> Dict:
        """
        Modify the workflow to use a specific input image

        Args:
            workflow_data: The workflow dictionary
            image_filename: The filename of the image to use (must be in ComfyUI input folder)

        Returns:
            Modified workflow dictionary
        """
        if workflow_data is None:
            return None

        import copy
        modified_workflow = copy.deepcopy(workflow_data)

        nodes = modified_workflow.get('nodes', [])

        for node in nodes:
            node_type = node.get('type', '')

            # Look for LoadImage nodes
            if node_type == 'LoadImage':
                if 'widgets_values' in node and len(node['widgets_values']) > 0:
                    print(f"Found LoadImage node, updating image to {image_filename}")
                    node['widgets_values'][0] = image_filename
                    # Keep the second value as "image" if it exists
                    if len(node['widgets_values']) < 2:
                        node['widgets_values'].append("image")

        return modified_workflow

    def modify_inpaint_settings(self, workflow_data: Dict, denoise: float = 0.75) -> Dict:
        """
        Modify inpainting-specific settings in the workflow.

        Args:
            workflow_data: The workflow dictionary
            denoise: Denoise strength for inpainting (0.0-1.0, default 0.75)

        Returns:
            Modified workflow dictionary
        """
        if workflow_data is None:
            return None

        import copy
        modified_workflow = copy.deepcopy(workflow_data)
        nodes = modified_workflow.get('nodes', [])

        for node in nodes:
            node_type = node.get('type', '')

            # Set denoise for KSampler in inpainting workflows
            if node_type == 'KSampler':
                widgets = node.get('widgets_values', [])
                if widgets and len(widgets) >= 7:
                    # widgets_values: [seed, control_after_generate, steps, cfg, sampler_name, scheduler, denoise]
                    node['widgets_values'][6] = denoise
                    print(f"Set inpaint denoise to {denoise}")

        return modified_workflow

    def modify_controlnet_settings(self, workflow_data: Dict,
                                    strength: float = 0.8,
                                    start_percent: float = 0.0,
                                    end_percent: float = 0.3) -> Dict:
        """
        Modify ControlNet settings for sketch-to-image workflows.

        Args:
            workflow_data: The workflow dictionary
            strength: ControlNet strength (0.0-1.0)
            start_percent: Start percentage for ControlNet application
            end_percent: End percentage for ControlNet application

        Returns:
            Modified workflow dictionary
        """
        if workflow_data is None:
            return None

        import copy
        modified_workflow = copy.deepcopy(workflow_data)
        nodes = modified_workflow.get('nodes', [])

        for node in nodes:
            node_type = node.get('type', '')

            if node_type == 'ControlNetApplyAdvanced':
                widgets = node.get('widgets_values', [])
                if widgets and len(widgets) >= 3:
                    # widgets_values: [strength, start_percent, end_percent]
                    node['widgets_values'][0] = strength
                    node['widgets_values'][1] = start_percent
                    node['widgets_values'][2] = end_percent
                    print(f"Set ControlNet: strength={strength}, start={start_percent}, end={end_percent}")

        return modified_workflow

    def detect_workflow_type(self, workflow_data: Dict) -> str:
        """
        Detect the type of workflow based on node types present.

        Returns:
            One of: 'inpainting', 'sketch_to_image', 'image_to_3d', 'text_to_image', 'video', 'unknown'
        """
        if workflow_data is None:
            return 'unknown'

        nodes = workflow_data.get('nodes', [])
        node_types = {node.get('type', '') for node in nodes}

        # Check for inpainting nodes
        if 'InpaintModelConditioning' in node_types or 'InpaintCropImproved' in node_types:
            return 'inpainting'

        # Check for ControlNet (sketch-to-image)
        if 'ControlNetApplyAdvanced' in node_types or 'AIO_Preprocessor' in node_types:
            return 'sketch_to_image'

        # Check for 3D generation
        if 'TripoSGModelLoader' in node_types or 'Hy3DModelLoader' in node_types:
            return 'image_to_3d'

        # Check for video generation
        if 'WanVideoSampler' in node_types or 'HunyuanVideoSampler' in node_types:
            return 'video'

        # Default to text-to-image
        if 'KSampler' in node_types and 'CLIPTextEncode' in node_types:
            return 'text_to_image'

        return 'unknown'

    def get_3d_workflows(self) -> Dict:
        """
        Get all 3D generation workflows

        Returns:
            Dictionary of workflow_filename -> workflow_info for 3D workflows
        """
        return {
            name: info for name, info in WORKFLOWS.items()
            if info.get('type') == '3d_generation'
        }

    def get_image_generation_workflows(self) -> Dict:
        """
        Get all 2D image generation workflows

        Returns:
            Dictionary of workflow_filename -> workflow_info for 2D workflows
        """
        return {
            name: info for name, info in WORKFLOWS.items()
            if info.get('type') == '2d_image'
        }

    def convert_to_api_format(self, workflow_data: Dict) -> Dict:
        """
        Convert workflow from UI format (nodes array) to API format (dict with class_type/inputs)

        ComfyUI UI saves workflows with a 'nodes' array, but the API expects:
        {
            "node_id": {
                "class_type": "NodeType",
                "inputs": {...}
            }
        }
        """
        if workflow_data is None:
            return None

        # If already in API format (no 'nodes' key, has string keys with 'class_type')
        if 'nodes' not in workflow_data:
            # Check if it's already API format
            for key, value in workflow_data.items():
                if isinstance(value, dict) and 'class_type' in value:
                    return workflow_data
            return workflow_data

        nodes = workflow_data.get('nodes', [])
        links = workflow_data.get('links', [])

        # Build node lookup: node_id -> node
        node_lookup = {node.get('id'): node for node in nodes}

        # Build a link lookup: link_id -> (source_node_id, source_slot)
        link_lookup = {}
        for link in links:
            # link format: [link_id, source_node_id, source_slot, target_node_id, target_slot, type]
            if len(link) >= 5:
                link_id = link[0]
                source_node_id = link[1]
                source_slot = link[2]
                link_lookup[link_id] = (source_node_id, source_slot)

        def resolve_reroute(node_id, slot, visited=None):
            """Follow Reroute nodes to find actual source"""
            if visited is None:
                visited = set()
            if node_id in visited:
                return node_id, slot  # Cycle detected
            visited.add(node_id)

            node = node_lookup.get(node_id)
            if not node:
                return node_id, slot

            node_type = node.get('type', '')
            if node_type == 'Reroute':
                # Reroute has single input, follow it
                node_inputs = node.get('inputs', [])
                if node_inputs:
                    link_id = node_inputs[0].get('link')
                    if link_id is not None and link_id in link_lookup:
                        src_id, src_slot = link_lookup[link_id]
                        return resolve_reroute(src_id, src_slot, visited)
            return node_id, slot

        def get_primitive_value(node_id):
            """Get the value from a PrimitiveNode"""
            node = node_lookup.get(node_id)
            if not node or node.get('type') != 'PrimitiveNode':
                return None
            widgets = node.get('widgets_values', [])
            if widgets:
                return widgets[0]
            return None

        api_workflow = {}

        for node in nodes:
            node_id = str(node.get('id'))
            class_type = node.get('type', '')

            # Skip certain UI-only nodes (they are resolved through connections)
            if class_type in ['Note', 'Reroute', 'PrimitiveNode', 'MarkdownNote', 'SetNode', 'GetNode']:
                continue

            inputs = {}

            # Get widget values and map them to input names
            widgets_values = node.get('widgets_values', [])

            # Get the node's input definitions
            node_inputs = node.get('inputs', [])

            # Process connected inputs
            for inp in node_inputs:
                inp_name = inp.get('name')
                link_id = inp.get('link')

                if link_id is not None and link_id in link_lookup:
                    source_node_id, source_slot = link_lookup[link_id]

                    # Resolve Reroute nodes to find actual source
                    actual_source_id, actual_slot = resolve_reroute(source_node_id, source_slot)

                    # Check if source is a PrimitiveNode - inline the value
                    source_node = node_lookup.get(actual_source_id)
                    if source_node and source_node.get('type') == 'PrimitiveNode':
                        prim_value = get_primitive_value(actual_source_id)
                        if prim_value is not None:
                            inputs[inp_name] = prim_value
                    else:
                        # Reference format: [node_id_string, slot_index]
                        inputs[inp_name] = [str(actual_source_id), actual_slot]

            # Process widget values - this is tricky as we need to know the widget names
            # For common node types, map widget_values to input names
            widget_inputs = self._get_widget_inputs(class_type, widgets_values, node)

            # Merge widget inputs (don't overwrite connected inputs)
            for key, value in widget_inputs.items():
                if key not in inputs:
                    inputs[key] = value

            api_workflow[node_id] = {
                "class_type": class_type,
                "inputs": inputs
            }

        return api_workflow

    def _get_widget_inputs(self, class_type: str, widgets_values: list, node: dict) -> Dict:
        """
        Map widget_values to input names based on node type

        This is node-type specific since ComfyUI doesn't store widget names in the workflow
        """
        inputs = {}

        if not widgets_values:
            return inputs

        # Get list of connected inputs (these shouldn't receive widget values)
        connected_inputs = set()
        if node:
            for inp in node.get('inputs', []):
                if inp.get('link') is not None:
                    connected_inputs.add(inp.get('name'))

        # Try to get widget names from cached object_info
        if hasattr(self, '_object_info') and self._object_info:
            node_info = self._object_info.get(class_type, {})
            if node_info:
                required = node_info.get('input', {}).get('required', {})
                optional = node_info.get('input', {}).get('optional', {})

                # Build widget info: name -> (expected_type, allowed_values or None)
                widget_info = {}
                for name, spec in required.items():
                    if isinstance(spec, list) and len(spec) > 0:
                        if isinstance(spec[0], list):
                            widget_info[name] = ('ENUM', spec[0])
                        elif spec[0] in ['INT', 'FLOAT', 'STRING', 'BOOLEAN']:
                            widget_info[name] = (spec[0], None)

                for name, spec in optional.items():
                    if isinstance(spec, list) and len(spec) > 0:
                        if isinstance(spec[0], list):
                            widget_info[name] = ('ENUM', spec[0])
                        elif spec[0] in ['INT', 'FLOAT', 'STRING', 'BOOLEAN']:
                            widget_info[name] = (spec[0], None)

                # Get ordered list of widget names
                widget_names = list(widget_info.keys())

                # Map widget values, validating types
                value_idx = 0
                for i, value in enumerate(widgets_values):
                    if value_idx >= len(widget_names):
                        break

                    name = widget_names[value_idx]
                    expected_type, allowed_values = widget_info[name]

                    # Skip if this input is connected (value comes from connection)
                    if name in connected_inputs:
                        value_idx += 1
                        continue

                    # Validate and convert the value
                    try:
                        if expected_type == 'INT':
                            if isinstance(value, (int, float)) and not isinstance(value, bool):
                                inputs[name] = int(value)
                                value_idx += 1
                            else:
                                # Value doesn't match expected type, might be from old workflow
                                # Skip this value and try the next widget with this value
                                continue
                        elif expected_type == 'FLOAT':
                            if isinstance(value, (int, float)) and not isinstance(value, bool):
                                inputs[name] = float(value)
                                value_idx += 1
                            else:
                                continue
                        elif expected_type == 'BOOLEAN':
                            if isinstance(value, bool):
                                inputs[name] = value
                                value_idx += 1
                            else:
                                continue
                        elif expected_type == 'ENUM':
                            # Check if value is in allowed values
                            if allowed_values and value in allowed_values:
                                inputs[name] = value
                                value_idx += 1
                            elif allowed_values and str(value) in allowed_values:
                                inputs[name] = str(value)
                                value_idx += 1
                            elif allowed_values and isinstance(value, str):
                                # Try to match by filename (for model/file paths)
                                # e.g., "hy3dgen\\model.safetensors" -> "model.safetensors"
                                value_filename = value.replace('\\', '/').split('/')[-1]
                                matched = None
                                for av in allowed_values:
                                    av_filename = av.replace('\\', '/').split('/')[-1]
                                    if value_filename == av_filename:
                                        matched = av
                                        break
                                if matched:
                                    inputs[name] = matched
                                    value_idx += 1
                                elif '.' in value_filename:
                                    # Looks like a file path, use as-is and let ComfyUI validate
                                    inputs[name] = value
                                    value_idx += 1
                                else:
                                    # Not a file path, value not in allowed list - skip
                                    continue
                            else:
                                # Non-string value or no allowed values, skip
                                continue
                        elif expected_type == 'STRING':
                            inputs[name] = str(value) if value is not None else ''
                            value_idx += 1
                        else:
                            inputs[name] = value
                            value_idx += 1
                    except (ValueError, TypeError):
                        continue

                return inputs

        # Fallback: Common node type mappings (may be outdated)
        widget_mappings = {
            # Standard ComfyUI nodes
            'LoadImage': ['image', 'upload'],
            'CheckpointLoaderSimple': ['ckpt_name'],
            'CLIPTextEncode': ['text'],
            'KSampler': ['seed', 'control_after_generate', 'steps', 'cfg', 'sampler_name', 'scheduler', 'denoise'],
            'EmptyLatentImage': ['width', 'height', 'batch_size'],
            'VAEDecode': [],
            'SaveImage': ['filename_prefix'],
            'PreviewImage': [],
            'UpscaleModelLoader': ['model_name'],
            'ImageCompositeMasked': ['x', 'y', 'resize_source'],

            # Hunyuan3D nodes
            'Hy3DModelLoader': ['model', 'attention_mode', 'use_fp8'],
            'Hy3DCameraConfig': ['camera_azimuths', 'camera_elevations', 'view_weights', 'camera_distance', 'ortho_scale'],
            'Hy3DExportMesh': ['filename_prefix', 'file_format', 'embed_textures'],
            'Hy3DPostprocessMesh': ['smooth_normals', 'remove_degenerate_faces', 'max_facenum', 'reduce_faces', 'remove_floaters'],
            'Hy3DVAEDecode': ['box_v', 'mc_level', 'num_chunks', 'octree_resolution', 'mc_algo'],
            'Hy3DRenderMultiView': ['render_size', 'texture_size'],
            'Hy3DDiffusersSchedulerConfig': ['scheduler', 'sigmas'],
            'Hy3DSampleMultiView': ['seed', 'steps', 'cfg', 'embedded_guidance', 'denoise', 'tile_size', 'tile_stride'],
            'Hy3DDelightImage': [],
            'Hy3DGenerateMesh': [],
            'Hy3DMeshUVWrap': [],
            'Hy3DApplyTexture': [],
            'DownloadAndLoadHy3DPaintModel': ['model'],
            'CV2InpaintTexture': ['inpaint_method', 'inpaint_radius'],

            # Impact Pack / ComfyUI-Impact-Pack nodes
            'ImageResize+': ['width', 'height', 'method', 'interpolation', 'condition', 'multiple_of'],
            'ImageRemoveBackground+': ['model', 'alpha_matting', 'alpha_matting_foreground_threshold', 'alpha_matting_background_threshold', 'alpha_matting_erode_size', 'post_process_mask'],

            # TripoSG / 3D nodes
            'TripoSGLoader': [],
            'TripoSGSampler': ['seed', 'seed_mode'],
            'TripoSGMeshExtractor': ['mc_level', 'edge_threshold'],
            'TripoSGSaveMesh': ['filename_prefix', 'file_format'],
            'Preview3D': ['model_file', 'image', 'width', 'height'],
        }

        widget_names = widget_mappings.get(class_type, [])

        # For unknown nodes, try to use input definitions from node itself
        if not widget_names and node:
            node_inputs = node.get('inputs', [])
            # Get names of inputs that have widget definitions
            for inp in node_inputs:
                if inp.get('widget'):
                    widget_names.append(inp['widget'].get('name', inp.get('name')))

        for i, value in enumerate(widgets_values):
            if i < len(widget_names):
                name = widget_names[i]
                if name:
                    inputs[name] = value

        return inputs

    def set_object_info(self, object_info: Dict):
        """Set the object_info cache from ComfyUI"""
        self._object_info = object_info

    def save_workflow(self, workflow_data: Dict, output_filename: str) -> bool:
        """Save modified workflow to a new file"""
        output_path = self.workflows_path / output_filename
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(workflow_data, f, indent=2)
            print(f"Workflow saved to: {output_path}")
            return True
        except Exception as e:
            print(f"Error saving workflow: {e}")
            return False
    
    def get_available_workflows(self) -> List[str]:
        """Get list of all available workflow JSON files"""
        if not self.workflows_path.exists():
            print(f"Workflows path does not exist: {self.workflows_path}")
            return []
        
        workflow_files = []
        for file in self.workflows_path.glob("*.json"):
            workflow_files.append(file.name)
        
        return sorted(workflow_files)
    
    def get_workflow_info(self, workflow_filename: str) -> Optional[Dict]:
        """Get information about a workflow from the config"""
        return WORKFLOWS.get(workflow_filename)
    
    def check_required_models(self, workflow_filename: str) -> Dict:
        """
        Check if the required models for a workflow are available
        
        Returns:
            {
                "has_checkpoint": bool,
                "checkpoint_path": Path or None,
                "missing_models": [list of missing model names]
            }
        """
        workflow_info = self.get_workflow_info(workflow_filename)
        
        if not workflow_info:
            return {
                "has_checkpoint": False,
                "checkpoint_path": None,
                "missing_models": ["Workflow not found in config"]
            }
        
        required_checkpoint = workflow_info.get('checkpoint')
        
        # If no checkpoint is required (like SVG conversion), return success
        if required_checkpoint is None:
            return {
                "has_checkpoint": True,
                "checkpoint_path": None,
                "missing_models": []
            }
        
        # Check if checkpoint exists
        from config import COMFYUI_CHECKPOINTS_PATH, COMFYUI_DIFFUSION_MODELS_PATH
        
        checkpoint_locations = [
            COMFYUI_CHECKPOINTS_PATH / required_checkpoint,
            COMFYUI_DIFFUSION_MODELS_PATH / required_checkpoint,
        ]
        
        for checkpoint_path in checkpoint_locations:
            if checkpoint_path.exists():
                return {
                    "has_checkpoint": True,
                    "checkpoint_path": checkpoint_path,
                    "missing_models": []
                }
        
        # Checkpoint not found
        return {
            "has_checkpoint": False,
            "checkpoint_path": None,
            "missing_models": [required_checkpoint]
        }

    def validate_workflow(self, workflow_filename: str) -> Dict:
        """
        Comprehensive workflow validation - checks all required models and custom nodes

        Returns:
            {
                "valid": bool,
                "errors": [list of error messages],
                "warnings": [list of warning messages],
                "missing_models": [list of missing model names],
                "missing_nodes": [list of missing custom node types],
                "required_models": {
                    "checkpoints": [list],
                    "loras": [list],
                    "vaes": [list],
                    "upscale_models": [list],
                    "controlnets": [list],
                    "diffusion_models": [list]
                }
            }
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "missing_models": [],
            "missing_nodes": [],
            "required_models": {
                "checkpoints": [],
                "loras": [],
                "vaes": [],
                "upscale_models": [],
                "controlnets": [],
                "diffusion_models": []
            }
        }

        # Load workflow
        workflow_data = self.load_workflow(workflow_filename)
        if not workflow_data:
            result["valid"] = False
            result["errors"].append(f"Failed to load workflow: {workflow_filename}")
            return result

        # Get nodes from workflow
        nodes = workflow_data.get('nodes', [])
        if not nodes:
            # Might be API format
            nodes = [{"type": v.get("class_type"), "id": k, **v}
                     for k, v in workflow_data.items()
                     if isinstance(v, dict) and "class_type" in v]

        # Model loader node types and their model paths
        from config import (COMFYUI_CHECKPOINTS_PATH, COMFYUI_DIFFUSION_MODELS_PATH,
                           COMFYUI_PATH)

        model_loaders = {
            'CheckpointLoaderSimple': ('checkpoints', COMFYUI_CHECKPOINTS_PATH, 'ckpt_name'),
            'CheckpointLoader': ('checkpoints', COMFYUI_CHECKPOINTS_PATH, 'ckpt_name'),
            'LoraLoader': ('loras', COMFYUI_PATH / 'models' / 'loras', 'lora_name'),
            'LoraLoaderModelOnly': ('loras', COMFYUI_PATH / 'models' / 'loras', 'lora_name'),
            'VAELoader': ('vaes', COMFYUI_PATH / 'models' / 'vae', 'vae_name'),
            'UpscaleModelLoader': ('upscale_models', COMFYUI_PATH / 'models' / 'upscale_models', 'model_name'),
            'ControlNetLoader': ('controlnets', COMFYUI_PATH / 'models' / 'controlnet', 'control_net_name'),
            'Hy3DModelLoader': ('diffusion_models', COMFYUI_DIFFUSION_MODELS_PATH, 'model'),
            'DownloadAndLoadHy3DPaintModel': ('diffusion_models', None, 'model'),  # Downloads automatically
            'TripoSGLoader': ('diffusion_models', None, None),  # Downloads automatically
        }

        # Scan workflow for model references
        for node in nodes:
            node_type = node.get('type', node.get('class_type', ''))
            widgets = node.get('widgets_values', [])
            inputs = node.get('inputs', {})

            if node_type in model_loaders:
                category, model_path, input_name = model_loaders[node_type]

                # Get model name from widgets or inputs
                model_name = None
                if input_name:
                    if isinstance(inputs, dict) and input_name in inputs:
                        model_name = inputs[input_name]
                    elif isinstance(inputs, list):
                        # Try to find from widgets
                        if widgets:
                            model_name = widgets[0] if widgets else None
                    elif widgets:
                        model_name = widgets[0] if widgets else None

                if model_name and isinstance(model_name, str):
                    result["required_models"][category].append(model_name)

                    # Check if model exists (skip auto-download models)
                    if model_path:
                        full_path = model_path / model_name
                        if not full_path.exists():
                            # Try without subdirectory
                            filename = model_name.replace('\\', '/').split('/')[-1]
                            alt_path = model_path / filename
                            if not alt_path.exists():
                                result["missing_models"].append(model_name)
                                result["errors"].append(f"Missing {category[:-1]}: {model_name}")

        # Check for custom nodes (by checking if class_type is known)
        # This requires object_info from ComfyUI
        if hasattr(self, '_object_info') and self._object_info:
            for node in nodes:
                node_type = node.get('type', node.get('class_type', ''))
                if node_type and node_type not in self._object_info:
                    # Skip known UI-only nodes
                    if node_type not in ['Note', 'Reroute', 'PrimitiveNode', 'MarkdownNote', 'SetNode', 'GetNode']:
                        result["missing_nodes"].append(node_type)
                        result["errors"].append(f"Missing custom node: {node_type}")

        # Set validity based on errors
        if result["errors"]:
            result["valid"] = False

        # Add warnings for missing optional items
        if result["missing_nodes"]:
            result["warnings"].append(
                f"Install missing custom nodes: {', '.join(set(result['missing_nodes']))}"
            )

        return result

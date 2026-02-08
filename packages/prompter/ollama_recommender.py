# ollama_recommender.py - Handles prompt analysis using Ollama

import requests
import json
from typing import Dict, List, Optional
from config import OLLAMA_MODEL, OLLAMA_URL, WORKFLOWS, CHECKPOINTS


class OllamaRecommender:
    """Analyzes prompts and recommends workflows and checkpoints using Ollama"""
    
    def __init__(self):
        self.ollama_url = OLLAMA_URL
        self.model = OLLAMA_MODEL
        
    def check_ollama_available(self) -> bool:
        """Check if Ollama is running"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def analyze_prompt(self, user_prompt: str) -> Dict:
        """
        Analyze user prompt and recommend workflow + checkpoint
        
        Returns:
            {
                "recommended_workflow": "workflow_filename.json",
                "recommended_checkpoint": "checkpoint_name",
                "reasoning": "Why these were chosen",
                "alternatives": ["other", "options"]
            }
        """
        # Build context for Ollama about available workflows
        workflows_context = self._build_workflows_context()
        
        # Create the prompt for Ollama
        system_prompt = f"""You are an AI assistant helping users choose the best ComfyUI workflow and checkpoint for their image/video generation task.

Available workflows:
{workflows_context}

Your task:
1. Analyze the user's prompt
2. Recommend the SINGLE BEST workflow from the list above
3. Recommend the appropriate checkpoint for that workflow
4. Explain your reasoning briefly (1-2 sentences)

Respond ONLY with valid JSON in this exact format:
{{
    "recommended_workflow": "exact_workflow_filename.json",
    "recommended_checkpoint": "exact_checkpoint_name",
    "reasoning": "Brief explanation",
    "task_type": "2d_image|3d_generation|video_generation|conversion"
}}

Do not include any text before or after the JSON."""

        user_message = f"User prompt: {user_prompt}"
        
        try:
            # Call Ollama API
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": f"{system_prompt}\n\n{user_message}",
                    "stream": False,
                    "format": "json"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get("response", "")
                
                # Parse the JSON response
                try:
                    recommendation = json.loads(response_text)
                    
                    # Validate the recommendation
                    if self._validate_recommendation(recommendation):
                        return recommendation
                    else:
                        return self._fallback_recommendation(user_prompt)
                        
                except json.JSONDecodeError:
                    print(f"Failed to parse Ollama response: {response_text}")
                    return self._fallback_recommendation(user_prompt)
            else:
                print(f"Ollama request failed: {response.status_code}")
                return self._fallback_recommendation(user_prompt)
                
        except Exception as e:
            print(f"Error calling Ollama: {e}")
            return self._fallback_recommendation(user_prompt)
    
    def _build_workflows_context(self) -> str:
        """Build a text description of all available workflows"""
        context = ""
        for workflow_name, info in WORKFLOWS.items():
            checkpoint = info['checkpoint'] if info['checkpoint'] else "None (no checkpoint needed)"
            context += f"\n- {workflow_name}:\n"
            context += f"  Description: {info['description']}\n"
            context += f"  Checkpoint: {checkpoint}\n"
            context += f"  Type: {info['type']}\n"
            context += f"  Best for: {info['use_case']}\n"
        return context
    
    def _validate_recommendation(self, recommendation: Dict) -> bool:
        """Validate that the recommendation contains valid workflow/checkpoint"""
        if not isinstance(recommendation, dict):
            return False
            
        workflow = recommendation.get("recommended_workflow")
        checkpoint = recommendation.get("recommended_checkpoint")
        
        # Check if workflow exists
        if workflow not in WORKFLOWS:
            return False
        
        # Check if checkpoint is valid (can be None for some workflows)
        workflow_info = WORKFLOWS[workflow]
        if workflow_info['checkpoint'] is None:
            return checkpoint is None or checkpoint == "None"
        
        return True
    
    def _fallback_recommendation(self, user_prompt: str) -> Dict:
        """
        Simple keyword-based fallback if Ollama fails
        """
        prompt_lower = user_prompt.lower()
        
        # Simple keyword matching
        if any(word in prompt_lower for word in ['sketch', 'drawing', 'wireframe']):
            return {
                "recommended_workflow": "EP20_Flux_Dev_Q8_Sketch_2_Image.json",
                "recommended_checkpoint": "flux1-dev-fp8.safetensors",
                "reasoning": "Detected sketch-related keywords (fallback mode)",
                "task_type": "2d_image"
            }
        elif any(word in prompt_lower for word in ['inpaint', 'fix', 'remove', 'fill']):
            return {
                "recommended_workflow": "EP19_SDXL_INPAINT.json",
                "recommended_checkpoint": "Juggernaut_X_RunDiffusion",
                "reasoning": "Detected inpainting keywords (fallback mode)",
                "task_type": "2d_image"
            }
        elif any(word in prompt_lower for word in ['3d', 'model', 'mesh', 'glb', 'stl', 'object', 'sculpt']):
            # Determine which 3D model variant to use based on keywords
            if any(word in prompt_lower for word in ['fast', 'quick', 'speed', 'turbo']):
                checkpoint = "hunyuan3d-dit-v2-turbo-fp16.safetensors"
                reasoning = "Detected 3D + speed keywords - using Turbo model (fallback mode)"
            elif any(word in prompt_lower for word in ['low vram', 'lightweight', 'small', 'mini']):
                checkpoint = "hunyuan3d-dit-v2-mini-fp16.safetensors"
                reasoning = "Detected 3D + low resource keywords - using Mini model (fallback mode)"
            elif any(word in prompt_lower for word in ['high quality', 'detailed', 'best', 'pbr', 'texture']):
                checkpoint = "hunyuan3d-dit-v2-5-fp16.safetensors"
                reasoning = "Detected 3D + quality keywords - using v2.5 model (fallback mode)"
            elif any(word in prompt_lower for word in ['tripo', 'triposg', 'stability']):
                return {
                    "recommended_workflow": "triposg_image_to_3d.json",
                    "recommended_checkpoint": "VAST-AI/TripoSG",
                    "reasoning": "Detected TripoSG keywords - using TripoSG model (fallback mode)",
                    "task_type": "3d_generation"
                }
            else:
                checkpoint = "hunyuan3d-dit-v2-0-fp16.safetensors"
                reasoning = "Detected 3D generation keywords - using Hunyuan3D v2.0 (fallback mode)"
            return {
                "recommended_workflow": "hy3d_example_01 (1) - Copy.json",
                "recommended_checkpoint": checkpoint,
                "reasoning": reasoning,
                "task_type": "3d_generation"
            }
        elif any(word in prompt_lower for word in ['video', 'animation', 'moving']):
            return {
                "recommended_workflow": "text_to_video_wan.json",
                "recommended_checkpoint": "wan2.1_t2v_1.3B_fp16.safetensors",
                "reasoning": "Detected video generation keywords (fallback mode)",
                "task_type": "video_generation"
            }
        elif any(word in prompt_lower for word in ['svg', 'vector']):
            return {
                "recommended_workflow": "Image_To_Vector_SVG.json",
                "recommended_checkpoint": None,
                "reasoning": "Detected SVG conversion keywords (fallback mode)",
                "task_type": "conversion"
            }
        else:
            # Default to Flux for general image generation
            return {
                "recommended_workflow": "EP20_Flux_Dev_Q8_Sketch_2_Image.json",
                "recommended_checkpoint": "flux1-dev-fp8.safetensors",
                "reasoning": "General image generation (fallback mode)",
                "task_type": "2d_image"
            }

# main.py - Main GUI application for ComfyUI Prompter

import sys
import io

# Fix Windows console encoding for emoji support
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
from pathlib import Path
import random

from ollama_recommender import OllamaRecommender
from workflow_manager import WorkflowManager
from comfyui_agent_sdk.client import ComfyUIClient
from comfyui_agent_sdk.config import ComfyUIConfig
from config import WORKFLOWS, CHECKPOINTS, COMFYUI_WORKFLOWS_PATH, COMFYUI_PATH, COMFYUI_URL, API_SERVER_HOST, API_SERVER_PORT
from model_downloader import ModelDownloader
from model_registry import get_model_info, MODEL_REGISTRY
from style_presets import STYLE_PRESETS, QUALITY_TAGS, NEGATIVE_PRESETS, build_enhanced_prompt, build_negative_prompt
from history_manager import get_history_manager
import subprocess
import time
import requests
import os

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Video models required for video generation
VIDEO_MODELS = {
    "wan2.1_t2v_1.3B_fp16.safetensors": {
        "description": "Wan 2.1 Text-to-Video diffusion model (2.6 GB)",
        "required_for": "Text-to-Video generation"
    },
    "umt5_xxl_fp8_e4m3fn_scaled.safetensors": {
        "description": "UMT5-XXL text encoder for Wan (4.9 GB)",
        "required_for": "All Wan video workflows"
    },
    "wan_2.1_vae.safetensors": {
        "description": "Wan 2.1 VAE decoder (0.2 GB)",
        "required_for": "All Wan video workflows"
    },
    "Wan2.1_14B_VACE-Q4_K_M.gguf": {
        "description": "Wan 2.1 VACE 14B quantized for Image-to-Video (8.5 GB)",
        "required_for": "Image-to-Video generation"
    },
}


class ComfyUIPrompterGUI:
    """Main GUI application"""

    def __init__(self, root):
        self.root = root
        self.root.title("ComfyUI Prompter - AI-Powered Workflow Selector")
        self.root.geometry("1200x800")

        # Initialize components
        self.recommender = OllamaRecommender()
        self.workflow_manager = WorkflowManager()
        _config = ComfyUIConfig(comfyui_url=COMFYUI_URL, comfyui_path=str(COMFYUI_PATH))
        self.comfyui_api = ComfyUIClient(config=_config)
        self.model_downloader = ModelDownloader()
        self.history_manager = get_history_manager()

        # Current state
        self.current_recommendation = None
        self.current_missing_model = None
        self.download_in_progress = False
        self.current_seed = None
        self.last_prompt = ""
        self.last_workflow = ""
        self.last_checkpoint = ""
        self.last_style = "None"
        self.current_history_entry_id = None
        self.latest_output_path = None
        self.current_prompt_id = None

        # Generation state
        self.is_generating = False

        # Setup GUI
        self.setup_gui()

        # Load history
        self.refresh_history_list()

        # Check systems on startup (non-blocking)
        self.log("Checking system availability...")
        threading.Thread(target=self._check_systems_async, daemon=True).start()
    
    def setup_gui(self):
        """Setup the GUI layout with enhanced features"""

        # Main container with two columns
        main_frame = ttk.Frame(self.root, padding="5")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=3)  # Left column (main content)
        main_frame.columnconfigure(1, weight=1)  # Right column (history/results)
        main_frame.rowconfigure(1, weight=1)

        # === HEADER ===
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        title_label = ttk.Label(header_frame, text="ComfyUI AI Prompter",
                                font=('Arial', 16, 'bold'))
        title_label.pack(side=tk.LEFT, padx=10)

        # Status indicators
        self.ollama_status_label = ttk.Label(header_frame, text="Ollama: ...", foreground="gray")
        self.ollama_status_label.pack(side=tk.RIGHT, padx=10)

        self.comfyui_status_label = ttk.Label(header_frame, text="ComfyUI: ...", foreground="gray")
        self.comfyui_status_label.pack(side=tk.RIGHT, padx=10)

        # === LEFT COLUMN (Main Content) ===
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(5, weight=1)  # Log area expands

        # --- Prompt Section ---
        prompt_frame = ttk.LabelFrame(left_frame, text="Prompt", padding="5")
        prompt_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        prompt_frame.columnconfigure(0, weight=1)

        self.prompt_text = scrolledtext.ScrolledText(prompt_frame, height=3, wrap=tk.WORD)
        self.prompt_text.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=2)

        # Custom negative prompt
        neg_input_frame = ttk.Frame(prompt_frame)
        neg_input_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=2)
        neg_input_frame.columnconfigure(1, weight=1)
        ttk.Label(neg_input_frame, text="Negative:").grid(row=0, column=0, sticky=tk.W, padx=2)
        self.negative_prompt_text = ttk.Entry(neg_input_frame)
        self.negative_prompt_text.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)

        # --- Style & Enhancement Section ---
        style_frame = ttk.LabelFrame(left_frame, text="Style & Enhancement", padding="5")
        style_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        style_frame.columnconfigure(1, weight=1)
        style_frame.columnconfigure(3, weight=1)

        # Style preset dropdown
        ttk.Label(style_frame, text="Style:").grid(row=0, column=0, sticky=tk.W, padx=2)
        self.style_var = tk.StringVar(value="None")
        self.style_combo = ttk.Combobox(style_frame, textvariable=self.style_var,
                                        state='readonly', width=20)
        self.style_combo['values'] = list(STYLE_PRESETS.keys())
        self.style_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)

        # Quality tags checkboxes
        ttk.Label(style_frame, text="Quality:").grid(row=0, column=2, sticky=tk.W, padx=10)
        self.quality_vars = {}
        quality_frame = ttk.Frame(style_frame)
        quality_frame.grid(row=0, column=3, sticky=tk.W)
        for i, (tag_name, _) in enumerate(list(QUALITY_TAGS.items())[:3]):  # Show first 3
            var = tk.BooleanVar(value=False)
            self.quality_vars[tag_name] = var
            ttk.Checkbutton(quality_frame, text=tag_name, variable=var).pack(side=tk.LEFT, padx=2)

        # Negative prompt presets
        ttk.Label(style_frame, text="Negatives:").grid(row=1, column=0, sticky=tk.W, padx=2)
        self.negative_vars = {}
        neg_frame = ttk.Frame(style_frame)
        neg_frame.grid(row=1, column=1, columnspan=3, sticky=tk.W, pady=2)
        for neg_name in NEGATIVE_PRESETS.keys():
            var = tk.BooleanVar(value=(neg_name == "General"))  # Default select General
            self.negative_vars[neg_name] = var
            ttk.Checkbutton(neg_frame, text=neg_name, variable=var).pack(side=tk.LEFT, padx=3)

        # --- Workflow Section ---
        wf_frame = ttk.LabelFrame(left_frame, text="Workflow & Model", padding="5")
        wf_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)
        wf_frame.columnconfigure(1, weight=1)
        wf_frame.columnconfigure(3, weight=1)

        # Workflow selection
        ttk.Label(wf_frame, text="Workflow:").grid(row=0, column=0, sticky=tk.W, padx=2)
        self.workflow_var = tk.StringVar()
        self.workflow_combo = ttk.Combobox(wf_frame, textvariable=self.workflow_var,
                                           state='readonly', width=35)
        self.workflow_combo['values'] = list(WORKFLOWS.keys())
        self.workflow_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
        self.workflow_combo.bind('<<ComboboxSelected>>', self.on_workflow_changed)

        # Checkpoint selection
        ttk.Label(wf_frame, text="Checkpoint:").grid(row=0, column=2, sticky=tk.W, padx=10)
        self.checkpoint_var = tk.StringVar()
        self.checkpoint_combo = ttk.Combobox(wf_frame, textvariable=self.checkpoint_var,
                                             state='readonly', width=30)
        self.checkpoint_combo['values'] = list(CHECKPOINTS.keys())
        self.checkpoint_combo.grid(row=0, column=3, sticky=(tk.W, tk.E), padx=5, pady=2)

        # Seed input
        seed_frame = ttk.Frame(wf_frame)
        seed_frame.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=2)
        ttk.Label(seed_frame, text="Seed:").pack(side=tk.LEFT, padx=2)
        self.seed_var = tk.StringVar(value="")
        self.seed_entry = ttk.Entry(seed_frame, textvariable=self.seed_var, width=15)
        self.seed_entry.pack(side=tk.LEFT, padx=2)
        ttk.Button(seed_frame, text="Random", width=7,
                   command=lambda: self.seed_var.set("")).pack(side=tk.LEFT, padx=2)
        ttk.Label(seed_frame, text="(blank = random)", foreground="gray",
                  font=('Arial', 8)).pack(side=tk.LEFT, padx=5)

        # Model status and download
        self.model_check_label = ttk.Label(wf_frame, text="", foreground="gray")
        self.model_check_label.grid(row=1, column=2, columnspan=2, sticky=tk.W, pady=2)

        self.download_button = ttk.Button(wf_frame, text="Download Model",
                                          command=self.download_missing_model)
        self.download_button.grid(row=2, column=2, columnspan=2, sticky=tk.E, pady=2)
        self.download_button.grid_remove()

        # AI reasoning display
        self.reasoning_label = ttk.Label(wf_frame, text="", wraplength=500,
                                         foreground="gray", font=('Arial', 8))
        self.reasoning_label.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=2)

        # Download progress (hidden by default)
        self.download_progress = ttk.Progressbar(wf_frame, orient="horizontal",
                                                 length=300, mode="determinate")
        self.download_progress.grid(row=3, column=0, columnspan=4, pady=2)
        self.download_progress.grid_remove()

        self.download_progress_label = ttk.Label(wf_frame, text="", foreground="blue")
        self.download_progress_label.grid(row=4, column=0, columnspan=4, pady=2)
        self.download_progress_label.grid_remove()

        # --- Action Buttons & Generation Progress ---
        action_frame = ttk.Frame(left_frame)
        action_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5)
        action_frame.columnconfigure(0, weight=1)

        button_frame = ttk.Frame(action_frame)
        button_frame.grid(row=0, column=0, sticky=tk.W)

        self.analyze_button = ttk.Button(button_frame, text="AI Analyze",
                                         command=self.analyze_prompt)
        self.analyze_button.pack(side=tk.LEFT, padx=5)

        self.generate_button = ttk.Button(button_frame, text="Generate",
                                          command=self.generate_content, state='disabled')
        self.generate_button.pack(side=tk.LEFT, padx=5)

        self.cancel_button = ttk.Button(button_frame, text="Cancel",
                                        command=self.cancel_generation, state='disabled')
        self.cancel_button.pack(side=tk.LEFT, padx=5)

        self.regenerate_button = ttk.Button(button_frame, text="Regenerate (New Seed)",
                                            command=self.regenerate_with_new_seed, state='disabled')
        self.regenerate_button.pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="Workflows Folder",
                   command=self.open_workflows_folder).pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="Video Models",
                   command=self.open_video_models_setup).pack(side=tk.LEFT, padx=5)

        # Generation progress bar (hidden by default)
        self.gen_progress_frame = ttk.Frame(action_frame)
        self.gen_progress_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=2)
        self.gen_progress_frame.columnconfigure(0, weight=1)

        self.gen_progress = ttk.Progressbar(self.gen_progress_frame, orient="horizontal",
                                            mode="determinate")
        self.gen_progress.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5)
        self.gen_progress_label = ttk.Label(self.gen_progress_frame, text="", foreground="blue")
        self.gen_progress_label.grid(row=0, column=1, padx=5)
        self.gen_progress_frame.grid_remove()

        # --- Log Section ---
        log_frame = ttk.LabelFrame(left_frame, text="Log", padding="5")
        log_frame.grid(row=5, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        left_frame.rowconfigure(5, weight=1)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, wrap=tk.WORD,
                                                  state='disabled')
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # === RIGHT COLUMN (Preview, History & Results) ===
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(1, weight=0)
        right_frame.rowconfigure(2, weight=1)

        # --- Image Preview Section ---
        preview_frame = ttk.LabelFrame(right_frame, text="Preview", padding="5")
        preview_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        preview_frame.columnconfigure(0, weight=1)

        self.preview_canvas = tk.Canvas(preview_frame, width=300, height=300,
                                        bg='#2b2b2b', highlightthickness=0)
        self.preview_canvas.grid(row=0, column=0, pady=2)
        self._preview_image_ref = None  # Keep reference to prevent GC

        # No-preview label
        self.preview_canvas.create_text(
            150, 150, text="No preview", fill="#666666", font=('Arial', 12)
        )

        # --- Recent Outputs Section ---
        outputs_frame = ttk.LabelFrame(right_frame, text="Recent Outputs", padding="5")
        outputs_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        outputs_frame.columnconfigure(0, weight=1)

        self.output_path_label = ttk.Label(outputs_frame, text="No recent output",
                                           wraplength=280, foreground="gray")
        self.output_path_label.grid(row=0, column=0, sticky=tk.W, pady=2)

        output_btn_frame = ttk.Frame(outputs_frame)
        output_btn_frame.grid(row=1, column=0, sticky=tk.W, pady=5)

        self.open_output_button = ttk.Button(output_btn_frame, text="Open Output",
                                             command=self.open_latest_output, state='disabled')
        self.open_output_button.pack(side=tk.LEFT, padx=2)

        self.open_folder_button = ttk.Button(output_btn_frame, text="Open Folder",
                                             command=self.open_output_folder)
        self.open_folder_button.pack(side=tk.LEFT, padx=2)

        # --- History Section ---
        history_frame = ttk.LabelFrame(right_frame, text="History", padding="5")
        history_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        history_frame.columnconfigure(0, weight=1)
        history_frame.rowconfigure(0, weight=1)

        # History listbox
        self.history_listbox = tk.Listbox(history_frame, height=10, selectmode=tk.SINGLE)
        self.history_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.history_listbox.bind('<<ListboxSelect>>', self.on_history_select)

        # History scrollbar
        history_scroll = ttk.Scrollbar(history_frame, orient=tk.VERTICAL,
                                       command=self.history_listbox.yview)
        history_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.history_listbox.config(yscrollcommand=history_scroll.set)

        # History buttons
        history_btn_frame = ttk.Frame(history_frame)
        history_btn_frame.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)

        self.load_history_button = ttk.Button(history_btn_frame, text="Load",
                                              command=self.load_selected_history, state='disabled')
        self.load_history_button.pack(side=tk.LEFT, padx=2)

        self.favorite_button = ttk.Button(history_btn_frame, text="Favorite",
                                          command=self.toggle_favorite, state='disabled')
        self.favorite_button.pack(side=tk.LEFT, padx=2)

        self.delete_history_button = ttk.Button(history_btn_frame, text="Delete",
                                                command=self.delete_selected_history, state='disabled')
        self.delete_history_button.pack(side=tk.LEFT, padx=2)

        ttk.Button(history_btn_frame, text="Refresh",
                   command=self.refresh_history_list).pack(side=tk.LEFT, padx=2)
    
    def log(self, message: str):
        """Add message to log"""
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        print(message)  # Also print to console
    
    def launch_comfyui(self):
        """Launch ComfyUI in the background (safe to call from any thread)"""
        try:
            venv_python = COMFYUI_PATH / "venv" / "Scripts" / "python.exe"
            main_script = COMFYUI_PATH / "main.py"

            if not venv_python.exists():
                self.root.after(0, lambda: self.log(f"ComfyUI venv not found at {venv_python}"))
                return False

            if not main_script.exists():
                self.root.after(0, lambda: self.log(f"ComfyUI main.py not found at {main_script}"))
                return False

            self.root.after(0, lambda: self.log("Starting ComfyUI..."))
            self.root.after(0, lambda: self.comfyui_status_label.config(
                text="ComfyUI: Starting...", foreground="orange"))

            # Launch ComfyUI in background
            subprocess.Popen(
                [str(venv_python), str(main_script)],
                cwd=str(COMFYUI_PATH),
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )

            # Wait for ComfyUI to start (up to 30 seconds)
            for i in range(30):
                time.sleep(1)
                if self.comfyui_api.is_available():
                    self.root.after(0, lambda: self.log("ComfyUI started successfully!"))
                    return True
                if i % 5 == 0:
                    self.root.after(0, lambda sec=i: self.log(f"Waiting for ComfyUI to start... ({sec}s)"))

            self.root.after(0, lambda: self.log("ComfyUI failed to start within 30 seconds"))
            return False

        except Exception as e:
            self.root.after(0, lambda: self.log(f"Error launching ComfyUI: {e}"))
            return False

    def _check_systems_async(self):
        """Check if Ollama and ComfyUI are available (runs in background thread)"""

        # Check Ollama
        ollama_ok = self.recommender.check_ollama_available()
        self.root.after(0, lambda: self._update_ollama_status(ollama_ok))

        # Check ComfyUI
        comfyui_ok = self.comfyui_api.is_available()
        if comfyui_ok:
            self.root.after(0, lambda: self._update_comfyui_status(True))
        else:
            self.root.after(0, lambda: self.log("ComfyUI not running - attempting to start..."))
            launched = self.launch_comfyui()
            self.root.after(0, lambda: self._update_comfyui_status(launched))

        self.root.after(0, lambda: self.log(f"Workflows folder: {COMFYUI_WORKFLOWS_PATH}"))

    def _update_ollama_status(self, available: bool):
        if available:
            self.ollama_status_label.config(text="Ollama: Running", foreground="green")
            self.log("Ollama is running")
        else:
            self.ollama_status_label.config(text="Ollama: Not available", foreground="red")
            self.log("Ollama is not running. Please start Ollama.")

    def _update_comfyui_status(self, available: bool):
        if available:
            self.comfyui_status_label.config(text="ComfyUI: Running", foreground="green")
            self.log("ComfyUI is running")
        else:
            self.comfyui_status_label.config(text="ComfyUI: Not available", foreground="red")
            self.log("Could not start ComfyUI automatically.")

    def check_systems(self):
        """Check if Ollama and ComfyUI are available (legacy synchronous version)"""
        self._check_systems_async()
    
    def cancel_generation(self):
        """Cancel the currently running generation"""
        if self.current_prompt_id:
            self.log("Cancelling generation...")
            success = self.comfyui_api.interrupt_execution()
            if success:
                self.log("Generation interrupted.")
            else:
                self.log("Failed to interrupt generation.")
            self._end_generation()

    def _start_generation_ui(self):
        """Update UI state when generation starts"""
        self.is_generating = True
        self.generate_button.config(state='disabled')
        self.regenerate_button.config(state='disabled')
        self.cancel_button.config(state='normal')
        self.gen_progress_frame.grid()
        self.gen_progress['value'] = 0
        self.gen_progress_label.config(text="Starting...")

    def _end_generation(self):
        """Update UI state when generation ends"""
        self.is_generating = False
        self.generate_button.config(state='normal')
        self.regenerate_button.config(state='normal')
        self.cancel_button.config(state='disabled')
        self.gen_progress_frame.grid_remove()

    def _update_gen_progress(self, percent: float, message: str = ""):
        """Update the generation progress bar"""
        self.gen_progress['value'] = percent
        if message:
            self.gen_progress_label.config(text=message)

    def _show_preview(self, image_path: str):
        """Show an image preview in the preview canvas"""
        if not HAS_PIL:
            return
        try:
            path = Path(image_path)
            if not path.exists():
                return
            # Only preview images
            if path.suffix.lower() not in ('.png', '.jpg', '.jpeg', '.webp', '.bmp'):
                return
            img = Image.open(path)
            # Resize to fit canvas (300x300)
            img.thumbnail((300, 300), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.preview_canvas.delete("all")
            self.preview_canvas.create_image(
                150, 150, image=photo, anchor=tk.CENTER
            )
            self._preview_image_ref = photo  # Prevent garbage collection
        except Exception as e:
            print(f"Error showing preview: {e}")

    def analyze_prompt(self):
        """Analyze the user's prompt and get recommendations"""
        user_prompt = self.prompt_text.get("1.0", tk.END).strip()
        
        if not user_prompt:
            messagebox.showwarning("Empty Prompt", "Please enter a prompt first!")
            return
        
        self.log(f"\n🔍 Analyzing prompt: {user_prompt[:100]}...")
        self.analyze_button.config(state='disabled')
        
        # Run analysis in background thread
        def analyze_thread():
            recommendation = self.recommender.analyze_prompt(user_prompt)
            
            # Update GUI from main thread
            self.root.after(0, lambda: self.display_recommendation(recommendation))
        
        thread = threading.Thread(target=analyze_thread, daemon=True)
        thread.start()
    
    def display_recommendation(self, recommendation: dict):
        """Display the AI recommendation"""
        self.current_recommendation = recommendation
        
        workflow = recommendation.get('recommended_workflow', '')
        checkpoint = recommendation.get('recommended_checkpoint', '')
        reasoning = recommendation.get('reasoning', '')
        
        self.log(f"✨ Recommended workflow: {workflow}")
        self.log(f"✨ Recommended checkpoint: {checkpoint}")
        self.log(f"💡 Reasoning: {reasoning}")
        
        # Update dropdowns
        if workflow in self.workflow_combo['values']:
            self.workflow_combo.set(workflow)
        
        if checkpoint and checkpoint != "None":
            # Add checkpoint if not in list
            current_checkpoints = list(self.checkpoint_combo['values'])
            if checkpoint not in current_checkpoints:
                current_checkpoints.append(checkpoint)
                self.checkpoint_combo['values'] = current_checkpoints
            self.checkpoint_combo.set(checkpoint)
        else:
            self.checkpoint_combo.set('')
        
        self.reasoning_label.config(text=reasoning)
        
        # Check if required models are available
        self.check_required_models()
        
        self.analyze_button.config(state='normal')
        self.generate_button.config(state='normal')
    
    def on_workflow_changed(self, event):
        """Handle workflow selection change"""
        workflow = self.workflow_var.get()
        workflow_info = WORKFLOWS.get(workflow)
        
        if workflow_info:
            # Auto-select the appropriate checkpoint
            checkpoint = workflow_info.get('checkpoint')
            if checkpoint:
                self.checkpoint_combo.set(checkpoint)
            else:
                self.checkpoint_combo.set('')
            
            self.check_required_models()
    
    def check_required_models(self):
        """Check if required models are present"""
        workflow = self.workflow_var.get()

        if not workflow:
            return

        result = self.workflow_manager.check_required_models(workflow)

        # Hide download UI by default
        self.download_button.grid_remove()
        self.download_progress.grid_remove()
        self.download_progress_label.grid_remove()
        self.current_missing_model = None

        if result['has_checkpoint']:
            if result['checkpoint_path']:
                self.model_check_label.config(
                    text=f"✅ Required model found: {result['checkpoint_path'].name}",
                    foreground="green"
                )
            else:
                self.model_check_label.config(
                    text="✅ No checkpoint required for this workflow",
                    foreground="green"
                )
        else:
            missing_models = result['missing_models']
            missing = ', '.join(missing_models)

            # Check if the first missing model is in the registry
            if missing_models:
                first_missing = missing_models[0]
                model_info = get_model_info(first_missing)

                if model_info:
                    # Model is downloadable
                    self.current_missing_model = {'filename': first_missing, **model_info}
                    size_gb = model_info.get('size_gb', '?')
                    requires_auth = model_info.get('requires_auth', False)

                    auth_note = " (requires login)" if requires_auth else ""
                    self.model_check_label.config(
                        text=f"⚠️ Missing: {first_missing} ({size_gb} GB){auth_note}",
                        foreground="orange"
                    )

                    # Show download button
                    self.download_button.config(text=f"Download {first_missing}")
                    self.download_button.grid()
                    self.log(f"⚠️ Missing model '{first_missing}' is available for download ({size_gb} GB)")
                else:
                    # Model not in registry
                    self.model_check_label.config(
                        text=f"⚠️ Missing models: {missing}",
                        foreground="red"
                    )
                    self.log(f"⚠️ WARNING: Missing required models: {missing}")
            else:
                self.model_check_label.config(
                    text=f"⚠️ Missing models: {missing}",
                    foreground="red"
                )
                self.log(f"⚠️ WARNING: Missing required models: {missing}")

    def download_missing_model(self):
        """Download the currently missing model"""
        if not self.current_missing_model or self.download_in_progress:
            return

        model_info = self.current_missing_model
        filename = model_info.get('filename', 'model')

        # Check for auth requirements
        requires_auth = model_info.get('requires_auth', False)
        source = model_info.get('source', '').lower()

        if requires_auth:
            if source == 'huggingface':
                from comfyui_agent_sdk.credentials import get_huggingface_token
                if not get_huggingface_token():
                    self.log("❌ This model requires HuggingFace authentication.")
                    self.log("   Please configure your HuggingFace token in credentials.")
                    messagebox.showwarning(
                        "Authentication Required",
                        "This model requires HuggingFace authentication.\n\n"
                        "Please configure your HuggingFace token first."
                    )
                    return
            elif source == 'civitai':
                from comfyui_agent_sdk.credentials import get_civitai_api_key
                if not get_civitai_api_key():
                    self.log("❌ This model requires CivitAI authentication.")
                    self.log("   Please configure your CivitAI API key in credentials.")
                    messagebox.showwarning(
                        "Authentication Required",
                        "This model requires CivitAI authentication.\n\n"
                        "Please configure your CivitAI API key first."
                    )
                    return

        # Disable button and show progress UI
        self.download_in_progress = True
        self.download_button.config(state='disabled')
        self.download_progress['value'] = 0
        self.download_progress.grid()
        self.download_progress_label.config(text="Starting download...")
        self.download_progress_label.grid()

        self.log(f"📥 Starting download of {filename}...")

        def download_thread():
            try:
                result = self.model_downloader.download_model(
                    model_info,
                    progress_callback=self.update_download_progress
                )

                if result:
                    self.root.after(0, lambda: self.on_download_complete(True, filename))
                else:
                    self.root.after(0, lambda: self.on_download_complete(False, filename))

            except Exception as e:
                self.root.after(0, lambda: self.on_download_error(str(e)))

        thread = threading.Thread(target=download_thread, daemon=True)
        thread.start()

    def update_download_progress(self, percent: float, message: str):
        """Callback for download progress updates - schedules GUI update on main thread"""
        def update_gui():
            self.download_progress['value'] = percent
            self.download_progress_label.config(text=message)
        self.root.after(0, update_gui)

    def on_download_complete(self, success: bool, filename: str):
        """Handle download completion"""
        self.download_in_progress = False
        self.download_button.config(state='normal')

        if success:
            self.log(f"✅ Successfully downloaded {filename}")
            # Hide progress UI
            self.download_progress.grid_remove()
            self.download_progress_label.grid_remove()
            self.download_button.grid_remove()
            # Re-check models to update the status
            self.check_required_models()
        else:
            self.log(f"❌ Failed to download {filename}")
            self.download_progress_label.config(text="Download failed", foreground="red")

    def on_download_error(self, error_msg: str):
        """Handle download error"""
        self.download_in_progress = False
        self.download_button.config(state='normal')
        self.log(f"❌ Download error: {error_msg}")
        self.download_progress_label.config(text=f"Error: {error_msg}", foreground="red")

    def generate_content(self):
        """Generate content using ComfyUI"""
        workflow_name = self.workflow_var.get()
        checkpoint_name = self.checkpoint_var.get()
        user_prompt = self.prompt_text.get("1.0", tk.END).strip()
        style = self.style_var.get()

        if not workflow_name:
            messagebox.showwarning("No Workflow", "Please select a workflow first!")
            return

        # Check for missing models before starting
        model_check = self.workflow_manager.check_required_models(workflow_name)
        if not model_check['has_checkpoint'] and model_check['missing_models']:
            missing = ', '.join(model_check['missing_models'])
            if not messagebox.askyesno("Missing Models",
                f"The following models are missing:\n{missing}\n\n"
                "Generation may fail. Continue anyway?"):
                return

        # Get enhanced prompt with style presets
        enhanced_prompt, negative_prompt = self.get_enhanced_prompt()

        # Use seed from entry field if provided, otherwise generate random
        seed_text = self.seed_var.get().strip()
        if seed_text:
            try:
                self.current_seed = int(seed_text)
            except ValueError:
                messagebox.showwarning("Invalid Seed", "Seed must be a number. Using random seed.")
                self.current_seed = random.randint(0, 2**32 - 1)
        elif self.current_seed is None:
            self.current_seed = random.randint(0, 2**32 - 1)

        # Display the seed being used
        self.seed_var.set(str(self.current_seed))

        # Store last settings for regeneration
        self.last_prompt = user_prompt
        self.last_workflow = workflow_name
        self.last_checkpoint = checkpoint_name
        self.last_style = style

        # Check workflow type
        workflow_info = WORKFLOWS.get(workflow_name, {})
        workflow_type = workflow_info.get('type', '2d_image')

        self.log(f"\n🎨 Starting generation...")
        self.log(f"Workflow: {workflow_name}")
        self.log(f"Type: {workflow_type}")
        self.log(f"Style: {style}")
        self.log(f"Seed: {self.current_seed}")
        self.log(f"Checkpoint: {checkpoint_name if checkpoint_name else 'Default'}")

        # Add to history
        self.current_history_entry_id = self.history_manager.add_generation(
            prompt=user_prompt,
            negative_prompt=negative_prompt,
            workflow=workflow_name,
            checkpoint=checkpoint_name,
            style=style,
            seed=self.current_seed,
            status="queued"
        )

        self._start_generation_ui()

        # For 3D workflows with text prompt but no image, use text-to-3D pipeline
        if workflow_type == '3d_generation' and user_prompt:
            self.log("📦 Using text-to-3D pipeline (text → image → 3D)")
            self._run_text_to_3d(workflow_name, enhanced_prompt, checkpoint_name)
            return

        # Capture variables for thread
        seed = self.current_seed
        history_entry_id = self.current_history_entry_id

        # Reset seed for next generation
        self.current_seed = None

        # Run standard generation in background thread
        def generate_thread():
            try:
                # Load workflow
                workflow_data = self.workflow_manager.load_workflow(workflow_name)
                if not workflow_data:
                    self.log("❌ Failed to load workflow")
                    self.root.after(0, lambda: self._on_generation_failed(history_entry_id))
                    return

                # Set generation defaults for placeholder workflows
                workflow_data = self.workflow_manager.set_generation_defaults(
                    workflow_data,
                    checkpoint=checkpoint_name if checkpoint_name else "flux1-dev-fp8.safetensors",
                    seed=seed
                )

                # Modify checkpoint if specified (overrides default)
                if checkpoint_name:
                    workflow_data = self.workflow_manager.modify_checkpoint(
                        workflow_data, checkpoint_name
                    )

                # Modify prompts with enhanced version
                if enhanced_prompt:
                    workflow_data = self.workflow_manager.modify_prompt(
                        workflow_data, enhanced_prompt, negative_prompt
                    )

                # Fetch object_info from ComfyUI for proper widget mapping
                try:
                    response = requests.get(f"{COMFYUI_URL}/object_info", timeout=10)
                    if response.status_code == 200:
                        object_info = response.json()
                        self.workflow_manager.set_object_info(object_info)
                        self.log(f"Loaded {len(object_info)} node definitions from ComfyUI")
                except Exception as e:
                    self.log(f"Warning: Could not fetch object_info: {e}")

                # Convert to API format
                api_workflow = self.workflow_manager.convert_to_api_format(workflow_data)
                if not api_workflow:
                    self.log("❌ Failed to convert workflow to API format")
                    self.root.after(0, lambda: self.generate_button.config(state='normal'))
                    return

                # Queue in ComfyUI
                try:
                    import requests as req
                    r = req.post(
                        f"{COMFYUI_URL}/prompt",
                        json={"prompt": api_workflow, "client_id": self.comfyui_api.client_id},
                        timeout=30,
                    )
                    if r.status_code == 200:
                        result = r.json()
                    else:
                        error_detail = r.text[:300] if r.text else "No details"
                        self.log(f"❌ ComfyUI rejected prompt (HTTP {r.status_code}): {error_detail}")
                        result = None
                except Exception as qe:
                    self.log(f"❌ Error connecting to ComfyUI: {qe}")
                    result = None

                if result:
                    prompt_id = result.get('prompt_id')
                    self.log(f"✅ Queued in ComfyUI! Prompt ID: {prompt_id}")
                    # Update history status
                    if history_entry_id:
                        self.history_manager.update_generation(history_entry_id, status="running")
                    # Start monitoring progress
                    self.root.after(0, lambda: self.start_progress_monitoring(prompt_id, history_entry_id))
                else:
                    self.log("❌ Failed to queue prompt in ComfyUI")
                    self.root.after(0, lambda: self._on_generation_failed(history_entry_id))

            except Exception as e:
                self.log(f"❌ Error: {e}")
                self.root.after(0, lambda: self._on_generation_failed(history_entry_id))

        thread = threading.Thread(target=generate_thread, daemon=True)
        thread.start()

    def _on_generation_failed(self, history_entry_id: str):
        """Handle generation failure"""
        self._end_generation()
        if history_entry_id:
            self.history_manager.update_generation(history_entry_id, status="error")
        self.refresh_history_list()

    def _on_generation_complete(self, history_entry_id: str, output_path: str = None):
        """Handle generation completion"""
        self._end_generation()
        if history_entry_id:
            self.history_manager.update_generation(
                history_entry_id,
                status="completed",
                output_path=output_path
            )
        if output_path:
            self.update_output_display(output_path)
            self._show_preview(output_path)
        self.refresh_history_list()

    def _run_text_to_3d(self, workflow_name: str, prompt: str, checkpoint: str):
        """Run text-to-3D pipeline via API server"""
        history_entry_id = self.current_history_entry_id
        self.current_seed = None  # Reset for next generation

        def text_to_3d_thread():
            try:
                # Call API server's text_to_3d endpoint
                response = requests.post(
                    f"http://{API_SERVER_HOST}:{API_SERVER_PORT}/api/generate",
                    json={
                        "workflow": workflow_name,
                        "mode": "text_to_3d",
                        "prompt": prompt
                    },
                    timeout=300  # 5 minute timeout for long generation
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        job_id = result.get('job_id')
                        self.log(f"✅ Text-to-3D job started: {job_id}")
                        if history_entry_id:
                            self.history_manager.update_generation(history_entry_id, status="running")
                        # Monitor the job via API
                        self._monitor_api_job(job_id, history_entry_id)
                    else:
                        self.log(f"❌ Error: {result.get('error', 'Unknown error')}")
                        self.root.after(0, lambda: self._on_generation_failed(history_entry_id))
                else:
                    error = response.json().get('error', f'HTTP {response.status_code}')
                    self.log(f"❌ API error: {error}")
                    self.root.after(0, lambda: self._on_generation_failed(history_entry_id))

            except requests.exceptions.ConnectionError:
                self.log("❌ Cannot connect to API server. Make sure api_server.py is running.")
                self.root.after(0, lambda: self._on_generation_failed(history_entry_id))
            except Exception as e:
                self.log(f"❌ Error: {e}")
                self.root.after(0, lambda: self._on_generation_failed(history_entry_id))

        thread = threading.Thread(target=text_to_3d_thread, daemon=True)
        thread.start()

    def _monitor_api_job(self, job_id: str, history_entry_id: str = None):
        """Monitor job progress via API server"""
        def check_job():
            try:
                response = requests.get(f"http://{API_SERVER_HOST}:{API_SERVER_PORT}/api/job/{job_id}", timeout=10)
                if response.status_code == 200:
                    result = response.json()
                    status = result.get('status', 'unknown')

                    if status == 'completed':
                        output_path = result.get('output_path')
                        self.log(f"✅ Generation complete!")
                        if output_path:
                            self.log(f"📁 Output: {output_path}")
                        self.root.after(0, lambda: self._on_generation_complete(history_entry_id, output_path))
                    elif status == 'error':
                        self.log(f"❌ Generation failed: {result.get('error', 'Unknown error')}")
                        self.root.after(0, lambda: self._on_generation_failed(history_entry_id))
                    else:
                        progress = result.get('progress', 0)
                        self.log(f"⏳ Status: {status} ({progress}%)")
                        # Check again in 5 seconds
                        self.root.after(5000, check_job)
                else:
                    self.log(f"❌ Failed to check job status")
                    self.root.after(0, lambda: self._on_generation_failed(history_entry_id))
            except Exception as e:
                self.log(f"❌ Error checking job: {e}")
                self.root.after(0, lambda: self._on_generation_failed(history_entry_id))

        # Start checking
        self.root.after(2000, check_job)

    def start_progress_monitoring(self, prompt_id: str, history_entry_id: str = None):
        """Start monitoring job progress"""
        self.current_prompt_id = prompt_id
        self.current_history_entry_id = history_entry_id
        self.monitor_progress()

    def monitor_progress(self):
        """Check job progress periodically"""
        if not hasattr(self, 'current_prompt_id') or not self.current_prompt_id:
            return

        def check_thread():
            status = self.comfyui_api.get_job_status(self.current_prompt_id)
            self.root.after(0, lambda: self.update_progress_display(status))

        thread = threading.Thread(target=check_thread, daemon=True)
        thread.start()

    def update_progress_display(self, status: dict):
        """Update the UI with job progress"""
        job_status = status.get('status', 'unknown')
        progress = status.get('progress', 0)

        if job_status == 'running':
            self._update_gen_progress(progress, f"Generating... {progress:.0f}%")
            # Check again in 2 seconds
            self.root.after(2000, self.monitor_progress)
        elif job_status == 'completed':
            self._update_gen_progress(100, "Complete!")
            self.log("Generation complete!")
            outputs = status.get('outputs', [])
            output_path = None
            if outputs:
                for output in outputs:
                    self.log(f"   Output: {output}")
                # Use first output as the main one
                output_path = outputs[0] if outputs else None
            self._on_generation_complete(self.current_history_entry_id, output_path)
            self.current_prompt_id = None
            self.current_history_entry_id = None
        elif job_status == 'error':
            self.log(f"Generation failed: {status.get('error', 'Unknown error')}")
            self._on_generation_failed(self.current_history_entry_id)
            self.current_prompt_id = None
            self.current_history_entry_id = None
        else:
            self._update_gen_progress(progress, "Queued...")
            # Still pending or unknown, check again
            self.root.after(2000, self.monitor_progress)
    
    def open_workflows_folder(self):
        """Open the workflows folder in file explorer"""
        import os
        import platform

        path = str(COMFYUI_WORKFLOWS_PATH)

        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":  # macOS
            os.system(f'open "{path}"')
        else:  # Linux
            os.system(f'xdg-open "{path}"')

    def open_video_models_setup(self):
        """Open the Video Models Setup dialog"""
        VideoModelsDialog(self.root, self.model_downloader, self.log)

    def regenerate_with_new_seed(self):
        """Regenerate using the last settings with a new random seed"""
        if not self.last_workflow:
            messagebox.showinfo("No Previous Generation",
                               "Please generate something first before regenerating.")
            return

        # Generate new seed
        self.current_seed = random.randint(0, 2**32 - 1)
        self.seed_var.set(str(self.current_seed))
        self.log(f"Regenerating with new seed: {self.current_seed}")

        # Restore last settings and generate
        self.prompt_text.delete("1.0", tk.END)
        self.prompt_text.insert("1.0", self.last_prompt)
        self.workflow_combo.set(self.last_workflow)
        if self.last_checkpoint:
            self.checkpoint_combo.set(self.last_checkpoint)
        self.style_var.set(self.last_style)

        # Generate
        self.generate_content()

    def refresh_history_list(self):
        """Refresh the history listbox"""
        self.history_listbox.delete(0, tk.END)

        history = self.history_manager.get_history(limit=50)

        status_icons = {
            "completed": "[OK]",
            "error": "[!!]",
            "running": "[..]",
            "queued": "[>>]",
        }

        for entry in history:
            is_fav = self.history_manager.is_favorite(entry['id'])
            fav_marker = "*" if is_fav else " "
            status = entry.get('status', 'unknown')
            status_icon = status_icons.get(status, "[??]")
            prompt_preview = entry.get('prompt', '')[:35]
            if len(entry.get('prompt', '')) > 35:
                prompt_preview += "..."
            workflow = entry.get('workflow', '?')[:15]
            # Extract time from timestamp
            ts = entry.get('timestamp', '')
            time_str = ""
            if ts:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(ts)
                    time_str = dt.strftime("%H:%M")
                except (ValueError, TypeError):
                    pass

            display = f"{fav_marker}{status_icon} {time_str} {prompt_preview} ({workflow})"
            self.history_listbox.insert(tk.END, display)

    def on_history_select(self, event):
        """Handle history selection"""
        selection = self.history_listbox.curselection()
        if selection:
            self.load_history_button.config(state='normal')
            self.favorite_button.config(state='normal')
            self.delete_history_button.config(state='normal')
        else:
            self.load_history_button.config(state='disabled')
            self.favorite_button.config(state='disabled')
            self.delete_history_button.config(state='disabled')

    def get_selected_history_entry(self):
        """Get the currently selected history entry"""
        selection = self.history_listbox.curselection()
        if not selection:
            return None

        idx = selection[0]
        history = self.history_manager.get_history(limit=50)
        if idx < len(history):
            return history[idx]
        return None

    def load_selected_history(self):
        """Load selected history entry into the form"""
        entry = self.get_selected_history_entry()
        if not entry:
            return

        # Load prompt
        self.prompt_text.delete("1.0", tk.END)
        self.prompt_text.insert("1.0", entry.get('prompt', ''))

        # Load workflow
        workflow = entry.get('workflow', '')
        if workflow and workflow in self.workflow_combo['values']:
            self.workflow_combo.set(workflow)

        # Load checkpoint
        checkpoint = entry.get('checkpoint', '')
        if checkpoint:
            self.checkpoint_combo.set(checkpoint)

        # Load style
        style = entry.get('style', 'None')
        if style in self.style_combo['values']:
            self.style_var.set(style)

        # Load seed
        self.current_seed = entry.get('seed')
        if self.current_seed is not None:
            self.seed_var.set(str(self.current_seed))
        else:
            self.seed_var.set("")

        # Show preview if output path exists
        output_path = entry.get('output_path')
        if output_path:
            self._show_preview(output_path)

        self.log(f"Loaded history entry: {entry.get('prompt', '')[:50]}...")

    def toggle_favorite(self):
        """Toggle favorite status for selected entry"""
        entry = self.get_selected_history_entry()
        if not entry:
            return

        is_now_favorite = self.history_manager.toggle_favorite(entry['id'])
        status = "favorited" if is_now_favorite else "unfavorited"
        self.log(f"Entry {status}")
        self.refresh_history_list()

    def delete_selected_history(self):
        """Delete selected history entry"""
        entry = self.get_selected_history_entry()
        if not entry:
            return

        if messagebox.askyesno("Delete Entry", "Delete this history entry?"):
            self.history_manager.delete_entry(entry['id'])
            self.log("History entry deleted")
            self.refresh_history_list()

    def open_latest_output(self):
        """Open the most recent output file"""
        if hasattr(self, 'latest_output_path') and self.latest_output_path:
            path = Path(self.latest_output_path)
            if path.exists():
                os.startfile(str(path))
            else:
                messagebox.showerror("File Not Found", f"Output file not found:\n{path}")
        else:
            messagebox.showinfo("No Output", "No recent output to open.")

    def open_output_folder(self):
        """Open the ComfyUI output folder"""
        output_folder = COMFYUI_PATH / "output"
        if output_folder.exists():
            os.startfile(str(output_folder))
        else:
            messagebox.showerror("Folder Not Found", f"Output folder not found:\n{output_folder}")

    def update_output_display(self, output_path: str):
        """Update the output display with a new output"""
        if output_path:
            # Resolve relative paths to ComfyUI output folder
            path = Path(output_path)
            if not path.is_absolute():
                path = COMFYUI_PATH / "output" / output_path
            self.latest_output_path = str(path)
            self.output_path_label.config(
                text=f"{path.name}\n({path.parent.name})",
                foreground="green"
            )
            self.open_output_button.config(state='normal')
        else:
            self.latest_output_path = None
            self.output_path_label.config(text="No recent output", foreground="gray")
            self.open_output_button.config(state='disabled')

    def get_enhanced_prompt(self) -> tuple:
        """
        Build the enhanced prompt with style presets and quality tags

        Returns:
            (positive_prompt, negative_prompt)
        """
        base_prompt = self.prompt_text.get("1.0", tk.END).strip()
        style = self.style_var.get()

        # Collect selected quality tags
        quality_tags = [name for name, var in self.quality_vars.items() if var.get()]

        # Build enhanced prompt
        enhanced = build_enhanced_prompt(base_prompt, style, quality_tags)

        # Build negative prompt from presets
        negative_presets = [name for name, var in self.negative_vars.items() if var.get()]
        negative = build_negative_prompt(style, negative_presets)

        # Append custom negative prompt from text field
        custom_negative = self.negative_prompt_text.get().strip()
        if custom_negative:
            if negative:
                negative = f"{negative}, {custom_negative}"
            else:
                negative = custom_negative

        return enhanced, negative


class VideoModelsDialog:
    """Dialog for managing video model downloads"""

    def __init__(self, parent, downloader: ModelDownloader, log_callback):
        self.downloader = downloader
        self.log_callback = log_callback
        self.download_in_progress = False
        self.current_download = None

        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Video Models Setup")
        self.dialog.geometry("700x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.setup_gui()
        self.check_installed_models()

    def setup_gui(self):
        """Setup the dialog GUI"""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(main_frame, text="🎥 Video Generation Models",
                                font=('Arial', 14, 'bold'))
        title_label.pack(pady=10)

        # Info label
        info_label = ttk.Label(main_frame,
                               text="Download the required models for video generation.\n"
                                    "Text-to-Video requires the first 3 models. Image-to-Video also needs VACE.",
                               justify=tk.CENTER)
        info_label.pack(pady=5)

        # Models list frame
        list_frame = ttk.LabelFrame(main_frame, text="Required Models", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # Create scrollable canvas for models
        canvas = tk.Canvas(list_frame)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        self.models_frame = ttk.Frame(canvas)

        self.models_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.models_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Store model widgets for updating
        self.model_widgets = {}

        # Create row for each video model
        for i, (model_name, model_meta) in enumerate(VIDEO_MODELS.items()):
            self.create_model_row(i, model_name, model_meta)

        # Progress section
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=10)

        self.progress_bar = ttk.Progressbar(progress_frame, orient="horizontal",
                                            length=500, mode="determinate")
        self.progress_bar.pack(pady=5)

        self.progress_label = ttk.Label(progress_frame, text="")
        self.progress_label.pack()

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)

        self.download_all_btn = ttk.Button(button_frame, text="Download All Missing",
                                           command=self.download_all_missing)
        self.download_all_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="Refresh Status",
                  command=self.check_installed_models).pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="Close",
                  command=self.dialog.destroy).pack(side=tk.LEFT, padx=5)

    def create_model_row(self, index: int, model_name: str, model_meta: dict):
        """Create a row for a single model"""
        row_frame = ttk.Frame(self.models_frame)
        row_frame.pack(fill=tk.X, pady=5, padx=5)

        # Model info
        info_frame = ttk.Frame(row_frame)
        info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        name_label = ttk.Label(info_frame, text=model_name, font=('Arial', 10, 'bold'))
        name_label.pack(anchor=tk.W)

        desc_label = ttk.Label(info_frame, text=model_meta['description'],
                               foreground="gray")
        desc_label.pack(anchor=tk.W)

        # Status and download button
        status_frame = ttk.Frame(row_frame)
        status_frame.pack(side=tk.RIGHT)

        status_label = ttk.Label(status_frame, text="Checking...", width=15)
        status_label.pack(side=tk.LEFT, padx=5)

        download_btn = ttk.Button(status_frame, text="Download", width=10,
                                  command=lambda m=model_name: self.download_model(m))
        download_btn.pack(side=tk.LEFT, padx=5)

        self.model_widgets[model_name] = {
            'status_label': status_label,
            'download_btn': download_btn
        }

    def check_installed_models(self):
        """Check which models are installed"""
        from config import MODEL_FOLDERS

        for model_name in VIDEO_MODELS.keys():
            model_info = get_model_info(model_name)
            if not model_info:
                self.update_model_status(model_name, "❓ Unknown", "disabled")
                continue

            model_type = model_info.get('type', 'diffusion_models')
            folder = MODEL_FOLDERS.get(model_type)

            if not folder:
                self.update_model_status(model_name, "❓ No folder", "disabled")
                continue

            # Check if model exists
            model_path = folder / model_name
            # Also check in subfolder if specified
            subfolder = model_info.get('subfolder')
            if subfolder:
                model_path_sub = folder / subfolder / model_name
                if model_path_sub.exists():
                    model_path = model_path_sub

            if model_path.exists():
                self.update_model_status(model_name, "✅ Installed", "disabled")
            else:
                size_gb = model_info.get('size_gb', '?')
                self.update_model_status(model_name, f"❌ Missing ({size_gb}GB)", "normal")

    def update_model_status(self, model_name: str, status: str, btn_state: str):
        """Update the status display for a model"""
        widgets = self.model_widgets.get(model_name)
        if widgets:
            widgets['status_label'].config(text=status)
            widgets['download_btn'].config(state=btn_state)

            # Color based on status
            if "✅" in status:
                widgets['status_label'].config(foreground="green")
            elif "❌" in status:
                widgets['status_label'].config(foreground="red")
            else:
                widgets['status_label'].config(foreground="orange")

    def download_model(self, model_name: str):
        """Download a single model"""
        if self.download_in_progress:
            return

        model_info = get_model_info(model_name)
        if not model_info:
            self.progress_label.config(text=f"Model {model_name} not found in registry")
            return

        self.download_in_progress = True
        self.current_download = model_name

        # Disable all download buttons
        for widgets in self.model_widgets.values():
            widgets['download_btn'].config(state='disabled')
        self.download_all_btn.config(state='disabled')

        self.progress_label.config(text=f"Downloading {model_name}...")
        self.progress_bar['value'] = 0

        def download_thread():
            try:
                result = self.downloader.download_model(
                    {'filename': model_name, **model_info},
                    progress_callback=self.update_progress
                )

                self.dialog.after(0, lambda: self.on_download_complete(model_name, result is not None))

            except Exception as e:
                self.dialog.after(0, lambda: self.on_download_error(str(e)))

        thread = threading.Thread(target=download_thread, daemon=True)
        thread.start()

    def download_all_missing(self):
        """Download all missing models sequentially"""
        if self.download_in_progress:
            return

        # Find all missing models
        from config import MODEL_FOLDERS
        missing = []

        for model_name in VIDEO_MODELS.keys():
            model_info = get_model_info(model_name)
            if not model_info:
                continue

            model_type = model_info.get('type', 'diffusion_models')
            folder = MODEL_FOLDERS.get(model_type)
            if not folder:
                continue

            model_path = folder / model_name
            subfolder = model_info.get('subfolder')
            if subfolder:
                model_path_sub = folder / subfolder / model_name
                if model_path_sub.exists():
                    continue
            if not model_path.exists():
                missing.append(model_name)

        if not missing:
            self.progress_label.config(text="All models are already installed!")
            return

        self.progress_label.config(text=f"Downloading {len(missing)} missing models...")

        # Start downloading the first one
        self.pending_downloads = missing[1:]  # Queue the rest
        self.download_model(missing[0])

    def update_progress(self, percent: float, message: str):
        """Update download progress"""
        def update():
            self.progress_bar['value'] = percent
            self.progress_label.config(text=message)
        self.dialog.after(0, update)

    def on_download_complete(self, model_name: str, success: bool):
        """Handle download completion"""
        self.download_in_progress = False

        if success:
            self.log_callback(f"✅ Downloaded {model_name}")
            self.update_model_status(model_name, "✅ Installed", "disabled")

            # Check if there are more pending downloads
            if hasattr(self, 'pending_downloads') and self.pending_downloads:
                next_model = self.pending_downloads.pop(0)
                self.download_model(next_model)
                return
        else:
            self.log_callback(f"❌ Failed to download {model_name}")

        # Re-enable buttons
        self.check_installed_models()
        self.download_all_btn.config(state='normal')
        self.progress_label.config(text="Download complete!" if success else "Download failed")

    def on_download_error(self, error_msg: str):
        """Handle download error"""
        self.download_in_progress = False
        self.progress_label.config(text=f"Error: {error_msg}")
        self.log_callback(f"❌ Download error: {error_msg}")

        # Re-enable buttons
        self.check_installed_models()
        self.download_all_btn.config(state='normal')


def main():
    root = tk.Tk()
    app = ComfyUIPrompterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()

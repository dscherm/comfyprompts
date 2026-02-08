# model_downloader.py - Download models from HuggingFace and CivitAI

import os
import requests
from pathlib import Path
from typing import Optional, Callable, Dict, Any
from huggingface_hub import hf_hub_download, HfApi
from tqdm import tqdm

from comfyui_agent_sdk.credentials import get_huggingface_token, get_civitai_api_key
from config import MODEL_FOLDERS


class DownloadProgress:
    """Track download progress with callbacks for UI updates."""

    def __init__(self, callback: Optional[Callable[[float, str], None]] = None):
        """
        Args:
            callback: Function called with (progress_percent, status_message)
        """
        self.callback = callback
        self.total_size = 0
        self.downloaded = 0

    def update(self, chunk_size: int):
        """Update progress with downloaded chunk size."""
        self.downloaded += chunk_size
        if self.callback and self.total_size > 0:
            percent = (self.downloaded / self.total_size) * 100
            msg = f"Downloaded {self._format_size(self.downloaded)} / {self._format_size(self.total_size)}"
            self.callback(percent, msg)

    def set_total(self, total: int):
        """Set total file size."""
        self.total_size = total

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format bytes as human-readable string."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"


class ModelDownloader:
    """Download models from HuggingFace and CivitAI."""

    def __init__(self):
        self.hf_api = HfApi()

    def check_model_exists(self, filename: str, model_type: str, subfolder: Optional[str] = None) -> Optional[Path]:
        """
        Check if a model file exists in the appropriate folder.

        Args:
            filename: Name of the model file (can include path)
            model_type: Type of model (e.g., 'checkpoints', 'loras', 'vae')
            subfolder: Optional subfolder to check within the model folder

        Returns:
            Path to the model if it exists, None otherwise
        """
        folder = MODEL_FOLDERS.get(model_type)
        if not folder:
            print(f"Unknown model type: {model_type}")
            return None

        # Extract just the filename if it contains a path
        local_filename = Path(filename).name

        # Check in main folder
        model_path = folder / local_filename
        if model_path.exists():
            return model_path

        # Check in subfolder if specified
        if subfolder:
            model_path_sub = folder / subfolder / local_filename
            if model_path_sub.exists():
                return model_path_sub

        # Also check for files without extension match
        for existing_file in folder.glob(f"{Path(local_filename).stem}*"):
            return existing_file

        # Check subfolders for the file
        for existing_file in folder.rglob(local_filename):
            return existing_file

        return None

    def download_from_huggingface(
        self,
        repo_id: str,
        filename: str,
        model_type: str,
        subfolder: Optional[str] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> Optional[Path]:
        """
        Download a model from HuggingFace Hub.

        Args:
            repo_id: HuggingFace repository ID (e.g., 'black-forest-labs/FLUX.1-dev')
            filename: Name of the file to download (can include path like 'split_files/model.safetensors')
            model_type: Type of model for destination folder
            subfolder: Optional subfolder within the repo
            progress_callback: Optional callback for progress updates

        Returns:
            Path to downloaded file, or None if failed
        """
        folder = MODEL_FOLDERS.get(model_type)
        if not folder:
            print(f"Unknown model type: {model_type}")
            return None

        # Extract just the filename if it contains a path
        local_filename = Path(filename).name

        # Check if already exists (using local filename)
        existing = self.check_model_exists(local_filename, model_type)
        if existing:
            if progress_callback:
                progress_callback(100, f"Model already exists: {existing.name}")
            return existing

        # Also check with subfolder if specified
        if subfolder:
            subfolder_path = folder / subfolder / local_filename
            if subfolder_path.exists():
                if progress_callback:
                    progress_callback(100, f"Model already exists: {subfolder_path.name}")
                return subfolder_path

        # Get token if available
        token = get_huggingface_token()

        try:
            if progress_callback:
                progress_callback(0, f"Downloading {local_filename} from HuggingFace...")

            # Determine destination folder (with subfolder if specified)
            dest_folder = folder / subfolder if subfolder else folder
            dest_folder.mkdir(parents=True, exist_ok=True)

            # Download using huggingface_hub
            downloaded_path = hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                local_dir=folder,
                local_dir_use_symlinks=False,
                token=token,
            )

            downloaded = Path(downloaded_path)

            # If the file was downloaded to a nested path, move it to the correct location
            expected_path = dest_folder / local_filename
            if downloaded != expected_path and downloaded.exists():
                # Move the file to the expected location
                import shutil
                expected_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(downloaded), str(expected_path))
                # Clean up empty directories
                try:
                    downloaded.parent.rmdir()
                except:
                    pass
                downloaded = expected_path

            if progress_callback:
                progress_callback(100, f"Download complete: {local_filename}")

            return downloaded

        except Exception as e:
            print(f"Error downloading from HuggingFace: {e}")
            if progress_callback:
                progress_callback(0, f"Error: {e}")
            return None

    def download_from_civitai(
        self,
        model_version_id: int,
        model_type: str,
        filename: Optional[str] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> Optional[Path]:
        """
        Download a model from CivitAI.

        Args:
            model_version_id: CivitAI model version ID
            model_type: Type of model for destination folder
            filename: Optional filename override
            progress_callback: Optional callback for progress updates

        Returns:
            Path to downloaded file, or None if failed
        """
        folder = MODEL_FOLDERS.get(model_type)
        if not folder:
            print(f"Unknown model type: {model_type}")
            return None

        api_key = get_civitai_api_key()
        if not api_key:
            print("CivitAI API key not configured")
            if progress_callback:
                progress_callback(0, "Error: CivitAI API key not configured")
            return None

        try:
            # Get model info from CivitAI API
            info_url = f"https://civitai.com/api/v1/model-versions/{model_version_id}"
            headers = {"Authorization": f"Bearer {api_key}"}

            if progress_callback:
                progress_callback(0, "Fetching model info from CivitAI...")

            response = requests.get(info_url, headers=headers, timeout=30)
            response.raise_for_status()
            model_info = response.json()

            # Find the primary file
            files = model_info.get('files', [])
            if not files:
                print("No files found for this model version")
                return None

            # Get the first file (usually the main model)
            file_info = files[0]
            download_url = file_info.get('downloadUrl')
            actual_filename = filename or file_info.get('name')

            if not download_url or not actual_filename:
                print("Could not get download URL or filename")
                return None

            # Check if already exists
            existing = self.check_model_exists(actual_filename, model_type)
            if existing:
                if progress_callback:
                    progress_callback(100, f"Model already exists: {existing.name}")
                return existing

            # Download the file
            dest_path = folder / actual_filename

            if progress_callback:
                progress_callback(0, f"Downloading {actual_filename} from CivitAI...")

            # Stream download with progress
            response = requests.get(
                download_url,
                headers=headers,
                stream=True,
                timeout=30
            )
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            progress = DownloadProgress(progress_callback)
            progress.set_total(total_size)

            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        progress.update(len(chunk))

            if progress_callback:
                progress_callback(100, f"Download complete: {actual_filename}")

            return dest_path

        except Exception as e:
            print(f"Error downloading from CivitAI: {e}")
            if progress_callback:
                progress_callback(0, f"Error: {e}")
            return None

    def download_model(
        self,
        model_info: Dict[str, Any],
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> Optional[Path]:
        """
        Download a model using info from the model registry.

        Args:
            model_info: Dictionary with model information from MODEL_REGISTRY
            progress_callback: Optional callback for progress updates

        Returns:
            Path to downloaded file, or None if failed
        """
        source = model_info.get('source', '').lower()
        model_type = model_info.get('type', 'checkpoints')

        if source == 'huggingface':
            return self.download_from_huggingface(
                repo_id=model_info.get('repo_id', ''),
                filename=model_info.get('filename', ''),
                model_type=model_type,
                subfolder=model_info.get('subfolder'),
                progress_callback=progress_callback
            )
        elif source == 'civitai':
            return self.download_from_civitai(
                model_version_id=model_info.get('version_id', 0),
                model_type=model_type,
                filename=model_info.get('filename'),
                progress_callback=progress_callback
            )
        else:
            print(f"Unknown source: {source}")
            return None

    def get_model_info_from_huggingface(self, repo_id: str) -> Optional[Dict]:
        """Get information about a HuggingFace repository."""
        try:
            token = get_huggingface_token()
            info = self.hf_api.repo_info(repo_id=repo_id, token=token)
            return {
                'id': info.id,
                'sha': info.sha,
                'private': info.private,
                'downloads': getattr(info, 'downloads', 0),
                'likes': getattr(info, 'likes', 0),
            }
        except Exception as e:
            print(f"Error getting repo info: {e}")
            return None

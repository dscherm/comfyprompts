# history_manager.py - Manages generation history and favorites

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import uuid


class HistoryManager:
    """Manages generation history and favorites"""

    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or Path.home() / ".comfyui-prompter"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.data_dir / "history.json"
        self.favorites_file = self.data_dir / "favorites.json"
        self._history: List[Dict] = []
        self._favorites: List[str] = []  # List of history IDs
        self._load()

    def _load(self):
        """Load history and favorites from disk"""
        # Load history
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self._history = json.load(f)
            except:
                self._history = []

        # Load favorites
        if self.favorites_file.exists():
            try:
                with open(self.favorites_file, 'r', encoding='utf-8') as f:
                    self._favorites = json.load(f)
            except:
                self._favorites = []

    def _save(self):
        """Save history and favorites to disk"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self._history, f, indent=2, ensure_ascii=False)
            with open(self.favorites_file, 'w', encoding='utf-8') as f:
                json.dump(self._favorites, f, indent=2)
        except Exception as e:
            print(f"Error saving history: {e}")

    def add_generation(self, prompt: str, negative_prompt: str = "",
                       workflow: str = "", checkpoint: str = "",
                       style: str = "", seed: int = None,
                       output_path: str = None, status: str = "queued") -> str:
        """
        Add a new generation to history

        Returns:
            The ID of the new history entry
        """
        entry_id = str(uuid.uuid4())[:8]
        entry = {
            "id": entry_id,
            "timestamp": datetime.now().isoformat(),
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "workflow": workflow,
            "checkpoint": checkpoint,
            "style": style,
            "seed": seed,
            "output_path": output_path,
            "status": status
        }

        self._history.insert(0, entry)

        # Keep only last 100 entries
        if len(self._history) > 100:
            self._history = self._history[:100]

        self._save()
        return entry_id

    def update_generation(self, entry_id: str, **kwargs):
        """Update a generation entry"""
        for entry in self._history:
            if entry["id"] == entry_id:
                entry.update(kwargs)
                self._save()
                return True
        return False

    def get_history(self, limit: int = 20) -> List[Dict]:
        """Get recent history entries"""
        return self._history[:limit]

    def get_entry(self, entry_id: str) -> Optional[Dict]:
        """Get a specific history entry"""
        for entry in self._history:
            if entry["id"] == entry_id:
                return entry
        return None

    def toggle_favorite(self, entry_id: str) -> bool:
        """Toggle favorite status for an entry"""
        if entry_id in self._favorites:
            self._favorites.remove(entry_id)
            result = False
        else:
            self._favorites.append(entry_id)
            result = True
        self._save()
        return result

    def is_favorite(self, entry_id: str) -> bool:
        """Check if an entry is favorited"""
        return entry_id in self._favorites

    def get_favorites(self) -> List[Dict]:
        """Get all favorited entries"""
        return [e for e in self._history if e["id"] in self._favorites]

    def delete_entry(self, entry_id: str) -> bool:
        """Delete a history entry"""
        for i, entry in enumerate(self._history):
            if entry["id"] == entry_id:
                del self._history[i]
                if entry_id in self._favorites:
                    self._favorites.remove(entry_id)
                self._save()
                return True
        return False

    def clear_history(self):
        """Clear all history (keeps favorites)"""
        favorite_entries = [e for e in self._history if e["id"] in self._favorites]
        self._history = favorite_entries
        self._save()

    def search(self, query: str) -> List[Dict]:
        """Search history by prompt text"""
        query = query.lower()
        return [e for e in self._history if query in e.get("prompt", "").lower()]


# Singleton instance
_history_manager = None


def get_history_manager() -> HistoryManager:
    """Get the singleton history manager"""
    global _history_manager
    if _history_manager is None:
        _history_manager = HistoryManager()
    return _history_manager

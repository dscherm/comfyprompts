"""Prompt library manager for saving, organizing, and reusing prompts"""

import json
import logging
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("MCP_Server")

# Configuration paths
CONFIG_DIR = Path.home() / ".config" / "comfy-mcp"
PROMPTS_FILE = CONFIG_DIR / "prompt_library.json"
TEMPLATES_FILE = CONFIG_DIR / "prompt_templates.json"
HISTORY_FILE = CONFIG_DIR / "prompt_history.json"

MAX_HISTORY_SIZE = 500  # Maximum prompts to keep in history


class PromptLibrary:
    """Manages saved prompts, templates, and prompt history"""

    def __init__(self):
        self._prompts: Dict[str, Dict[str, Any]] = {}
        self._templates: Dict[str, Dict[str, Any]] = {}
        self._history: List[Dict[str, Any]] = []
        self._load_all()

    def _load_all(self) -> None:
        """Load prompts, templates, and history from config files"""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        # Load saved prompts
        if PROMPTS_FILE.exists():
            try:
                with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
                    self._prompts = json.load(f)
                logger.info(f"Loaded {len(self._prompts)} saved prompts")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load prompts: {e}")

        # Load templates
        if TEMPLATES_FILE.exists():
            try:
                with open(TEMPLATES_FILE, "r", encoding="utf-8") as f:
                    self._templates = json.load(f)
                logger.info(f"Loaded {len(self._templates)} prompt templates")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load templates: {e}")

        # Load history
        if HISTORY_FILE.exists():
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    self._history = json.load(f)
                logger.info(f"Loaded {len(self._history)} prompts from history")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load history: {e}")

    def _save_prompts(self) -> None:
        """Save prompts to config file"""
        try:
            with open(PROMPTS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._prompts, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save prompts: {e}")

    def _save_templates(self) -> None:
        """Save templates to config file"""
        try:
            with open(TEMPLATES_FILE, "w", encoding="utf-8") as f:
                json.dump(self._templates, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save templates: {e}")

    def _save_history(self) -> None:
        """Save history to config file"""
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self._history, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save history: {e}")

    # ==================== PROMPT MANAGEMENT ====================

    def save_prompt(
        self,
        prompt: str,
        name: str,
        tags: Optional[List[str]] = None,
        negative_prompt: str = "",
        description: str = "",
        category: str = "general",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Save a prompt to the library

        Args:
            prompt: The positive prompt text
            name: A memorable name for this prompt
            tags: Optional list of tags for organization
            negative_prompt: Associated negative prompt
            description: Optional description of what this prompt creates
            category: Category for organization (e.g., "portraits", "landscapes")
            metadata: Optional additional metadata (settings, model used, etc.)

        Returns:
            Dict with prompt_id and saved prompt data
        """
        prompt_id = str(uuid.uuid4())[:8]

        # Ensure unique name
        existing_names = [p.get("name", "").lower() for p in self._prompts.values()]
        base_name = name
        counter = 1
        while name.lower() in existing_names:
            name = f"{base_name}_{counter}"
            counter += 1

        prompt_data = {
            "prompt": prompt,
            "name": name,
            "tags": tags or [],
            "negative_prompt": negative_prompt,
            "description": description,
            "category": category,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "use_count": 0,
            "favorite": False
        }

        self._prompts[prompt_id] = prompt_data
        self._save_prompts()

        return {
            "success": True,
            "prompt_id": prompt_id,
            "prompt": prompt_data
        }

    def get_prompt(self, prompt_id: str) -> Optional[Dict[str, Any]]:
        """Get a saved prompt by ID"""
        if prompt_id in self._prompts:
            return {"id": prompt_id, **self._prompts[prompt_id]}
        return None

    def list_prompts(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        search: Optional[str] = None,
        favorites_only: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """List saved prompts with optional filtering

        Args:
            category: Filter by category
            tags: Filter by tags (prompts must have ALL specified tags)
            search: Search in prompt text, name, and description
            favorites_only: Only return favorited prompts
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            Dict with prompts list and pagination info
        """
        results = []

        for prompt_id, prompt_data in self._prompts.items():
            # Apply filters
            if category and prompt_data.get("category", "").lower() != category.lower():
                continue

            if tags:
                prompt_tags = [t.lower() for t in prompt_data.get("tags", [])]
                if not all(t.lower() in prompt_tags for t in tags):
                    continue

            if favorites_only and not prompt_data.get("favorite", False):
                continue

            if search:
                search_lower = search.lower()
                searchable = (
                    prompt_data.get("prompt", "") +
                    prompt_data.get("name", "") +
                    prompt_data.get("description", "")
                ).lower()
                if search_lower not in searchable:
                    continue

            results.append({
                "id": prompt_id,
                "name": prompt_data.get("name", ""),
                "prompt": prompt_data.get("prompt", "")[:100] + ("..." if len(prompt_data.get("prompt", "")) > 100 else ""),
                "tags": prompt_data.get("tags", []),
                "category": prompt_data.get("category", ""),
                "favorite": prompt_data.get("favorite", False),
                "use_count": prompt_data.get("use_count", 0),
                "created_at": prompt_data.get("created_at", "")
            })

        # Sort by use_count (most used first), then by created_at
        results.sort(key=lambda x: (-x.get("use_count", 0), x.get("created_at", "")), reverse=False)

        total = len(results)
        results = results[offset:offset + limit]

        return {
            "prompts": results,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total
        }

    def update_prompt(
        self,
        prompt_id: str,
        prompt: Optional[str] = None,
        name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        negative_prompt: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        favorite: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Update a saved prompt"""
        if prompt_id not in self._prompts:
            return {"error": f"Prompt '{prompt_id}' not found"}

        if prompt is not None:
            self._prompts[prompt_id]["prompt"] = prompt
        if name is not None:
            self._prompts[prompt_id]["name"] = name
        if tags is not None:
            self._prompts[prompt_id]["tags"] = tags
        if negative_prompt is not None:
            self._prompts[prompt_id]["negative_prompt"] = negative_prompt
        if description is not None:
            self._prompts[prompt_id]["description"] = description
        if category is not None:
            self._prompts[prompt_id]["category"] = category
        if favorite is not None:
            self._prompts[prompt_id]["favorite"] = favorite

        self._prompts[prompt_id]["updated_at"] = datetime.now().isoformat()
        self._save_prompts()

        return {"success": True, "prompt": {"id": prompt_id, **self._prompts[prompt_id]}}

    def delete_prompt(self, prompt_id: str) -> Dict[str, Any]:
        """Delete a saved prompt"""
        if prompt_id not in self._prompts:
            return {"error": f"Prompt '{prompt_id}' not found"}

        del self._prompts[prompt_id]
        self._save_prompts()

        return {"success": True, "deleted": prompt_id}

    def use_prompt(self, prompt_id: str) -> Dict[str, Any]:
        """Mark a prompt as used and return it

        This increments the use count and returns the full prompt data
        for use in generation.
        """
        if prompt_id not in self._prompts:
            return {"error": f"Prompt '{prompt_id}' not found"}

        self._prompts[prompt_id]["use_count"] = self._prompts[prompt_id].get("use_count", 0) + 1
        self._prompts[prompt_id]["last_used"] = datetime.now().isoformat()
        self._save_prompts()

        return {
            "prompt": self._prompts[prompt_id]["prompt"],
            "negative_prompt": self._prompts[prompt_id].get("negative_prompt", ""),
            "metadata": self._prompts[prompt_id].get("metadata", {})
        }

    def get_categories(self) -> List[str]:
        """Get all unique categories"""
        categories = set()
        for prompt_data in self._prompts.values():
            cat = prompt_data.get("category", "")
            if cat:
                categories.add(cat)
        return sorted(list(categories))

    def get_all_tags(self) -> List[Dict[str, Any]]:
        """Get all unique tags with counts"""
        tag_counts = {}
        for prompt_data in self._prompts.values():
            for tag in prompt_data.get("tags", []):
                tag_lower = tag.lower()
                tag_counts[tag_lower] = tag_counts.get(tag_lower, 0) + 1

        return sorted(
            [{"tag": tag, "count": count} for tag, count in tag_counts.items()],
            key=lambda x: -x["count"]
        )

    # ==================== TEMPLATE MANAGEMENT ====================

    def save_template(
        self,
        template_id: str,
        name: str,
        template: str,
        description: str = "",
        variables: Optional[Dict[str, Dict[str, Any]]] = None,
        example_values: Optional[Dict[str, str]] = None,
        category: str = "general"
    ) -> Dict[str, Any]:
        """Save a prompt template with variables

        Templates use {variable_name} syntax for placeholders.

        Args:
            template_id: Unique identifier for the template
            name: Display name
            template: Template text with {variables}
            description: What this template creates
            variables: Dict of variable definitions with optional defaults and descriptions
                       e.g., {"subject": {"default": "person", "description": "Main subject"}}
            example_values: Example values to show users
            category: Template category

        Returns:
            Dict with saved template data

        Example:
            save_template(
                template_id="portrait",
                name="Portrait Template",
                template="portrait of {subject}, {style} style, {lighting} lighting",
                variables={
                    "subject": {"description": "Person or character to portray"},
                    "style": {"default": "realistic", "description": "Art style"},
                    "lighting": {"default": "soft", "description": "Lighting type"}
                },
                example_values={"subject": "a young woman with red hair", "style": "oil painting", "lighting": "dramatic"}
            )
        """
        # Extract variables from template
        found_vars = re.findall(r'\{(\w+)\}', template)

        if variables is None:
            variables = {var: {} for var in found_vars}

        template_data = {
            "name": name,
            "template": template,
            "description": description,
            "variables": variables,
            "variable_names": found_vars,
            "example_values": example_values or {},
            "category": category,
            "created_at": datetime.now().isoformat(),
            "use_count": 0
        }

        self._templates[template_id] = template_data
        self._save_templates()

        return {
            "success": True,
            "template_id": template_id,
            "template": template_data
        }

    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get a template by ID"""
        if template_id in self._templates:
            return {"id": template_id, **self._templates[template_id]}
        return None

    def list_templates(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List all templates with optional filtering"""
        results = []

        for template_id, template_data in self._templates.items():
            if category and template_data.get("category", "").lower() != category.lower():
                continue

            if search:
                search_lower = search.lower()
                searchable = (
                    template_data.get("name", "") +
                    template_data.get("description", "") +
                    template_data.get("template", "")
                ).lower()
                if search_lower not in searchable:
                    continue

            results.append({
                "id": template_id,
                "name": template_data.get("name", ""),
                "description": template_data.get("description", ""),
                "variables": template_data.get("variable_names", []),
                "category": template_data.get("category", ""),
                "use_count": template_data.get("use_count", 0)
            })

        return sorted(results, key=lambda x: -x.get("use_count", 0))

    def fill_template(
        self,
        template_id: str,
        values: Dict[str, str]
    ) -> Dict[str, Any]:
        """Fill a template with values

        Args:
            template_id: Template to use
            values: Dict of variable_name -> value

        Returns:
            Dict with filled prompt and any missing variables
        """
        if template_id not in self._templates:
            return {"error": f"Template '{template_id}' not found"}

        template_data = self._templates[template_id]
        template = template_data["template"]
        variables = template_data.get("variables", {})

        # Apply defaults for missing values
        final_values = {}
        missing = []

        for var_name in template_data.get("variable_names", []):
            if var_name in values and values[var_name]:
                final_values[var_name] = values[var_name]
            elif var_name in variables and "default" in variables[var_name]:
                final_values[var_name] = variables[var_name]["default"]
            else:
                missing.append(var_name)

        if missing:
            return {
                "error": f"Missing required variables: {missing}",
                "missing_variables": missing,
                "template": template
            }

        # Fill template
        filled = template
        for var_name, value in final_values.items():
            filled = filled.replace(f"{{{var_name}}}", value)

        # Increment use count
        self._templates[template_id]["use_count"] = template_data.get("use_count", 0) + 1
        self._save_templates()

        return {
            "prompt": filled,
            "template_id": template_id,
            "values_used": final_values
        }

    def delete_template(self, template_id: str) -> Dict[str, Any]:
        """Delete a template"""
        if template_id not in self._templates:
            return {"error": f"Template '{template_id}' not found"}

        del self._templates[template_id]
        self._save_templates()

        return {"success": True, "deleted": template_id}

    # ==================== HISTORY MANAGEMENT ====================

    def add_to_history(
        self,
        prompt: str,
        negative_prompt: str = "",
        workflow_id: str = "",
        settings: Optional[Dict[str, Any]] = None,
        asset_id: Optional[str] = None
    ) -> None:
        """Add a prompt to history (called automatically during generation)"""
        history_entry = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "workflow_id": workflow_id,
            "settings": settings or {},
            "asset_id": asset_id,
            "timestamp": datetime.now().isoformat()
        }

        # Add to beginning of history
        self._history.insert(0, history_entry)

        # Trim history if too long
        if len(self._history) > MAX_HISTORY_SIZE:
            self._history = self._history[:MAX_HISTORY_SIZE]

        self._save_history()

    def get_history(
        self,
        limit: int = 50,
        offset: int = 0,
        search: Optional[str] = None,
        workflow_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get prompt history with optional filtering"""
        results = self._history.copy()

        # Apply filters
        if search:
            search_lower = search.lower()
            results = [
                h for h in results
                if search_lower in h.get("prompt", "").lower()
                or search_lower in h.get("negative_prompt", "").lower()
            ]

        if workflow_id:
            results = [h for h in results if h.get("workflow_id") == workflow_id]

        total = len(results)
        results = results[offset:offset + limit]

        return {
            "history": results,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total
        }

    def clear_history(self) -> Dict[str, Any]:
        """Clear all prompt history"""
        count = len(self._history)
        self._history = []
        self._save_history()
        return {"success": True, "cleared": count}

    def save_from_history(
        self,
        history_index: int,
        name: str,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Save a prompt from history to the library"""
        if history_index < 0 or history_index >= len(self._history):
            return {"error": f"Invalid history index: {history_index}"}

        history_entry = self._history[history_index]

        return self.save_prompt(
            prompt=history_entry.get("prompt", ""),
            name=name,
            tags=tags,
            negative_prompt=history_entry.get("negative_prompt", ""),
            metadata=history_entry.get("settings", {})
        )

    # ==================== UTILITY ====================

    def get_stats(self) -> Dict[str, Any]:
        """Get library statistics"""
        return {
            "total_prompts": len(self._prompts),
            "total_templates": len(self._templates),
            "history_size": len(self._history),
            "categories": self.get_categories(),
            "total_tags": len(self.get_all_tags()),
            "favorites_count": sum(1 for p in self._prompts.values() if p.get("favorite", False)),
            "most_used": sorted(
                [
                    {"id": pid, "name": p.get("name", ""), "use_count": p.get("use_count", 0)}
                    for pid, p in self._prompts.items()
                ],
                key=lambda x: -x["use_count"]
            )[:5]
        }

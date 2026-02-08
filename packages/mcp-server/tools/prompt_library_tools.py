"""Prompt library tools for saving, organizing, and reusing prompts"""

import logging
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("MCP_Server")


def register_prompt_library_tools(
    mcp: FastMCP,
    prompt_library
):
    """Register prompt library tools"""

    # ==================== PROMPT MANAGEMENT ====================

    @mcp.tool()
    def save_prompt(
        prompt: str,
        name: str,
        tags: Optional[List[str]] = None,
        negative_prompt: str = "",
        description: str = "",
        category: str = "general"
    ) -> dict:
        """Save a successful prompt to your library for reuse.

        Args:
            prompt: The positive prompt text
            name: A memorable name for this prompt
            tags: Optional tags for organization (e.g., ["portrait", "anime"])
            negative_prompt: Associated negative prompt
            description: What this prompt creates
            category: Category like "portraits", "landscapes", "characters"

        Returns:
            dict: Saved prompt with ID

        Example:
            save_prompt(
                prompt="a majestic dragon flying over mountains at sunset",
                name="Epic Dragon",
                tags=["fantasy", "dragon", "landscape"],
                negative_prompt="blurry, low quality",
                category="fantasy"
            )
        """
        return prompt_library.save_prompt(
            prompt=prompt,
            name=name,
            tags=tags,
            negative_prompt=negative_prompt,
            description=description,
            category=category
        )

    @mcp.tool()
    def list_prompts(
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        search: Optional[str] = None,
        favorites_only: bool = False,
        limit: int = 20
    ) -> dict:
        """List saved prompts with optional filtering.

        Args:
            category: Filter by category
            tags: Filter by tags (must have ALL specified tags)
            search: Search in prompt text, name, and description
            favorites_only: Only return favorited prompts
            limit: Maximum results to return

        Returns:
            dict: List of matching prompts

        Example:
            list_prompts(category="portraits", tags=["anime"])
            list_prompts(search="dragon")
            list_prompts(favorites_only=True)
        """
        return prompt_library.list_prompts(
            category=category,
            tags=tags,
            search=search,
            favorites_only=favorites_only,
            limit=limit
        )

    @mcp.tool()
    def get_prompt(prompt_id: str) -> dict:
        """Get full details of a saved prompt.

        Args:
            prompt_id: The prompt ID

        Returns:
            dict: Full prompt data including negative prompt and metadata
        """
        prompt = prompt_library.get_prompt(prompt_id)
        if not prompt:
            return {"error": f"Prompt '{prompt_id}' not found"}
        return {"prompt": prompt}

    @mcp.tool()
    def use_prompt(prompt_id: str) -> dict:
        """Get a prompt for generation and track its usage.

        Returns the prompt and negative_prompt ready to use with generate_image.
        Automatically increments the use counter.

        Args:
            prompt_id: The prompt ID to use

        Returns:
            dict: Prompt and negative_prompt for generation
        """
        return prompt_library.use_prompt(prompt_id)

    @mcp.tool()
    def favorite_prompt(prompt_id: str, favorite: bool = True) -> dict:
        """Mark or unmark a prompt as favorite.

        Args:
            prompt_id: The prompt ID
            favorite: True to favorite, False to unfavorite

        Returns:
            dict: Updated prompt data
        """
        return prompt_library.update_prompt(prompt_id, favorite=favorite)

    @mcp.tool()
    def update_prompt(
        prompt_id: str,
        prompt: Optional[str] = None,
        name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        negative_prompt: Optional[str] = None,
        category: Optional[str] = None
    ) -> dict:
        """Update a saved prompt.

        Args:
            prompt_id: The prompt ID to update
            prompt: New prompt text
            name: New name
            tags: New tags (replaces existing)
            negative_prompt: New negative prompt
            category: New category

        Returns:
            dict: Updated prompt data
        """
        return prompt_library.update_prompt(
            prompt_id=prompt_id,
            prompt=prompt,
            name=name,
            tags=tags,
            negative_prompt=negative_prompt,
            category=category
        )

    @mcp.tool()
    def delete_prompt(prompt_id: str) -> dict:
        """Delete a saved prompt.

        Args:
            prompt_id: The prompt ID to delete

        Returns:
            dict: Success status
        """
        return prompt_library.delete_prompt(prompt_id)

    @mcp.tool()
    def get_prompt_categories() -> dict:
        """Get all prompt categories in your library.

        Returns:
            dict: List of categories
        """
        return {"categories": prompt_library.get_categories()}

    @mcp.tool()
    def get_prompt_tags() -> dict:
        """Get all tags used in your prompt library with counts.

        Returns:
            dict: List of tags with usage counts
        """
        return {"tags": prompt_library.get_all_tags()}

    # ==================== TEMPLATE MANAGEMENT ====================

    @mcp.tool()
    def save_template(
        template_id: str,
        name: str,
        template: str,
        description: str = "",
        variables: Optional[Dict[str, Dict[str, Any]]] = None,
        example_values: Optional[Dict[str, str]] = None,
        category: str = "general"
    ) -> dict:
        """Save a prompt template with fillable variables.

        Templates use {variable_name} syntax for placeholders.
        Great for consistent character/style generation.

        Args:
            template_id: Unique ID for this template
            name: Display name
            template: Template text with {variables}
            description: What this template creates
            variables: Variable definitions with defaults and descriptions
            example_values: Example values to show users
            category: Template category

        Returns:
            dict: Saved template data

        Example:
            save_template(
                template_id="character_portrait",
                name="Character Portrait",
                template="portrait of {character}, {expression} expression, {style} style, {background} background",
                variables={
                    "character": {"description": "Character description"},
                    "expression": {"default": "neutral", "description": "Facial expression"},
                    "style": {"default": "digital art", "description": "Art style"},
                    "background": {"default": "simple gradient", "description": "Background type"}
                },
                example_values={
                    "character": "a young elf mage with silver hair",
                    "expression": "determined",
                    "style": "fantasy illustration",
                    "background": "magical forest"
                }
            )
        """
        return prompt_library.save_template(
            template_id=template_id,
            name=name,
            template=template,
            description=description,
            variables=variables,
            example_values=example_values,
            category=category
        )

    @mcp.tool()
    def list_templates(
        category: Optional[str] = None,
        search: Optional[str] = None
    ) -> dict:
        """List all prompt templates.

        Args:
            category: Filter by category
            search: Search in name, description, template text

        Returns:
            dict: List of templates
        """
        templates = prompt_library.list_templates(category=category, search=search)
        return {"templates": templates, "total": len(templates)}

    @mcp.tool()
    def get_template(template_id: str) -> dict:
        """Get full details of a template including variables.

        Args:
            template_id: The template ID

        Returns:
            dict: Full template data with variable definitions
        """
        template = prompt_library.get_template(template_id)
        if not template:
            return {"error": f"Template '{template_id}' not found"}
        return {"template": template}

    @mcp.tool()
    def fill_template(
        template_id: str,
        values: Dict[str, str]
    ) -> dict:
        """Fill a template with values to generate a prompt.

        Args:
            template_id: Template to use
            values: Variable values to fill in

        Returns:
            dict: Filled prompt ready for generation

        Example:
            fill_template(
                template_id="character_portrait",
                values={
                    "character": "a fierce warrior with scars",
                    "expression": "angry",
                    "style": "oil painting"
                }
            )
        """
        return prompt_library.fill_template(template_id, values)

    @mcp.tool()
    def delete_template(template_id: str) -> dict:
        """Delete a template.

        Args:
            template_id: The template ID to delete

        Returns:
            dict: Success status
        """
        return prompt_library.delete_template(template_id)

    # ==================== HISTORY MANAGEMENT ====================

    @mcp.tool()
    def get_prompt_history(
        limit: int = 20,
        search: Optional[str] = None,
        workflow_id: Optional[str] = None
    ) -> dict:
        """Get your prompt history (most recent first).

        Args:
            limit: Maximum results to return
            search: Search in prompts
            workflow_id: Filter by workflow (e.g., "generate_image")

        Returns:
            dict: List of recent prompts with timestamps
        """
        return prompt_library.get_history(
            limit=limit,
            search=search,
            workflow_id=workflow_id
        )

    @mcp.tool()
    def save_from_history(
        history_index: int,
        name: str,
        tags: Optional[List[str]] = None
    ) -> dict:
        """Save a prompt from history to your library.

        Args:
            history_index: Index in history (0 = most recent)
            name: Name for the saved prompt
            tags: Optional tags

        Returns:
            dict: Saved prompt data
        """
        return prompt_library.save_from_history(history_index, name, tags)

    @mcp.tool()
    def clear_prompt_history() -> dict:
        """Clear all prompt history.

        Returns:
            dict: Number of entries cleared
        """
        return prompt_library.clear_history()

    # ==================== STATS ====================

    @mcp.tool()
    def get_prompt_library_stats() -> dict:
        """Get statistics about your prompt library.

        Returns:
            dict: Stats including total prompts, templates, favorites, most used
        """
        return prompt_library.get_stats()

    logger.info("Registered prompt library tools")

"""Tests for prompt library functionality"""

import pytest
from managers.prompt_library import PromptLibrary


@pytest.fixture
def prompt_lib():
    """Create a fresh PromptLibrary for each test."""
    lib = PromptLibrary()
    # Clear any existing data
    lib._prompts = {}
    lib._templates = {}
    lib._history = []
    return lib


class TestPromptSaving:
    """Test saving prompts to the library"""

    def test_save_prompt_returns_id(self, prompt_lib):
        """Verify save_prompt returns a prompt ID."""
        result = prompt_lib.save_prompt(
            prompt="a beautiful sunset over mountains",
            name="Sunset Mountains"
        )
        assert result["success"] is True
        assert "prompt_id" in result
        assert len(result["prompt_id"]) > 0

    def test_save_prompt_with_tags(self, prompt_lib):
        """Verify prompts can be saved with tags."""
        result = prompt_lib.save_prompt(
            prompt="a dragon flying",
            name="Dragon",
            tags=["fantasy", "creature"]
        )
        saved = prompt_lib.get_prompt(result["prompt_id"])
        assert saved is not None
        assert "fantasy" in saved["tags"]
        assert "creature" in saved["tags"]

    def test_save_prompt_with_negative(self, prompt_lib):
        """Verify prompts can include negative prompts."""
        result = prompt_lib.save_prompt(
            prompt="portrait of a person",
            name="Portrait",
            negative_prompt="blurry, low quality"
        )
        saved = prompt_lib.get_prompt(result["prompt_id"])
        assert saved["negative_prompt"] == "blurry, low quality"


class TestPromptRetrieval:
    """Test retrieving prompts"""

    def test_get_prompt_returns_full_data(self, prompt_lib):
        """Verify get_prompt returns complete prompt data."""
        result = prompt_lib.save_prompt(
            prompt="test prompt",
            name="Test",
            category="testing"
        )
        prompt = prompt_lib.get_prompt(result["prompt_id"])

        assert prompt is not None
        assert prompt["prompt"] == "test prompt"
        assert prompt["name"] == "Test"
        assert prompt["category"] == "testing"

    def test_get_nonexistent_prompt(self, prompt_lib):
        """Verify get_prompt returns None for unknown IDs."""
        prompt = prompt_lib.get_prompt("nonexistent_id")
        assert prompt is None

    def test_list_prompts_empty(self, prompt_lib):
        """Verify list_prompts works with empty library."""
        result = prompt_lib.list_prompts()
        assert "prompts" in result
        assert result["total"] == 0

    def test_list_prompts_with_filter(self, prompt_lib):
        """Verify list_prompts filters by category."""
        prompt_lib.save_prompt(prompt="p1", name="n1", category="landscapes")
        prompt_lib.save_prompt(prompt="p2", name="n2", category="portraits")
        prompt_lib.save_prompt(prompt="p3", name="n3", category="landscapes")

        result = prompt_lib.list_prompts(category="landscapes")
        assert result["total"] == 2

    def test_list_prompts_with_search(self, prompt_lib):
        """Verify list_prompts searches text."""
        prompt_lib.save_prompt(prompt="a dragon flying over mountains", name="Dragon")
        prompt_lib.save_prompt(prompt="a cat sleeping", name="Cat")

        result = prompt_lib.list_prompts(search="dragon")
        assert result["total"] == 1


class TestPromptUpdate:
    """Test updating prompts"""

    def test_update_prompt_name(self, prompt_lib):
        """Verify prompts can be renamed."""
        result = prompt_lib.save_prompt(prompt="test", name="Old Name")
        prompt_lib.update_prompt(result["prompt_id"], name="New Name")

        prompt = prompt_lib.get_prompt(result["prompt_id"])
        assert prompt["name"] == "New Name"

    def test_favorite_prompt(self, prompt_lib):
        """Verify prompts can be favorited."""
        result = prompt_lib.save_prompt(prompt="test", name="Test")
        prompt_lib.update_prompt(result["prompt_id"], favorite=True)

        prompt = prompt_lib.get_prompt(result["prompt_id"])
        assert prompt["favorite"] is True


class TestUsePrompt:
    """Test using prompts"""

    def test_use_prompt_increments_count(self, prompt_lib):
        """Verify use_prompt increments the use counter."""
        result = prompt_lib.save_prompt(prompt="test", name="Test")
        prompt_id = result["prompt_id"]

        prompt_lib.use_prompt(prompt_id)
        prompt_lib.use_prompt(prompt_id)

        prompt = prompt_lib.get_prompt(prompt_id)
        assert prompt["use_count"] == 2

    def test_use_prompt_returns_text(self, prompt_lib):
        """Verify use_prompt returns the prompt text."""
        result = prompt_lib.save_prompt(
            prompt="the actual prompt",
            name="Test",
            negative_prompt="bad stuff"
        )

        used = prompt_lib.use_prompt(result["prompt_id"])
        assert used["prompt"] == "the actual prompt"
        assert used["negative_prompt"] == "bad stuff"


class TestTemplates:
    """Test prompt templates"""

    def test_save_template(self, prompt_lib):
        """Verify templates can be saved."""
        result = prompt_lib.save_template(
            template_id="portrait",
            name="Portrait Template",
            template="portrait of {subject} in {style} style"
        )
        assert result["success"] is True

    def test_template_extracts_variables(self, prompt_lib):
        """Verify template variables are extracted."""
        prompt_lib.save_template(
            template_id="test",
            name="Test",
            template="{a} and {b} and {c}"
        )
        template = prompt_lib.get_template("test")
        assert "a" in template["variable_names"]
        assert "b" in template["variable_names"]
        assert "c" in template["variable_names"]

    def test_fill_template(self, prompt_lib):
        """Verify templates can be filled with values."""
        prompt_lib.save_template(
            template_id="simple",
            name="Simple",
            template="a {color} {animal}"
        )
        result = prompt_lib.fill_template("simple", {"color": "red", "animal": "fox"})
        assert result["prompt"] == "a red fox"

    def test_fill_template_with_defaults(self, prompt_lib):
        """Verify template defaults are used."""
        prompt_lib.save_template(
            template_id="defaults",
            name="Defaults",
            template="{subject} in {style} style",
            variables={
                "subject": {},
                "style": {"default": "realistic"}
            }
        )
        result = prompt_lib.fill_template("defaults", {"subject": "a cat"})
        assert "realistic" in result["prompt"]


class TestHistory:
    """Test prompt history"""

    def test_add_to_history(self, prompt_lib):
        """Verify prompts are added to history."""
        prompt_lib.add_to_history(
            prompt="test prompt",
            workflow_id="generate_image"
        )
        history = prompt_lib.get_history()
        assert history["total"] == 1
        assert history["history"][0]["prompt"] == "test prompt"

    def test_history_order(self, prompt_lib):
        """Verify history is newest first."""
        prompt_lib.add_to_history(prompt="first", workflow_id="test")
        prompt_lib.add_to_history(prompt="second", workflow_id="test")

        history = prompt_lib.get_history()
        assert history["history"][0]["prompt"] == "second"
        assert history["history"][1]["prompt"] == "first"

    def test_save_from_history(self, prompt_lib):
        """Verify prompts can be saved from history."""
        prompt_lib.add_to_history(prompt="history prompt", workflow_id="test")

        result = prompt_lib.save_from_history(0, "Saved From History")
        assert result["success"] is True

        saved = prompt_lib.get_prompt(result["prompt_id"])
        assert saved["prompt"] == "history prompt"


class TestStats:
    """Test library statistics"""

    def test_get_stats(self, prompt_lib):
        """Verify stats are computed correctly."""
        prompt_lib.save_prompt(prompt="p1", name="n1", category="cat1")
        prompt_lib.save_prompt(prompt="p2", name="n2", category="cat2")
        prompt_lib.save_template(template_id="t1", name="T1", template="{x}")

        stats = prompt_lib.get_stats()
        assert stats["total_prompts"] == 2
        assert stats["total_templates"] == 1
        assert len(stats["categories"]) == 2

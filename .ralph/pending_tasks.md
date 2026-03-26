# Pending Tasks (auto-generated)

1 pending task(s), sorted by priority:

### Task 4 [MEDIUM] (testing)
**Establish integration test suite for Blender-ComfyUI pipeline with mocked and live test modes**

1. Create tests/integration/ directory with conftest.py
2. Write mocked tests for the Blender-ComfyUI pipeline (no running services needed)
3. Write live integration tests (marked @pytest.mark.integration) that require ComfyUI
4. Add test fixtures for sample Blender scenes and expected outputs
5. Run the full test suite and baseline the count
6. Update CLAUDE.md with test commands

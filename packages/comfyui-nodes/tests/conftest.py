"""Pytest configuration for comfyui-nodes tests.

Uses importlib import mode to avoid loading the package __init__.py,
which contains ComfyUI-specific relative imports that fail outside
the ComfyUI runtime.
"""
import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: requires ComfyUI runtime")

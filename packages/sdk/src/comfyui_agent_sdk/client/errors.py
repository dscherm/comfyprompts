"""Structured error parsing for ComfyUI responses."""

import logging

logger = logging.getLogger(__name__)


class ComfyUIError(Exception):
    """Base exception for ComfyUI errors."""

    def __init__(self, message: str, error_type: str = "", details: str = "", raw: dict | None = None):
        super().__init__(message)
        self.error_type = error_type
        self.details = details
        self.raw = raw or {}


class VRAMError(ComfyUIError):
    """GPU ran out of memory."""
    pass


class MissingModelError(ComfyUIError):
    """Required model is not installed."""
    pass


class MissingNodeError(ComfyUIError):
    """Required custom node is not installed."""
    pass


class ConnectionError(ComfyUIError):
    """Cannot reach ComfyUI server."""
    pass


class TimeoutError(ComfyUIError):
    """ComfyUI took too long to respond."""
    pass


class WorkflowValidationError(ComfyUIError):
    """Workflow failed validation."""
    pass


def parse_comfyui_error(error_info: dict) -> str:
    """Parse ComfyUI error responses into human-readable messages."""
    if not isinstance(error_info, dict):
        return str(error_info)

    error_type = error_info.get("type", "")
    message = error_info.get("message", "")
    details = error_info.get("details", "")
    extra_info = error_info.get("extra_info", {})

    error_str = f"{message} {details}".lower()

    if "out of memory" in error_str or "cuda out of memory" in error_str or "oom" in error_str:
        return (
            "VRAM Error: GPU ran out of memory. Try:\n"
            "  - Reducing image/video resolution\n"
            "  - Reducing batch size or frame count\n"
            "  - Starting ComfyUI with --lowvram or --medvram flag\n"
            "  - Closing other GPU applications"
        )

    if "value_not_in_list" in error_type or "value_not_in_list" in error_str:
        node_errors = extra_info.get("node_errors", {}) if extra_info else {}
        missing_items = []
        for node_id, errors in node_errors.items():
            for err in errors.get("errors", []):
                if err.get("type") == "value_not_in_list":
                    missing_items.append(f"Node {node_id}: value not found")
        if missing_items:
            return (
                f"Missing model or value: {'; '.join(missing_items)}. "
                "Check that required models are installed."
            )
        return "Missing model or configuration value. Verify ComfyUI has required models installed."

    if "missing" in error_str and ("node" in error_str or "class_type" in error_str):
        return f"Missing ComfyUI node: {message}. Install the required custom node package."

    if "connection" in error_str or "refused" in error_str:
        return "Connection error: Cannot reach ComfyUI. Ensure ComfyUI is running."

    if "timeout" in error_str:
        return (
            "Timeout: ComfyUI took too long to respond. "
            "The model may be loading or generation is slow."
        )

    return message if message else str(error_info)


def parse_execution_error(msg_data: dict) -> str:
    """Parse an execution_error message from ComfyUI history status."""
    exception_msg = msg_data.get("exception_message", "")
    node_type = msg_data.get("node_type", "")

    lower = exception_msg.lower()
    if "out of memory" in lower or "cuda" in lower:
        return (
            "VRAM Error: GPU ran out of memory. Try:\n"
            "  - Reducing image/video resolution\n"
            "  - Starting ComfyUI with --lowvram flag"
        )
    if "FP8" in exception_msg or "GGUF" in exception_msg:
        return f"Model compatibility error: {exception_msg}"

    return f"Workflow failed at {node_type}: {exception_msg}"


def raise_for_node_errors(error_data: dict) -> None:
    """Raise WorkflowValidationError from ComfyUI node errors."""
    node_errors = error_data.get("node_errors", {})
    msgs = []
    for node_id, node_err in node_errors.items():
        for err in node_err.get("errors", []):
            msgs.append(f"Node {node_id}: {err.get('message', str(err))}")
    if msgs:
        raise WorkflowValidationError(
            "Workflow validation failed:\n" + "\n".join(msgs)
        )

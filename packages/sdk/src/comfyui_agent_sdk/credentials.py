"""Keyring-based credential storage for API tokens."""

import logging
from typing import Optional

import keyring

logger = logging.getLogger(__name__)

# Service name prefix for all SDK credentials
_SERVICE_PREFIX = "comfyui-agent-sdk"
_CREDENTIAL_USERNAME = "api_token"

# Known service aliases
_SERVICE_MAP = {
    "huggingface": f"{_SERVICE_PREFIX}-huggingface",
    "hf": f"{_SERVICE_PREFIX}-huggingface",
    "civitai": f"{_SERVICE_PREFIX}-civitai",
    "elevenlabs": f"{_SERVICE_PREFIX}-elevenlabs",
    "el": f"{_SERVICE_PREFIX}-elevenlabs",
}


def _resolve_service(service: str) -> str:
    return _SERVICE_MAP.get(service.lower(), f"{_SERVICE_PREFIX}-{service.lower()}")


def get_credential(service: str) -> Optional[str]:
    """Retrieve an API credential from the system keyring.

    Args:
        service: Service name (e.g. 'huggingface', 'civitai', 'elevenlabs')
    """
    service_name = _resolve_service(service)
    try:
        return keyring.get_password(service_name, _CREDENTIAL_USERNAME)
    except Exception as e:
        logger.warning("Failed to retrieve credential for %s: %s", service, e)
        return None


def set_credential(service: str, token: str) -> bool:
    """Store an API credential in the system keyring."""
    service_name = _resolve_service(service)
    try:
        keyring.set_password(service_name, _CREDENTIAL_USERNAME, token)
        return True
    except Exception as e:
        logger.error("Failed to store credential for %s: %s", service, e)
        return False


def delete_credential(service: str) -> bool:
    """Remove an API credential from the system keyring."""
    service_name = _resolve_service(service)
    try:
        keyring.delete_password(service_name, _CREDENTIAL_USERNAME)
        return True
    except keyring.errors.PasswordDeleteError:
        return True
    except Exception as e:
        logger.error("Failed to delete credential for %s: %s", service, e)
        return False


def has_credential(service: str) -> bool:
    """Check whether a credential exists for the given service."""
    return get_credential(service) is not None


def get_all_credentials_status() -> dict[str, bool]:
    """Return existence status for all known credential services."""
    return {
        "huggingface": has_credential("huggingface"),
        "civitai": has_credential("civitai"),
        "elevenlabs": has_credential("elevenlabs"),
    }


# Convenience accessors
def get_huggingface_token() -> Optional[str]:
    return get_credential("huggingface")


def get_civitai_api_key() -> Optional[str]:
    return get_credential("civitai")

from __future__ import annotations

from copy import deepcopy
from typing import Any

from wiki_ai_rag_api.core.config import get_settings

SENSITIVE_CONFIG_KEYS = {
    "api_key",
    "access_key",
    "credentials",
    "dsn",
    "password",
    "secret",
    "secret_key",
    "token",
}
ENCRYPTED_MARKER = "__encrypted__"


def encrypt_config(config: dict[str, Any]) -> dict[str, Any]:
    key = get_settings().credentials_encryption_key
    if not key:
        return deepcopy(config)
    return _walk_config(config, key=key, encrypt=True)


def decrypt_config(config: dict[str, Any]) -> dict[str, Any]:
    key = get_settings().credentials_encryption_key
    if not key:
        return deepcopy(config)
    return _walk_config(config, key=key, encrypt=False)


def _walk_config(value: Any, *, key: str, encrypt: bool, current_key: str | None = None) -> Any:
    if isinstance(value, dict):
        if not encrypt and value.get(ENCRYPTED_MARKER) is True:
            return _decrypt_secret(value["value"], key)
        return {
            child_key: _walk_config(
                child_value,
                key=key,
                encrypt=encrypt,
                current_key=child_key,
            )
            for child_key, child_value in value.items()
        }

    if isinstance(value, list):
        return [
            _walk_config(item, key=key, encrypt=encrypt, current_key=current_key)
            for item in value
        ]

    if encrypt and current_key and current_key.lower() in SENSITIVE_CONFIG_KEYS and isinstance(value, str):
        return {ENCRYPTED_MARKER: True, "value": _encrypt_secret(value, key)}

    return deepcopy(value)


def _encrypt_secret(value: str, key: str) -> str:
    from cryptography.fernet import Fernet

    return Fernet(key.encode("utf-8")).encrypt(value.encode("utf-8")).decode("utf-8")


def _decrypt_secret(value: str, key: str) -> str:
    from cryptography.fernet import Fernet

    return Fernet(key.encode("utf-8")).decrypt(value.encode("utf-8")).decode("utf-8")


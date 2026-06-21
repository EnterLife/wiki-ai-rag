import pytest

from wiki_ai_rag_api.core.config import get_settings
from wiki_ai_rag_api.services.secrets import ENCRYPTED_MARKER, decrypt_config, encrypt_config


def test_config_is_copied_without_encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CREDENTIALS_ENCRYPTION_KEY", raising=False)
    get_settings.cache_clear()
    config = {"username": "rag", "password": "secret"}

    encrypted = encrypt_config(config)

    assert encrypted == config
    assert encrypted is not config

    get_settings.cache_clear()


def test_sensitive_config_values_are_encrypted_and_decrypted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fernet_module = pytest.importorskip("cryptography.fernet")
    key = fernet_module.Fernet.generate_key().decode("utf-8")
    monkeypatch.setenv("CREDENTIALS_ENCRYPTION_KEY", key)
    get_settings.cache_clear()

    encrypted = encrypt_config(
        {
            "host": "localhost",
            "password": "secret",
            "tables": [{"name": "pages", "text_fields": ["body"]}],
        }
    )

    assert encrypted["password"][ENCRYPTED_MARKER] is True
    assert encrypted["password"]["value"] != "secret"
    assert decrypt_config(encrypted)["password"] == "secret"

    get_settings.cache_clear()


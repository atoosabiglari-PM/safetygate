from typing import Any


REDACTED = "[REDACTED]"

SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "access_token",
    "refresh_token",
    "token",
    "password",
    "secret",
    "client_secret",
    "private_key",
}


def _normalize_key(key: str) -> str:
    return key.strip().lower().replace("-", "_")


def redact_sensitive_data(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}

        for key, item in value.items():
            key_text = str(key)

            if _normalize_key(key_text) in SENSITIVE_KEYS:
                redacted[key_text] = REDACTED
            else:
                redacted[key_text] = redact_sensitive_data(item)

        return redacted

    if isinstance(value, list):
        return [
            redact_sensitive_data(item)
            for item in value
        ]

    if isinstance(value, tuple):
        return tuple(
            redact_sensitive_data(item)
            for item in value
        )

    return value

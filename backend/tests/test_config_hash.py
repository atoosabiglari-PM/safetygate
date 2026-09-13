from app.core.certification.config_hash import calculate_configuration_hash


def test_configuration_hash_is_deterministic() -> None:
    config_a = {
        "model": "gemini",
        "tools": ["search", "read"],
        "autonomy": "limited",
    }

    config_b = {
        "autonomy": "limited",
        "tools": ["search", "read"],
        "model": "gemini",
    }

    assert calculate_configuration_hash(config_a) == calculate_configuration_hash(config_b)


def test_configuration_change_changes_hash() -> None:
    original = {
        "model": "gemini",
        "tools": ["search"],
    }

    changed = {
        "model": "gemini",
        "tools": ["search", "delete"],
    }

    assert calculate_configuration_hash(original) != calculate_configuration_hash(changed)

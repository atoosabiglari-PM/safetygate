import hashlib
import json
from typing import Any


def calculate_configuration_hash(configuration: dict[str, Any]) -> str:
    canonical = json.dumps(
        configuration,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.certification.config_hash import calculate_configuration_hash
from app.models.certification import SafetyPassport
from app.models.governance import AgentVersion

MATERIAL_CONFIGURATION_FIELDS = frozenset(
    {
        "model_provider",
        "model_name",
        "system_prompt_hash",
        "tools",
        "permissions",
        "memory_config",
        "jurisdictions",
        "autonomy_level",
    }
)


@dataclass(frozen=True)
class MaterialChangeResult:
    changed: bool
    previous_configuration_hash: str
    current_configuration_hash: str
    invalidated_passport_count: int


def build_material_configuration(
    agent_version: AgentVersion,
) -> dict[str, Any]:
    return {
        "model_provider": agent_version.model_provider,
        "model_name": agent_version.model_name,
        "system_prompt_hash": agent_version.system_prompt_hash,
        "tools": agent_version.tools,
        "permissions": agent_version.permissions,
        "memory_config": agent_version.memory_config,
        "jurisdictions": agent_version.jurisdictions,
        "autonomy_level": agent_version.autonomy_level,
    }


def apply_material_configuration_update(
    session: Session,
    *,
    agent_version: AgentVersion,
    updates: Mapping[str, Any],
) -> MaterialChangeResult:
    unsupported_fields = set(updates) - MATERIAL_CONFIGURATION_FIELDS

    if unsupported_fields:
        raise ValueError(
            "Unsupported material configuration field(s): "
            + ", ".join(sorted(unsupported_fields))
        )

    previous_hash = agent_version.configuration_hash

    for field_name, value in updates.items():
        setattr(agent_version, field_name, value)

    current_hash = calculate_configuration_hash(
        build_material_configuration(agent_version)
    )

    if current_hash == previous_hash:
        return MaterialChangeResult(
            changed=False,
            previous_configuration_hash=previous_hash,
            current_configuration_hash=current_hash,
            invalidated_passport_count=0,
        )

    agent_version.configuration_hash = current_hash
    agent_version.certification_status = "RECERTIFICATION_REQUIRED"

    active_passports = session.scalars(
        select(SafetyPassport).where(
            SafetyPassport.agent_version_id == agent_version.id,
            SafetyPassport.status == "ACTIVE",
        )
    ).all()

    for passport in active_passports:
        passport.status = "RECERTIFICATION_REQUIRED"

    session.commit()
    session.refresh(agent_version)

    return MaterialChangeResult(
        changed=True,
        previous_configuration_hash=previous_hash,
        current_configuration_hash=current_hash,
        invalidated_passport_count=len(active_passports),
    )

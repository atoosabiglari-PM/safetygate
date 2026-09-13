from app.core.certification.config_hash import calculate_configuration_hash
from app.core.recertification.material_change import (
    apply_material_configuration_update,
)
from app.db.base import Base
from app.db.session import create_database_engine, create_session_factory
from app.models.certification import SafetyPassport
from app.models.governance import Agent, AgentVersion, Organization


def test_material_change_requires_recertification(tmp_path) -> None:
    database_path = tmp_path / "material-change.db"
    engine = create_database_engine(
        f"sqlite+pysqlite:///{database_path}"
    )
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    original_configuration = {
        "model_provider": "google",
        "model_name": "gemini",
        "system_prompt_hash": "prompt-hash-001",
        "tools": ["read_documents"],
        "permissions": ["documents:read"],
        "memory_config": {"enabled": True},
        "jurisdictions": ["US"],
        "autonomy_level": "MEDIUM",
    }

    original_hash = calculate_configuration_hash(
        original_configuration
    )

    with session_factory() as session:
        organization = Organization(
            name="SafetyGate Test Organization",
        )
        session.add(organization)
        session.flush()

        agent = Agent(
            organization_id=organization.id,
            name="Recertification Test Agent",
            owner_identity="owner@example.com",
            purpose="Test material configuration changes.",
            status="ACTIVE",
        )
        session.add(agent)
        session.flush()

        agent_version = AgentVersion(
            organization_id=organization.id,
            agent_id=agent.id,
            version_number=1,
            model_provider=original_configuration["model_provider"],
            model_name=original_configuration["model_name"],
            system_prompt_hash=original_configuration[
                "system_prompt_hash"
            ],
            tools=original_configuration["tools"],
            permissions=original_configuration["permissions"],
            memory_config=original_configuration["memory_config"],
            jurisdictions=original_configuration["jurisdictions"],
            autonomy_level=original_configuration["autonomy_level"],
            configuration_hash=original_hash,
            certification_status="CERTIFIED",
        )
        session.add(agent_version)
        session.flush()

        passport = SafetyPassport(
            organization_id=organization.id,
            agent_version_id=agent_version.id,
            configuration_hash=original_hash,
            policy_version="policy-v1",
            risk_class="MEDIUM",
            allowed_tools=["read_documents"],
            conditional_tools=[],
            prohibited_tools=[],
            status="ACTIVE",
            certification_reason="Initial certification passed.",
        )
        session.add(passport)
        session.commit()

        result = apply_material_configuration_update(
            session,
            agent_version=agent_version,
            updates={
                "tools": [
                    "read_documents",
                    "deploy_service",
                ]
            },
        )

        session.refresh(passport)

        assert result.changed is True
        assert result.previous_configuration_hash == original_hash
        assert result.current_configuration_hash != original_hash
        assert result.invalidated_passport_count == 1

        assert (
            agent_version.certification_status
            == "RECERTIFICATION_REQUIRED"
        )
        assert passport.status == "RECERTIFICATION_REQUIRED"

        # Preserve the evidence of what the old passport certified.
        assert passport.configuration_hash == original_hash

        # The live agent configuration now has a new identity.
        assert agent_version.configuration_hash != original_hash

    engine.dispose()


def test_identical_material_configuration_keeps_certification(tmp_path) -> None:
    database_path = tmp_path / "no-material-change.db"
    engine = create_database_engine(
        f"sqlite+pysqlite:///{database_path}"
    )
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    configuration = {
        "model_provider": "google",
        "model_name": "gemini",
        "system_prompt_hash": "prompt-hash-001",
        "tools": ["read_documents"],
        "permissions": ["documents:read"],
        "memory_config": {"enabled": True},
        "jurisdictions": ["US"],
        "autonomy_level": "MEDIUM",
    }

    configuration_hash = calculate_configuration_hash(configuration)

    with session_factory() as session:
        organization = Organization(
            name="No Change Test Organization",
        )
        session.add(organization)
        session.flush()

        agent = Agent(
            organization_id=organization.id,
            name="No Change Test Agent",
            owner_identity="owner@example.com",
            purpose="Prove unchanged configuration preserves certification.",
            status="ACTIVE",
        )
        session.add(agent)
        session.flush()

        agent_version = AgentVersion(
            organization_id=organization.id,
            agent_id=agent.id,
            version_number=1,
            model_provider=configuration["model_provider"],
            model_name=configuration["model_name"],
            system_prompt_hash=configuration["system_prompt_hash"],
            tools=configuration["tools"],
            permissions=configuration["permissions"],
            memory_config=configuration["memory_config"],
            jurisdictions=configuration["jurisdictions"],
            autonomy_level=configuration["autonomy_level"],
            configuration_hash=configuration_hash,
            certification_status="CERTIFIED",
        )
        session.add(agent_version)
        session.flush()

        passport = SafetyPassport(
            organization_id=organization.id,
            agent_version_id=agent_version.id,
            configuration_hash=configuration_hash,
            policy_version="policy-v1",
            risk_class="MEDIUM",
            allowed_tools=["read_documents"],
            conditional_tools=[],
            prohibited_tools=[],
            status="ACTIVE",
            certification_reason="Initial certification passed.",
        )
        session.add(passport)
        session.commit()

        result = apply_material_configuration_update(
            session,
            agent_version=agent_version,
            updates={
                "tools": ["read_documents"],
            },
        )

        session.refresh(passport)

        assert result.changed is False
        assert result.previous_configuration_hash == configuration_hash
        assert result.current_configuration_hash == configuration_hash
        assert result.invalidated_passport_count == 0

        assert agent_version.certification_status == "CERTIFIED"
        assert passport.status == "ACTIVE"

    engine.dispose()

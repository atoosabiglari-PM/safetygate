from app.core.certification.passport_payload import build_passport_payload


def passport_fields() -> dict:
    return {
        "passport_id": "passport-123",
        "organization_id": "org-123",
        "agent_version_id": "agent-version-123",
        "configuration_hash": "abc123",
        "policy_version": "policy-v1",
        "risk_class": "HIGH",
        "allowed_tools": ["read_documents"],
        "conditional_tools": ["send_message"],
        "prohibited_tools": ["delete_records"],
        "human_approvers": ["security@example.com"],
        "issued_at": "2026-09-13T12:00:00+00:00",
    }


def test_passport_payload_is_deterministic() -> None:
    fields = passport_fields()

    reversed_fields = dict(reversed(list(fields.items())))

    assert build_passport_payload(**fields) == build_passport_payload(
        **reversed_fields
    )


def test_material_passport_change_changes_payload() -> None:
    original = passport_fields()
    changed = passport_fields()
    changed["risk_class"] = "LOW"

    assert build_passport_payload(**original) != build_passport_payload(
        **changed
    )


def test_missing_signed_field_fails_closed() -> None:
    fields = passport_fields()
    del fields["configuration_hash"]

    try:
        build_passport_payload(**fields)
    except ValueError as exc:
        assert "configuration_hash" in str(exc)
    else:
        raise AssertionError("Missing signed field did not fail closed.")



def test_tool_order_does_not_change_signed_payload() -> None:
    original = passport_fields()
    original["allowed_tools"] = ["read_documents", "send_message"]

    reordered = passport_fields()
    reordered["allowed_tools"] = ["send_message", "read_documents"]

    assert build_passport_payload(**original) == build_passport_payload(
        **reordered
    )

def test_human_approver_change_changes_signed_payload() -> None:
    original = passport_fields()

    changed = passport_fields()
    changed["human_approvers"] = ["attacker@example.com"]

    assert build_passport_payload(**original) != build_passport_payload(
        **changed
    )


def test_human_approver_order_does_not_change_signed_payload() -> None:
    original = passport_fields()
    original["human_approvers"] = [
        "security@example.com",
        "owner@example.com",
    ]

    reordered = passport_fields()
    reordered["human_approvers"] = [
        "owner@example.com",
        "security@example.com",
    ]

    assert build_passport_payload(**original) == build_passport_payload(
        **reordered
    )



def test_runtime_passport_context_reconstructs_exact_signed_payload() -> None:
    from app.core.certification.passport_payload import (
        build_runtime_passport_payload,
    )
    from app.schemas.runtime import PassportContext

    fields = passport_fields()

    passport = PassportContext(
        passport_id=fields["passport_id"],
        organization_id=fields["organization_id"],
        agent_version_id=fields["agent_version_id"],
        status="ACTIVE",
        certified_configuration_hash=fields["configuration_hash"],
        current_configuration_hash=fields["configuration_hash"],
        policy_version=fields["policy_version"],
        risk_class=fields["risk_class"],
        allowed_tools=fields["allowed_tools"],
        conditional_tools=fields["conditional_tools"],
        prohibited_tools=fields["prohibited_tools"],
        human_approvers=fields["human_approvers"],
        issued_at=fields["issued_at"],
        signature_key_id="kms-version-1",
        signature="signature",
    )

    expected = build_passport_payload(**fields)
    actual = build_runtime_passport_payload(passport)

    assert actual == expected


def test_runtime_payload_uses_certified_not_current_configuration_hash() -> None:
    from app.core.certification.passport_payload import (
        build_runtime_passport_payload,
    )
    from app.schemas.runtime import PassportContext

    fields = passport_fields()

    passport = PassportContext(
        passport_id=fields["passport_id"],
        organization_id=fields["organization_id"],
        agent_version_id=fields["agent_version_id"],
        status="ACTIVE",
        certified_configuration_hash=fields["configuration_hash"],
        current_configuration_hash="materially-changed-hash",
        policy_version=fields["policy_version"],
        risk_class=fields["risk_class"],
        allowed_tools=fields["allowed_tools"],
        conditional_tools=fields["conditional_tools"],
        prohibited_tools=fields["prohibited_tools"],
        human_approvers=fields["human_approvers"],
        issued_at=fields["issued_at"],
        signature_key_id="kms-version-1",
        signature="signature",
    )

    assert build_runtime_passport_payload(
        passport
    ) == build_passport_payload(**fields)


def test_datetime_and_equivalent_iso_string_have_same_payload() -> None:
    from datetime import UTC, datetime

    datetime_fields = passport_fields()
    datetime_fields["issued_at"] = datetime(
        2026,
        9,
        13,
        12,
        0,
        0,
        tzinfo=UTC,
    )

    string_fields = passport_fields()
    string_fields["issued_at"] = "2026-09-13T12:00:00+00:00"

    assert build_passport_payload(
        **datetime_fields
    ) == build_passport_payload(**string_fields)

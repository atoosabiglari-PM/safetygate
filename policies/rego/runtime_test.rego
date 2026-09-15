package safetygate.runtime_test

has_rule(decisions, rule_id) if {
	some item in decisions
	item.rule_id == rule_id
}

low_risk_input := {
	"proposal": {
		"action_id": "action-001",
		"tool_name": "read_documents",
		"risk_level": "LOW",
		"is_irreversible": false,
	},
	"passport": {
		"prohibited_tools": ["delete_records"],
		"human_approvers": ["reviewer@example.com"],
	},
	"approval": null,
}

medium_risk_input := {
	"proposal": {
		"action_id": "action-002",
		"tool_name": "read_documents",
		"risk_level": "MEDIUM",
		"is_irreversible": false,
	},
	"passport": {
		"prohibited_tools": ["delete_records"],
		"human_approvers": ["reviewer@example.com"],
	},
	"approval": null,
}

high_risk_without_approval_input := {
	"proposal": {
		"action_id": "action-003",
		"tool_name": "send_message",
		"risk_level": "HIGH",
		"is_irreversible": true,
	},
	"passport": {
		"prohibited_tools": ["delete_records"],
		"human_approvers": ["reviewer@example.com"],
	},
	"approval": null,
}

high_risk_with_valid_approval_input := {
	"proposal": {
		"action_id": "action-004",
		"tool_name": "send_message",
		"risk_level": "HIGH",
		"is_irreversible": true,
	},
	"passport": {
		"prohibited_tools": ["delete_records"],
		"human_approvers": ["reviewer@example.com"],
	},
	"approval": {
		"approval_id": "approval-001",
		"action_id": "action-004",
		"approver_identity": "reviewer@example.com",
		"approved": true,
	},
}

outbound_message_input := {
	"proposal": {
		"action_id": "action-006",
		"tool_name": "send_message",
		"risk_level": "LOW",
		"is_irreversible": false,
	},
	"passport": {
		"prohibited_tools": ["delete_records"],
		"human_approvers": [],
	},
	"approval": null,
}

prohibited_tool_input := {
	"proposal": {
		"action_id": "action-005",
		"tool_name": "delete_records",
		"risk_level": "LOW",
		"is_irreversible": false,
	},
	"passport": {
		"prohibited_tools": ["delete_records"],
		"human_approvers": [],
	},
	"approval": null,
}

test_low_risk_has_only_default_allow if {
	decisions := data.safetygate.runtime.rule_decisions
		with input as low_risk_input

	count(decisions) == 1
	has_rule(
		decisions,
		"safetygate.runtime.default_allow",
	)
}

test_medium_risk_adds_conditions if {
	decisions := data.safetygate.runtime.rule_decisions
		with input as medium_risk_input

	has_rule(
		decisions,
		"safetygate.runtime.medium_risk_controls",
	)

	some item in decisions
	item.rule_id == "safetygate.runtime.medium_risk_controls"
	item.decision == "ALLOW_WITH_CONDITIONS"
	item.conditions == [
		"Record full audit evidence.",
		"Verify execution result.",
	]
}

test_high_risk_irreversible_requires_review_without_approval if {
	decisions := data.safetygate.runtime.rule_decisions
		with input as high_risk_without_approval_input

	has_rule(
		decisions,
		"safetygate.runtime.high_risk_irreversible_review",
	)

	some item in decisions
	item.rule_id == "safetygate.runtime.high_risk_irreversible_review"
	item.decision == "HUMAN_REVIEW_REQUIRED"
}

test_valid_approval_removes_high_risk_review_rule if {
	decisions := data.safetygate.runtime.rule_decisions
		with input as high_risk_with_valid_approval_input

	has_rule(
		decisions,
		"safetygate.runtime.default_allow",
	)

	not has_rule(
		decisions,
		"safetygate.runtime.high_risk_irreversible_review",
	)
}

test_prohibited_tool_produces_deny if {
	decisions := data.safetygate.runtime.rule_decisions
		with input as prohibited_tool_input

	has_rule(
		decisions,
		"safetygate.runtime.passport_prohibited_tool",
	)

	some item in decisions
	item.rule_id == "safetygate.runtime.passport_prohibited_tool"
	item.decision == "DENY"
	item.authority == "ORGANIZATION_POLICY"
	item.source_version == "v1"
}

test_outbound_message_requires_policy_controls if {
	decisions := data.safetygate.runtime.rule_decisions
		with input as outbound_message_input

	has_rule(
		decisions,
		"safetygate.runtime.outbound_message_controls",
	)

	some item in decisions
	item.rule_id == "safetygate.runtime.outbound_message_controls"
	item.decision == "ALLOW_WITH_CONDITIONS"
	item.conditions == [
		"Record full audit evidence.",
		"Verify execution result.",
	]
}

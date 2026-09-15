package safetygate.runtime

# OPA is an additional policy decision layer.
# An ALLOW result means OPA adds no additional restriction.
# Python SafetyGate enforcement remains authoritative for hard safety gates.

valid_approval if {
	input.approval != null
	input.approval.action_id == input.proposal.action_id
	input.approval.approved == true
	input.approval.approver_identity in input.passport.human_approvers
}

rule_decisions contains {
	"rule_id": "safetygate.runtime.default_allow",
	"authority": "ORGANIZATION_POLICY",
	"source_name": "SafetyGate OPA runtime policy",
	"source_version": "v1",
	"source_reference": "policies/rego/runtime.rego",
	"decision": "ALLOW",
	"reason": "OPA policy adds no additional restriction.",
	"conditions": [],
}

rule_decisions contains {
	"rule_id": "safetygate.runtime.passport_prohibited_tool",
	"authority": "ORGANIZATION_POLICY",
	"source_name": "SafetyGate OPA runtime policy",
	"source_version": "v1",
	"source_reference": "policies/rego/runtime.rego",
	"decision": "DENY",
	"reason": "OPA policy prohibits tools listed in the Safety Passport.",
	"conditions": [],
} if {
	input.proposal.tool_name in input.passport.prohibited_tools
}

rule_decisions contains {
	"rule_id": "safetygate.runtime.medium_risk_controls",
	"authority": "ORGANIZATION_POLICY",
	"source_name": "SafetyGate OPA runtime policy",
	"source_version": "v1",
	"source_reference": "policies/rego/runtime.rego",
	"decision": "ALLOW_WITH_CONDITIONS",
	"reason": "OPA policy requires additional controls for medium-risk actions.",
	"conditions": [
		"Record full audit evidence.",
		"Verify execution result.",
	],
} if {
	upper(input.proposal.risk_level) == "MEDIUM"
}

rule_decisions contains {
	"rule_id": "safetygate.runtime.high_risk_irreversible_review",
	"authority": "ORGANIZATION_POLICY",
	"source_name": "SafetyGate OPA runtime policy",
	"source_version": "v1",
	"source_reference": "policies/rego/runtime.rego",
	"decision": "HUMAN_REVIEW_REQUIRED",
	"reason": "OPA policy requires human review for high-risk irreversible actions without valid approval.",
	"conditions": [],
} if {
	upper(input.proposal.risk_level) == "HIGH"
	input.proposal.is_irreversible == true
	not valid_approval
}

rule_decisions contains {
	"rule_id": "safetygate.runtime.outbound_message_controls",
	"authority": "ORGANIZATION_POLICY",
	"source_name": "SafetyGate OPA runtime policy",
	"source_version": "v1",
	"source_reference": "policies/rego/runtime.rego",
	"decision": "ALLOW_WITH_CONDITIONS",
	"reason": "Organization policy requires additional controls for outbound messaging.",
	"conditions": [
		"Record full audit evidence.",
		"Verify execution result.",
	],
} if {
	input.proposal.tool_name == "send_message"
}

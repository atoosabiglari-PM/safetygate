const startButton = document.getElementById("start-onboarding");
const orgMetric = document.getElementById("metric-org");

function showOrganizationForm() {
  const existing = document.getElementById("org-form");
  if (existing) {
    existing.scrollIntoView({ behavior: "smooth", block: "center" });
    return;
  }

  const panel = startButton.closest(".panel");

  const form = document.createElement("form");
  form.id = "org-form";
  form.innerHTML = `
    <div class="form-group">
      <label for="organization-name">Organization name</label>
      <input
        id="organization-name"
        name="organization-name"
        type="text"
        placeholder="Acme AI"
        required
        minlength="1"
        maxlength="255"
      >
    </div>

    <div class="form-actions">
      <button type="submit" class="primary-button">
        Create organization
      </button>
      <span id="org-status" class="form-status"></span>
    </div>
  `;

  panel.appendChild(form);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const input = document.getElementById("organization-name");
    const status = document.getElementById("org-status");
    const name = input.value.trim();

    if (!name) {
      status.textContent = "Organization name is required.";
      status.className = "form-status error";
      return;
    }

    status.textContent = "Creating...";
    status.className = "form-status";

    try {
      const response = await fetch("/api/v1/organizations", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ name }),
      });

      const body = await response.json();

      if (!response.ok) {
        throw new Error(body.detail || "Organization creation failed.");
      }

      localStorage.setItem("safetygate_org_id", body.id);
      localStorage.setItem("safetygate_org_name", body.name);

      orgMetric.textContent = body.name;
      status.textContent = "Organization created.";
      status.className = "form-status success";

      const firstStepState = document.querySelector(
        ".step-card:nth-child(1) .state"
      );

      if (firstStepState) {
        firstStepState.textContent = "Complete";
        firstStepState.className = "state complete";
      }

      startButton.textContent = "Organization created";
      startButton.disabled = true;
    } catch (error) {
      status.textContent = error.message;
      status.className = "form-status error";
    }
  });
}

startButton.addEventListener("click", showOrganizationForm);

const savedOrgName = localStorage.getItem("safetygate_org_name");

if (savedOrgName) {
  orgMetric.textContent = savedOrgName;

  const firstStepState = document.querySelector(
    ".step-card:nth-child(1) .state"
  );

  if (firstStepState) {
    firstStepState.textContent = "Complete";
    firstStepState.className = "state complete";
  }

  startButton.textContent = "Organization created";
  startButton.disabled = true;
}


function markStepComplete(stepNumber) {
  const state = document.querySelector(
    `.step-card:nth-child(${stepNumber}) .state`
  );

  if (state) {
    state.textContent = "Complete";
    state.className = "state complete";
  }
}


function showAgentRegistrationForm() {
  const orgId = localStorage.getItem("safetygate_org_id");

  if (!orgId) {
    alert("Create an organization first.");
    return;
  }

  const existing = document.getElementById("agent-form");
  if (existing) {
    existing.scrollIntoView({ behavior: "smooth", block: "center" });
    return;
  }

  const workflow = document.querySelector(".workflow");

  const panel = document.createElement("article");
  panel.className = "panel workflow-form-panel";
  panel.innerHTML = `
    <div class="panel-header">
      <div>
        <p class="eyebrow">AGENT REGISTRATION</p>
        <h2>Register AI agent</h2>
      </div>
    </div>

    <form id="agent-form">
      <div class="form-grid">
        <div class="form-group">
          <label for="agent-name">Agent name</label>
          <input id="agent-name" required placeholder="Research Assistant">
        </div>

        <div class="form-group">
          <label for="owner-identity">Owner identity</label>
          <input id="owner-identity" required placeholder="owner@example.com">
        </div>

        <div class="form-group full">
          <label for="agent-purpose">Purpose</label>
          <textarea
            id="agent-purpose"
            required
            placeholder="Describe the governed purpose of this agent."
          ></textarea>
        </div>

        <div class="form-group">
          <label for="model-provider">Model provider</label>
          <input id="model-provider" required value="OpenAI">
        </div>

        <div class="form-group">
          <label for="model-name">Model name</label>
          <input id="model-name" required placeholder="gpt-model">
        </div>

        <div class="form-group full">
          <label for="prompt-hash">System prompt hash</label>
          <input
            id="prompt-hash"
            required
            minlength="64"
            maxlength="64"
            value="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
          >
        </div>

        <div class="form-group">
          <label for="agent-tools">Tools</label>
          <input id="agent-tools" value="read_documents">
          <small>Comma-separated</small>
        </div>

        <div class="form-group">
          <label for="agent-permissions">Permissions</label>
          <input id="agent-permissions" value="documents:read">
          <small>Comma-separated</small>
        </div>

        <div class="form-group">
          <label for="jurisdictions">Jurisdictions</label>
          <input id="jurisdictions" value="US">
          <small>Comma-separated</small>
        </div>

        <div class="form-group">
          <label for="autonomy-level">Autonomy level</label>
          <select id="autonomy-level">
            <option value="SUPERVISED">Supervised</option>
            <option value="MEDIUM">Medium</option>
            <option value="HIGH">High</option>
          </select>
        </div>
      </div>

      <div class="form-actions">
        <button type="submit" class="primary-button">
          Register agent
        </button>
        <span id="agent-status" class="form-status"></span>
      </div>
    </form>
  `;

  workflow.insertAdjacentElement("afterend", panel);

  const form = document.getElementById("agent-form");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const status = document.getElementById("agent-status");

    const splitValues = (value) =>
      value
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);

    const payload = {
      name: document.getElementById("agent-name").value.trim(),
      owner_identity: document.getElementById("owner-identity").value.trim(),
      purpose: document.getElementById("agent-purpose").value.trim(),
      model_provider: document.getElementById("model-provider").value.trim(),
      model_name: document.getElementById("model-name").value.trim(),
      system_prompt_hash: document.getElementById("prompt-hash").value.trim(),
      tools: splitValues(document.getElementById("agent-tools").value),
      permissions: splitValues(
        document.getElementById("agent-permissions").value
      ),
      memory_config: {},
      jurisdictions: splitValues(
        document.getElementById("jurisdictions").value
      ),
      autonomy_level: document.getElementById("autonomy-level").value,
    };

    status.textContent = "Registering...";
    status.className = "form-status";

    try {
      const response = await fetch(
        `/api/v1/organizations/${orgId}/agents`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(body.detail || "Agent registration failed.");
      }

      localStorage.setItem("safetygate_agent_id", body.agent_id);
      localStorage.setItem(
        "safetygate_agent_version_id",
        body.agent_version_id
      );
      localStorage.setItem("safetygate_agent_name", body.name);

      document.getElementById("metric-agent").textContent =
        `${body.name} · ${body.status}`;

      markStepComplete(2);

      status.textContent = "Agent registered.";
      status.className = "form-status success";
    } catch (error) {
      status.textContent = error.message;
      status.className = "form-status error";
    }
  });
}


document.querySelectorAll(".nav-item").forEach((button) => {
  if (button.textContent.trim() === "Register Agent") {
    button.addEventListener("click", showAgentRegistrationForm);
  }
});

const savedAgentName = localStorage.getItem("safetygate_agent_name");

if (savedAgentName) {
  document.getElementById("metric-agent").textContent =
    `${savedAgentName} · REGISTERED`;
  markStepComplete(2);
}


function showAdmissionForm() {
  const orgId = localStorage.getItem("safetygate_org_id");
  const agentId = localStorage.getItem("safetygate_agent_id");

  if (!orgId || !agentId) {
    alert("Register an agent first.");
    return;
  }

  const existing = document.getElementById("admission-form");
  if (existing) {
    existing.scrollIntoView({ behavior: "smooth", block: "center" });
    return;
  }

  const workflow = document.querySelector(".workflow");

  const panel = document.createElement("article");
  panel.className = "panel workflow-form-panel";
  panel.innerHTML = `
    <div class="panel-header">
      <div>
        <p class="eyebrow">ADMISSION CONTROL</p>
        <h2>Evaluate agent admission</h2>
      </div>
    </div>

    <p>
      SafetyGate evaluates the registered configuration against tool,
      permission, jurisdiction and autonomy controls before certification.
    </p>

    <form id="admission-form">
      <div class="form-grid">
        <div class="form-group">
          <label for="human-approval-actions">
            Human approval actions
          </label>
          <input
            id="human-approval-actions"
            placeholder="deploy_model, transfer_funds"
          >
          <small>Comma-separated, optional</small>
        </div>

        <div class="form-group">
          <label for="prohibited-actions">
            Prohibited actions
          </label>
          <input
            id="prohibited-actions"
            placeholder="delete_records"
          >
          <small>Comma-separated, optional</small>
        </div>
      </div>

      <div class="form-actions">
        <button type="submit" class="primary-button">
          Run admission evaluation
        </button>
        <span id="admission-status" class="form-status"></span>
      </div>

      <div id="admission-result" class="decision-card hidden"></div>
    </form>
  `;

  workflow.insertAdjacentElement("afterend", panel);

  document
    .getElementById("admission-form")
    .addEventListener("submit", async (event) => {
      event.preventDefault();

      const status = document.getElementById("admission-status");
      const result = document.getElementById("admission-result");

      const splitValues = (value) =>
        value
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean);

      const payload = {
        human_approval_actions: splitValues(
          document.getElementById("human-approval-actions").value
        ),
        prohibited_actions: splitValues(
          document.getElementById("prohibited-actions").value
        ),
      };

      status.textContent = "Evaluating...";
      status.className = "form-status";

      try {
        const response = await fetch(
          `/api/v1/organizations/${orgId}/agents/${agentId}/admission`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify(payload),
          }
        );

        const body = await response.json();

        if (!response.ok) {
          throw new Error(body.detail || "Admission evaluation failed.");
        }

        const passed = body.decision === "PASS";

        result.className =
          `decision-card ${passed ? "allow" : "deny"}`;

        result.innerHTML = `
          <div class="decision-title">
            <span>Admission decision</span>
            <strong>${body.decision}</strong>
          </div>
          <p>${body.reasons.join(" ") || "No additional reasons."}</p>
          <small>
            Agent: ${body.agent_status} · Certification:
            ${body.certification_status}
          </small>
        `;

        document.getElementById("metric-agent").textContent =
          body.agent_status;

        if (passed) {
          markStepComplete(3);
          localStorage.setItem("safetygate_admission", "PASS");
        }

        status.textContent = passed
          ? "Admission passed."
          : "Admission did not pass.";

        status.className =
          `form-status ${passed ? "success" : "error"}`;
      } catch (error) {
        status.textContent = error.message;
        status.className = "form-status error";
      }
    });
}


document.querySelectorAll(".nav-item").forEach((button) => {
  if (button.textContent.trim() === "Admission") {
    button.addEventListener("click", showAdmissionForm);
  }
});

if (localStorage.getItem("safetygate_admission") === "PASS") {
  markStepComplete(3);
}


function showPassportForm() {
  const orgId = localStorage.getItem("safetygate_org_id");
  const agentId = localStorage.getItem("safetygate_agent_id");
  const admission = localStorage.getItem("safetygate_admission");

  if (!orgId || !agentId) {
    alert("Register an agent first.");
    return;
  }

  if (admission !== "PASS") {
    alert("The agent must pass admission before passport issuance.");
    return;
  }

  const existing = document.getElementById("passport-form");
  if (existing) {
    existing.scrollIntoView({ behavior: "smooth", block: "center" });
    return;
  }

  const workflow = document.querySelector(".workflow");

  const panel = document.createElement("article");
  panel.className = "panel workflow-form-panel";
  panel.innerHTML = `
    <div class="panel-header">
      <div>
        <p class="eyebrow">CERTIFICATION</p>
        <h2>Issue Safety Passport</h2>
      </div>
      <span class="secure-badge">Cryptographically signed</span>
    </div>

    <p>
      The Safety Passport binds the certified agent configuration,
      policy version, tool boundaries and human authority.
    </p>

    <form id="passport-form">
      <div class="form-grid">

        <div class="form-group">
          <label for="policy-version">Policy version</label>
          <input id="policy-version" value="1.0" required>
        </div>

        <div class="form-group">
          <label for="risk-class">Risk class</label>
          <select id="risk-class">
            <option value="LOW">Low</option>
            <option value="MEDIUM">Medium</option>
            <option value="HIGH">High</option>
          </select>
        </div>

        <div class="form-group">
          <label for="allowed-tools">Allowed tools</label>
          <input id="allowed-tools" value="read_documents">
          <small>Comma-separated</small>
        </div>

        <div class="form-group">
          <label for="conditional-tools">Conditional tools</label>
          <input id="conditional-tools">
          <small>Comma-separated</small>
        </div>

        <div class="form-group">
          <label for="prohibited-tools">Prohibited tools</label>
          <input id="prohibited-tools">
          <small>Comma-separated</small>
        </div>

        <div class="form-group">
          <label for="human-approvers">Human approvers</label>
          <input
            id="human-approvers"
            placeholder="reviewer@example.com"
          >
          <small>Comma-separated</small>
        </div>

        <div class="form-group full">
          <label for="certification-reason">Certification reason</label>
          <textarea
            id="certification-reason"
            required
          >Agent passed SafetyGate admission and satisfies the certified governance profile.</textarea>
        </div>

      </div>

      <div class="form-actions">
        <button type="submit" class="primary-button">
          Issue signed Safety Passport
        </button>
        <span id="passport-status" class="form-status"></span>
      </div>

      <div id="passport-result" class="passport-card hidden"></div>
    </form>
  `;

  workflow.insertAdjacentElement("afterend", panel);

  document
    .getElementById("passport-form")
    .addEventListener("submit", async (event) => {
      event.preventDefault();

      const status = document.getElementById("passport-status");
      const result = document.getElementById("passport-result");

      const splitValues = (value) =>
        value
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean);

      const payload = {
        policy_version:
          document.getElementById("policy-version").value.trim(),
        risk_class:
          document.getElementById("risk-class").value,
        allowed_tools:
          splitValues(document.getElementById("allowed-tools").value),
        conditional_tools:
          splitValues(document.getElementById("conditional-tools").value),
        prohibited_tools:
          splitValues(document.getElementById("prohibited-tools").value),
        human_approvers:
          splitValues(document.getElementById("human-approvers").value),
        certification_reason:
          document.getElementById("certification-reason").value.trim(),
      };

      status.textContent = "Signing Safety Passport...";
      status.className = "form-status";

      try {
        const response = await fetch(
          `/api/v1/organizations/${orgId}/agents/${agentId}/passport`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify(payload),
          }
        );

        const body = await response.json();

        if (!response.ok) {
          throw new Error(body.detail || "Safety Passport issuance failed.");
        }

        localStorage.setItem(
          "safetygate_passport_id",
          body.passport_id
        );

        localStorage.setItem(
          "safetygate_passport_status",
          body.status
        );

        document.getElementById("metric-passport").textContent =
          body.status;

        markStepComplete(4);

        result.className = "passport-card";

        result.innerHTML = `
          <div class="passport-header">
            <div>
              <p class="eyebrow">SAFETY PASSPORT</p>
              <h3>Certified Agent Authorization</h3>
            </div>
            <span class="passport-status">${body.status}</span>
          </div>

          <div class="passport-details">
            <div>
              <span>Passport ID</span>
              <strong>${body.passport_id}</strong>
            </div>

            <div>
              <span>Policy</span>
              <strong>${body.policy_version}</strong>
            </div>

            <div>
              <span>Risk</span>
              <strong>${body.risk_class}</strong>
            </div>

            <div>
              <span>Configuration</span>
              <strong>${body.configuration_hash.slice(0, 16)}...</strong>
            </div>

            <div>
              <span>Allowed tools</span>
              <strong>${body.allowed_tools.join(", ") || "None"}</strong>
            </div>

            <div>
              <span>Signing key</span>
              <strong>${body.signature_key_id}</strong>
            </div>
          </div>
        `;

        status.textContent = "Safety Passport issued.";
        status.className = "form-status success";

      } catch (error) {
        status.textContent = error.message;
        status.className = "form-status error";
      }
    });
}


document.querySelectorAll(".nav-item").forEach((button) => {
  if (button.textContent.trim() === "Safety Passport") {
    button.addEventListener("click", showPassportForm);
  }
});


if (localStorage.getItem("safetygate_passport_status") === "ACTIVE") {
  document.getElementById("metric-passport").textContent = "ACTIVE";
  markStepComplete(4);
}


function showRuntimeForm() {
  const orgId = localStorage.getItem("safetygate_org_id");
  const agentId = localStorage.getItem("safetygate_agent_id");
  const passportStatus = localStorage.getItem("safetygate_passport_status");

  if (!orgId || !agentId) {
    alert("Register an agent first.");
    return;
  }

  if (passportStatus !== "ACTIVE") {
    alert("Issue an active Safety Passport first.");
    return;
  }

  const existing = document.getElementById("runtime-form");
  if (existing) {
    existing.scrollIntoView({ behavior: "smooth", block: "center" });
    return;
  }

  const workflow = document.querySelector(".workflow");

  const panel = document.createElement("article");
  panel.className = "panel workflow-form-panel";
  panel.innerHTML = `
    <div class="panel-header">
      <div>
        <p class="eyebrow">RUNTIME GATE</p>
        <h2>Authorize proposed action</h2>
      </div>
      <span class="secure-badge">Authorization before execution</span>
    </div>

    <p>
      Every consequential action is evaluated against the active Safety
      Passport, configuration, permissions, policy and human authority.
    </p>

    <form id="runtime-form">
      <div class="form-grid">

        <div class="form-group">
          <label for="runtime-action-id">Action ID</label>
          <input
            id="runtime-action-id"
            value="portal-runtime-action-001"
            required
          >
        </div>

        <div class="form-group">
          <label for="runtime-action-name">Action name</label>
          <input
            id="runtime-action-name"
            value="read_document"
            required
          >
        </div>

        <div class="form-group">
          <label for="runtime-tool">Tool</label>
          <input
            id="runtime-tool"
            value="read_documents"
            required
          >
        </div>

        <div class="form-group">
          <label for="runtime-permissions">Requested permissions</label>
          <input
            id="runtime-permissions"
            value="documents:read"
          >
          <small>Comma-separated</small>
        </div>

        <div class="form-group">
          <label for="runtime-risk">Risk level</label>
          <select id="runtime-risk">
            <option value="LOW">Low</option>
            <option value="MEDIUM">Medium</option>
            <option value="HIGH">High</option>
          </select>
        </div>

        <div class="form-group checkbox-group">
          <label>
            <input id="runtime-irreversible" type="checkbox">
            Irreversible action
          </label>
        </div>

        <div class="form-group">
          <label for="runtime-approval-id">Approval ID</label>
          <input
            id="runtime-approval-id"
            placeholder="Optional"
          >
        </div>

        <div class="form-group">
          <label for="runtime-approver">Approver identity</label>
          <input
            id="runtime-approver"
            placeholder="reviewer@example.com"
          >
        </div>

      </div>

      <div class="form-actions">
        <button type="submit" class="primary-button">
          Request authorization
        </button>
        <span id="runtime-status" class="form-status"></span>
      </div>

      <div id="runtime-result" class="decision-card hidden"></div>
    </form>
  `;

  workflow.insertAdjacentElement("afterend", panel);

  document
    .getElementById("runtime-form")
    .addEventListener("submit", async (event) => {
      event.preventDefault();

      const status = document.getElementById("runtime-status");
      const result = document.getElementById("runtime-result");

      const splitValues = (value) =>
        value
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean);

      const approvalId =
        document.getElementById("runtime-approval-id").value.trim();

      const approver =
        document.getElementById("runtime-approver").value.trim();

      const payload = {
        action_id:
          document.getElementById("runtime-action-id").value.trim(),
        tool_name:
          document.getElementById("runtime-tool").value.trim(),
        action_name:
          document.getElementById("runtime-action-name").value.trim(),
        requested_permissions:
          splitValues(
            document.getElementById("runtime-permissions").value
          ),
        is_irreversible:
          document.getElementById("runtime-irreversible").checked,
        risk_level:
          document.getElementById("runtime-risk").value,
        evidence: {
          source: "SafetyGate Client Portal"
        },
        approval:
          approvalId && approver
            ? {
                approval_id: approvalId,
                approver_identity: approver,
                approved: true
              }
            : null
      };

      status.textContent = "Evaluating runtime policy...";
      status.className = "form-status";

      try {
        const response = await fetch(
          `/api/v1/organizations/${orgId}/agents/${agentId}/authorize`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify(payload),
          }
        );

        const body = await response.json();

        if (!response.ok) {
          throw new Error(
            body.detail || "Runtime authorization failed."
          );
        }

        const decision = body.decision;

        let decisionClass = "deny";

        if (
          decision === "ALLOW" ||
          decision === "ALLOW_WITH_CONDITIONS"
        ) {
          decisionClass = "allow";
        } else if (decision === "HUMAN_REVIEW_REQUIRED") {
          decisionClass = "review";
        }

        result.className =
          `decision-card ${decisionClass}`;

        result.innerHTML = `
          <div class="decision-title">
            <span>Runtime decision</span>
            <strong>${decision}</strong>
          </div>

          <p>
            ${body.reasons.join(" ") || "No additional reasons."}
          </p>

          ${
            body.conditions.length
              ? `
                <div class="conditions">
                  <span>Conditions</span>
                  <ul>
                    ${body.conditions
                      .map((condition) => `<li>${condition}</li>`)
                      .join("")}
                  </ul>
                </div>
              `
              : ""
          }

          <small>
            Audit event: ${body.audit_event_id}
          </small>
        `;

        document.getElementById("metric-runtime").textContent =
          decision;

        localStorage.setItem(
          "safetygate_runtime_decision",
          decision
        );

        markStepComplete(5);

        status.textContent = "Runtime decision recorded.";
        status.className = "form-status success";

      } catch (error) {
        status.textContent = error.message;
        status.className = "form-status error";
      }
    });
}


document.querySelectorAll(".nav-item").forEach((button) => {
  if (button.textContent.trim() === "Runtime") {
    button.addEventListener("click", showRuntimeForm);
  }
});


const savedRuntimeDecision =
  localStorage.getItem("safetygate_runtime_decision");

if (savedRuntimeDecision) {
  document.getElementById("metric-runtime").textContent =
    savedRuntimeDecision;
  markStepComplete(5);
}


function applyStoredReviewEvidence() {
  const approvalId =
    localStorage.getItem("safetygate_review_approval_id");

  const approver =
    localStorage.getItem("safetygate_review_approver");

  const approved =
    localStorage.getItem("safetygate_review_approved");

  const approvalInput =
    document.getElementById("runtime-approval-id");

  const approverInput =
    document.getElementById("runtime-approver");

  if (
    approvalId &&
    approver &&
    approved === "true" &&
    approvalInput &&
    approverInput
  ) {
    approvalInput.value = approvalId;
    approverInput.value = approver;

    const status =
      document.getElementById("runtime-status");

    if (status) {
      status.textContent =
        "Authorized human approval loaded from Operator Console.";
      status.className = "form-status success";
    }
  }
}


document.querySelectorAll(".nav-item").forEach((button) => {
  if (button.textContent.trim() === "Runtime") {
    button.addEventListener(
      "click",
      () => setTimeout(applyStoredReviewEvidence, 0)
    );
  }
});


function restoreLifecycleState() {
  const orgName = localStorage.getItem("safetygate_org_name");
  const agentName = localStorage.getItem("safetygate_agent_name");
  const admission = localStorage.getItem("safetygate_admission");
  const passportStatus = localStorage.getItem("safetygate_passport_status");
  const runtimeDecision = localStorage.getItem("safetygate_runtime_decision");

  if (orgName) {
    document.getElementById("metric-org").textContent = orgName;
    markStepComplete(1);
  }

  if (agentName) {
    document.getElementById("metric-agent").textContent =
      `${agentName} · REGISTERED`;
    markStepComplete(2);
  }

  if (admission === "PASS") {
    markStepComplete(3);
  }

  if (passportStatus === "ACTIVE") {
    document.getElementById("metric-passport").textContent = "ACTIVE";
    markStepComplete(4);
  }

  if (runtimeDecision) {
    document.getElementById("metric-runtime").textContent =
      runtimeDecision;
    markStepComplete(5);
  }
}


function enhanceAccessibility() {
  document.querySelectorAll(".form-status").forEach((element) => {
    element.setAttribute("role", "status");
    element.setAttribute("aria-live", "polite");
  });

  document.querySelectorAll("button, a, input, textarea, select")
    .forEach((element) => {
      if (!element.getAttribute("tabindex")) {
        element.setAttribute("tabindex", "0");
      }
    });
}


window.addEventListener("error", () => {
  const runtimeMetric = document.getElementById("metric-runtime");

  if (
    runtimeMetric &&
    runtimeMetric.textContent === "Awaiting action"
  ) {
    runtimeMetric.textContent = "UI error — action not executed";
  }
});


restoreLifecycleState();
enhanceAccessibility();

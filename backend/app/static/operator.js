const operatorState = {
  organizationId: localStorage.getItem("safetygate_org_id"),
};

const message = document.getElementById("operator-message");
const tableWrap = document.getElementById("operator-table-wrap");
const tableBody = document.getElementById("operator-table-body");

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatTime(value) {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}

function decisionClass(decision) {
  if (decision === "ALLOW") return "operator-decision allow";
  if (decision === "ALLOW_WITH_CONDITIONS") {
    return "operator-decision conditional";
  }
  if (decision === "HUMAN_REVIEW_REQUIRED") {
    return "operator-decision review";
  }

  return "operator-decision deny";
}

async function loadSummary() {
  const response = await fetch(
    `/api/v1/organizations/${operatorState.organizationId}/operator/summary`
  );

  const body = await response.json();

  if (!response.ok) {
    throw new Error(body.detail || "Unable to load operator summary.");
  }

  document.getElementById("operator-agents").textContent =
    body.agents_total;

  document.getElementById("operator-active").textContent =
    body.agents_active;

  document.getElementById("operator-reviews").textContent =
    body.pending_reviews;

  document.getElementById("operator-denies").textContent =
    body.hard_denies;
}

async function loadAudit() {
  const response = await fetch(
    `/api/v1/organizations/${operatorState.organizationId}/operator/audit`
  );

  const body = await response.json();

  if (!response.ok) {
    throw new Error(body.detail || "Unable to load audit trail.");
  }

  if (!body.length) {
    tableWrap.classList.add("hidden");
    message.style.display = "block";
    message.textContent = "No runtime audit events have been recorded yet.";
    return;
  }

  tableBody.innerHTML = body.map((entry) => `
    <tr>
      <td>${escapeHtml(formatTime(entry.timestamp))}</td>

      <td>
        <strong>${escapeHtml(entry.action_name)}</strong>
        <div class="table-meta">
          ${escapeHtml(entry.action_id)}
        </div>
      </td>

      <td>
        ${escapeHtml(entry.tool_name)}
      </td>

      <td>
        <span class="${decisionClass(entry.decision)}">
          ${escapeHtml(entry.decision)}
        </span>
      </td>

      <td>
        <strong>
          ${escapeHtml(entry.policy_rule_id || "Runtime hard gate")}
        </strong>
        <div class="table-meta">
          ${escapeHtml(entry.policy_authority || "SafetyGate")}
        </div>
      </td>

      <td>
        ${escapeHtml(entry.execution_outcome || "Not executed")}
      </td>
    </tr>
  `).join("");

  message.style.display = "none";
  tableWrap.classList.remove("hidden");
}

async function loadOperatorConsole() {
  if (!operatorState.organizationId) {
    message.textContent =
      "Select or create an organization in the Client Portal first.";
    return;
  }

  message.textContent = "Loading governance activity...";

  try {
    await Promise.all([
      loadSummary(),
      loadAudit(),
    ]);
  } catch (error) {
    tableWrap.classList.add("hidden");
    message.style.display = "block";
    message.textContent = error.message;
  }
}

document.getElementById("operator-refresh").addEventListener(
  "click",
  loadOperatorConsole
);

document.querySelectorAll(".nav-item").forEach((button) => {
  if (button.dataset.view === "audit") {
    button.addEventListener("click", () => {
      document.querySelectorAll(".nav-item").forEach((item) => {
        item.classList.remove("active");
      });

      button.classList.add("active");
      loadAudit();
    });
  }

  if (button.dataset.view === "overview") {
    button.addEventListener("click", () => {
      document.querySelectorAll(".nav-item").forEach((item) => {
        item.classList.remove("active");
      });

      button.classList.add("active");
      loadOperatorConsole();
    });
  }
});

loadOperatorConsole();


async function loadReviews() {
  if (!operatorState.organizationId) {
    message.textContent =
      "Select or create an organization in the Client Portal first.";
    return;
  }

  message.style.display = "block";
  message.textContent = "Loading human review queue...";
  tableWrap.classList.add("hidden");

  try {
    const response = await fetch(
      `/api/v1/organizations/${operatorState.organizationId}/operator/reviews`
    );

    const body = await response.json();

    if (!response.ok) {
      throw new Error(body.detail || "Unable to load review queue.");
    }

    if (!body.length) {
      message.textContent = "No actions currently require human review.";
      return;
    }

    tableBody.innerHTML = body.map((entry) => `
      <tr>
        <td>${escapeHtml(formatTime(entry.timestamp))}</td>

        <td>
          <strong>${escapeHtml(entry.action_name)}</strong>
          <div class="table-meta">${escapeHtml(entry.action_id)}</div>
        </td>

        <td>${escapeHtml(entry.tool_name)}</td>

        <td>
          <span class="operator-decision review">
            HUMAN REVIEW
          </span>
        </td>

        <td>
          <input
            class="review-approver"
            data-action="${escapeHtml(entry.action_id)}"
            placeholder="Authorized reviewer"
          >
        </td>

        <td>
          <div class="review-actions">
            <button
              class="review-button approve"
              data-action="${escapeHtml(entry.action_id)}"
              data-approved="true"
            >
              Approve
            </button>

            <button
              class="review-button reject"
              data-action="${escapeHtml(entry.action_id)}"
              data-approved="false"
            >
              Reject
            </button>
          </div>
        </td>
      </tr>
    `).join("");

    message.style.display = "none";
    tableWrap.classList.remove("hidden");

    document.querySelectorAll(".review-button").forEach((button) => {
      button.addEventListener("click", async () => {
        const actionId = button.dataset.action;
        const approved = button.dataset.approved === "true";

        const approverInput = document.querySelector(
          `.review-approver[data-action="${CSS.escape(actionId)}"]`
        );

        const approver = approverInput.value.trim();

        if (!approver) {
          alert("Enter an authorized reviewer identity.");
          return;
        }

        button.disabled = true;

        try {
          const decisionResponse = await fetch(
            `/api/v1/organizations/${operatorState.organizationId}` +
            `/operator/reviews/${encodeURIComponent(actionId)}/decision`,
            {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
              },
              body: JSON.stringify({
                approver_identity: approver,
                approved,
              }),
            }
          );

          const result = await decisionResponse.json();

          if (!decisionResponse.ok) {
            throw new Error(
              result.detail || "Unable to record review decision."
            );
          }

          localStorage.setItem(
            "safetygate_review_approval_id",
            result.approval_id
          );

          localStorage.setItem(
            "safetygate_review_approver",
            result.approver_identity
          );

          localStorage.setItem(
            "safetygate_review_approved",
            String(result.approved)
          );

          alert(
            `${result.status}. Approval evidence ${result.approval_id} recorded.`
          );

          await loadSummary();
          await loadReviews();
        } catch (error) {
          alert(error.message);
          button.disabled = false;
        }
      });
    });

  } catch (error) {
    message.style.display = "block";
    message.textContent = error.message;
  }
}


document.querySelectorAll(".nav-item").forEach((button) => {
  if (button.dataset.view === "reviews") {
    button.addEventListener("click", () => {
      document.querySelectorAll(".nav-item").forEach((item) => {
        item.classList.remove("active");
      });

      button.classList.add("active");
      loadReviews();
    });
  }
});


async function loadPolicy() {
  if (!operatorState.organizationId) {
    message.textContent =
      "Select or create an organization in the Client Portal first.";
    return;
  }

  tableWrap.classList.add("hidden");
  message.style.display = "block";
  message.textContent = "Loading policy controls...";

  try {
    const response = await fetch(
      `/api/v1/organizations/${operatorState.organizationId}/operator/policy`
    );

    const body = await response.json();

    if (!response.ok) {
      throw new Error(body.detail || "Unable to load policy controls.");
    }

    message.innerHTML = `
      <div class="policy-view">
        <div class="policy-status-row">
          <div>
            <span>OPA / Rego</span>
            <strong>${body.opa_configured ? "CONFIGURED" : "NOT CONFIGURED"}</strong>
          </div>

          <div>
            <span>Failure mode</span>
            <strong>${body.fail_closed ? "FAIL CLOSED" : "UNKNOWN"}</strong>
          </div>
        </div>

        <p>${escapeHtml(body.enforcement_model)}</p>

        <div class="policy-path">
          <span>Runtime policy endpoint</span>
          <code>${escapeHtml(body.opa_policy_path)}</code>
        </div>

        <h3>Authority hierarchy</h3>

        <ol class="authority-list">
          ${body.authority_hierarchy
            .map((authority) => `<li>${escapeHtml(authority)}</li>`)
            .join("")}
        </ol>
      </div>
    `;
  } catch (error) {
    message.textContent = error.message;
  }
}


document.querySelectorAll(".nav-item").forEach((button) => {
  if (button.dataset.view === "policy") {
    button.addEventListener("click", () => {
      document.querySelectorAll(".nav-item").forEach((item) => {
        item.classList.remove("active");
      });

      button.classList.add("active");
      loadPolicy();
    });
  }
});


function enhanceOperatorAccessibility() {
  message.setAttribute("role", "status");
  message.setAttribute("aria-live", "polite");

  document.querySelectorAll("button, a, input").forEach((element) => {
    if (!element.getAttribute("tabindex")) {
      element.setAttribute("tabindex", "0");
    }
  });
}


window.addEventListener("error", () => {
  message.style.display = "block";
  message.textContent =
    "Operator Console encountered an error. No governance action was executed.";
});


enhanceOperatorAccessibility();

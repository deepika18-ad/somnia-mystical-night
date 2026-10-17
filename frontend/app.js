
const pages = ["home", "auth", "dashboard", "assessment", "result", "about"];

let authMode = "login";
let latestResult = null;
let toastTimer = null;

function showToast(message) {
  const el = document.getElementById("toast");
  if (!el) return;

  el.textContent = message;
  el.classList.add("show");

  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    el.classList.remove("show");
  }, 3500);
}

function showPage(page) {
  if (!pages.includes(page)) page = "home";

  document.querySelectorAll(".page").forEach(el => {
    el.classList.remove("active");
  });

  const target = document.getElementById(`${page}Page`);
  if (target) target.classList.add("active");

  document.querySelectorAll(".nav-link").forEach(el => {
    el.classList.toggle("active", el.dataset.page === page);
  });

  window.scrollTo({ top: 0, behavior: "smooth" });

  if (page === "dashboard") loadDashboard();
  if (page === "about") loadMetrics();
  if (page === "assessment") checkModelStatus();
}

document.addEventListener("click", event => {
  const pageButton = event.target.closest("[data-page]");

  if (pageButton) {
    event.preventDefault();

    const page = pageButton.dataset.page;

    if (page === "dashboard" || page === "assessment") {
      fetch("/api/me")
        .then(response => response.json())
        .then(data => {
          if (!data.user) {
            showPage("auth");
            showToast("Please sign in first.");
          } else {
            showPage(page);
          }
        })
        .catch(() => {
          showPage("auth");
        });
    } else {
      showPage(page);
    }
  }

  const authTab = event.target.closest("[data-auth]");
  if (authTab) setAuthMode(authTab.dataset.auth);
});

const authTop = document.getElementById("authTop");

if (authTop) {
  authTop.addEventListener("click", async () => {
    try {
      const response = await fetch("/api/me");
      const data = await response.json();

      if (data.user) {
        if (confirm("You are signed in. Log out?")) {
          await fetch("/api/logout", { method: "POST" });

          authTop.innerHTML = 'Sign in <span>↗</span>';
          showPage("home");
          showToast("You have signed out.");
        } else {
          showPage("dashboard");
        }
      } else {
        setAuthMode("login");
        showPage("auth");
      }
    } catch {
      showToast("Could not connect to the server.");
    }
  });
}

function setAuthMode(mode) {
  authMode = mode;

  document.querySelectorAll(".auth-tab").forEach(el => {
    el.classList.toggle("active", el.dataset.auth === mode);
  });

  const nameField = document.getElementById("nameField");
  const name = document.getElementById("name");
  const password = document.getElementById("password");
  const authSubmit = document.getElementById("authSubmit");
  const authMessage = document.getElementById("authMessage");

  if (nameField) nameField.classList.toggle("hidden", mode !== "register");
  if (name) name.required = mode === "register";

  if (password) {
    password.autocomplete =
      mode === "register" ? "new-password" : "current-password";
  }

  if (authSubmit) {
    authSubmit.innerHTML =
      mode === "register"
        ? 'Create my observatory <span>→</span>'
        : 'Enter my observatory <span>→</span>';
  }

  if (authMessage) authMessage.textContent = "";
}

const authForm = document.getElementById("authForm");

if (authForm) {
  authForm.addEventListener("submit", async event => {
    event.preventDefault();

    const form = event.currentTarget;
    const message = document.getElementById("authMessage");

    message.textContent = "Connecting to your observatory…";

    const payload = {
      name: document.getElementById("name").value.trim(),
      email: document.getElementById("email").value.trim(),
      password: document.getElementById("password").value
    };

    try {
      const response = await fetch(`/api/${authMode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Could not authenticate.");
      }

      document.getElementById("authTop").textContent = "My account";
      message.textContent = "";

      showToast(
        authMode === "register"
          ? "Your account has been created."
          : "Welcome back."
      );

      form.reset();
      setAuthMode("login");
      showPage("dashboard");
    } catch (error) {
      message.textContent = error.message;
    }
  });
}

async function loadDashboard() {
  const list = document.getElementById("historyList");
  const dashboardMessage = document.getElementById("dashboardMessage");

  if (!list) return;
  if (dashboardMessage) dashboardMessage.textContent = "";

  try {
    const response = await fetch("/api/dashboard");
    const data = await response.json();

    if (!response.ok) {
      showPage("auth");
      showToast(data.error || "Please sign in.");
      return;
    }

    document.getElementById("welcomeTitle").textContent =
      `Welcome, ${data.user.name}`;

    document.getElementById("totalCount").textContent =
      data.assessments.length;

    document.getElementById("latestClass").textContent =
      data.assessments[0]?.predicted_class || "—";

    document.getElementById("modelStatus").textContent =
      data.model_ready ? "Ready" : "Setup";

    document.getElementById("modelSub").textContent =
      data.model_ready ? "Model artifact found" : "Dataset training required";

    document.getElementById("authTop").textContent = "My account";

    if (!data.assessments.length) {
      list.innerHTML = `
        <div class="empty-state">
          No assessments yet. When you are ready, begin a new assessment
          and your saved results will appear here.
        </div>`;
    } else {
      list.innerHTML = data.assessments.map(item => `
        <div class="history-item">
          <div>
            <strong>${escapeHtml(item.predicted_class)}</strong>
            <small>
              ${formatDate(item.created_at)} · Model
              ${escapeHtml(item.model_version)}
            </small>
          </div>
          <button class="history-tag" data-open-result="${item.id}">
            View details ↗
          </button>
        </div>
      `).join("");

      list.querySelectorAll("[data-open-result]").forEach(button => {
        button.addEventListener("click", () => {
          openHistoryItem(button.dataset.openResult);
        });
      });
    }
  } catch {
    list.innerHTML = `
      <div class="empty-state">
        Could not connect to the server. Check that Flask is running.
      </div>`;
  }
}

async function openHistoryItem(id) {
  try {
    const response = await fetch(`/api/assessments/${id}`);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Could not open assessment.");
    }

    latestResult = {
      ...data,
      suggestions: [
        "Try keeping sleep and wake times consistent across the week.",
        "These are general ideas, not treatment or medical advice."
      ],
      disclaimer: "Saved model estimate, not a medical diagnosis."
    };

    renderResult(latestResult);
    showPage("result");
  } catch (error) {
    showToast(error.message);
  }
}

async function checkModelStatus() {
  try {
    const response = await fetch("/api/dashboard");
    const data = await response.json();
    const warning = document.getElementById("modelWarning");

    if (!warning) return;

    if (response.ok && data.model_ready) {
      warning.classList.add("hidden");
    } else {
      warning.classList.remove("hidden");
    }
  } catch {
    // The warning state remains unchanged if the server is unavailable.
  }
}

const assessmentForm = document.getElementById("assessmentForm");

if (assessmentForm) {
  assessmentForm.addEventListener("submit", async event => {
    event.preventDefault();

    // Save the form reference before any await call.
    const form = event.currentTarget;

    const button = document.getElementById("assessSubmit");
    const message = document.getElementById("assessmentMessage");

    const payload = {};

    new FormData(form).forEach((value, key) => {
      payload[key] = value;
    });

    // Map the friendly field ID to the dataset column name.
    const bmiCategory = document.getElementById("BMICategory");

    if (bmiCategory) {
      payload["BMI Category"] = bmiCategory.value;
    }

    button.disabled = true;
    button.textContent = "Reading the pattern…";
    message.textContent = "";

    try {
      const response = await fetch("/api/assess", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Assessment failed.");
      }

      latestResult = data;
      renderResult(data);

      // FIX: use the saved form reference, not event.currentTarget.
      form.reset();

      showPage("result");
      showToast("Assessment saved to your history.");
    } catch (error) {
      message.textContent = error.message;
    } finally {
      button.disabled = false;
      button.innerHTML = 'Generate model estimate <span>→</span>';
    }
  });
}

function renderResult(data) {
  const resultClass = document.getElementById("resultClass");
  const resultDate = document.getElementById("resultDate");
  const disclaimer = document.getElementById("resultDisclaimer");
  const suggestionList = document.getElementById("suggestionList");

  if (resultClass) {
    resultClass.textContent = data.predicted_class || "Not available";
  }

  if (resultDate) {
    resultDate.textContent = formatDate(data.created_at);
  }

  if (disclaimer) {
    disclaimer.textContent =
      data.disclaimer ||
      "This is a dataset-based model estimate, not a medical diagnosis.";
  }

  if (suggestionList) {
    const suggestions = data.suggestions || [];

    suggestionList.innerHTML = suggestions
      .map(s => `<li>${escapeHtml(s)}</li>`)
      .join("");
  }
}

async function loadMetrics() {
  const box = document.getElementById("metricsContent");
  if (!box) return;

  try {
    const response = await fetch("/api/metrics");
    const data = await response.json();

    if (!data.available) {
      box.textContent = data.message || "Metrics are not available yet.";
      return;
    }

    box.innerHTML = `
      <div class="metric-row">
        <span>Held-out accuracy</span>
        <strong>${(data.accuracy * 100).toFixed(1)}%</strong>
      </div>
      <div class="metric-row">
        <span>Macro F1-score</span>
        <strong>${(data.macro_f1 * 100).toFixed(1)}%</strong>
      </div>
      <div class="metric-row">
        <span>Test records</span>
        <strong>${data.test_rows}</strong>
      </div>
      <div class="metric-row">
        <span>Classes</span>
        <strong>${(data.classes || []).map(escapeHtml).join(", ")}</strong>
      </div>
      <p class="muted">${escapeHtml(data.note || "")}</p>
    `;
  } catch {
    box.textContent = "Could not load metrics from the backend.";
  }
}

function formatDate(value) {
  if (!value) return "Date unavailable";

  const date = new Date(value);

  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString();
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, ch => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  })[ch]);
}

(async function init() {
  try {
    const response = await fetch("/api/me");
    const data = await response.json();

    if (data.user) {
      document.getElementById("authTop").textContent = "My account";
    }
  } catch {
    // The page can still display if the server is unavailable.
  }

  loadMetrics();
})();

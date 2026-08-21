/* Dashboard controller: fetches /api/v1/dashboard/summary and renders.
   Falls back to a clear offline state instead of a blank screen. */
const API_BASE = "/api/v1";

const els = {
  envBadge: document.getElementById("env-badge"),
  refresh: document.getElementById("refresh-btn"),
  toast: document.getElementById("status-toast"),
  apps: document.getElementById("stat-apps"),
  pages: document.getElementById("stat-pages"),
  apis: document.getElementById("stat-apis"),
  runs: document.getElementById("stat-runs"),
  total: document.getElementById("stat-total"),
  passed: document.getElementById("stat-passed"),
  failed: document.getElementById("stat-failed"),
  flaky: document.getElementById("stat-flaky"),
  passRateBar: document.getElementById("pass-rate-bar"),
  passRateLabel: document.getElementById("pass-rate-label"),
  healing: document.getElementById("stat-healing"),
  confidence: document.getElementById("stat-confidence"),
  halluc: document.getElementById("stat-halluc"),
  eval: document.getElementById("stat-eval"),
  passrate: document.getElementById("stat-passrate"),
  failrate: document.getElementById("stat-failrate"),
  duration: document.getElementById("stat-duration"),
  browser: document.getElementById("stat-browser"),
  failureList: document.getElementById("failure-list"),
};

function set(el, value) {
  if (el) el.textContent = value;
}

function toast(msg, isError = false) {
  els.toast.hidden = false;
  els.toast.textContent = msg;
  els.toast.classList.toggle("error", isError);
  setTimeout(() => { els.toast.hidden = true; }, 3000);
}

function render(data) {
  set(els.apps, data.applications ?? "—");
  set(els.pages, data.pages ?? "—");
  set(els.apis, data.apis ?? "—");
  set(els.runs, data.runs ?? "—");

  const tests = data.tests || {};
  set(els.total, tests.total ?? "—");
  set(els.passed, tests.passed ?? "—");
  set(els.failed, tests.failed ?? "—");
  set(els.flaky, tests.flaky ?? "—");

  const passRate = data.execution?.pass_rate ?? 0;
  els.passRateBar.style.width = `${Math.round(passRate * 100)}%`;
  set(els.passRateLabel, `${Math.round(passRate * 100)}%`);
  set(els.passrate, `${Math.round(passRate * 100)}%`);
  set(els.failrate, `${Math.round((1 - passRate) * 100)}%`);

  const ai = data.ai || {};
  set(els.healing, ai.healing_events ?? "—");
  set(els.confidence, ai.confidence != null ? `${Math.round(ai.confidence * 100)}%` : "—");
  set(els.halluc, ai.hallucination_rate != null ? `${Math.round(ai.hallucination_rate * 100)}%` : "—");
  set(els.eval, ai.evaluation_score != null ? Math.round(ai.evaluation_score * 100) / 100 : "—");

  set(els.duration, data.execution?.avg_duration_ms != null ? `${data.execution.avg_duration_ms}ms` : "—");
  set(els.browser, (data.execution?.browsers || []).join(", ") || "—");

  renderFailures(data.failures || []);
}

function renderFailures(failures) {
  if (!failures || failures.length === 0) {
    els.failureList.innerHTML = '<p class="empty">No failures recorded yet.</p>';
    return;
  }
  els.failureList.innerHTML = failures.map((f) => `
    <div class="list-item">
      <span class="cause">${escapeHtml(f.root_cause || f.test_id || "unknown")}</span>
      <span class="tag ${f.classification || ""}">${f.classification || "unknown"}</span>
    </div>
  `).join("");
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

async function load() {
  els.refresh.disabled = true;
  try {
    const token = localStorage.getItem("api_token");
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    const res = await fetch(`${API_BASE}/dashboard/summary`, { headers });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    els.envBadge.textContent = "online";
    els.envBadge.classList.add("online");
    render(data);
  } catch (err) {
    els.envBadge.textContent = "offline";
    els.envBadge.classList.remove("online");
    set(els.apps, "—"); set(els.total, "—");
    toast(`Backend unreachable — start it with \`make dev\` (${err.message})`, true);
  } finally {
    els.refresh.disabled = false;
  }
}

els.refresh.addEventListener("click", load);
load();

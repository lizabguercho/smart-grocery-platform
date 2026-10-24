"""Single-page labeling UI (zero frontend deps). Schema-driven from task field specs."""

from __future__ import annotations

LABELING_UI_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Smart Grocery — Labeling</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet" />
  <style>
    :root {
      --bg: #f3efe6;
      --bg-panel: #fffdf8;
      --ink: #1c1a16;
      --muted: #5c574e;
      --line: #d9d2c4;
      --accent: #0f6b5c;
      --accent-ink: #ffffff;
      --warn: #8a4b12;
      --danger: #8b1e1e;
      --ok: #1f6b3a;
      --corrected: #1a4f8a;
      --shadow: 0 12px 40px rgba(28, 26, 22, 0.08);
      --radius: 14px;
      --sidebar-w: 300px;
      --status-unreviewed: #c47a1a;
      --status-accepted: #1f6b3a;
      --status-corrected: #1a4f8a;
      --status-excluded: #8b1e1e;
      --status-unreviewed-bg: rgba(196, 122, 26, 0.12);
      --status-accepted-bg: rgba(31, 107, 58, 0.12);
      --status-corrected-bg: rgba(26, 79, 138, 0.12);
      --status-excluded-bg: rgba(139, 30, 30, 0.12);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "IBM Plex Sans", system-ui, sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(15, 107, 92, 0.08), transparent 40%),
        linear-gradient(180deg, #efe8da 0%, var(--bg) 40%, #e7e1d4 100%);
      min-height: 100vh;
    }
    header {
      display: flex;
      justify-content: space-between;
      gap: 1rem;
      align-items: center;
      padding: 1rem 1.25rem;
      border-bottom: 1px solid var(--line);
      background: rgba(255, 253, 248, 0.86);
      backdrop-filter: blur(8px);
      position: sticky;
      top: 0;
      z-index: 10;
    }
    h1 { margin: 0; font-size: 1.1rem; font-weight: 600; letter-spacing: -0.02em; }
    .sub { color: var(--muted); font-size: 0.85rem; margin-top: 0.15rem; }
    .shell {
      display: grid;
      grid-template-columns: var(--sidebar-w) 1fr;
      min-height: calc(100vh - 70px);
      align-items: stretch;
    }
    .sidebar {
      border-right: 1px solid var(--line);
      background: rgba(255, 253, 248, 0.92);
      display: flex;
      flex-direction: column;
      max-height: calc(100vh - 70px);
      position: sticky;
      top: 70px;
    }
    .sidebar-head {
      padding: 0.85rem 0.9rem 0.65rem;
      border-bottom: 1px solid var(--line);
      display: grid;
      gap: 0.65rem;
    }
    .sidebar-head h2 {
      margin: 0;
      font-size: 0.85rem;
      font-weight: 600;
    }
    .legend {
      display: flex;
      flex-wrap: wrap;
      gap: 0.4rem;
      font-size: 0.7rem;
      color: var(--muted);
    }
    .legend span {
      display: inline-flex;
      align-items: center;
      gap: 0.3rem;
    }
    .dot {
      width: 0.55rem;
      height: 0.55rem;
      border-radius: 50%;
      flex: 0 0 auto;
    }
    .dot-unreviewed { background: var(--status-unreviewed); }
    .dot-accepted { background: var(--status-accepted); }
    .dot-corrected { background: var(--status-corrected); }
    .dot-excluded { background: var(--status-excluded); }
    .sidebar-list {
      overflow: auto;
      flex: 1;
      padding: 0.4rem;
    }
    .queue-item {
      width: 100%;
      text-align: left;
      border: 1px solid transparent;
      border-radius: 10px;
      background: transparent;
      padding: 0.55rem 0.6rem 0.55rem 0.7rem;
      cursor: pointer;
      display: grid;
      gap: 0.15rem;
      margin-bottom: 0.25rem;
      position: relative;
      color: var(--ink);
      border-left: 3px solid transparent;
    }
    .queue-item:hover { background: rgba(28, 26, 22, 0.04); }
    .queue-item.active {
      background: #fff;
      border-color: var(--line);
      box-shadow: var(--shadow);
    }
    .queue-item.status-unreviewed { border-left-color: var(--status-unreviewed); }
    .queue-item.status-accepted { border-left-color: var(--status-accepted); }
    .queue-item.status-corrected { border-left-color: var(--status-corrected); }
    .queue-item.status-excluded { border-left-color: var(--status-excluded); }
    .queue-item.active.status-unreviewed { background: var(--status-unreviewed-bg); }
    .queue-item.active.status-accepted { background: var(--status-accepted-bg); }
    .queue-item.active.status-corrected { background: var(--status-corrected-bg); }
    .queue-item.active.status-excluded { background: var(--status-excluded-bg); }
    .queue-top {
      display: flex;
      justify-content: space-between;
      gap: 0.4rem;
      align-items: baseline;
      font-size: 0.7rem;
      color: var(--muted);
    }
    .queue-status {
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.03em;
      font-size: 0.65rem;
    }
    .queue-item.status-unreviewed .queue-status { color: var(--status-unreviewed); }
    .queue-item.status-accepted .queue-status { color: var(--status-accepted); }
    .queue-item.status-corrected .queue-status { color: var(--status-corrected); }
    .queue-item.status-excluded .queue-status { color: var(--status-excluded); }
    .queue-title {
      font-size: 0.88rem;
      line-height: 1.3;
      direction: rtl;
      text-align: right;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .queue-id {
      font-family: "IBM Plex Mono", monospace;
      font-size: 0.68rem;
      color: var(--muted);
    }
    .workspace {
      padding: 1.25rem;
      display: grid;
      gap: 1rem;
      align-content: start;
      max-width: 1100px;
    }
    .panel {
      background: var(--bg-panel);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      padding: 1rem 1.1rem;
    }
    .row { display: flex; gap: 0.75rem; flex-wrap: wrap; align-items: center; }
    select, input, textarea, button {
      font: inherit;
    }
    select, input, textarea {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 0.65rem 0.75rem;
      background: #fff;
      color: var(--ink);
    }
    textarea { min-height: 4.5rem; resize: vertical; }
    label { display: block; font-size: 0.8rem; font-weight: 500; color: var(--muted); margin-bottom: 0.35rem; }
    .field { margin-bottom: 0.85rem; }
    .help { font-size: 0.75rem; color: var(--muted); margin-top: 0.25rem; }
    .candidate {
      font-family: "IBM Plex Mono", monospace;
      font-size: 0.75rem;
      color: var(--muted);
      margin-top: 0.25rem;
    }
    .candidate button {
      margin-left: 0.35rem;
      border: none;
      background: transparent;
      color: var(--accent);
      cursor: pointer;
      padding: 0;
      font: inherit;
      text-decoration: underline;
    }
    .he {
      font-size: 1.35rem;
      line-height: 1.45;
      direction: rtl;
      text-align: right;
      font-weight: 500;
    }
    .meta {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 0.5rem 1rem;
      margin-top: 0.75rem;
      font-size: 0.85rem;
      color: var(--muted);
    }
    .meta strong { color: var(--ink); font-weight: 500; }
    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      position: sticky;
      bottom: 0;
      padding: 0.75rem 0 0.25rem;
      background: linear-gradient(180deg, transparent, var(--bg) 30%);
    }
    button.primary, button.secondary, button.danger, button.ghost {
      border-radius: 999px;
      padding: 0.7rem 1rem;
      border: 1px solid transparent;
      cursor: pointer;
      font-weight: 500;
    }
    button.primary { background: var(--accent); color: var(--accent-ink); }
    button.secondary { background: #fff; border-color: var(--line); color: var(--ink); }
    button.danger { background: #f8e8e8; color: var(--danger); border-color: #efcfcf; }
    button.ghost { background: transparent; color: var(--muted); border-color: var(--line); }
    button:disabled { opacity: 0.5; cursor: not-allowed; }
    .stats { display: flex; gap: 0.75rem; flex-wrap: wrap; font-size: 0.8rem; }
    .pill {
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 0.25rem 0.65rem;
      background: #fff;
    }
    .status-unreviewed { color: var(--status-unreviewed); }
    .status-accepted { color: var(--status-accepted); }
    .status-corrected { color: var(--status-corrected); }
    .status-excluded { color: var(--status-excluded); }
    .empty { color: var(--muted); padding: 2rem 0; text-align: center; }
    .kbd {
      font-family: "IBM Plex Mono", monospace;
      font-size: 0.7rem;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 0.05rem 0.35rem;
      background: #fff;
    }
    @media (min-width: 900px) {
      .layout {
        display: grid;
        grid-template-columns: 1.1fr 0.9fr;
        gap: 1rem;
        align-items: start;
      }
    }
    @media (max-width: 900px) {
      .shell { grid-template-columns: 1fr; }
      .sidebar {
        position: relative;
        top: 0;
        max-height: 240px;
        border-right: none;
        border-bottom: 1px solid var(--line);
      }
    }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>Labeling desk</h1>
      <div class="sub">Local review UI · task-plugin architecture</div>
    </div>
    <div class="row">
      <label for="task-select" style="margin:0">Task</label>
      <select id="task-select" style="width:auto;min-width:220px"></select>
    </div>
  </header>

  <div class="shell">
    <aside class="sidebar">
      <div class="sidebar-head">
        <h2>All rows</h2>
        <div class="legend">
          <span><i class="dot dot-unreviewed"></i> unlabeled</span>
          <span><i class="dot dot-accepted"></i> accepted</span>
          <span><i class="dot dot-corrected"></i> corrected</span>
          <span><i class="dot dot-excluded"></i> excluded</span>
        </div>
      </div>
      <div id="queue-list" class="sidebar-list" aria-label="Labeling queue"></div>
    </aside>

    <main class="workspace">
      <section class="panel">
        <div class="row" style="justify-content:space-between">
          <div id="stats" class="stats"></div>
          <div class="row">
            <label for="filter-status" style="margin:0">Queue</label>
            <select id="filter-status" style="width:auto">
              <option value="unreviewed">Unreviewed</option>
              <option value="">All</option>
              <option value="accepted">Accepted</option>
              <option value="corrected">Corrected</option>
              <option value="excluded">Excluded</option>
            </select>
            <button type="button" class="danger" id="btn-reset-all">Reset all labels…</button>
          </div>
        </div>
      </section>

      <section id="item-panel" class="panel layout">
        <div>
          <div class="row" style="justify-content:space-between;margin-bottom:0.75rem">
            <div id="progress" class="sub"></div>
            <div id="status-badge" class="pill"></div>
          </div>
          <div id="title" class="he"></div>
          <div id="subtitle" class="sub" style="margin-top:0.35rem;direction:ltr;text-align:left"></div>
          <div id="meta" class="meta"></div>
        </div>
        <div>
          <form id="label-form"></form>
          <div class="field">
            <label for="notes">Notes</label>
            <input id="notes" type="text" placeholder="Optional note" />
          </div>
          <div class="actions">
            <button type="button" class="primary" id="btn-accept">Accept <span class="kbd">A</span></button>
            <button type="button" class="secondary" id="btn-correct">Save corrected <span class="kbd">C</span></button>
            <button type="button" class="danger" id="btn-exclude">Exclude <span class="kbd">X</span></button>
            <button type="button" class="ghost" id="btn-unlabel">Unlabel this row</button>
            <button type="button" class="ghost" id="btn-skip">Skip <span class="kbd">S</span></button>
            <button type="button" class="ghost" id="btn-use-candidates">Fill from candidates</button>
          </div>
        </div>
      </section>
      <div id="empty" class="empty panel" hidden>No items in this queue.</div>
    </main>
  </div>

<script>
  const state = {
    taskId: null,
    specs: [],
    item: null,
    filterStatus: "unreviewed",
    queue: [],
  };

  const $ = (id) => document.getElementById(id);

  async function api(path, opts = {}) {
    const res = await fetch(path, {
      headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
      ...opts,
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || res.statusText);
    }
    if (res.status === 204) return null;
    return res.json();
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  async function loadTasks() {
    const tasks = await api("/api/tasks");
    const select = $("task-select");
    select.innerHTML = "";
    for (const task of tasks) {
      const opt = document.createElement("option");
      opt.value = task.task_id;
      opt.textContent = task.title;
      select.appendChild(opt);
    }
    if (!tasks.length) return;
    state.taskId = tasks[0].task_id;
    select.value = state.taskId;
    await loadTaskDetails();
  }

  async function loadTaskDetails() {
    const detail = await api(`/api/tasks/${state.taskId}`);
    state.specs = detail.fields;
    $("stats").innerHTML = "";
    await refreshStats();
    await refreshQueue();
    await loadNext();
  }

  async function refreshStats() {
    const stats = await api(`/api/tasks/${state.taskId}/stats`);
    const parts = [
      `<span class="pill">total ${stats.total}</span>`,
      `<span class="pill">unreviewed ${stats.remaining_unreviewed}</span>`,
    ];
    for (const [k, v] of Object.entries(stats.by_status || {})) {
      parts.push(`<span class="pill">${escapeHtml(k)} ${v}</span>`);
    }
    $("stats").innerHTML = parts.join("");
  }

  async function refreshQueue() {
    state.queue = await api(`/api/tasks/${state.taskId}/items`);
    renderQueue();
  }

  function renderQueue() {
    const list = $("queue-list");
    const activeId = state.item?.item_id;
    list.innerHTML = state.queue.map((row) => {
      const active = row.item_id === activeId ? "active" : "";
      return `
        <button type="button"
          class="queue-item status-${escapeHtml(row.status)} ${active}"
          data-item-id="${escapeHtml(row.item_id)}"
          title="${escapeHtml(row.title)}">
          <div class="queue-top">
            <span>#${row.position}</span>
            <span class="queue-status">${escapeHtml(row.status)}</span>
          </div>
          <div class="queue-title">${escapeHtml(row.title || "(no title)")}</div>
          <div class="queue-id">${escapeHtml(row.item_id)}</div>
        </button>
      `;
    }).join("");
    list.querySelectorAll(".queue-item").forEach((btn) => {
      btn.addEventListener("click", () => openItem(btn.getAttribute("data-item-id")));
    });
    if (activeId) {
      const activeBtn = list.querySelector(`.queue-item[data-item-id="${CSS.escape(activeId)}"]`);
      if (activeBtn) {
        activeBtn.scrollIntoView({ block: "nearest" });
      }
    }
  }

  async function openItem(itemId) {
    if (!itemId) return;
    const item = await api(`/api/tasks/${state.taskId}/items/${encodeURIComponent(itemId)}`);
    renderItem(item);
  }

  function renderForm(item) {
    const form = $("label-form");
    form.innerHTML = "";
    for (const spec of state.specs) {
      if (!spec.editable) continue;
      const wrap = document.createElement("div");
      wrap.className = "field";
      const value = item.values?.[spec.key] ?? "";
      const candidate = item.candidates?.[spec.key];
      let control = "";
      if (spec.field_type === "textarea") {
        control = `<textarea name="${spec.key}" id="f-${spec.key}">${escapeHtml(value ?? "")}</textarea>`;
      } else if (spec.field_type === "number") {
        control = `<input name="${spec.key}" id="f-${spec.key}" type="number" step="any" value="${escapeHtml(value ?? "")}" />`;
      } else if (spec.field_type === "bool") {
        control = `<select name="${spec.key}" id="f-${spec.key}">
          <option value=""></option>
          <option value="true" ${value === true || value === "true" ? "selected" : ""}>true</option>
          <option value="false" ${value === false || value === "false" ? "selected" : ""}>false</option>
        </select>`;
      } else if (spec.field_type === "select") {
        const opts = (spec.options || []).map(o =>
          `<option value="${escapeHtml(o)}" ${value === o ? "selected" : ""}>${escapeHtml(o)}</option>`
        ).join("");
        control = `<select name="${spec.key}" id="f-${spec.key}"><option value=""></option>${opts}</select>`;
      } else {
        control = `<input name="${spec.key}" id="f-${spec.key}" type="text" value="${escapeHtml(value ?? "")}" />`;
      }
      wrap.innerHTML = `
        <label for="f-${spec.key}">${escapeHtml(spec.label)}${spec.required ? " *" : ""}</label>
        ${control}
        ${spec.help_text ? `<div class="help">${escapeHtml(spec.help_text)}</div>` : ""}
        ${candidate !== undefined && candidate !== null && candidate !== ""
          ? `<div class="candidate">candidate: ${escapeHtml(candidate)} <button type="button" data-fill="${spec.key}" data-value="${escapeHtml(candidate)}">use</button></div>`
          : ""}
      `;
      form.appendChild(wrap);
    }
    form.querySelectorAll("button[data-fill]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const key = btn.getAttribute("data-fill");
        const el = document.getElementById(`f-${key}`);
        if (el) el.value = btn.getAttribute("data-value") || "";
      });
    });
  }

  function renderItem(item) {
    state.item = item;
    if (!item) {
      $("item-panel").hidden = true;
      $("empty").hidden = false;
      renderQueue();
      return;
    }
    $("item-panel").hidden = false;
    $("empty").hidden = true;
    $("title").textContent = item.title || "";
    $("subtitle").textContent = item.subtitle || "";
    $("progress").textContent = item.position && item.total
      ? `${item.position} / ${item.total}`
      : "";
    $("status-badge").textContent = item.status;
    $("status-badge").className = `pill status-${item.status}`;
    const metaBits = Object.entries(item.meta || {}).map(([k, v]) =>
      `<div><strong>${escapeHtml(k)}</strong><br/>${escapeHtml(v ?? "")}</div>`
    );
    $("meta").innerHTML = metaBits.join("");
    $("notes").value = item.notes || "";
    renderForm(item);
    renderQueue();
  }

  function collectValues() {
    const values = {};
    for (const spec of state.specs) {
      if (!spec.editable) continue;
      const el = document.getElementById(`f-${spec.key}`);
      if (!el) continue;
      let value = el.value;
      if (spec.field_type === "number") {
        values[spec.key] = value === "" ? null : Number(value);
      } else if (spec.field_type === "bool") {
        values[spec.key] = value === "" ? null : value === "true";
      } else {
        values[spec.key] = value;
      }
    }
    return values;
  }

  async function submit(action, { advance = true } = {}) {
    if (!state.item) return;
    const itemId = state.item.item_id;
    const body = {
      action,
      values: collectValues(),
      notes: $("notes").value || "",
    };
    const updated = await api(`/api/tasks/${state.taskId}/items/${encodeURIComponent(itemId)}/decision`, {
      method: "POST",
      body: JSON.stringify(body),
    });
    await refreshStats();
    await refreshQueue();
    if (advance) {
      await loadNext(itemId);
    } else {
      renderItem(updated);
    }
  }

  async function unlabelCurrent() {
    if (!state.item) return;
    const ok = window.confirm(
      `Unlabel this row (${state.item.item_id})?\\n\\nClears gold fields and sets status back to unreviewed. LLM candidates are kept.`
    );
    if (!ok) return;
    await submit("unlabel", { advance: false });
  }

  async function resetAllLabels() {
    const ok = window.confirm(
      "Reset ALL labels for this task?\\n\\nThis clears every gold field and sets all rows to unreviewed.\\nLLM candidates are kept.\\n\\nThis cannot be undone from the UI."
    );
    if (!ok) return;
    const typed = window.prompt('Type RESET to confirm wiping all human labels:');
    if (typed !== "RESET") {
      window.alert("Reset cancelled.");
      return;
    }
    await api(`/api/tasks/${state.taskId}/reset`, {
      method: "POST",
      body: JSON.stringify({ confirm: true }),
    });
    await refreshStats();
    await refreshQueue();
    await loadNext();
  }

  async function loadNext(afterId = null) {
    const params = new URLSearchParams();
    if (state.filterStatus) params.set("status", state.filterStatus);
    if (afterId) params.set("after", afterId);
    const item = await api(`/api/tasks/${state.taskId}/next?${params.toString()}`);
    renderItem(item);
  }

  function fillCandidates() {
    if (!state.item) return;
    for (const spec of state.specs) {
      const el = document.getElementById(`f-${spec.key}`);
      const candidate = state.item.candidates?.[spec.key];
      if (el && candidate !== undefined && candidate !== null) {
        el.value = candidate;
      }
    }
  }

  $("task-select").addEventListener("change", async (e) => {
    state.taskId = e.target.value;
    await loadTaskDetails();
  });
  $("filter-status").addEventListener("change", async (e) => {
    state.filterStatus = e.target.value;
    await loadNext();
  });
  $("btn-accept").addEventListener("click", () => submit("accept"));
  $("btn-correct").addEventListener("click", () => submit("correct"));
  $("btn-exclude").addEventListener("click", () => submit("exclude"));
  $("btn-unlabel").addEventListener("click", () => unlabelCurrent());
  $("btn-skip").addEventListener("click", () => submit("skip"));
  $("btn-use-candidates").addEventListener("click", fillCandidates);
  $("btn-reset-all").addEventListener("click", () => resetAllLabels());

  window.addEventListener("keydown", (e) => {
    // Allow normal copy/paste/select-all (Cmd/Ctrl+C, etc.).
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    if (e.target.matches("input, textarea, select")) return;
    const key = e.key.toLowerCase();
    if (key === "a") submit("accept");
    if (key === "c") submit("correct");
    if (key === "x") submit("exclude");
    if (key === "s") submit("skip");
  });

  loadTasks().catch((err) => {
    $("empty").hidden = false;
    $("empty").textContent = `Failed to load tasks: ${err.message}`;
    $("item-panel").hidden = true;
  });
</script>
</body>
</html>
"""

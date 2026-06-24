"use strict";

// ----- State -----
let currentConversationId = null;
let sending = false;

// ----- Element helpers -----
const $ = (id) => document.getElementById(id);
const messagesEl = $("messages");
const listEl = $("conversation-list");
const inputEl = $("input");

// ----- API helpers -----
async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail || detail;
    } catch (e) {}
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

// ----- Conversations -----
async function loadConversations() {
  const convos = await api("/api/conversations");
  listEl.innerHTML = "";
  for (const c of convos) {
    const li = document.createElement("li");
    li.dataset.id = c.id;
    if (c.id === currentConversationId) li.classList.add("active");

    const title = document.createElement("span");
    title.className = "title";
    title.textContent = c.title || "Untitled";
    li.appendChild(title);

    const del = document.createElement("button");
    del.className = "del";
    del.textContent = "🗑";
    del.title = "Delete conversation";
    del.onclick = (e) => {
      e.stopPropagation();
      deleteConversation(c.id);
    };
    li.appendChild(del);

    li.onclick = () => openConversation(c.id);
    listEl.appendChild(li);
  }
}

async function openConversation(id) {
  const conv = await api(`/api/conversations/${id}`);
  currentConversationId = id;
  renderMessages(conv.messages);
  highlightActive();
}

function highlightActive() {
  [...listEl.children].forEach((li) =>
    li.classList.toggle("active", Number(li.dataset.id) === currentConversationId)
  );
}

function newConversation() {
  currentConversationId = null;
  renderMessages([]);
  highlightActive();
  inputEl.focus();
}

async function deleteConversation(id) {
  if (!confirm("Delete this conversation?")) return;
  await api(`/api/conversations/${id}`, { method: "DELETE" });
  if (id === currentConversationId) newConversation();
  await loadConversations();
}

// ----- Message rendering -----
function renderMessages(messages) {
  messagesEl.innerHTML = "";
  if (!messages.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.innerHTML = "<h2>Start chatting with your local model</h2><p>Your messages are stored in Postgres so you can come back to them.</p>";
    messagesEl.appendChild(empty);
    return;
  }
  for (const m of messages) addMessage(m.role, m.content);
  scrollToBottom();
}

function addMessage(role, content) {
  const empty = messagesEl.querySelector(".empty");
  if (empty) empty.remove();

  const el = document.createElement("div");
  el.className = `msg ${role}`;

  const roleEl = document.createElement("div");
  roleEl.className = "role";
  roleEl.textContent = role;
  el.appendChild(roleEl);

  const body = document.createElement("div");
  body.className = "body";
  body.textContent = content;
  el.appendChild(body);

  if (role === "assistant") {
    const save = document.createElement("button");
    save.className = "save";
    save.textContent = "💾 Save";
    save.title = "Save this answer to a file";
    save.onclick = () => saveAnswer(body.textContent);
    el.appendChild(save);
  }

  messagesEl.appendChild(el);
  scrollToBottom();
  return body;
}

function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

// ----- Save an answer as a file -----
function saveAnswer(text) {
  const stamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
  const blob = new Blob([text], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `ollapi-answer-${stamp}.md`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

// ----- Sending / streaming chat -----
async function sendMessage(text) {
  if (sending || !text.trim()) return;
  sending = true;
  $("send").disabled = true;

  addMessage("user", text);
  const bodyEl = addMessage("assistant", "");
  bodyEl.parentElement.classList.add("typing");

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        conversation_id: currentConversationId,
      }),
    });
    if (!res.ok || !res.body) {
      throw new Error(`Request failed (${res.status})`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let isNew = currentConversationId === null;

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const parts = buffer.split("\n\n");
      buffer = parts.pop();
      for (const part of parts) {
        const line = part.trim();
        if (!line.startsWith("data:")) continue;
        const event = JSON.parse(line.slice(5).trim());

        if (event.type === "meta") {
          currentConversationId = event.conversation_id;
        } else if (event.type === "token") {
          bodyEl.textContent += event.content;
          scrollToBottom();
        } else if (event.type === "error") {
          bodyEl.textContent += `\n\n[error: ${event.error}]`;
        } else if (event.type === "done") {
          currentConversationId = event.conversation_id;
        }
      }
    }

    bodyEl.parentElement.classList.remove("typing");
    if (isNew) await loadConversations();
    highlightActive();
  } catch (err) {
    bodyEl.parentElement.classList.remove("typing");
    bodyEl.textContent += `\n\n[error: ${err.message}]`;
  } finally {
    sending = false;
    $("send").disabled = false;
    inputEl.focus();
  }
}

// ----- Status indicator -----
async function refreshStatus() {
  const dot = $("status-dot");
  const text = $("status-text");
  try {
    const s = await api("/api/status");
    if (!s.ollama_reachable) {
      dot.className = "dot bad";
      text.textContent = "Ollama offline";
    } else if (!s.model_ready) {
      dot.className = "dot warn";
      text.textContent = `Pulling ${s.model}…`;
    } else {
      dot.className = "dot ok";
      text.textContent = s.model;
    }
  } catch (e) {
    dot.className = "dot bad";
    text.textContent = "server error";
  }
}

// ----- Settings -----
async function openSettings() {
  const [cfg, models] = await Promise.all([
    api("/api/config"),
    api("/api/models"),
  ]);

  const select = $("model-select");
  select.innerHTML = "";
  const opts = new Set(models.available);
  opts.add(cfg.model);
  for (const m of opts) {
    const o = document.createElement("option");
    o.value = m;
    o.textContent = m;
    if (m === cfg.model) o.selected = true;
    select.appendChild(o);
  }

  $("model-custom").value = "";
  $("system-prompt").value = cfg.system_prompt;
  $("temperature").value = cfg.temperature;
  $("temp-val").textContent = cfg.temperature;
  $("top_p").value = cfg.top_p;
  $("topp-val").textContent = cfg.top_p;
  $("num_ctx").value = cfg.num_ctx;
  $("num_predict").value = cfg.num_predict;
  $("settings-msg").textContent = "";
  $("pull-log").classList.add("hidden");

  $("settings-modal").classList.remove("hidden");
}

function closeSettings() {
  $("settings-modal").classList.add("hidden");
}

async function saveSettings() {
  const custom = $("model-custom").value.trim();
  const payload = {
    model: custom || $("model-select").value,
    system_prompt: $("system-prompt").value,
    temperature: parseFloat($("temperature").value),
    top_p: parseFloat($("top_p").value),
    num_ctx: parseInt($("num_ctx").value, 10),
    num_predict: parseInt($("num_predict").value, 10),
  };
  try {
    await api("/api/config", { method: "PUT", body: JSON.stringify(payload) });
    $("settings-msg").textContent = "Saved ✓";
    refreshStatus();
    setTimeout(closeSettings, 600);
  } catch (err) {
    $("settings-msg").textContent = `Error: ${err.message}`;
  }
}

async function pullModel() {
  const model = $("pull-model").value.trim();
  if (!model) return;
  const log = $("pull-log");
  log.classList.remove("hidden");
  log.textContent = `Pulling ${model}…\n`;
  $("pull-btn").disabled = true;

  try {
    const res = await fetch("/api/models/pull", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model }),
    });
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop();
      for (const part of parts) {
        const line = part.trim();
        if (!line.startsWith("data:")) continue;
        const event = JSON.parse(line.slice(5).trim());
        if (event.error) {
          log.textContent += `Error: ${event.error}\n`;
        } else if (event.status) {
          const pct =
            event.total && event.completed
              ? ` (${Math.round((event.completed / event.total) * 100)}%)`
              : "";
          log.textContent += `${event.status}${pct}\n`;
        }
        log.scrollTop = log.scrollHeight;
      }
    }
    log.textContent += "Done.\n";
    await openSettings.refresh?.();
  } catch (err) {
    log.textContent += `Error: ${err.message}\n`;
  } finally {
    $("pull-btn").disabled = false;
    refreshStatus();
  }
}

// ----- Wiring -----
function autoGrow() {
  inputEl.style.height = "auto";
  inputEl.style.height = Math.min(inputEl.scrollHeight, 200) + "px";
}

$("composer").addEventListener("submit", (e) => {
  e.preventDefault();
  const text = inputEl.value;
  inputEl.value = "";
  autoGrow();
  sendMessage(text);
});

inputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    $("composer").requestSubmit();
  }
});
inputEl.addEventListener("input", autoGrow);

$("new-chat").onclick = newConversation;
$("open-settings").onclick = openSettings;
$("close-settings").onclick = closeSettings;
$("save-settings").onclick = saveSettings;
$("pull-btn").onclick = pullModel;
$("temperature").oninput = (e) => ($("temp-val").textContent = e.target.value);
$("top_p").oninput = (e) => ($("topp-val").textContent = e.target.value);
$("settings-modal").addEventListener("click", (e) => {
  if (e.target.id === "settings-modal") closeSettings();
});

// ----- Init -----
(async function init() {
  await loadConversations();
  newConversation();
  refreshStatus();
  setInterval(refreshStatus, 8000);
})();

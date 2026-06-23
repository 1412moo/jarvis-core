const tabs = document.querySelectorAll(".tab-button");
const panels = document.querySelectorAll(".tab-panel");
const commandInput = document.getElementById("commandInput");
const suggestButton = document.getElementById("suggestButton");
const suggestionBox = document.getElementById("suggestionBox");
const statusText = document.getElementById("statusText");
const nextActionText = document.getElementById("nextActionText");
const skillGrid = document.getElementById("skillGrid");
const skillDetail = document.getElementById("skillDetail");

let registrySkills = [];

function activateTab(tabId) {
  tabs.forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === tabId);
  });
  panels.forEach((panel) => {
    panel.classList.toggle("hidden", panel.id !== `tab-${tabId}`);
  });
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function listMarkup(items, emptyText) {
  if (!items || !items.length) {
    return `<p class="muted">${escapeHtml(emptyText)}</p>`;
  }
  return `<ul class="metadata-list">${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}

function commandRow(label, command, copyable) {
  if (!command) {
    return "";
  }
  const copyButton = copyable
    ? `<button class="copy-command" type="button" data-command="${escapeHtml(command)}">Copy</button>`
    : "";
  return `
    <div class="command-row">
      <div class="command-row-header">
        <span class="command-label">${escapeHtml(label)}</span>
        ${copyButton}
      </div>
      <code>${escapeHtml(command)}</code>
    </div>
  `;
}

function commandMarkup(commands, options = {}) {
  if (!commands) {
    return "<p class=\"muted\">No command. Choose manually or refine the request.</p>";
  }

  const gitBash = commands.git_bash || "";
  const powershell = commands.powershell || "";
  if (!gitBash && !powershell) {
    return "<p class=\"muted\">No command yet. This skill is a proposal or placeholder.</p>";
  }

  return [
    commandRow("Git Bash", gitBash, Boolean(options.copyable)),
    commandRow("PowerShell", powershell, Boolean(options.copyable)),
  ].join("");
}

function renderSuggestion(data) {
  suggestionBox.innerHTML = `
    <div class="suggestion-header">
      <span class="status available">${escapeHtml(data.recommended_skill)}</span>
      <h3>${escapeHtml(data.display_name || data.recommended_skill)}</h3>
    </div>
    <p><strong>Why:</strong> ${escapeHtml(data.reason)}</p>
    <p><strong>Suggested next action:</strong> ${escapeHtml(data.suggested_next_action)}</p>
    <div class="command-list">${commandMarkup(data.commands)}</div>
    <p class="safety-note">This is only a recommendation. Jarvis Console does not run this skill.</p>
  `;
  statusText.textContent = `Recommended skill: ${data.display_name || data.recommended_skill}`;
  nextActionText.textContent = data.suggested_next_action || "Choose manually.";
}

function renderSkillCards(skills) {
  skillGrid.innerHTML = skills
    .map((skill) => `
      <button class="skill-card" type="button" data-skill-id="${escapeHtml(skill.skill_id)}">
        <span class="status ${escapeHtml(skill.status)}">${escapeHtml(skill.status)}</span>
        <span class="skill-card-title">${escapeHtml(skill.display_name)}</span>
        <span class="skill-card-description">${escapeHtml(skill.short_description || skill.purpose)}</span>
        <strong>View read-only details</strong>
      </button>
    `)
    .join("");
}

function renderSkillDetail(skill) {
  if (!skillDetail || !skill) {
    return;
  }

  const localUrl = skill.local_url
    ? `<div class="detail-section"><h4>Local URL</h4><p><a href="${escapeHtml(skill.local_url)}" rel="noreferrer">${escapeHtml(skill.local_url)}</a></p></div>`
    : "";
  skillDetail.innerHTML = `
    <div class="detail-heading">
      <div>
        <p class="eyebrow">Skill Detail</p>
        <h3>${escapeHtml(skill.display_name)}</h3>
      </div>
      <span class="status ${escapeHtml(skill.status)}">${escapeHtml(skill.status)}</span>
    </div>
    <p>${escapeHtml(skill.purpose)}</p>
    <dl class="detail-grid">
      <div><dt>Category</dt><dd>${escapeHtml(skill.category)}</dd></div>
      <div><dt>App path</dt><dd>${escapeHtml(skill.app_path || "Not assigned yet")}</dd></div>
      <div><dt>Safe next action</dt><dd>${escapeHtml(skill.safe_next_action)}</dd></div>
    </dl>
    <div class="detail-section">
      <h4>Commands</h4>
      <p class="muted">Display-only. Copying a command only places text on the clipboard; Jarvis Console never runs it.</p>
      <div class="command-list">${commandMarkup(skill.commands, { copyable: true })}</div>
    </div>
    ${localUrl}
    <div class="detail-section"><h4>Docs / Guides</h4>${listMarkup(skill.docs, "No docs registered.")}</div>
    <div class="detail-section"><h4>Smoke Tests</h4>${listMarkup(skill.tests, "No tests registered.")}</div>
    <div class="detail-section"><h4>Examples / Artifacts</h4>${listMarkup(skill.examples, "No examples registered.")}</div>
    <div class="detail-section"><h4>Safety Notes</h4>${listMarkup(skill.safety_notes, "No safety notes registered.")}</div>
    <div class="detail-section"><h4>Non-Goals</h4>${listMarkup(skill.non_goals, "No non-goals registered.")}</div>
  `;
}

async function loadSkillDetail(skillId) {
  try {
    const response = await fetch(`/api/skill?skill_id=${encodeURIComponent(skillId)}`);
    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.error || `Request failed: ${response.status}`);
    }
    renderSkillDetail(data.skill);
    statusText.textContent = `Showing read-only detail: ${data.skill.display_name}`;
  } catch (error) {
    if (skillDetail) {
      skillDetail.innerHTML = `<p class="safety-note">Skill detail failed: ${escapeHtml(error.message)}</p>`;
    }
    statusText.textContent = `Skill detail failed: ${error.message}`;
  }
}

function renderSkillDetails(skillId, prefix) {
  const skill = registrySkills.find((item) => item.skill_id === skillId);
  if (!skill) return;

  const title = document.getElementById(`${prefix}Title`);
  const description = document.getElementById(`${prefix}Description`);
  const details = document.getElementById(`${prefix}Details`);
  if (title) title.textContent = skill.display_name;
  if (description) description.textContent = skill.purpose;
  if (details) {
    const urlMarkup = skill.local_url
      ? `<div class="command-card"><span>Local URL after running it separately</span><a href="${escapeHtml(skill.local_url)}" rel="noreferrer">${escapeHtml(skill.local_url)}</a></div>`
      : "";
    details.innerHTML = `
      <div class="command-card">
        ${commandMarkup(skill.commands)}
      </div>
      ${urlMarkup}
      <div class="detail-section"><h4>Docs / Guides</h4>${listMarkup(skill.docs, "No docs registered.")}</div>
      <div class="detail-section"><h4>Smoke Tests</h4>${listMarkup(skill.tests, "No tests registered.")}</div>
      <div class="detail-section"><h4>Safety Notes</h4>${listMarkup(skill.safety_notes, "No safety notes registered.")}</div>
    `;
  }
}

function renderRegistry(status) {
  registrySkills = status.skills || [];
  renderSkillCards(registrySkills);
  if (registrySkills.length) {
    renderSkillDetail(registrySkills[0]);
  }
  renderSkillDetails("hermes_manager", "hermes");
  renderSkillDetails("research_council", "research");
  renderSkillDetails("daily_ai_radar", "radar");
  renderSkillDetails("tasks_reports", "tasks");
  renderSkillDetails("memory_skills", "memory");
  renderSkillDetails("settings", "settings");
  statusText.textContent = `Ready. Loaded ${registrySkills.length} read-only registry skills.`;
}

async function loadRegistryStatus() {
  try {
    const response = await fetch("/api/status");
    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.error || `Request failed: ${response.status}`);
    }
    renderRegistry(data);
  } catch (error) {
    statusText.textContent = `Registry load failed: ${error.message}`;
  }
}

async function suggestSkill() {
  const message = commandInput.value.trim();
  if (!message) {
    statusText.textContent = "Enter a goal before asking for a suggestion.";
    return;
  }

  try {
    const response = await fetch("/api/suggest-skill", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.error || `Request failed: ${response.status}`);
    }
    renderSuggestion(data);
  } catch (error) {
    statusText.textContent = `Suggestion failed: ${error.message}`;
  }
}

async function copyCommand(command) {
  try {
    await navigator.clipboard.writeText(command);
    statusText.textContent = "Command copied. Jarvis Console did not run it.";
  } catch (error) {
    statusText.textContent = `Copy failed: ${error.message}`;
  }
}

tabs.forEach((button) => {
  button.addEventListener("click", () => activateTab(button.dataset.tab));
});

suggestButton.addEventListener("click", suggestSkill);

commandInput.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    suggestSkill();
  }
});

skillGrid.addEventListener("click", (event) => {
  const card = event.target.closest("[data-skill-id]");
  if (!card) {
    return;
  }
  loadSkillDetail(card.dataset.skillId);
});

document.addEventListener("click", (event) => {
  const button = event.target.closest(".copy-command");
  if (!button) {
    return;
  }
  copyCommand(button.dataset.command || "");
});

loadRegistryStatus();

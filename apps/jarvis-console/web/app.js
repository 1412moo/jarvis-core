const tabs = Array.from(document.querySelectorAll(".tab-button"));
const panels = Array.from(document.querySelectorAll(".tab-panel"));

const commandInput = document.getElementById("commandInput");
const suggestButton = document.getElementById("suggestButton");
const suggestionBox = document.getElementById("suggestionBox");
const statusText = document.getElementById("statusText");
const nextActionText = document.getElementById("nextActionText");
const skillGrid = document.getElementById("skillGrid");

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

function commandMarkup(commands) {
  if (!commands) {
    return "<p class=\"muted\">No command. Choose manually or refine the request.</p>";
  }

  const gitBash = commands.git_bash || "";
  const powershell = commands.powershell || "";
  if (!gitBash && !powershell) {
    return "<p class=\"muted\">No command yet. This skill is a proposal or placeholder.</p>";
  }

  const parts = [];
  if (gitBash) {
    parts.push(`<span class="command-label">Git Bash</span><code>${escapeHtml(gitBash)}</code>`);
  }
  if (powershell) {
    parts.push(`<span class="command-label">PowerShell</span><code>${escapeHtml(powershell)}</code>`);
  }
  return parts.join("");
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
      <article class="skill-card" data-skill="${escapeHtml(skill.skill_id)}">
        <span class="status ${escapeHtml(skill.status)}">${escapeHtml(skill.status)}</span>
        <h3>${escapeHtml(skill.display_name)}</h3>
        <p>${escapeHtml(skill.short_description || skill.purpose)}</p>
        <div class="command-list">${commandMarkup(skill.commands)}</div>
        <strong>Does not auto-run from Jarvis Console.</strong>
      </article>
    `)
    .join("");
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
    const safetyMarkup = (skill.safety_notes || [])
      .map((note) => `<li>${escapeHtml(note)}</li>`)
      .join("");
    details.innerHTML = `
      <div class="command-card">
        ${commandMarkup(skill.commands)}
      </div>
      ${urlMarkup}
      <ul class="metadata-list">${safetyMarkup}</ul>
    `;
  }
}

function renderRegistry(status) {
  registrySkills = status.skills || [];
  renderSkillCards(registrySkills);
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

tabs.forEach((button) => {
  button.addEventListener("click", () => activateTab(button.dataset.tab));
});

suggestButton.addEventListener("click", suggestSkill);

commandInput.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    suggestSkill();
  }
});

loadRegistryStatus();

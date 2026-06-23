const tabs = Array.from(document.querySelectorAll(".tab-button"));
const panels = Array.from(document.querySelectorAll(".tab-panel"));

const commandInput = document.getElementById("commandInput");
const suggestButton = document.getElementById("suggestButton");
const suggestionBox = document.getElementById("suggestionBox");
const statusText = document.getElementById("statusText");
const nextActionText = document.getElementById("nextActionText");

function activateTab(tabId) {
  tabs.forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === tabId);
  });
  panels.forEach((panel) => {
    panel.classList.toggle("hidden", panel.id !== `tab-${tabId}`);
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderSuggestion(data) {
  const commands = data.commands || [];
  const commandMarkup = commands.length
    ? commands.map((command) => `<code>${escapeHtml(command)}</code>`).join("")
    : "<p class=\"muted\">No command. Choose manually or refine the request.</p>";

  suggestionBox.innerHTML = `
    <div class="suggestion-header">
      <span class="status available">${escapeHtml(data.recommended_skill)}</span>
      <h3>${escapeHtml(data.display_name || data.recommended_skill)}</h3>
    </div>
    <p><strong>Why:</strong> ${escapeHtml(data.reason)}</p>
    <p><strong>Suggested next action:</strong> ${escapeHtml(data.suggested_next_action)}</p>
    <div class="command-list">${commandMarkup}</div>
    <p class="safety-note">This is only a recommendation. Jarvis Console does not run this skill.</p>
  `;
  statusText.textContent = `Recommended skill: ${data.display_name || data.recommended_skill}`;
  nextActionText.textContent = data.suggested_next_action || "Choose manually.";
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

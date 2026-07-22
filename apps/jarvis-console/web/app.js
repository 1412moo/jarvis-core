const tabs = document.querySelectorAll(".tab-button");
const panels = document.querySelectorAll(".tab-panel");
const commandInput = document.getElementById("commandInput");
const suggestButton = document.getElementById("suggestButton");
const suggestionBox = document.getElementById("suggestionBox");
const statusText = document.getElementById("statusText");
const nextActionText = document.getElementById("nextActionText");
const skillGrid = document.getElementById("skillGrid");
const skillDetail = document.getElementById("skillDetail");
const tasksDetails = document.getElementById("tasksDetails");
const refreshOverviewButton = document.getElementById("refreshOverviewButton");
const historyDetails = document.getElementById("historyDetails");
const refreshHistoryButton = document.getElementById("refreshHistoryButton");
const memoryPanel = document.getElementById("memoryPanel");
const refreshMemoryButton = document.getElementById("refreshMemoryButton");
const voiceTranscriptInput = document.getElementById("voiceTranscriptInput");
const prepareVoiceButton = document.getElementById("prepareVoiceButton");
const pasteVoiceButton = document.getElementById("pasteVoiceButton");
const clearVoiceButton = document.getElementById("clearVoiceButton");
const voiceResultBox = document.getElementById("voiceResultBox");
const codexReviewItemId = document.getElementById("codexReviewItemId");
const codexReviewQueueInput = document.getElementById("codexReviewQueueInput");
const loadCodexReviewButton = document.getElementById("loadCodexReviewButton");
const codexReviewResult = document.getElementById("codexReviewResult");

let registrySkills = [];
let selectedSkillId = "";
let recommendedSkillId = "";
let registryLoadPromise = null;
let memorySkillsData = null;
let lastVoiceCandidateData = null;
const LOCAL_URL_PREFIX = "http:" + "//127.0.0.1";
const LOCAL_URL_PROTOCOL = "http:";
const LOCAL_URL_HOSTNAME = "127.0.0.1";

function activateTab(tabId) {
  tabs.forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === tabId);
  });
  panels.forEach((panel) => {
    panel.classList.toggle("hidden", panel.id !== `tab-${tabId}`);
  });
  if (tabId === "skills" && recommendedSkillId) {
    loadSkillDetail(recommendedSkillId);
  }
  if (tabId === "tasks") {
    loadOverview();
  }
  if (tabId === "history") {
    loadHistory();
  }
  if (tabId === "memory" && !memorySkillsData) {
    loadMemorySkills();
  }
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function truncateText(value, maxChars) {
  const text = String(value || "").trim();
  if (text.length <= maxChars) {
    return text;
  }
  return `${text.slice(0, Math.max(0, maxChars - 1)).trim()}...`;
}

function listMarkup(items, emptyText) {
  if (!items || !items.length) {
    return `<p class="muted">${escapeHtml(emptyText)}</p>`;
  }
  return `<ul class="metadata-list">${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}

function renderCodexReview(data) {
  if (!codexReviewResult) {
    return;
  }
  const project = data.project || {};
  const review = data.review || {};
  const safety = data.safety || {};
  codexReviewResult.innerHTML = `
    <article class="overview-card codex-review-card">
      <div class="overview-section-heading">
        <div>
          <p class="eyebrow">Fresh local evidence</p>
          <h3>${escapeHtml(project.display_name || project.project_id || "Codex work package")}</h3>
        </div>
        <div class="overview-badges">
          <span class="overview-badge read-only">Read-only</span>
          <span class="overview-badge">${escapeHtml(review.next_action || "REVIEW_REQUEST")}</span>
        </div>
      </div>
      <dl class="overview-facts">
        <div><dt>Repository</dt><dd>${escapeHtml(project.repo_name || "local repo")}</dd></div>
        <div><dt>Branch</dt><dd>${escapeHtml(project.branch || "unknown")}</dd></div>
        <div><dt>HEAD</dt><dd><code>${escapeHtml(project.head || "unknown")}</code></dd></div>
        <div><dt>Item</dt><dd>${escapeHtml(review.item_id || "unknown")}</dd></div>
      </dl>
      <section class="codex-review-summary">
        <h4>Work summary</h4>
        <p><strong>Goal:</strong> ${escapeHtml(review.current_goal || "Not supplied")}</p>
        <p><strong>Task:</strong> ${escapeHtml(review.current_task || "Not supplied")}</p>
        <p><strong>Last prompt summary:</strong> ${escapeHtml(review.last_prompt_summary || "Not supplied")}</p>
        <p><strong>Last result summary:</strong> ${escapeHtml(review.last_result_summary || "Not supplied")}</p>
        <p><strong>Working tree:</strong> <code class="codex-review-status">${escapeHtml(review.working_tree_status || "clean")}</code></p>
      </section>
      <div class="codex-review-columns">
        <section>
          <h4>Changed files</h4>
          ${listMarkup(review.files_touched, "No changed files reported.")}
        </section>
        <section>
          <h4>Approved targets</h4>
          ${listMarkup(review.target_files, "No target files reported.")}
        </section>
        <section>
          <h4>Validation commands</h4>
          ${listMarkup(review.validation_commands, "No validation commands reported.")}
        </section>
      </div>
      <section>
        <h4>Safety boundary</h4>
        <dl class="codex-review-safety-grid">
          <div><dt>Fresh evidence</dt><dd>${safety.fresh_local_evidence ? "Verified" : "Not verified"}</dd></div>
          <div><dt>Review approval</dt><dd>${safety.human_approval_granted ? "Granted" : "Not granted"}</dd></div>
          <div><dt>Commit</dt><dd>${safety.commit_allowed ? "Allowed" : "Disabled"}</dd></div>
          <div><dt>Push</dt><dd>${safety.push_allowed ? "Allowed" : "Disabled"}</dd></div>
          <div><dt>Prompt rendered</dt><dd>${safety.prompt_rendered ? "Yes" : "No"}</dd></div>
          <div><dt>Command executed</dt><dd>${safety.command_executed ? "Yes" : "No"}</dd></div>
        </dl>
      </section>
      <section>
        <h4>Review notes</h4>
        ${listMarkup(data.notes, "No review notes reported.")}
      </section>
    </article>
  `;
  statusText.textContent = "Fresh Codex work package loaded for read-only review.";
  nextActionText.textContent = "Inspect the work summary and validation evidence. No approval or action was created.";
}

function renderCodexReviewFailure(data) {
  if (!codexReviewResult) {
    return;
  }
  const reasons = data.blocking_reasons || (data.detail ? [data.detail] : []);
  codexReviewResult.innerHTML = `
    <article class="overview-card codex-review-card blocked">
      <div class="overview-section-heading">
        <div>
          <p class="eyebrow">Review unavailable</p>
          <h3>Fresh safety checks did not produce a review session</h3>
        </div>
        <span class="overview-badge">Blocked</span>
      </div>
      ${listMarkup(reasons, "The review handoff was rejected.")}
      <p class="safety-note">Nothing was saved, approved, rendered, or executed.</p>
    </article>
  `;
  statusText.textContent = "Codex review remained blocked.";
  nextActionText.textContent = "Correct the Hermes handoff or working-tree mismatch, then request a new read-only review.";
}

async function loadCodexReview() {
  if (!codexReviewQueueInput || !codexReviewItemId || !codexReviewResult) {
    return;
  }
  const itemId = codexReviewItemId.value.trim();
  let queue;
  try {
    queue = JSON.parse(codexReviewQueueInput.value);
  } catch (error) {
    renderCodexReviewFailure({ detail: "Queue snapshot must be valid JSON." });
    return;
  }
  codexReviewResult.innerHTML = "<p class=\"muted\">Rechecking bounded local evidence. Nothing is being saved...</p>";
  try {
    const response = await fetch("/api/codex-review/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ queue, item_id: itemId }),
    });
    const data = await response.json();
    if (!response.ok || !data.ok) {
      renderCodexReviewFailure(data);
      return;
    }
    renderCodexReview(data);
  } catch (error) {
    renderCodexReviewFailure({ detail: error.message });
  }
}

function copyCommandLabel(label) {
  const labels = {
    "Git Bash": "Copy Git Bash",
    PowerShell: "Copy PowerShell",
  };
  return labels[label] || `Copy ${label}`;
}

function localOnlyUrl(value) {
  const url = String(value || "").trim();
  try {
    const parsed = new URL(url);
    if (parsed.protocol === LOCAL_URL_PROTOCOL && parsed.hostname === LOCAL_URL_HOSTNAME) {
      return url.startsWith(LOCAL_URL_PREFIX) ? url : "";
    }
  } catch (_error) {
    return "";
  }
  return "";
}

function skillById(skillId) {
  return registrySkills.find((item) => item.skill_id === skillId);
}

function commandRow(label, command, copyable) {
  if (!command) {
    return "";
  }
  const copyLabel = copyCommandLabel(label);
  const copyButton = copyable
    ? `<button class="copy-command" type="button" data-command="${escapeHtml(command)}" aria-label="${escapeHtml(copyLabel)}">${escapeHtml(copyLabel)}</button>`
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

function handoffStepsForSkill(skill, localUrl) {
  const registeredSteps = Array.isArray(skill?.handoff_steps)
    ? skill.handoff_steps.filter((step) => String(step || "").trim())
    : [];
  if (registeredSteps.length) {
    return registeredSteps;
  }
  return [
    "Copy Git Bash or PowerShell command.",
    "Run it in your terminal.",
    localUrl ? "Open the local URL after the server starts." : "Follow the copied command output.",
  ];
}

function copyNextActionForHandoff(handoffSteps, localUrl) {
  if (localUrl) {
    return "Run it in your terminal, then open the local URL.";
  }
  const thirdStep = handoffSteps[2] || "follow the copied command output.";
  return `Run it in your terminal, then ${thirdStep.charAt(0).toLowerCase()}${thirdStep.slice(1)}`;
}

function actionGuideMarkup(items) {
  if (!items || !items.length) {
    return "<p class=\"muted\">No action guide registered.</p>";
  }
  return `<ol class="action-guide">${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ol>`;
}

function suggestedActionPanel(data, skill) {
  const commands = data.commands || skill?.commands || {};
  const localUrl = localOnlyUrl(skill?.local_url);
  const gitBash = commands.git_bash || "";
  const powershell = commands.powershell || "";
  const handoffSteps = handoffStepsForSkill(skill, localUrl);
  const copyNextAction = copyNextActionForHandoff(handoffSteps, localUrl);
  const registeredSafetyNotes = Array.isArray(skill?.safety_notes)
    ? skill.safety_notes.filter((note) => String(note || "").trim())
    : [];
  const localUrlButton = localUrl
    ? `<button class="secondary-action open-local-url" type="button" data-local-url="${escapeHtml(localUrl)}">Open Local URL</button>`
    : "";
  const localUrlMarkup = localUrl
    ? `
      <div class="suggestion-url">
        <span>Local URL</span>
        <code>${escapeHtml(localUrl)}</code>
        <p class="muted">This only opens the URL. It does not start the server. Run the command first if the page does not load.</p>
      </div>
    `
    : "";

  return `
    <section class="suggestion-action-panel" aria-label="Suggested skill action panel">
      <h4>Suggested Skill Action Panel</h4>
      <p><strong>Recommended skill:</strong> ${escapeHtml(data.display_name || data.recommended_skill)}</p>
      <p><strong>Why this skill was recommended:</strong> ${escapeHtml(data.reason)}</p>
      <p><strong>Next action:</strong> ${escapeHtml(data.suggested_next_action)}</p>
      <div class="handoff-hint" aria-label="Next handoff">
        <strong>Next handoff</strong>
        <ol>
          ${handoffSteps.map((step) => `<li>${escapeHtml(step)}</li>`).join("")}
        </ol>
      </div>
      <div class="command-list">${commandMarkup(commands)}</div>
      ${localUrlMarkup}
      <div class="suggestion-actions">
        ${gitBash ? `<button class="copy-command" type="button" data-command="${escapeHtml(gitBash)}" data-copy-next-action="${escapeHtml(copyNextAction)}" aria-label="Copy Git Bash">Copy Git Bash</button>` : ""}
        ${powershell ? `<button class="copy-command" type="button" data-command="${escapeHtml(powershell)}" data-copy-next-action="${escapeHtml(copyNextAction)}" aria-label="Copy PowerShell">Copy PowerShell</button>` : ""}
        ${localUrlButton}
        <button class="secondary-action open-skill-details" type="button" data-skill-id="${escapeHtml(data.recommended_skill)}">Open Skill Details</button>
      </div>
      <ul class="safety-list">
        <li>Jarvis Console does not run this skill.</li>
        <li>Commands are copy-only.</li>
        <li>Opening a URL does not start the server.</li>
        ${registeredSafetyNotes.map((note) => `<li>${escapeHtml(note)}</li>`).join("")}
      </ul>
    </section>
  `;
}

function renderSuggestion(data) {
  const skillId = data.recommended_skill || "";
  const hasRecommendedSkill = skillId && skillId !== "unknown";
  recommendedSkillId = hasRecommendedSkill ? skillId : "";
  const skill = hasRecommendedSkill ? skillById(skillId) : null;
  const actionPanel = hasRecommendedSkill
    ? suggestedActionPanel(data, skill)
    : "<p class=\"muted\">Choose a skill manually from the sidebar.</p>";
  suggestionBox.innerHTML = `
    <div class="suggestion-header">
      <span class="status available">${escapeHtml(skillId)}</span>
      <h3>${escapeHtml(data.display_name || skillId)}</h3>
    </div>
    <p><strong>Why:</strong> ${escapeHtml(data.reason)}</p>
    <p><strong>Suggested next action:</strong> ${escapeHtml(data.suggested_next_action)}</p>
    ${actionPanel}
    <p class="safety-note">This is only a recommendation. Jarvis Console does not run this skill.</p>
  `;
  statusText.textContent = `Recommended skill: ${data.display_name || skillId}`;
  nextActionText.textContent = data.suggested_next_action || "Choose manually.";
}

function voiceSkillActions(data, skill) {
  const candidate = data.task_candidate || {};
  const skillId = candidate.suggested_skill || "unknown";
  const knownSkill = skillId && skillId !== "unknown" && skill;
  if (!knownSkill) {
    return "<p class=\"muted\">Choose a skill manually from the sidebar.</p>";
  }

  const commands = data.commands || skill.commands || {};
  const gitBash = commands.git_bash || "";
  const powershell = commands.powershell || "";
  const localUrl = localOnlyUrl(skill.local_url);
  const localUrlButton = localUrl
    ? `<button class="secondary-action open-local-url" type="button" data-local-url="${escapeHtml(localUrl)}">Open Local URL</button>`
    : "";
  const copyNextAction = "Review the task candidate, then use the copied command manually.";

  if (skillId === "memory_skills") {
    return `
      <div class="voice-handoff-card">
        <h4>Memory / Skills proposal</h4>
        <p class="muted">Voice Inbox can suggest Memory / Skills, but it does not save this candidate automatically.</p>
        <div class="suggestion-actions">
          <button class="secondary-action preview-voice-memory-candidate" type="button">Preview Local Candidate</button>
          <button class="secondary-action open-memory-skills" type="button">Open Memory / Skills</button>
          <button class="secondary-action open-skill-details" type="button" data-skill-id="${escapeHtml(skillId)}">Open Skill Details</button>
        </div>
        <ul class="safety-list">
          <li>Manual review only.</li>
          <li>No persistence, no runtime write, and no automatic skill creation.</li>
        </ul>
      </div>
    `;
  }

  return `
    <div class="voice-handoff-card">
      <h4>Handoff options</h4>
      <div class="command-list">${commandMarkup(commands)}</div>
      ${localUrl ? `<p class="muted">Open Local URL only opens <code>${escapeHtml(localUrl)}</code>. It does not start the server.</p>` : ""}
      <div class="suggestion-actions">
        ${gitBash ? `<button class="copy-command" type="button" data-command="${escapeHtml(gitBash)}" data-copy-next-action="${escapeHtml(copyNextAction)}" aria-label="Copy Git Bash">Copy Git Bash</button>` : ""}
        ${powershell ? `<button class="copy-command" type="button" data-command="${escapeHtml(powershell)}" data-copy-next-action="${escapeHtml(copyNextAction)}" aria-label="Copy PowerShell">Copy PowerShell</button>` : ""}
        ${localUrlButton}
        <button class="secondary-action open-skill-details" type="button" data-skill-id="${escapeHtml(skillId)}">Open Skill Details</button>
      </div>
    </div>
  `;
}

function jarvisCommandFromCleaned(cleanedTranscript) {
  const cleaned = String(cleanedTranscript || "").trim();
  if (/^(jarvis|자비스)(,|\s)/i.test(cleaned)) {
    return cleaned;
  }
  return `Jarvis, ${cleaned}`;
}

function voiceUnknownGuidance(skillId) {
  if (skillId !== "unknown") {
    return "";
  }
  return `
    <div class="voice-unknown-guidance">
      <strong>No matching skill yet.</strong>
      <ul>
        <li>Idea validation -> Research Council</li>
        <li>Codex/repo work -> Hermes Manager</li>
        <li>AI tech scouting -> Daily AI Radar</li>
        <li>Repeated workflow -> Memory / Skills</li>
      </ul>
    </div>
  `;
}

function renderVoiceCandidate(data) {
  if (!voiceResultBox) {
    return;
  }
  const candidate = data.task_candidate || {};
  const skillId = candidate.suggested_skill || "unknown";
  const skill = skillId !== "unknown" ? skillById(skillId) : null;
  const rawPreview = truncateText(data.raw_transcript || "", 360);
  const cleaned = data.cleaned_transcript || "";
  const jarvisCommand = jarvisCommandFromCleaned(cleaned);
  const matchedKeywords = candidate.matched_keywords || [];
  lastVoiceCandidateData = data;
  voiceResultBox.innerHTML = `
    <section class="voice-candidate-card" aria-label="Voice Inbox task candidate">
      <div class="overview-section-heading">
        <div>
          <p class="eyebrow">Task Candidate</p>
          <h3>${escapeHtml(candidate.title || "Untitled candidate")}</h3>
        </div>
        <span class="overview-badge read-only">Needs confirmation: ${candidate.needs_confirmation ? "Yes" : "No"}</span>
      </div>
      <div class="voice-preview-grid">
        <div>
          <strong>Raw transcript preview</strong>
          <p>${escapeHtml(rawPreview)}</p>
        </div>
        <div>
          <strong>Cleaned transcript</strong>
          <p>${escapeHtml(cleaned)}</p>
        </div>
      </div>
      <dl class="voice-candidate-facts">
        <div><dt>Suggested skill</dt><dd>${escapeHtml(skill?.display_name || data.display_name || skillId)}</dd></div>
        <div><dt>Confidence</dt><dd>${escapeHtml(candidate.confidence || "low")}</dd></div>
        <div><dt>Matched keywords</dt><dd>${escapeHtml(matchedKeywords.length ? matchedKeywords.join(", ") : "none")}</dd></div>
      </dl>
      <p><strong>Summary:</strong> ${escapeHtml(candidate.summary || "")}</p>
      <p><strong>Reason:</strong> ${escapeHtml(candidate.reason || "")}</p>
      <p><strong>Next action:</strong> ${escapeHtml(candidate.next_action || "")}</p>
      ${voiceUnknownGuidance(skillId)}
      <div class="suggestion-actions">
        <button class="copy-text" type="button" data-copy-text="${escapeHtml(cleaned)}" aria-label="Copy Cleaned Task">Copy Cleaned Task</button>
        <button class="copy-text" type="button" data-copy-text="${escapeHtml(jarvisCommand)}" aria-label="Copy As Jarvis Command">Copy As Jarvis Command</button>
      </div>
      ${voiceSkillActions(data, skill)}
      <ul class="safety-list">
        ${(data.safety_notes || []).map((note) => `<li>${escapeHtml(note)}</li>`).join("")}
        <li>Transcript text is not saved by default.</li>
        <li>No microphone, recording, STT, TTS, Codex, ChatGPT, Hermes, git, or external tool is called.</li>
      </ul>
    </section>
  `;
  statusText.textContent = `Voice Inbox candidate prepared: ${skill?.display_name || data.display_name || skillId}`;
  nextActionText.textContent = candidate.next_action || "Review the task candidate.";
}

function renderSkillCards(skills) {
  skillGrid.innerHTML = skills
    .map((skill) => {
      const selected = skill.skill_id === selectedSkillId;
      return `
      <button class="skill-card ${selected ? "selected-skill" : ""}" type="button" data-skill-id="${escapeHtml(skill.skill_id)}" aria-pressed="${selected ? "true" : "false"}">
        <span class="status ${escapeHtml(skill.status)}">${escapeHtml(skill.status)}</span>
        ${selected ? "<span class=\"selected-label\">Selected</span>" : ""}
        <span class="skill-card-title">${escapeHtml(skill.display_name)}</span>
        <span class="skill-card-description">${escapeHtml(skill.short_description || skill.purpose)}</span>
        <strong>View read-only details</strong>
      </button>
    `;
    })
    .join("");
}

function renderSkillDetail(skill) {
  if (!skillDetail || !skill) {
    return;
  }

  selectedSkillId = skill.skill_id;
  renderSkillCards(registrySkills);

  const isPlanned = skill.status === "planned";
  const localUrl = skill.local_url
    ? `<p class="local-url"><strong>Local URL:</strong> <a href="${escapeHtml(skill.local_url)}" rel="noreferrer">${escapeHtml(skill.local_url)}</a></p>`
    : "";
  const commandIntro = isPlanned
    ? "No command yet. This planned skill is not runnable from Jarvis Console."
    : "Copy only; Jarvis does not run this command.";
  const docsTitle = isPlanned ? "Reference docs" : "Docs / Guides";
  const limitationTitle = isPlanned ? "Current limitation" : "Non-goals";
  const evidenceMarkup = isPlanned
    ? ""
    : `
      <div class="guide-subsection">
        <h5>Smoke tests</h5>
        ${listMarkup(skill.tests, "No tests registered.")}
      </div>
      <div class="guide-subsection">
        <h5>Examples / Artifacts</h5>
        ${listMarkup(skill.examples, "No examples registered.")}
      </div>
    `;
  skillDetail.innerHTML = `
    <div class="detail-heading">
      <div>
        <p class="eyebrow">${isPlanned ? "Planned Skill" : "Skill Detail"}</p>
        <h3>${escapeHtml(skill.display_name)}</h3>
        ${localUrl}
      </div>
      <span class="status ${escapeHtml(skill.status)}">${escapeHtml(skill.status)}</span>
    </div>
    <section class="usage-card">
      <h4>What it does</h4>
      <p>${escapeHtml(skill.purpose)}</p>
    </section>
    <section class="usage-card">
      <h4>When to use</h4>
      <p>${escapeHtml(skill.when_to_use)}</p>
    </section>
    <section class="usage-card primary-action-card">
      <h4>Next action</h4>
      <strong>${escapeHtml(skill.primary_next_action_label)}</strong>
      <p>${escapeHtml(skill.primary_next_action_description)}</p>
      ${actionGuideMarkup(skill.action_guide)}
    </section>
    <section class="usage-card">
      <h4>Commands</h4>
      <p class="muted">${escapeHtml(commandIntro)}</p>
      <div class="command-list">${commandMarkup(skill.commands, { copyable: true })}</div>
    </section>
    <section class="usage-card"><h4>${docsTitle}</h4>${listMarkup(skill.docs, "No docs registered.")}${evidenceMarkup}</section>
    <section class="usage-card safety-card"><h4>Safety notes</h4>${listMarkup(skill.safety_notes, "No safety notes registered.")}</section>
    <section class="usage-card"><h4>${limitationTitle}</h4>${listMarkup(skill.non_goals, "No non-goals registered.")}</section>
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

function formatBytes(value) {
  const bytes = Number(value || 0);
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${Math.round(bytes / 1024)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatModified(value) {
  const date = new Date(Number(value || 0) * 1000);
  if (Number.isNaN(date.getTime())) {
    return "unknown time";
  }
  return date.toLocaleString();
}

function sourceAreaLabel(item) {
  if (item?.source_area_label) {
    return item.source_area_label;
  }
  const labels = {
    docs: "Docs",
    research_council: "Research Council",
    daily_ai_radar: "Daily AI Radar",
    hermes_manager: "Hermes Manager",
    jarvis_console: "Jarvis Console",
    tasks: "Tasks",
    reports: "Reports",
    checkpoints: "Checkpoints",
    unknown: "Unknown",
  };
  return labels[item?.source_area] || item?.directory_label || "Local file";
}

function itemTypeLabel(item) {
  const value = String(item?.item_type || "doc").replaceAll("_", " ");
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function overviewItemsMarkup(items, emptyText) {
  if (!items || !items.length) {
    return `<p class="placeholder">${escapeHtml(emptyText)}</p>`;
  }
  return `
    <div class="overview-list">
      ${items
        .map(
          (item) => `
        <article class="overview-item">
          <div>
            <strong>${escapeHtml(item.title || item.name)}</strong>
            <span>${escapeHtml(item.directory_label || "Local file")} · ${escapeHtml(formatModified(item.modified))} · ${escapeHtml(formatBytes(item.size_bytes))}</span>
          </div>
          <code>${escapeHtml(item.path)}</code>
        </article>
      `,
        )
        .join("")}
    </div>
  `;
}

function normalizedOverviewItemsMarkup(items, emptyText) {
  if (!items || !items.length) {
    return `<p class="placeholder">${escapeHtml(emptyText)}</p>`;
  }
  return `
    <div class="overview-list">
      ${items
        .map(
          (item) => `
        <article class="overview-item normalized-overview-item">
          <div class="overview-item-heading">
            <strong>${escapeHtml(item.title || item.name)}</strong>
            <div class="overview-badges">
              <span class="overview-badge type-${escapeHtml(item.item_type || "doc")}">${escapeHtml(itemTypeLabel(item))}</span>
              <span class="overview-badge source-area">${escapeHtml(sourceAreaLabel(item))}</span>
              <span class="overview-badge read-only">Read-only</span>
            </div>
          </div>
          ${item.summary ? `<p>${escapeHtml(item.summary)}</p>` : ""}
          <code>${escapeHtml(item.path)}</code>
          <span>${escapeHtml(formatModified(item.modified_time || item.modified))} | ${escapeHtml(formatBytes(item.size_bytes))}</span>
        </article>
      `,
        )
        .join("")}
    </div>
  `;
}

function memoryDraftPrompt(candidate) {
  const tags = (candidate.tags || []).join(", ") || "none";
  const safetyNotes = (candidate.safety_notes || []).join("; ") || "No candidate safety notes registered.";
  return [
    "Task: Prepare a Memory / Skills candidate draft for human review.",
    "",
    "Context:",
    "- This is a proposal copied from Jarvis Console Memory / Skills.",
    "- The user is manually pasting this into Hermes/Codex for review.",
    "- Treat it as a candidate, not an approved skill.",
    "- Do not create, install, run, or register a skill automatically.",
    "",
    "Candidate:",
    `- Title: ${candidate.title || "Untitled candidate"}`,
    `- Type: ${candidate.candidate_type || "candidate"}`,
    `- Source: ${candidate.source || "sample"}`,
    `- Confidence: ${candidate.confidence || "low"}`,
    `- Cleaned text: ${candidate.cleaned_text || ""}`,
    `- Suggested next action: ${candidate.next_action || "Review manually."}`,
    `- Tags: ${tags}`,
    `- Safety notes: ${safetyNotes}`,
    "",
    "Safety boundaries:",
    "- Local-only.",
    "- Human-approved.",
    "- No autonomous execution.",
    "- No automatic code modification.",
    "- No automatic repo/file write.",
    "- No automatic git add/commit/push.",
    "- No external API/web/LLM calls.",
    "- No skill registry modification unless explicitly approved later.",
    "",
    "Requested output:",
    "1. Clarify the candidate into a small skill draft.",
    "2. Identify risks and assumptions.",
    "3. Propose the smallest safe first implementation unit.",
    "4. List files that might change if later approved.",
    "5. Do not implement yet.",
    "6. Do not commit or push.",
    "Do not create, install, or run a skill automatically.",
  ].join("\n");
}

function memoryPreviewRequest(candidate, sourceOverride = "") {
  return {
    source: sourceOverride || candidate.source || "manual",
    title: candidate.title || "Memory / Skills candidate preview",
    cleaned_text: candidate.cleaned_text || candidate.summary || "",
    original_text_preview: truncateText(candidate.original_text_preview || candidate.cleaned_text || "", 240),
    candidate_type: candidate.candidate_type || "unknown",
    confidence: candidate.confidence || "low",
    tags: candidate.tags || [],
    safety_notes: candidate.safety_notes || [],
  };
}

function memoryPreviewRequestFromVoice(data) {
  const candidate = data?.task_candidate || {};
  return {
    source: "voice_inbox",
    title: candidate.title || "Voice Inbox Memory / Skills candidate preview",
    cleaned_text: data?.cleaned_transcript || candidate.summary || "",
    original_text_preview: truncateText(data?.raw_transcript || "", 240),
    candidate_type: "repeated_workflow",
    confidence: candidate.confidence || "low",
    tags: ["voice_inbox", "memory_skills"],
    safety_notes: [
      "Preview only; Voice Inbox did not save this candidate.",
      "No persistence, no runtime write, and no automatic skill creation.",
    ],
  };
}

function findMemoryCandidate(candidateId) {
  const candidates = memorySkillsData?.candidates || [];
  return candidates.find((candidate) => candidate.id === candidateId) || null;
}

function renderMemoryCandidatePreview(data) {
  const result = document.getElementById("memoryPreviewResult");
  if (!result) {
    return;
  }
  const preview = data.candidate_preview || {};
  const tags = preview.tags || [];
  const safetyNotes = preview.safety_notes || [];
  const localSaveLabel = data.save_endpoint ? "Available" : "Not available in Phase 2B";
  result.innerHTML = `
    <article class="memory-preview-result-card">
      <div class="overview-section-heading">
        <div>
          <p class="eyebrow">Candidate preview</p>
          <h4>Review before saving</h4>
        </div>
        <div class="overview-badges">
          <span class="overview-badge read-only">Preview only</span>
          <span class="overview-badge">Not saved</span>
          <span class="overview-badge">No persistence</span>
          <span class="overview-badge">No runtime write</span>
        </div>
      </div>
      <p class="memory-preview-summary">This is only a preview of what could be saved later. Nothing has been saved.</p>
      <p class="memory-preview-summary">Local save is not available in Phase 2B. This is not an approved skill and will not run automatically.</p>

      <section class="memory-preview-main">
        <h5>${escapeHtml(preview.title || "Untitled candidate")}</h5>
        <dl class="overview-facts compact-facts">
          <div><dt>Type</dt><dd>${escapeHtml(preview.candidate_type || "unknown")}</dd></div>
          <div><dt>Source</dt><dd>${escapeHtml(preview.source || "manual")}</dd></div>
          <div><dt>Confidence</dt><dd>${escapeHtml(preview.confidence || "low")}</dd></div>
        </dl>
        <p><strong>Cleaned text:</strong> ${escapeHtml(preview.cleaned_text || "")}</p>
        <p><strong>Tags:</strong> ${escapeHtml(tags.length ? tags.join(", ") : "No tags")}</p>
      </section>

      <p class="safety-note"><strong>Privacy warning:</strong> ${escapeHtml(data.privacy_warning || preview.privacy_note || "")}</p>
      ${listMarkup(safetyNotes.concat(data.safety_notes || []), "No additional safety notes.")}

      <section class="memory-preview-technical">
        <h5>Technical details</h5>
        <dl class="overview-facts compact-facts">
          <div><dt>Phase</dt><dd>${escapeHtml(data.phase || "phase_2b_preview_only")}</dd></div>
          <div><dt>Status</dt><dd>${escapeHtml(preview.status || "preview_only")}</dd></div>
          <div><dt>User approval</dt><dd>${preview.user_approved_at ? escapeHtml(preview.user_approved_at) : "none"}</dd></div>
          <div><dt>Local save</dt><dd>${localSaveLabel}</dd></div>
        </dl>
        <p><strong>Original text preview:</strong> ${escapeHtml(preview.original_text_preview || "")}</p>
        <p><strong>Next step:</strong> ${escapeHtml(data.next_step || preview.next_action || "")}</p>
      </section>
    </article>
  `;
  statusText.textContent = "Preview-only Memory / Skills candidate prepared. Nothing was saved.";
  nextActionText.textContent = "Review the preview fields. Phase 2B has no persistence or local state write.";
}

async function previewMemoryCandidatePayload(payload) {
  const result = document.getElementById("memoryPreviewResult");
  if (result) {
    result.innerHTML = "<p class=\"muted\">Preparing preview only. Nothing is being saved...</p>";
  }
  try {
    const response = await fetch("/api/memory-skills/candidates/preview", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.error || `Request failed: ${response.status}`);
    }
    renderMemoryCandidatePreview(data);
  } catch (error) {
    if (result) {
      result.innerHTML = `<p class="safety-note">Preview failed: ${escapeHtml(error.message)}</p>`;
    }
    statusText.textContent = `Memory / Skills preview failed: ${error.message}`;
  }
}

async function previewVoiceMemoryCandidate() {
  if (!lastVoiceCandidateData || lastVoiceCandidateData.task_candidate?.suggested_skill !== "memory_skills") {
    statusText.textContent = "No Memory / Skills Voice Inbox candidate is ready to preview.";
    return;
  }
  if (!memorySkillsData) {
    await loadMemorySkills();
  }
  activateTab("memory");
  await previewMemoryCandidatePayload(memoryPreviewRequestFromVoice(lastVoiceCandidateData));
}

function memoryCandidateCards(candidates) {
  if (!candidates || !candidates.length) {
    return "<p class=\"placeholder\">No sample candidates registered.</p>";
  }
  return `
    <div class="memory-candidate-grid">
      ${candidates
        .map(
          (candidate) => `
        <article class="memory-candidate-card">
          <div class="overview-item-heading">
            <div>
              <strong>${escapeHtml(candidate.title || "Untitled candidate")}</strong>
              <span>${escapeHtml(candidate.candidate_type || "candidate")} · ${escapeHtml(candidate.source || "sample")}</span>
            </div>
            <div class="overview-badges">
              <span class="overview-badge read-only">Read-only sample</span>
              <span class="overview-badge">${escapeHtml(candidate.status || "candidate")}</span>
              <span class="overview-badge">Confidence: ${escapeHtml(candidate.confidence || "low")}</span>
            </div>
          </div>
          <p>${escapeHtml(candidate.cleaned_text || "")}</p>
          <p><strong>Next action:</strong> ${escapeHtml(candidate.next_action || "")}</p>
          <p><strong>Tags:</strong> ${escapeHtml((candidate.tags || []).join(", ") || "none")}</p>
          ${listMarkup(candidate.safety_notes, "No candidate safety notes registered.")}
          <div class="suggestion-actions">
            <button class="secondary-action memory-review-candidate" type="button" data-candidate-id="${escapeHtml(candidate.id || "")}">Review Candidate</button>
            <button class="secondary-action memory-preview-candidate" type="button" data-candidate-id="${escapeHtml(candidate.id || "")}">Preview Local Candidate</button>
            <button class="copy-text" type="button" data-copy-text="${escapeHtml(candidate.cleaned_text || "")}" data-manual-copy-label="Copy Candidate" aria-label="Copy Candidate">Copy Candidate</button>
            <button class="copy-text" type="button" data-copy-text="${escapeHtml(memoryDraftPrompt(candidate))}" data-manual-copy-label="Copy Skill Draft Prompt" aria-label="Copy Skill Draft Prompt">Copy Skill Draft Prompt</button>
            <button class="secondary-action open-skill-details" type="button" data-skill-id="${escapeHtml(candidate.suggested_skill_id || "memory_skills")}">Open Skill Details</button>
          </div>
          <p class="muted memory-handoff-note">Copy a proposal-only prompt for manual Hermes/Codex review. Paste it yourself when ready; Jarvis does not send or run it automatically. No automatic handoff, no skill creation, no commit.</p>
        </article>
      `,
        )
        .join("")}
    </div>
  `;
}

function renderMemorySkills(data) {
  if (!memoryPanel) {
    return;
  }
  memorySkillsData = data;
  memoryPanel.innerHTML = `
    <section class="overview-card memory-phase-card">
      <div class="overview-section-heading">
        <div>
          <p class="eyebrow">${escapeHtml(data.phase || "phase_2b_preview_only")}</p>
          <h3>${escapeHtml(data.title || "Memory / Skills")}</h3>
        </div>
        <div class="overview-badges">
          <span class="overview-badge read-only">Read-only sample</span>
          <span class="overview-badge">Preview only</span>
          <span class="overview-badge">Not saved</span>
        </div>
      </div>
      <p>${escapeHtml(data.description || "")}</p>
      <dl class="overview-facts">
        <div><dt>Mode</dt><dd>${escapeHtml(data.mode || "read-only")}</dd></div>
        <div><dt>Persistence</dt><dd>${data.no_persistence ? "None in Phase 2B" : "Not reported"}</dd></div>
        <div><dt>Runtime write</dt><dd>${data.runtime_write ? "Present" : "None"}</dd></div>
        <div><dt>Local save</dt><dd>${data.save_endpoint ? "Available" : "Not available in Phase 2B"}</dd></div>
        <div><dt>Preview endpoint</dt><dd>${data.preview_endpoint ? "Write-free POST" : "Not reported"}</dd></div>
      </dl>
      ${listMarkup(data.guidance, "No Memory / Skills guidance registered.")}
    </section>
    <section class="overview-card memory-preview-card">
      <div class="overview-section-heading">
        <div>
          <p class="eyebrow">Candidate Preview</p>
          <h3>Preview before any future local save</h3>
        </div>
        <div class="overview-badges">
          <span class="overview-badge read-only">Preview only</span>
          <span class="overview-badge">No persistence</span>
          <span class="overview-badge">No runtime write</span>
        </div>
      </div>
      <p class="muted">Use Preview Local Candidate to see the fields that would be reviewed later. This is not a local save, not an approved skill, and not an execution.</p>
      <div id="memoryPreviewResult" class="memory-preview-result" aria-live="polite">
        <p class="placeholder">No candidate preview prepared yet.</p>
      </div>
    </section>
    <section class="overview-card">
      <div class="overview-section-heading">
        <div>
          <p class="eyebrow">Sample Candidates</p>
          <h3>Repeated workflow proposals</h3>
        </div>
        <span class="overview-badge read-only">No saved user memory</span>
      </div>
      ${memoryCandidateCards(data.candidates || [])}
      <div id="memoryCopyFallback" class="manual-copy-fallback hidden" aria-live="polite">
        <h4>Manual copy fallback</h4>
        <p>Clipboard was not available. Copy the text below manually.</p>
        <label for="memoryCopyFallbackText">Copy-only payload</label>
        <textarea id="memoryCopyFallbackText" readonly></textarea>
        <p class="muted">No file was created. No action was executed.</p>
      </div>
    </section>
    <section class="overview-card">
      <div class="overview-section-heading">
        <div>
          <p class="eyebrow">Manual Actions</p>
          <h3>Copy-only handoff</h3>
        </div>
        <span class="overview-badge read-only">No state change</span>
      </div>
      <div class="overview-rule-grid">
        <div class="overview-skill-card"><h4>Allowed in Phase 1</h4>${listMarkup(data.allowed_actions, "No allowed actions registered.")}</div>
        <div class="overview-skill-card"><h4>Unavailable in Phase 1</h4>${listMarkup(data.unavailable_actions, "No unavailable actions registered.")}</div>
      </div>
    </section>
    <section class="overview-card safety-card">
      <h3>Safety Boundary</h3>
      ${listMarkup(data.safety_boundary, "No Memory / Skills safety notes registered.")}
    </section>
  `;
}

async function loadMemorySkills() {
  if (!memoryPanel) {
    return;
  }
  memoryPanel.innerHTML = "<p class=\"muted\">Loading read-only Memory / Skills samples...</p>";
  try {
    const response = await fetch("/api/memory-skills");
    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.error || `Request failed: ${response.status}`);
    }
    memorySkillsData = data;
    renderMemorySkills(data);
    statusText.textContent = "Read-only Memory / Skills samples refreshed.";
  } catch (error) {
    memoryPanel.innerHTML = `<p class="safety-note">Memory / Skills failed: ${escapeHtml(error.message)}</p>`;
    statusText.textContent = `Memory / Skills failed: ${error.message}`;
  }
}

function renderRepoStatus(repo) {
  const workingTree = repo?.working_tree_status || "unknown";
  return `
    <section class="overview-card repo-status-card">
      <h3>Current Repo Status</h3>
      <dl class="overview-facts">
        <div><dt>Branch</dt><dd>${escapeHtml(repo?.branch || "unknown")}</dd></div>
        <div><dt>HEAD</dt><dd>${escapeHtml(repo?.head_short || "unknown")}</dd></div>
        <div><dt>Working tree</dt><dd><code>${escapeHtml(workingTree)}</code></dd></div>
      </dl>
      <p class="muted">${escapeHtml(repo?.protected_path_note || "jarvis.bat remains protected.")}</p>
    </section>
  `;
}

function renderOverviewSkills(skills) {
  if (!skills || !skills.length) {
    return "<p class=\"placeholder\">No skill status loaded.</p>";
  }
  return `
    <div class="overview-skill-grid">
      ${skills
        .map(
          (skill) => `
        <article class="overview-skill-card">
          <span class="status ${escapeHtml(skill.status)}">${escapeHtml(skill.status)}</span>
          <h4>${escapeHtml(skill.display_name)}</h4>
          <p>${escapeHtml(skill.safe_next_action)}</p>
          ${normalizedOverviewItemsMarkup(skill.recent_items, "No recent local examples found.")}
        </article>
      `,
        )
        .join("")}
    </div>
  `;
}

function renderRecentGroups(groups) {
  if (!groups || !groups.length) {
    return `
      <section class="overview-card">
        <h3>Recent Items</h3>
        <p class="placeholder">No read-only recent item groups found yet.</p>
      </section>
    `;
  }
  return groups
    .map(
      (group) => `
    <section class="overview-card recent-group-card">
      <div class="overview-section-heading">
        <h3>${escapeHtml(group.title)}</h3>
        <span class="overview-badge read-only">Read-only metadata</span>
      </div>
      ${normalizedOverviewItemsMarkup(group.items, group.empty_text || "No recent items found yet.")}
    </section>
  `,
    )
    .join("");
}

function renderDiscoveryRules(discovery) {
  const directories = discovery?.safe_directories || [];
  return `
    <section class="overview-card">
      <h3>Read-only Discovery Rules</h3>
      <p class="muted">Jarvis Console lists metadata only from fixed safe directories. It does not edit, delete, generate, or execute files.</p>
      <div class="overview-rule-grid">
        <div>
          <strong>Limits</strong>
          <ul class="metadata-list">
            <li>Max ${escapeHtml(discovery?.max_items_per_directory || "")} items per directory</li>
            <li>Max ${escapeHtml(discovery?.max_total_items || "")} items total per discovery call</li>
            <li>Extensions: ${escapeHtml((discovery?.allowed_extensions || []).join(", "))}</li>
          </ul>
        </div>
        <div>
          <strong>Safe directories</strong>
          <ul class="metadata-list">
            ${directories
              .map((item) => `<li>${escapeHtml(item.path)} ${item.exists ? "" : "(missing)"}</li>`)
              .join("")}
          </ul>
        </div>
      </div>
    </section>
  `;
}

function renderOverview(data) {
  if (!tasksDetails) {
    return;
  }
  tasksDetails.innerHTML = `
    ${renderRepoStatus(data.repo)}
    <section class="overview-card">
      <h3>Skill Status</h3>
      ${renderOverviewSkills(data.skills)}
    </section>
    ${renderRecentGroups(data.recent_groups)}
    <section class="overview-card safety-card">
      <h3>Safety Notes</h3>
      ${listMarkup(data.notes, "No overview safety notes registered.")}
    </section>
    ${renderDiscoveryRules(data.discovery)}
  `;
}

function renderRecentCommits(commits) {
  if (!commits || !commits.length) {
    return "<p class=\"placeholder\">No recent commits found.</p>";
  }
  return `
    <div class="overview-list">
      ${commits
        .map(
          (commit) => `
        <article class="overview-item history-commit">
          <div class="overview-item-heading">
            <strong>${escapeHtml(commit.subject || "(no subject)")}</strong>
            <div class="overview-badges">
              <span class="overview-badge read-only">Read-only</span>
            </div>
          </div>
          <code class="history-commit-hash">${escapeHtml(commit.hash)}</code>
        </article>
      `,
        )
        .join("")}
    </div>
  `;
}

function renderHistoryDiscovery(discovery) {
  const directories = discovery?.safe_directories || [];
  return `
    <section class="overview-card">
      <h3>Read-only History Discovery</h3>
      <p class="muted">Jarvis Console lists commit and checkpoint metadata only. It does not create commits, checkpoints, reports, or files.</p>
      <div class="overview-rule-grid">
        <div>
          <strong>Limits</strong>
          <ul class="metadata-list">
            <li>Max ${escapeHtml(discovery?.max_commits || "")} commits</li>
            <li>Max ${escapeHtml(discovery?.max_items_per_directory || "")} items per directory</li>
            <li>Extensions: ${escapeHtml((discovery?.allowed_extensions || []).join(", "))}</li>
            <li>Name markers: ${escapeHtml((discovery?.name_markers || []).join(", "))}</li>
          </ul>
        </div>
        <div>
          <strong>Safe directories</strong>
          <ul class="metadata-list history-discovery-list">
            ${directories
              .map((item) => `<li>${escapeHtml(item.path)} ${item.exists ? "" : "(missing)"}</li>`)
              .join("")}
          </ul>
        </div>
      </div>
    </section>
  `;
}

function renderHistory(data) {
  if (!historyDetails) {
    return;
  }
  historyDetails.innerHTML = `
    ${renderRepoStatus(data.repo)}
    <section class="overview-card">
      <div class="overview-section-heading">
        <h3>Recent Commits</h3>
        <span class="overview-badge read-only">Read-only git log</span>
      </div>
      ${renderRecentCommits(data.recent_commits)}
    </section>
    <section class="overview-card">
      <div class="overview-section-heading">
        <h3>Checkpoint Docs</h3>
        <span class="overview-badge read-only">Read-only metadata</span>
      </div>
      ${normalizedOverviewItemsMarkup(data.checkpoint_docs, "No checkpoint docs found yet.")}
    </section>
    <section class="overview-card">
      <div class="overview-section-heading">
        <h3>Related Reports / Examples</h3>
        <span class="overview-badge read-only">Read-only metadata</span>
      </div>
      ${normalizedOverviewItemsMarkup(data.related_items, "No related reports or examples found yet.")}
    </section>
    <section class="overview-card safety-card">
      <h3>Safety Notes</h3>
      ${listMarkup(data.notes, "No history safety notes registered.")}
    </section>
    ${renderHistoryDiscovery(data.discovery)}
  `;
}

async function loadOverview() {
  if (!tasksDetails) {
    return;
  }
  tasksDetails.innerHTML = "<p class=\"muted\">Loading read-only overview...</p>";
  try {
    const response = await fetch("/api/overview");
    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.error || `Request failed: ${response.status}`);
    }
    renderOverview(data);
    statusText.textContent = "Read-only Tasks / Reports overview refreshed.";
  } catch (error) {
    tasksDetails.innerHTML = `<p class="safety-note">Overview failed: ${escapeHtml(error.message)}</p>`;
    statusText.textContent = `Overview failed: ${error.message}`;
  }
}

async function loadHistory() {
  if (!historyDetails) {
    return;
  }
  historyDetails.innerHTML = "<p class=\"muted\">Loading read-only history...</p>";
  try {
    const response = await fetch("/api/history");
    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.error || `Request failed: ${response.status}`);
    }
    renderHistory(data);
    statusText.textContent = "Read-only Checkpoints / History refreshed.";
  } catch (error) {
    historyDetails.innerHTML = `<p class="safety-note">History failed: ${escapeHtml(error.message)}</p>`;
    statusText.textContent = `History failed: ${error.message}`;
  }
}

function renderRegistry(status) {
  registrySkills = status.skills || [];
  selectedSkillId = registrySkills[0]?.skill_id || "";
  renderSkillCards(registrySkills);
  if (registrySkills.length) {
    renderSkillDetail(registrySkills[0]);
  }
  renderSkillDetails("hermes_manager", "hermes");
  renderSkillDetails("research_council", "research");
  renderSkillDetails("daily_ai_radar", "radar");
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
    if (!registrySkills.length && registryLoadPromise) {
      await registryLoadPromise;
    }
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

async function prepareVoiceCandidate() {
  const transcript = voiceTranscriptInput?.value.trim() || "";
  if (!transcript) {
    statusText.textContent = "Paste a transcript before preparing a task candidate.";
    return;
  }

  try {
    if (!registrySkills.length && registryLoadPromise) {
      await registryLoadPromise;
    }
    const response = await fetch("/api/voice-inbox/prepare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ transcript }),
    });
    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.error || `Request failed: ${response.status}`);
    }
    renderVoiceCandidate(data);
  } catch (error) {
    if (voiceResultBox) {
      voiceResultBox.innerHTML = `<p class="safety-note">Voice Inbox failed: ${escapeHtml(error.message)}</p>`;
    }
    statusText.textContent = `Voice Inbox failed: ${error.message}`;
  }
}

async function pasteVoiceTranscriptFromClipboard() {
  try {
    const text = await navigator.clipboard.readText();
    if (voiceTranscriptInput) {
      voiceTranscriptInput.value = text;
    }
    statusText.textContent = "Clipboard text pasted into Voice Inbox. Nothing was sent or run.";
  } catch (error) {
    statusText.textContent = `Paste failed: ${error.message}`;
  }
}

function clearVoiceTranscript() {
  if (voiceTranscriptInput) {
    voiceTranscriptInput.value = "";
  }
  if (voiceResultBox) {
    voiceResultBox.innerHTML = "<p class=\"muted\">No task candidate prepared yet.</p>";
  }
  statusText.textContent = "Voice Inbox cleared. No transcript was saved.";
}

async function copyCommand(command, nextAction = "") {
  try {
    await navigator.clipboard.writeText(command);
    statusText.textContent = nextAction
      ? `Command copied. ${nextAction} Jarvis Console does not run it for you.`
      : "Command copied. Jarvis Console did not run it.";
  } catch (error) {
    statusText.textContent = `Copy failed: ${error.message}`;
  }
}

function hideManualCopyFallback() {
  const fallback = document.getElementById("memoryCopyFallback");
  if (fallback) {
    fallback.classList.add("hidden");
  }
}

function showManualCopyFallback(label, text) {
  const fallback = document.getElementById("memoryCopyFallback");
  const fallbackText = document.getElementById("memoryCopyFallbackText");
  if (!fallback || !fallbackText) {
    return false;
  }
  const heading = fallback.querySelector("h4");
  if (heading) {
    heading.textContent = label ? `Manual copy fallback: ${label}` : "Manual copy fallback";
  }
  fallbackText.value = text;
  fallback.classList.remove("hidden");
  fallbackText.focus();
  fallbackText.select();
  return true;
}

async function copyPlainText(text, successMessage, manualFallbackLabel = "") {
  try {
    await navigator.clipboard.writeText(text);
    hideManualCopyFallback();
    statusText.textContent = successMessage;
  } catch (error) {
    const fallbackShown = manualFallbackLabel ? showManualCopyFallback(manualFallbackLabel, text) : false;
    statusText.textContent = fallbackShown
      ? "Clipboard was not available. Copy the text below manually."
      : `Copy failed: ${error.message}`;
  }
}

tabs.forEach((button) => {
  button.addEventListener("click", () => activateTab(button.dataset.tab));
});

suggestButton.addEventListener("click", suggestSkill);

if (prepareVoiceButton) {
  prepareVoiceButton.addEventListener("click", prepareVoiceCandidate);
}

if (pasteVoiceButton) {
  pasteVoiceButton.addEventListener("click", pasteVoiceTranscriptFromClipboard);
}

if (clearVoiceButton) {
  clearVoiceButton.addEventListener("click", clearVoiceTranscript);
}

if (loadCodexReviewButton) {
  loadCodexReviewButton.addEventListener("click", loadCodexReview);
}

if (refreshOverviewButton) {
  refreshOverviewButton.addEventListener("click", () => {
    loadOverview();
  });
}

if (refreshHistoryButton) {
  refreshHistoryButton.addEventListener("click", () => {
    loadHistory();
  });
}

if (refreshMemoryButton) {
  refreshMemoryButton.addEventListener("click", () => {
    loadMemorySkills();
  });
}

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
  const detailButton = event.target.closest(".open-skill-details");
  if (detailButton) {
    recommendedSkillId = detailButton.dataset.skillId || "";
    activateTab("skills");
    return;
  }

  const localUrlButton = event.target.closest(".open-local-url");
  if (localUrlButton) {
    const localUrl = localOnlyUrl(localUrlButton.dataset.localUrl);
    if (localUrl) {
      window.open(localUrl, "_blank", "noopener,noreferrer");
      statusText.textContent = "Local URL opened. Jarvis Console did not start the server.";
    }
    return;
  }

  const memoryButton = event.target.closest(".open-memory-skills");
  if (memoryButton) {
    activateTab("memory");
    statusText.textContent = "Showing Memory / Skills read-only sample panel.";
    nextActionText.textContent = "Review the sample candidate guidance; nothing is saved automatically.";
    return;
  }

  const reviewCandidateButton = event.target.closest(".memory-review-candidate");
  if (reviewCandidateButton) {
    statusText.textContent = "Memory / Skills candidate selected for manual review only.";
    nextActionText.textContent = "Copy the candidate or open skill details. No state is changed.";
    return;
  }

  const previewVoiceButton = event.target.closest(".preview-voice-memory-candidate");
  if (previewVoiceButton) {
    previewVoiceMemoryCandidate();
    return;
  }

  const previewCandidateButton = event.target.closest(".memory-preview-candidate");
  if (previewCandidateButton) {
    const candidate = findMemoryCandidate(previewCandidateButton.dataset.candidateId || "");
    if (candidate) {
      previewMemoryCandidatePayload(memoryPreviewRequest(candidate, "sample"));
    } else {
      statusText.textContent = "Candidate preview failed: sample candidate not found.";
    }
    return;
  }

  const copyTextButton = event.target.closest(".copy-text");
  if (copyTextButton) {
    copyPlainText(
      copyTextButton.dataset.copyText || "",
      "Text copied. Jarvis Console did not run anything.",
      copyTextButton.dataset.manualCopyLabel || "",
    );
    return;
  }

  const button = event.target.closest(".copy-command");
  if (!button) {
    return;
  }
  copyCommand(button.dataset.command || "", button.dataset.copyNextAction || "");
});

registryLoadPromise = loadRegistryStatus();

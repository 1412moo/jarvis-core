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
const evaluateIdeaInput = document.getElementById("evaluateIdeaInput");
const evaluateIdeaGoal = document.getElementById("evaluateIdeaGoal");
const evaluateIdeaContext = document.getElementById("evaluateIdeaContext");
const evaluateIdeaEvidence = document.getElementById("evaluateIdeaEvidence");
const evaluateIdeaButton = document.getElementById("evaluateIdeaButton");
const researchDetails = document.getElementById("researchDetails");

let registrySkills = [];
let selectedSkillId = "";
let recommendedSkillId = "";
let registryLoadPromise = null;
let memorySkillsData = null;
let lastVoiceCandidateData = null;
let createLocalTaskToken = "";
let createLocalTaskConfirmation = "";
let createLocalTaskBusy = false;
let evaluateIdeaBusy = false;
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
  let itemId = codexReviewItemId.value.trim();
  let queue;
  try {
    const parsed = JSON.parse(codexReviewQueueInput.value);
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed) && ("queue" in parsed || "item_id" in parsed)) {
      const keys = Object.keys(parsed).sort();
      if (keys.length !== 2 || keys[0] !== "item_id" || keys[1] !== "queue" || !parsed.queue || typeof parsed.item_id !== "string") {
        throw new Error("Hermes handoff fields must be exactly queue and item_id.");
      }
      queue = parsed.queue;
      itemId = parsed.item_id.trim();
      codexReviewItemId.value = itemId;
    } else {
      queue = parsed;
    }
    if (!itemId) {
      throw new Error("Review item ID is required.");
    }
  } catch (error) {
    renderCodexReviewFailure({ detail: error.message || "Review handoff must be valid JSON." });
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

function evaluateIdeaList(items, renderer, emptyText) {
  if (!items || !items.length) {
    return `<p class="muted">${escapeHtml(emptyText)}</p>`;
  }
  return `<div class="evaluate-idea-items">${items.map(renderer).join("")}</div>`;
}

function renderEvaluateIdea(data) {
  if (!researchDetails) {
    return;
  }
  const recommendation = data.recommendation || {};
  const evidenceGaps = data.evidence_gaps || [];
  const critiques = data.key_critiques_risks || [];
  const experiments = data.minimum_experiments || [];
  researchDetails.innerHTML = `
    <article class="evaluate-idea-report">
      <div class="overview-section-heading">
        <div>
          <p class="eyebrow">Evaluate Idea</p>
          <h3>Deterministic evaluation</h3>
        </div>
        <span class="overview-badge read-only">Write-free</span>
      </div>
      <section class="evaluate-idea-section">
        <h4>Executive summary</h4>
        <p>${escapeHtml(data.executive_summary || "No summary was produced.")}</p>
      </section>
      <section class="evaluate-idea-section">
        <h4>Evidence gaps</h4>
        ${evaluateIdeaList(
          evidenceGaps,
          (gap) => `
            <article class="evaluate-idea-item">
              <h5>${escapeHtml(gap.summary || "Missing evidence")}</h5>
              <p><strong>Missing:</strong> ${escapeHtml(gap.missing_evidence || gap.required_evidence || "Not specified")}</p>
              <p><strong>Required:</strong> ${escapeHtml(gap.required_evidence || "Not specified")}</p>
              <p><strong>Validation:</strong> ${escapeHtml(gap.validation_experiment || "Not specified")}</p>
              <p><strong>Confidence impact:</strong> ${escapeHtml(gap.confidence_impact || "Not specified")}</p>
            </article>
          `,
          "No missing evidence entries were returned.",
        )}
      </section>
      <section class="evaluate-idea-section">
        <h4>Key critiques / risks</h4>
        ${evaluateIdeaList(
          critiques,
          (critique) => {
            const severity = ["low", "medium", "high"].includes(critique.severity)
              ? critique.severity
              : "unknown";
            return `
              <article class="evaluate-idea-item">
                <div class="evaluate-idea-item-heading">
                  <h5>${escapeHtml(critique.reviewer_role || "Reviewer")}</h5>
                  <span class="severity-badge severity-${escapeHtml(severity)}">${escapeHtml(severity)}</span>
                </div>
                <p>${escapeHtml(critique.finding || "No finding supplied.")}</p>
                <p><strong>Suggested action:</strong> ${escapeHtml(critique.suggested_action || "Not specified")}</p>
              </article>
            `;
          },
          "No critiques were returned.",
        )}
      </section>
      <section class="evaluate-idea-section">
        <h4>Minimum experiments</h4>
        ${evaluateIdeaList(
          experiments,
          (experiment) => `
            <article class="evaluate-idea-item">
              <h5>${escapeHtml(experiment.title || "Minimum experiment")}</h5>
              <p><strong>Method:</strong> ${escapeHtml(experiment.method || "Not specified")}</p>
              <p><strong>Success:</strong> ${escapeHtml(experiment.success_metric || "Not specified")}</p>
              <p><strong>Minimum:</strong> ${escapeHtml(experiment.minimum_sample || "Not specified")}</p>
              <p><strong>Risk:</strong> ${escapeHtml(experiment.risk || "Not specified")}</p>
            </article>
          `,
          "No experiments were returned.",
        )}
      </section>
      <section class="evaluate-idea-section recommendation">
        <div class="evaluate-idea-item-heading">
          <h4>Recommendation</h4>
          <span class="overview-badge">${escapeHtml(recommendation.decision || "Review")}</span>
        </div>
        <p><strong>Summary:</strong> ${escapeHtml(recommendation.summary || "No recommendation summary.")}</p>
        <p><strong>Rationale:</strong> ${escapeHtml(recommendation.rationale || "Not specified")}</p>
        <p><strong>Next step:</strong> ${escapeHtml(recommendation.next_step || "Review the evaluation.")}</p>
      </section>
      <dl class="evaluate-idea-safety">
        <div><dt>Write-free</dt><dd>${data.write_free ? "Yes" : "No"}</dd></div>
        <div><dt>Local-only</dt><dd>${data.local_only ? "Yes" : "No"}</dd></div>
        <div><dt>External calls</dt><dd>${data.external_calls ? "Yes" : "No"}</dd></div>
      </dl>
    </article>
  `;
  statusText.textContent = "Evaluate Idea completed in memory. Nothing was saved.";
  nextActionText.textContent = recommendation.next_step || "Review the minimum experiments.";
}

function renderEvaluateIdeaFailure(message) {
  if (researchDetails) {
    researchDetails.innerHTML = `
      <article class="evaluate-idea-report blocked">
        <h3>Evaluate Idea could not complete</h3>
        <p class="safety-note">${escapeHtml(message)}</p>
        <p class="muted">Nothing was saved and no external call was made.</p>
      </article>
    `;
  }
  statusText.textContent = `Evaluate Idea failed: ${message}`;
}

async function evaluateIdea() {
  if (evaluateIdeaBusy) {
    return;
  }
  const idea = evaluateIdeaInput?.value.trim() || "";
  const goal = evaluateIdeaGoal?.value.trim() || "";
  const context = evaluateIdeaContext?.value.trim() || "";
  const providedEvidence = (evaluateIdeaEvidence?.value || "")
    .split(/\r?\n/)
    .map((entry) => entry.trim())
    .filter(Boolean);
  if (!idea || !goal) {
    renderEvaluateIdeaFailure("Idea and Goal are required.");
    return;
  }
  if (providedEvidence.length > 8) {
    renderEvaluateIdeaFailure("Provided Evidence accepts up to 8 non-empty entries.");
    return;
  }

  evaluateIdeaBusy = true;
  if (evaluateIdeaButton) {
    evaluateIdeaButton.disabled = true;
    evaluateIdeaButton.textContent = "Evaluating Idea...";
  }
  if (researchDetails) {
    researchDetails.innerHTML = "<p class=\"muted\">Running deterministic local evaluation. Nothing is being saved...</p>";
  }
  try {
    const response = await fetch("/api/evaluate-idea", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        idea,
        goal,
        context,
        provided_evidence: providedEvidence,
      }),
    });
    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.error || `Request failed: ${response.status}`);
    }
    renderEvaluateIdea(data);
  } catch (error) {
    renderEvaluateIdeaFailure(error.message || "Evaluation failed.");
  } finally {
    evaluateIdeaBusy = false;
    if (evaluateIdeaButton) {
      evaluateIdeaButton.disabled = false;
      evaluateIdeaButton.textContent = "Evaluate Idea";
    }
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

function createLocalTaskPanel() {
  return `
    <section class="create-local-task-card" aria-label="Create Local Task">
      <div class="overview-section-heading">
        <div>
          <p class="eyebrow">Create Local Task</p>
          <h4>Create one local TODO Task</h4>
        </div>
        <span class="overview-badge approval-needed">Explicit Confirm required</span>
      </div>
      <p>Preview the exact normalized Title, Summary, status, and local destination before creating anything.</p>
      <p class="muted">The raw transcript is not saved. Create Local Task writes only after you click Confirm.</p>
      <div class="suggestion-actions">
        <button class="primary-button preview-create-local-task" type="button">Preview Create Local Task</button>
      </div>
      <div class="create-local-task-result">
        <p class="muted">No Create Local Task preview yet.</p>
      </div>
    </section>
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
  createLocalTaskToken = "";
  createLocalTaskConfirmation = "";
  createLocalTaskBusy = false;
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
      ${createLocalTaskPanel()}
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

function createLocalTaskResultElement() {
  return voiceResultBox?.querySelector(".create-local-task-result") || null;
}

function renderCreateLocalTaskPreview(data) {
  const target = createLocalTaskResultElement();
  if (!target) {
    return;
  }
  const preview = data.preview || {};
  createLocalTaskToken = data.token || "";
  createLocalTaskConfirmation = data.confirmation_literal || "";
  target.innerHTML = `
    <article class="create-local-task-preview">
      <div class="overview-section-heading">
        <h4>Create Local Task Preview</h4>
        <span class="overview-badge approval-needed">Not created</span>
      </div>
      <dl class="create-local-task-facts">
        <div><dt>Title</dt><dd>${escapeHtml(preview.title || "")}</dd></div>
        <div><dt>Summary</dt><dd>${escapeHtml(preview.summary || "")}</dd></div>
        <div><dt>Status</dt><dd>${escapeHtml(preview.status || "")}</dd></div>
        <div><dt>Local destination</dt><dd><code>${escapeHtml(preview.local_destination || "")}</code></dd></div>
      </dl>
      <p class="muted">${escapeHtml(data.destination_note || "")}</p>
      <p class="safety-note">Raw transcript saved: ${data.raw_transcript_saved ? "Yes" : "No"}</p>
      <div class="suggestion-actions">
        <button class="primary-button confirm-create-local-task" type="button">Confirm Create Local Task</button>
      </div>
    </article>
  `;
}

function renderCreateLocalTaskReceipt(data) {
  const target = createLocalTaskResultElement();
  if (!target) {
    return;
  }
  const receipt = data.receipt || {};
  const receiptState = data.result_type === "already_created" ? "Already created" : "Created";
  target.innerHTML = `
    <article class="create-local-task-receipt">
      <div class="overview-section-heading">
        <h4>Create Local Task Receipt</h4>
        <span class="overview-badge read-only">${escapeHtml(receiptState)}</span>
      </div>
      <dl class="create-local-task-facts">
        <div><dt>Task ID</dt><dd><code>${escapeHtml(receipt.task_id || "")}</code></dd></div>
        <div><dt>Title</dt><dd>${escapeHtml(receipt.title || "")}</dd></div>
        <div><dt>Status</dt><dd>${escapeHtml(receipt.status || "")}</dd></div>
        <div><dt>Storage location</dt><dd><code>${escapeHtml(receipt.storage_location || "")}</code></dd></div>
        <div><dt>Created at</dt><dd>${escapeHtml(receipt.created_at || "")}</dd></div>
        <div><dt>Next recommended action</dt><dd>${escapeHtml(receipt.next_recommended_action || "")}</dd></div>
      </dl>
    </article>
  `;
  statusText.textContent = `${receiptState}: ${receipt.task_id || "local TODO task"}.`;
  nextActionText.textContent = receipt.next_recommended_action || "Review the new TODO task.";
}

async function previewCreateLocalTask() {
  if (createLocalTaskBusy) {
    return;
  }
  const preparedTranscript = String(lastVoiceCandidateData?.raw_transcript || "").trim();
  const currentTranscript = voiceTranscriptInput?.value.trim() || "";
  if (!preparedTranscript || currentTranscript !== preparedTranscript) {
    statusText.textContent = "Prepare the current Voice Inbox text again before Create Local Task.";
    return;
  }

  createLocalTaskBusy = true;
  const target = createLocalTaskResultElement();
  if (target) {
    target.innerHTML = "<p class=\"muted\">Preparing Create Local Task preview...</p>";
  }
  try {
    const response = await fetch("/api/create-local-task/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ transcript: preparedTranscript }),
    });
    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.error || `Request failed: ${response.status}`);
    }
    renderCreateLocalTaskPreview(data);
    statusText.textContent = "Create Local Task preview ready. Nothing has been created.";
    nextActionText.textContent = "Review every persisted field, then Confirm Create Local Task.";
  } catch (error) {
    createLocalTaskToken = "";
    createLocalTaskConfirmation = "";
    if (target) {
      target.innerHTML = `<p class="safety-note">Create Local Task preview failed: ${escapeHtml(error.message)}</p>`;
    }
    statusText.textContent = `Create Local Task preview failed: ${error.message}`;
  } finally {
    createLocalTaskBusy = false;
  }
}

async function confirmCreateLocalTask() {
  if (createLocalTaskBusy || !createLocalTaskToken || !createLocalTaskConfirmation) {
    return;
  }
  createLocalTaskBusy = true;
  const button = voiceResultBox?.querySelector(".confirm-create-local-task");
  if (button) {
    button.disabled = true;
    button.textContent = "Creating local TODO Task...";
  }
  try {
    const response = await fetch("/api/create-local-task/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        token: createLocalTaskToken,
        confirmation: createLocalTaskConfirmation,
      }),
    });
    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.error || `Request failed: ${response.status}`);
    }
    renderCreateLocalTaskReceipt(data);
  } catch (error) {
    const target = createLocalTaskResultElement();
    if (target) {
      target.innerHTML = `
        <p class="safety-note">Create Local Task failed: ${escapeHtml(error.message)}</p>
        <button class="secondary-action preview-create-local-task" type="button">Preview Create Local Task again</button>
      `;
    }
    createLocalTaskToken = "";
    createLocalTaskConfirmation = "";
    statusText.textContent = `Create Local Task failed: ${error.message}`;
  } finally {
    createLocalTaskBusy = false;
  }
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

function renderRecentMilestoneEvidence(evidence) {
  if (
    !evidence ||
    evidence.contract_type !== "jarvis_recent_milestone_evidence" ||
    evidence.version !== "0.1" ||
    evidence.read_only !== true ||
    !Array.isArray(evidence.commits) ||
    evidence.commits.length < 1 ||
    evidence.commits.length > 5
  ) {
    return `
      <section class="workstream-status-section safety-card">
        <div class="overview-section-heading">
          <h4>최근 로컬 작업 증거</h4>
          <span class="overview-badge approval-needed">Unavailable</span>
        </div>
        <p class="safety-note">Bounded recent milestone evidence is unavailable. No repository action was created.</p>
      </section>
    `;
  }

  const commits = Array.isArray(evidence.commits) ? evidence.commits : [];
  const headStatus = evidence.head_matches_latest_commit ? "HEAD verified" : "HEAD changed";
  return `
    <section class="workstream-status-section recent-milestone-section">
      <div class="overview-section-heading">
        <div>
          <p class="eyebrow">Bounded local Git evidence</p>
          <h4>최근 로컬 작업 증거</h4>
        </div>
        <div class="overview-badges">
          <span class="overview-badge read-only">Read-only</span>
          <span class="overview-badge ${evidence.head_matches_latest_commit ? "read-only" : "approval-needed"}">${escapeHtml(headStatus)}</span>
        </div>
      </div>
      <p class="muted">현재 HEAD에서 역순으로 수집한 최근 ${escapeHtml(String(commits.length))}개 로컬 커밋입니다. 커밋 제목은 검증 결과가 아니라 작업 증거 요약입니다.</p>
      <div class="recent-milestone-grid">
        ${commits
          .map(
            (commit) => `
              <article class="recent-milestone-card">
                <div class="overview-section-heading">
                  <h5>${escapeHtml(commit.subject || "(no subject)")}</h5>
                  <div class="overview-badges">
                    ${commit.is_head ? '<span class="overview-badge read-only">HEAD</span>' : ""}
                    <span class="overview-badge read-only">${escapeHtml(commit.short_hash || "unknown")}</span>
                  </div>
                </div>
                <p><strong>변경 파일 ${escapeHtml(String(commit.changed_file_count ?? 0))}개</strong></p>
                ${listMarkup(commit.changed_files, "No changed files recorded for this commit.")}
                ${commit.files_truncated ? '<p class="muted">Only the first bounded file names are shown.</p>' : ""}
                ${commit.protected_path_present ? '<p class="safety-note">Protected path jarvis.bat appears in this commit.</p>' : ""}
              </article>
            `,
          )
          .join("")}
      </div>
      <p class="approval-note">이 증거는 읽기 전용 보고 자료입니다. 완료 판정, 승인, 실행, stage, commit, push 또는 PR 권한을 만들지 않습니다.</p>
    </section>
  `;
}

function renderDirectorReport(directorReport) {
  const isRecord = (value) =>
    value !== null && typeof value === "object" && !Array.isArray(value);
  const isNonEmptyTrimmedText = (value) =>
    typeof value === "string" && value.length > 0 && value === value.trim();
  const packageItemsValid =
    Array.isArray(directorReport?.completed_packages) &&
    directorReport.completed_packages.every(
      (item) =>
        isRecord(item) &&
        isNonEmptyTrimmedText(item.work_package_id) &&
        isNonEmptyTrimmedText(item.result_type) &&
        isNonEmptyTrimmedText(item.summary) &&
        typeof item.commit_hash === "string",
    );
  const riskItemsValid =
    Array.isArray(directorReport?.risk_summary) &&
    directorReport.risk_summary.every(
      (item) =>
        isRecord(item) &&
        isNonEmptyTrimmedText(item.severity) &&
        isNonEmptyTrimmedText(item.summary),
    );
  const recommendationValid =
    directorReport?.next_recommendation === null ||
    (isRecord(directorReport?.next_recommendation) &&
      isNonEmptyTrimmedText(directorReport.next_recommendation.work_package_id) &&
      isNonEmptyTrimmedText(directorReport.next_recommendation.summary) &&
      isNonEmptyTrimmedText(directorReport.next_recommendation.user_value));
  const ownerDecisionValid =
    (directorReport?.owner_action === "none" &&
      directorReport?.owner_decision === "") ||
    (directorReport?.owner_action === "decision_required" &&
      isNonEmptyTrimmedText(directorReport?.owner_decision));
  const blockedStateValid =
    directorReport?.status !== "blocked" ||
    directorReport?.owner_action === "decision_required";
  const blockingRiskStateValid =
    !riskItemsValid ||
    !directorReport.risk_summary.some((item) => item.severity === "blocking") ||
    (directorReport?.status === "blocked" &&
      directorReport?.owner_action === "decision_required");
  if (
    !directorReport ||
    directorReport.contract_type !== "jarvis_director_report" ||
    directorReport.version !== "0.1A" ||
    directorReport.source_contract_type !== "hermes_manager_report" ||
    directorReport.derived_view !== true ||
    directorReport.read_only !== true ||
    directorReport.authority_boundary !== "derived_owner_summary_only" ||
    !["in_progress", "milestone_complete", "blocked"].includes(directorReport.status) ||
    !["none", "decision_required"].includes(directorReport.owner_action) ||
    !isNonEmptyTrimmedText(directorReport.milestone_id) ||
    !isNonEmptyTrimmedText(directorReport.milestone_summary) ||
    !isNonEmptyTrimmedText(directorReport.owner_outcome) ||
    !packageItemsValid ||
    !riskItemsValid ||
    !recommendationValid ||
    !ownerDecisionValid ||
    !blockedStateValid ||
    !blockingRiskStateValid
  ) {
    return `
      <section class="workstream-status-section safety-card director-report-section">
        <div class="overview-section-heading">
          <h4>Director Summary</h4>
          <span class="overview-badge approval-needed">Unavailable</span>
        </div>
        <p class="safety-note">The bounded Director Report is unavailable. No Owner outcome, milestone result, decision, or next recommendation was inferred.</p>
      </section>
    `;
  }

  const packages = directorReport.completed_packages;
  const risks = directorReport.risk_summary;
  const recommendation = directorReport.next_recommendation || null;
  const ownerAction = directorReport.owner_action || "decision_required";
  return `
    <section class="workstream-status-section director-report-section" aria-label="Director Summary">
      <div class="overview-section-heading">
        <div>
          <p class="eyebrow">Director to Owner</p>
          <h4>Director Summary</h4>
        </div>
        <div class="overview-badges">
          <span class="overview-badge read-only">Read-only</span>
          <span class="overview-badge">${escapeHtml(directorReport.status || "blocked")}</span>
          <span class="overview-badge ${ownerAction === "none" ? "read-only" : "approval-needed"}">Owner action: ${escapeHtml(ownerAction)}</span>
        </div>
      </div>

      <div class="owner-priority-grid">
        <article class="owner-priority-card reason-card">
          <p class="eyebrow">Milestone</p>
          <h4>지금 진행 중인 결과</h4>
          <p>${escapeHtml(directorReport.milestone_summary || "Not supplied")}</p>
        </article>
        <article class="owner-priority-card outcome-card">
          <p class="eyebrow">Owner outcome</p>
          <h4>Owner가 얻게 된 기능</h4>
          <p>${escapeHtml(directorReport.owner_outcome || "Not supplied")}</p>
        </article>
      </div>

      <dl class="overview-facts compact-facts">
        <div><dt>Milestone ID</dt><dd><code>${escapeHtml(directorReport.milestone_id || "unknown")}</code></dd></div>
        <div><dt>Status</dt><dd>${escapeHtml(directorReport.status || "blocked")}</dd></div>
      </dl>

      <div class="overview-rule-grid">
        <div>
          <strong>완료 package / 검증 commit</strong>
          ${
            packages.length
              ? `<ul class="metadata-list">${packages
                  .map(
                    (item) => `<li><code>${escapeHtml(item.work_package_id || "unknown")}</code> — ${escapeHtml(item.summary || "No summary supplied.")}<br><span class="muted">${escapeHtml(item.commit_hash || "no verified commit")}</span></li>`,
                  )
                  .join("")}</ul>`
              : '<p class="placeholder">No completed package checkpoint is recorded.</p>'
          }
        </div>
        <div>
          <strong>남은 위험</strong>
          ${
            risks.length
              ? `<ul class="metadata-list">${risks
                  .map(
                    (risk) => `<li><code>${escapeHtml(risk.severity || "unknown")}</code> ${escapeHtml(risk.summary || "")}</li>`,
                  )
                  .join("")}</ul>`
              : '<p class="placeholder">None.</p>'
          }
        </div>
        <div>
          <strong>다음 추천</strong>
          ${
            recommendation
              ? `<p><code>${escapeHtml(recommendation.work_package_id || "unknown")}</code><br>${escapeHtml(recommendation.summary || "")}<br><span class="muted">${escapeHtml(recommendation.user_value || "")}</span></p>`
              : '<p class="placeholder">None.</p>'
          }
        </div>
      </div>

      <p class="approval-note">
        <strong>Owner action:</strong> ${escapeHtml(ownerAction)}
        ${directorReport.owner_decision ? `<br>${escapeHtml(directorReport.owner_decision)}` : ""}
      </p>
      <p class="muted">이 요약은 검증된 Manager Report에서 파생된 읽기 전용 Owner view입니다. Manager의 상세 증거를 복제하거나 승인·실행 권한을 만들지 않습니다.</p>
    </section>
  `;
}

function renderManagerReport(managerReport) {
  if (
    !managerReport ||
    managerReport.contract_type !== "hermes_manager_report" ||
    managerReport.version !== "0.1A" ||
    managerReport.source_of_truth !== "master_plan" ||
    managerReport.derived_view !== true ||
    managerReport.read_only !== true ||
    managerReport.authority_boundary !== "derived_reporting_only"
  ) {
    return `
      <section class="workstream-status-section safety-card manager-report-section">
        <div class="overview-section-heading">
          <h4>Hermes Manager Report</h4>
          <span class="overview-badge approval-needed">Unavailable</span>
        </div>
        <p class="safety-note">The bounded Manager Report is unavailable. No milestone result, approval, or next action was inferred.</p>
      </section>
    `;
  }

  const packages = Array.isArray(managerReport.completed_work_packages)
    ? managerReport.completed_work_packages
    : [];
  const risks = Array.isArray(managerReport.risks) ? managerReport.risks : [];
  const conflicts = Array.isArray(managerReport.source_conflicts)
    ? managerReport.source_conflicts
    : [];
  const recommendation = managerReport.next_recommendation || null;
  const ownerAction = managerReport.owner_action || "decision_required";
  return `
    <section class="workstream-status-section manager-report-section" aria-label="Hermes Manager Report">
      <div class="overview-section-heading">
        <div>
          <p class="eyebrow">Manager technical evidence</p>
          <h4>Hermes Manager Report — Detailed Evidence</h4>
        </div>
        <div class="overview-badges">
          <span class="overview-badge read-only">Read-only</span>
          <span class="overview-badge">${escapeHtml(managerReport.status || "blocked")}</span>
          <span class="overview-badge ${ownerAction === "none" ? "read-only" : "approval-needed"}">Owner action: ${escapeHtml(ownerAction)}</span>
        </div>
      </div>

      <div class="owner-priority-grid manager-report-priority">
        <article class="owner-priority-card reason-card">
          <p class="eyebrow">Milestone meaning</p>
          <h4>이번 milestone의 의미</h4>
          <p>${escapeHtml(managerReport.milestone_meaning || "Not supplied")}</p>
        </article>
        <article class="owner-priority-card outcome-card">
          <p class="eyebrow">User outcome</p>
          <h4>사용자가 얻은 결과</h4>
          <p>${escapeHtml(managerReport.user_outcome || "Not supplied")}</p>
        </article>
      </div>

      <dl class="overview-facts compact-facts manager-report-facts">
        <div><dt>전체 목표</dt><dd>${escapeHtml(managerReport.current_goal || "Not supplied")}</dd></div>
        <div><dt>현재 위치</dt><dd>${escapeHtml(managerReport.current_position || "Not supplied")}</dd></div>
        <div><dt>Milestone ID</dt><dd><code>${escapeHtml(managerReport.milestone_id || "unknown")}</code></dd></div>
        <div><dt>Source</dt><dd><code>${escapeHtml(managerReport.source_of_truth)}</code></dd></div>
      </dl>

      <div>
        <p class="eyebrow">Completed work packages</p>
        <div class="manager-report-package-grid">
          ${
            packages.length
              ? packages
                  .map(
                    (item) => `
                      <article class="manager-report-package-card">
                        <div class="overview-section-heading">
                          <h5>${escapeHtml(item.work_package_id || "Unknown package")}</h5>
                          <span class="overview-badge read-only">${escapeHtml(item.result_type || "unknown")}</span>
                        </div>
                        <p>${escapeHtml(item.summary || "No summary supplied.")}</p>
                        <code>${escapeHtml(item.commit_hash || "no commit")}</code>
                      </article>
                    `,
                  )
                  .join("")
              : '<p class="placeholder">No completed package checkpoint is recorded.</p>'
          }
        </div>
      </div>

      <div class="overview-rule-grid manager-report-review-grid">
        <div><strong>검증 근거</strong>${listMarkup(managerReport.evidence_summary, "No evidence supplied.")}</div>
        <div><strong>Source conflicts</strong>${listMarkup(conflicts, "None.")}</div>
        <div>
          <strong>위험</strong>
          ${
            risks.length
              ? `<ul class="metadata-list">${risks
                  .map(
                    (risk) => `<li><code>${escapeHtml(risk.severity || "unknown")}</code> ${escapeHtml(risk.category || "risk")} — ${escapeHtml(risk.summary || "")}</li>`,
                  )
                  .join("")}</ul>`
              : '<p class="placeholder">None.</p>'
          }
        </div>
        <div>
          <strong>다음 추천</strong>
          ${
            recommendation
              ? `<p><code>${escapeHtml(recommendation.work_package_id || "unknown")}</code><br>${escapeHtml(recommendation.summary || "")}<br><span class="muted">${escapeHtml(recommendation.user_value || "")}</span></p>`
              : '<p class="placeholder">None.</p>'
          }
        </div>
      </div>

      <p class="approval-note manager-owner-action">
        <strong>Owner action:</strong> ${escapeHtml(ownerAction)}
        ${managerReport.owner_decision ? `<br>${escapeHtml(managerReport.owner_decision)}` : ""}
      </p>
      <p class="muted">이 화면은 Master Plan과 bounded local Git evidence에서 파생된 읽기 전용 요약입니다. 승인, 실행, stage, commit, push 또는 PR 권한을 만들지 않습니다.</p>
    </section>
  `;
}

function renderProjectControl(projectControl) {
  const cards = projectControl?.project_cards || [];
  if (!cards.length) {
    return `
      <section class="overview-card safety-card">
        <h3>Project Control</h3>
        <p class="placeholder">No trusted project card is available.</p>
      </section>
    `;
  }
  return `
    <section class="overview-card">
      <div class="overview-section-heading">
        <div>
          <p class="eyebrow">Owner Dashboard</p>
          <h3>Project Control</h3>
        </div>
        <div class="overview-badges">
          <span class="overview-badge read-only">Read-only</span>
          <span class="overview-badge">${escapeHtml(projectControl.version || "project_control.v0.1F")}</span>
        </div>
      </div>
      <p class="muted">Current direction comes from ${escapeHtml(projectControl.source || "the tracked master plan")}; live repository facts are refreshed locally.</p>
      <div class="overview-skill-grid">
        ${cards
          .map(
            (card) => {
              const ownerSummary = card.owner_summary || {};
              const directorReport = card.director_report || null;
              const managerReport = card.manager_report || null;
              const ownerDecision = card.owner_decision || null;
              const recentMilestoneEvidence = card.recent_milestone_evidence || null;
              const workstreams = Array.isArray(card.workstreams) ? card.workstreams : [];
              const lockedCapabilities = card.locked_capabilities || card.forbidden_actions || [];
              const approvalState = ownerSummary.approval_state || "blocked";
              const approvalLabel =
                approvalState === "none"
                  ? "No approval needed"
                  : approvalState === "required"
                    ? "Approval required"
                    : "Blocked";
              return `
                <article class="overview-skill-card project-control-card">
                  <div class="overview-section-heading">
                    <h4>${escapeHtml(card.display_name || card.project_id || "Local project")}</h4>
                    <span class="overview-badge ${card.status === "observed" ? "read-only" : ""}">${card.status === "observed" ? "Observed" : "Attention"}</span>
                  </div>

                  <div class="owner-priority-grid">
                    <section class="owner-priority-card reason-card">
                      <p class="eyebrow">Owner context</p>
                      <h4>현재 만드는 이유</h4>
                      <p>${escapeHtml(ownerSummary.current_reason || "Not supplied")}</p>
                    </section>
                    <section class="owner-priority-card outcome-card">
                      <p class="eyebrow">Owner outcome</p>
                      <h4>이 단계가 끝나면 사용자가 얻는 것</h4>
                      <p>${escapeHtml(ownerSummary.owner_outcome || "Not supplied")}</p>
                    </section>
                  </div>

                  <section class="owner-milestone-card">
                    <div class="overview-section-heading">
                      <h4>현재 위치와 다음 결정</h4>
                      <span class="overview-badge ${approvalState === "none" ? "read-only" : "approval-needed"}">${escapeHtml(approvalLabel)}</span>
                    </div>
                    <dl class="overview-facts owner-milestone-facts">
                      <div><dt>최근 완료</dt><dd>${escapeHtml(ownerSummary.recent_completed || "Not supplied")}</dd></div>
                      <div><dt>현재 milestone</dt><dd>${escapeHtml(ownerSummary.current_milestone || card.current_milestone || "Not supplied")}</dd></div>
                      <div><dt>다음 사용자 체감 결과</dt><dd>${escapeHtml(ownerSummary.next_user_visible_milestone || card.next_user_visible_milestone || "Not supplied")}</dd></div>
                      <div><dt>다음 단계</dt><dd>${escapeHtml(ownerSummary.recommended_next_step || card.recommended_next_step || "Not supplied")}</dd></div>
                    </dl>
                    <p class="approval-note"><strong>승인 필요 여부:</strong> ${escapeHtml(ownerSummary.approval_note || "Not supplied")}</p>
                  </section>

                  ${renderDirectorReport(directorReport)}

                  ${renderManagerReport(managerReport)}

                  ${renderRecentMilestoneEvidence(recentMilestoneEvidence)}

                  ${managerReport?.owner_action === "none" ? "" : renderOwnerDecision(ownerDecision)}

                  <section class="workstream-status-section">
                    <div class="overview-section-heading">
                      <div>
                        <p class="eyebrow">Single-repo visibility</p>
                        <h4>Jarvis-Core 내부 workstream</h4>
                      </div>
                      <span class="overview-badge read-only">${escapeHtml(String(workstreams.length))} read-only</span>
                    </div>
                    <div class="workstream-status-grid">
                      ${workstreams
                        .map(
                          (workstream) => `
                            <article class="workstream-status-card">
                              <div class="overview-section-heading">
                                <h5>${escapeHtml(workstream.display_name || workstream.workstream_id || "Internal workstream")}</h5>
                                <span class="overview-badge read-only">Read-only</span>
                              </div>
                              <p><strong>현재 상태</strong>${escapeHtml(workstream.status_summary || "Not supplied")}</p>
                              <p><strong>사용자에게 보이는 기능</strong>${escapeHtml(workstream.user_visible_capability || "Not supplied")}</p>
                              <p><strong>다음 안전 단계</strong>${escapeHtml(workstream.next_safe_step || "Not supplied")}</p>
                            </article>
                          `,
                        )
                        .join("")}
                    </div>
                  </section>

                  <div class="overview-rule-grid owner-boundary-grid">
                    <div><strong>잠긴 기능</strong>${listMarkup(lockedCapabilities, "None declared.")}</div>
                    <div><strong>Known protected / untracked</strong>${listMarkup(card.known_protected_untracked, "None declared.")}</div>
                    <div><strong>Validation commands</strong>${listMarkup(card.validation_commands, "None declared.")}</div>
                    <div><strong>Attention</strong>${listMarkup(card.attention_reasons, "No master-plan branch mismatch detected.")}</div>
                  </div>

                  <section class="project-control-technical">
                    <div class="overview-section-heading">
                      <h4>Repository facts</h4>
                      <span class="overview-badge">Technical</span>
                    </div>
                    <dl class="overview-facts compact-facts">
                      <div><dt>Branch</dt><dd>${escapeHtml(card.branch || "unknown")}</dd></div>
                      <div><dt>Live HEAD</dt><dd><code>${escapeHtml(card.live_head || "unknown")}</code></dd></div>
                      <div><dt>Verified implementation</dt><dd><code>${escapeHtml(card.verified_implementation_head || "unknown")}</code></dd></div>
                      <div><dt>Last verified</dt><dd>${escapeHtml(card.last_verified || "unknown")}</dd></div>
                      <div><dt>Current workstream</dt><dd>${escapeHtml(card.current_workstream || "Not supplied")}</dd></div>
                      <div><dt>Working tree</dt><dd><code class="codex-review-status">${escapeHtml(card.working_tree_status || "clean")}</code></dd></div>
                    </dl>
                  </section>
                </article>
              `;
            },
          )
          .join("")}
      </div>
      ${listMarkup(projectControl.notes, "No Project Control notes registered.")}
    </section>
  `;
}

function renderOwnerDecision(ownerDecision) {
  if (
    !ownerDecision ||
    ownerDecision.contract_type !== "jarvis_owner_decision" ||
    ownerDecision.version !== "0.1A" ||
    ownerDecision.read_only !== true
  ) {
    return `
      <section class="workstream-status-section safety-card">
        <div class="overview-section-heading">
          <h4>Owner Decision</h4>
          <span class="overview-badge approval-needed">Unavailable</span>
        </div>
        <p class="safety-note">The bounded Owner Decision contract is unavailable. No selection, approval, or action was created.</p>
      </section>
    `;
  }

  const candidates = Array.isArray(ownerDecision.candidates) ? ownerDecision.candidates : [];
  const selectedWorkstream = ownerDecision.selected_workstream_id || "Not selected";
  const desiredOutcome = ownerDecision.desired_outcome || "Not provided";
  return `
    <section class="workstream-status-section">
      <div class="overview-section-heading">
        <div>
          <p class="eyebrow">Shared read-only contract</p>
          <h4>다음 workstream 결정</h4>
        </div>
        <div class="overview-badges">
          <span class="overview-badge read-only">Read-only</span>
          <span class="overview-badge">${escapeHtml(ownerDecision.version)}</span>
          <span class="overview-badge approval-needed">${escapeHtml(ownerDecision.status || "blocked")}</span>
        </div>
      </div>
      <p>${escapeHtml(ownerDecision.reason || "No decision reason supplied.")}</p>
      <dl class="overview-facts compact-facts">
        <div><dt>권한 경계</dt><dd><code>${escapeHtml(ownerDecision.authority_boundary || "blocked")}</code></dd></div>
        <div><dt>추천 workstream</dt><dd><code>${escapeHtml(ownerDecision.recommended_workstream_id || "none")}</code></dd></div>
        <div><dt>현재 선택</dt><dd>${escapeHtml(selectedWorkstream)}</dd></div>
        <div><dt>원하는 결과</dt><dd>${escapeHtml(desiredOutcome)}</dd></div>
      </dl>
      <div class="workstream-status-grid">
        ${candidates
          .map(
            (candidate) => `
              <article class="workstream-status-card">
                <div class="overview-section-heading">
                  <h5>${escapeHtml(candidate.display_name || candidate.workstream_id || "Unknown workstream")}</h5>
                  ${candidate.workstream_id === ownerDecision.recommended_workstream_id ? '<span class="overview-badge read-only">Recommended</span>' : '<span class="overview-badge read-only">Candidate</span>'}
                </div>
                <p><strong>현재 사용자 기능</strong>${escapeHtml(candidate.current_capability || "Not supplied")}</p>
                <p><strong>선택 후 사용자 결과</strong>${escapeHtml(candidate.next_user_outcome || "Not supplied")}</p>
                <div><strong>계속 잠기는 기능</strong>${listMarkup(candidate.locked_capabilities, "None declared.")}</div>
              </article>
            `,
          )
          .join("")}
      </div>
      <div>
        <p class="eyebrow">Conversation response template</p>
        <code>${escapeHtml(ownerDecision.response_template || "No response template supplied.")}</code>
      </div>
      <p class="approval-note">이 화면은 Decision 객체를 읽기만 합니다. 선택, 구현 승인, 저장, 실행, push 또는 PR 권한을 만들지 않습니다.</p>
    </section>
  `;
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
    ${renderProjectControl(data.project_control)}
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
    statusText.textContent = "Read-only Project Control overview refreshed.";
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
  lastVoiceCandidateData = null;
  createLocalTaskToken = "";
  createLocalTaskConfirmation = "";
  createLocalTaskBusy = false;
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

if (evaluateIdeaButton) {
  evaluateIdeaButton.addEventListener("click", evaluateIdea);
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
  const createLocalTaskPreviewButton = event.target.closest(".preview-create-local-task");
  if (createLocalTaskPreviewButton) {
    previewCreateLocalTask();
    return;
  }

  const createLocalTaskConfirmButton = event.target.closest(".confirm-create-local-task");
  if (createLocalTaskConfirmButton) {
    confirmCreateLocalTask();
    return;
  }

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

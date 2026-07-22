const state = {
  step: 1,
  session: null,
  repo: "C:\\work\\jarvis-core",
  artifactTitle: "No artifact yet",
  output: "",
  scopeConfirmed: false,
};

const stepMeta = {
  1: {
    title: "What do you want Codex to do?",
    help: "Write one task. No automation is triggered.",
    section: "taskSection",
  },
  2: {
    title: "Confirm Scope",
    help: "Review the prepared scope before sending anything to Codex.",
    section: "preparedSection",
  },
  3: {
    title: "Copy Task Prompt for Codex",
    help: "Paste this prompt into Codex. After Codex responds, copy the result.",
    section: "taskPromptSection",
  },
  4: {
    title: "Paste Codex Result",
    help: "Use this after Codex answers.",
    section: "resultSection",
  },
  5: {
    title: "Copy Review Prompt for Codex",
    help: "Now ask Codex to review the result.",
    section: "reviewSection",
  },
  6: {
    title: "Approve Commit Prompt",
    help: "Approve commit only after review passes. This UI never commits or pushes.",
    section: "approvalSection",
  },
  7: {
    title: "Copy Commit Prompt for Codex",
    help: "Paste this commit prompt into Codex.",
    section: "commitSection",
  },
  8: {
    title: "Checkpoint",
    help: "After commit, paste the commit result and save a checkpoint.",
    section: "checkpointSection",
  },
};

const elements = {
  stepList: document.getElementById("stepList"),
  currentStepLabel: document.getElementById("currentStepLabel"),
  actionTitle: document.getElementById("actionTitle"),
  actionHelp: document.getElementById("actionHelp"),
  taskInput: document.getElementById("taskInput"),
  targetFilesInput: document.getElementById("targetFilesInput"),
  codexResult: document.getElementById("codexResult"),
  reviewedCheckbox: document.getElementById("reviewedCheckbox"),
  approveCheckbox: document.getElementById("approveCheckbox"),
  commitMessage: document.getElementById("commitMessage"),
  generatedOutput: document.getElementById("generatedOutput"),
  artifactTitle: document.getElementById("artifactTitle"),
  statusBar: document.getElementById("statusBar"),
  confirmationWarning: document.getElementById("confirmationWarning"),
  summaryGoal: document.getElementById("summaryGoal"),
  summaryTask: document.getElementById("summaryTask"),
  summaryValidation: document.getElementById("summaryValidation"),
  taskPromptTargets: document.getElementById("taskPromptTargets"),
  taskPromptCommitMessage: document.getElementById("taskPromptCommitMessage"),
};

const sectionIds = [
  "taskSection",
  "preparedSection",
  "taskPromptSection",
  "resultSection",
  "reviewSection",
  "approvalSection",
  "commitSection",
  "checkpointSection",
];

function setStatus(message) {
  elements.statusBar.textContent = message;
}

function updateStep(step) {
  state.step = step;
  const meta = stepMeta[step] || stepMeta[1];
  elements.currentStepLabel.textContent = `Step ${step} of 8`;
  elements.actionTitle.textContent = meta.title;
  elements.actionHelp.textContent = meta.help;
  sectionIds.forEach((id) => document.getElementById(id).classList.add("hidden"));
  document.getElementById(meta.section).classList.remove("hidden");
  Array.from(elements.stepList.children).forEach((item) => {
    item.classList.toggle("active", Number(item.dataset.step) === step);
  });
}

function updateSummary() {
  if (!state.session) {
    elements.summaryGoal.textContent = "-";
    elements.summaryTask.textContent = "-";
    elements.targetFilesInput.value = "";
    elements.summaryValidation.textContent = "-";
    elements.confirmationWarning.classList.add("hidden");
    return;
  }
  elements.summaryGoal.textContent = state.session.current_goal || "-";
  elements.summaryTask.textContent = state.session.active_task || "-";
  elements.targetFilesInput.value = (state.session.target_files || []).join("\n");
  elements.summaryValidation.textContent = `${(state.session.validation_commands || []).length} commands`;
  elements.commitMessage.value = state.session.commit_message || elements.commitMessage.value;
  updateTaskPromptSummary();
  updateConfirmationWarning();
}

function targetFiles() {
  return elements.targetFilesInput.value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

function updateSessionFromForm() {
  if (!state.session) return;
  const targets = targetFiles();
  state.session.target_files = targets;
  state.session.files_touched = targets;
  state.session.last_codex_result_summary = elements.codexResult.value.trim();
  state.session.commit_message = elements.commitMessage.value.trim() || state.session.commit_message;
  state.session.push_allowed = false;
}

function needsConfirmation() {
  return targetFiles().some((path) => path.startsWith("NEEDS_USER_CONFIRMATION"));
}

function updateConfirmationWarning() {
  elements.confirmationWarning.classList.toggle("hidden", !needsConfirmation());
}

function updateTaskPromptSummary() {
  elements.taskPromptTargets.textContent = targetFiles().join("\n") || "-";
  elements.taskPromptCommitMessage.textContent = elements.commitMessage.value.trim() || "-";
}

function setOutput(title, artifact) {
  state.artifactTitle = title;
  state.output = artifact || "";
  elements.artifactTitle.textContent = title;
  elements.generatedOutput.value = state.output;
}

async function apiPost(path, payload) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok || !data.ok) {
    throw new Error(data.error || `Request failed: ${response.status}`);
  }
  return data;
}

async function copyText(text) {
  if (!text) return "No output to copy.";
  try {
    await navigator.clipboard.writeText(text);
    return "";
  } catch (error) {
    return error.message || "Clipboard copy failed.";
  }
}

async function prepareSession() {
  try {
    const data = await apiPost("/api/prepare", {
      task: elements.taskInput.value,
      repo: state.repo,
    });
    state.session = data.session;
    state.scopeConfirmed = false;
    updateSummary();
    updateStep(data.next_step || 2);
    setStatus(data.needs_confirmation ? "Confirm target files before continuing to the task prompt." : "Prepared session. Confirm scope, then continue to the task prompt.");
  } catch (error) {
    setStatus(`Prepare failed: ${error.message}`);
  }
}

function continueToTaskPrompt() {
  if (!state.session) {
    setStatus("Prepare a session first.");
    return;
  }
  updateSessionFromForm();
  updateConfirmationWarning();
  if (needsConfirmation()) {
    setStatus("Target files need confirmation before Step 3.");
    return;
  }
  state.scopeConfirmed = true;
  updateTaskPromptSummary();
  updateStep(3);
  setStatus("Scope confirmed. Next: copy the task prompt for Codex.");
}

async function copyJarvisReviewHandoff() {
  if (!state.session) {
    setStatus("Prepare a session first.");
    return;
  }
  if (!state.scopeConfirmed) {
    setStatus("Confirm the current target-file scope before creating a Jarvis handoff.");
    return;
  }
  updateSessionFromForm();
  if (!state.session.last_codex_result_summary) {
    setStatus("Paste the Codex result before creating a Jarvis handoff.");
    return;
  }
  try {
    const data = await apiPost("/api/review-handoff", {
      session: state.session,
      scope_confirmed: true,
    });
    setOutput("Jarvis Review Handoff", data.artifact);
    const copyError = await copyText(data.artifact);
    const next = ` Item ID: ${data.item_id}. Paste the JSON once into Jarvis Console Codex Review.`;
    setStatus(copyError ? `${data.message}${next} Clipboard copy failed: ${copyError}` : `${data.message}${next} Copied to clipboard.`);
  } catch (error) {
    setStatus(`Review handoff failed: ${error.message}`);
  }
}

async function renderPrompt(mode, title) {
  if (!state.session) {
    setStatus("Prepare a session first.");
    return;
  }
  updateSessionFromForm();
  try {
    const data = await apiPost("/api/render", { mode, session: state.session });
    setOutput(title, data.artifact);
    const copyError = await copyText(data.artifact);
    if (mode === "implementation-prompt") updateStep(data.next_step || 4);
    if (mode === "review-prompt") updateStep(data.next_step || 6);
    if (mode === "commit-prompt") updateStep(data.next_step || 8);
    if (mode === "checkpoint-summary") updateStep(8);
    setStatus(copyError ? `${data.message} Clipboard copy failed: ${copyError}` : `${data.message} Copied to clipboard.`);
  } catch (error) {
    setStatus(`Render failed: ${error.message}`);
  }
}

async function pasteFromClipboard() {
  try {
    elements.codexResult.value = await navigator.clipboard.readText();
    saveResultAndContinue();
  } catch (error) {
    setStatus(`Paste failed: ${error.message || "clipboard read failed"}`);
  }
}

function saveResultAndContinue() {
  if (!state.session) {
    setStatus("Prepare a session first.");
    return;
  }
  const result = elements.codexResult.value.trim();
  if (!result) {
    setStatus("Paste the Codex result before continuing.");
    return;
  }
  state.session.last_codex_result_summary = result;
  updateStep(5);
  setStatus("Codex result saved. Next: copy the review prompt for Codex.");
}

function approveCommit() {
  if (!state.session) {
    setStatus("Prepare a session first.");
    return;
  }
  if (!elements.reviewedCheckbox.checked || !elements.approveCheckbox.checked) {
    setStatus("Check both approval boxes after review passes.");
    return;
  }
  state.session.commit_allowed = true;
  state.session.human_approval_required = true;
  state.session.human_approval_granted = true;
  state.session.push_allowed = false;
  updateStep(7);
  setStatus("Commit prompt approved. This only allows prompt generation; it does not commit.");
}

function resetApproval() {
  if (state.session) {
    state.session.commit_allowed = false;
    state.session.human_approval_granted = false;
    state.session.push_allowed = false;
  }
  elements.reviewedCheckbox.checked = false;
  elements.approveCheckbox.checked = false;
  state.scopeConfirmed = false;
  updateStep(1);
  setStatus("Approval reset. Start the next task when ready.");
}

async function copyOutput() {
  const copyError = await copyText(elements.generatedOutput.value);
  setStatus(copyError ? `Copy failed: ${copyError}` : "Output copied to clipboard.");
}

function clearOutput() {
  setOutput("No artifact yet", "");
  setStatus("Output cleared.");
}

async function loadGitStatus() {
  try {
    const data = await apiPost("/api/git-status", { repo: state.repo });
    if (state.session) {
      Object.assign(state.session, data.git_status);
    }
    setStatus(`Loaded git status: ${data.git_status.branch} ${data.git_status.head}`);
  } catch (error) {
    setStatus(`Git status failed: ${error.message}`);
  }
}

document.getElementById("prepareButton").addEventListener("click", prepareSession);
document.getElementById("continueToTaskPromptButton").addEventListener("click", continueToTaskPrompt);
document.getElementById("copyTaskPromptButton").addEventListener("click", () => renderPrompt("implementation-prompt", "Task Prompt for Codex"));
document.getElementById("pasteResultButton").addEventListener("click", pasteFromClipboard);
document.getElementById("saveResultButton").addEventListener("click", saveResultAndContinue);
document.getElementById("copyReviewPromptButton").addEventListener("click", () => renderPrompt("review-prompt", "Review Prompt for Codex"));
document.getElementById("copyJarvisReviewHandoffButton").addEventListener("click", copyJarvisReviewHandoff);
document.getElementById("approveCommitButton").addEventListener("click", approveCommit);
document.getElementById("copyCommitPromptButton").addEventListener("click", () => renderPrompt("commit-prompt", "Commit Prompt for Codex"));
document.getElementById("checkpointButton").addEventListener("click", () => renderPrompt("checkpoint-summary", "Checkpoint Summary"));
document.getElementById("resetApprovalButton").addEventListener("click", resetApproval);
document.getElementById("copyOutputButton").addEventListener("click", copyOutput);
document.getElementById("clearOutputButton").addEventListener("click", clearOutput);
document.getElementById("loadGitStatus").addEventListener("click", loadGitStatus);
elements.targetFilesInput.addEventListener("input", () => {
  state.scopeConfirmed = false;
  updateConfirmationWarning();
});
elements.targetFilesInput.addEventListener("input", updateTaskPromptSummary);
elements.commitMessage.addEventListener("input", updateTaskPromptSummary);

updateStep(1);
setOutput("No artifact yet", "");

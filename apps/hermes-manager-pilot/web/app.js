const state = {
  step: 1,
  session: null,
  repo: "C:\\work\\jarvis-core",
  artifactTitle: "No artifact yet",
  output: "",
  scopeConfirmed: false,
  review: null,
  localSessionId: "",
  savePreview: null,
  deletePreview: null,
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
  privacyAcknowledged: document.getElementById("privacyAcknowledged"),
  retentionAcknowledged: document.getElementById("retentionAcknowledged"),
  confirmDurableSaveButton: document.getElementById("confirmDurableSaveButton"),
  savedReviewSelect: document.getElementById("savedReviewSelect"),
  reviewIdInput: document.getElementById("reviewIdInput"),
  reopenScopeConfirmed: document.getElementById("reopenScopeConfirmed"),
  deleteConfirmationInput: document.getElementById("deleteConfirmationInput"),
  confirmDeleteReviewButton: document.getElementById("confirmDeleteReviewButton"),
  durableReviewDetails: document.getElementById("durableReviewDetails"),
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
  state.session.last_codex_result_summary = state.review && reviewMatchesSession()
    ? state.review.resultSummary
    : elements.codexResult.value.trim();
  state.session.commit_message = elements.commitMessage.value.trim() || state.session.commit_message;
  state.session.push_allowed = false;
}

function reviewMatchesSession() {
  if (!state.review || !state.session) return false;
  const sessionTargets = Array.isArray(state.session.target_files) ? state.session.target_files : [];
  return (
    state.review.activeTask === state.session.active_task &&
    JSON.stringify(state.review.targetFiles) === JSON.stringify(sessionTargets)
  );
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
    const requestError = new Error(data.error || `Request failed: ${response.status}`);
    requestError.payload = data;
    throw requestError;
  }
  return data;
}

async function lifecyclePost(path, payload) {
  if (!state.localSessionId) {
    throw new Error("local_review_session_unavailable");
  }
  const response = await fetch(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Hermes-Local-Session": state.localSessionId,
    },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok || !data.ok) {
    const requestError = new Error(data.error || `Request failed: ${response.status}`);
    requestError.payload = data;
    throw requestError;
  }
  return data;
}

function setDurableDetails(value) {
  elements.durableReviewDetails.textContent = typeof value === "string"
    ? value
    : JSON.stringify(value, null, 2);
}

function invalidateLifecyclePreviews() {
  state.savePreview = null;
  state.deletePreview = null;
  elements.confirmDurableSaveButton.disabled = true;
  elements.confirmDeleteReviewButton.disabled = true;
  elements.deleteConfirmationInput.value = "";
  elements.deleteConfirmationInput.placeholder = "Preview deletion first";
}

function requestedReviewId() {
  return elements.reviewIdInput.value.trim();
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
    state.review = null;
    invalidateLifecyclePreviews();
    elements.codexResult.value = "";
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
  state.review = null;
  invalidateLifecyclePreviews();
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
  if (!state.review) {
    setStatus("Save the Codex result as a Review object before creating a Jarvis handoff.");
    return;
  }
  if (!reviewMatchesSession()) {
    setStatus("The saved Review object no longer matches the current task and target-file scope.");
    return;
  }
  state.session.last_codex_result_summary = state.review.resultSummary;
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
  state.review = Object.freeze({
    activeTask: state.session.active_task,
    targetFiles: Object.freeze([...(state.session.target_files || [])]),
    resultSummary: result,
  });
  invalidateLifecyclePreviews();
  state.session.last_codex_result_summary = state.review.resultSummary;
  updateStep(5);
  setStatus("Review object saved. Copy a Jarvis handoff or render a direct review prompt.");
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
  state.review = null;
  elements.codexResult.value = "";
  elements.reviewedCheckbox.checked = false;
  elements.approveCheckbox.checked = false;
  state.scopeConfirmed = false;
  invalidateLifecyclePreviews();
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

async function initializeReviewLifecycle() {
  try {
    const response = await fetch("/api/local-session", { cache: "no-store" });
    const data = await response.json();
    if (!response.ok || !data.ok || !data.local_session_id) {
      throw new Error(data.error || "local_review_session_unavailable");
    }
    state.localSessionId = data.local_session_id;
    await refreshSavedReviews();
  } catch (error) {
    state.localSessionId = "";
    setDurableDetails(`Durable Review lifecycle unavailable: ${error.message}`);
  }
}

async function refreshSavedReviews(options = {}) {
  const preserveDetails = options && options.preserveDetails === true;
  try {
    const data = await lifecyclePost("/api/reviews/list", {});
    const previous = requestedReviewId();
    elements.savedReviewSelect.replaceChildren();
    const emptyOption = document.createElement("option");
    emptyOption.value = "";
    emptyOption.textContent = data.listing.count
      ? "Select one saved Review"
      : "No saved Reviews";
    elements.savedReviewSelect.appendChild(emptyOption);
    data.listing.records.forEach((record) => {
      const option = document.createElement("option");
      option.value = record.review_id;
      option.textContent = `${record.created_at} — ${record.active_task} (${record.review_id})`;
      elements.savedReviewSelect.appendChild(option);
    });
    if (previous && data.listing.records.some((record) => record.review_id === previous)) {
      elements.savedReviewSelect.value = previous;
    }
    if (!preserveDetails) {
      setDurableDetails({
        status: "ready",
        saved_review_count: data.listing.count,
        capacity: data.listing.capacity,
        retention_policy: data.listing.retention_policy,
      });
    }
  } catch (error) {
    setDurableDetails({ status: "recovery_required", error: error.message });
  }
}

async function previewDurableSave() {
  if (!state.session || !state.review || !reviewMatchesSession()) {
    setStatus("Save one current in-memory Review object before previewing durable Save.");
    return;
  }
  if (!state.scopeConfirmed) {
    setStatus("Confirm the current target-file scope before previewing durable Save.");
    return;
  }
  updateSessionFromForm();
  try {
    const data = await lifecyclePost("/api/reviews/save-preview", {
      session: state.session,
      result_summary: state.review.resultSummary,
      scope_confirmed: true,
      privacy_acknowledged: elements.privacyAcknowledged.checked,
      retention_acknowledged: elements.retentionAcknowledged.checked,
    });
    state.savePreview = Object.freeze(data.preview);
    elements.confirmDurableSaveButton.disabled = false;
    const { confirmation_token: ignoredToken, ...displayPreview } = data.preview;
    setDurableDetails({ operation: "save_preview", ...displayPreview });
    setStatus(`Review ${data.preview.record.review_id} is previewed only. Confirm Durable Save to write it locally.`);
  } catch (error) {
    state.savePreview = null;
    elements.confirmDurableSaveButton.disabled = true;
    setDurableDetails({ operation: "save_preview_blocked", error: error.message });
    setStatus(`Durable Save preview blocked: ${error.message}`);
  }
}

async function confirmDurableSave() {
  if (!state.savePreview) {
    setStatus("Preview the exact durable Save first.");
    return;
  }
  const preview = state.savePreview;
  state.savePreview = null;
  elements.confirmDurableSaveButton.disabled = true;
  try {
    const data = await lifecyclePost("/api/reviews/save-confirm", {
      confirmation_token: preview.confirmation_token,
    });
    elements.reviewIdInput.value = data.receipt.review_id;
    setDurableDetails({ operation: "save_receipt", ...data.receipt });
    setStatus(`Saved ${data.receipt.review_id} locally. It grants no review, commit, or push approval.`);
    await refreshSavedReviews({ preserveDetails: true });
  } catch (error) {
    const uncertainId = error.payload && error.payload.review_id;
    if (uncertainId) elements.reviewIdInput.value = uncertainId;
    setDurableDetails({
      operation: "save_blocked_or_uncertain",
      error: error.message,
      review_id: uncertainId || "",
      recovery_action: uncertainId ? "Use Inspect Recovery before any new Save attempt." : "Create a new preview.",
    });
    setStatus(`Durable Save did not return success: ${error.message}. Do not retry blindly.`);
  }
}

async function reopenSavedReview() {
  const reviewId = requestedReviewId();
  if (!reviewId) {
    setStatus("Enter or select one exact Review ID first.");
    return;
  }
  try {
    const data = await lifecyclePost("/api/reviews/reopen", { review_id: reviewId });
    setDurableDetails({ operation: "read_only_reopen", record: data.record });
    setStatus(`Reopened ${reviewId} read-only. No workflow approval was restored.`);
  } catch (error) {
    setDurableDetails({ operation: "reopen_blocked", review_id: reviewId, error: error.message });
    setStatus(`Review reopen blocked: ${error.message}`);
  }
}

async function copyReopenedHandoff() {
  const reviewId = requestedReviewId();
  if (!reviewId) {
    setStatus("Enter or select one exact Review ID first.");
    return;
  }
  if (!elements.reopenScopeConfirmed.checked) {
    setStatus("Reconfirm the saved target files as the current review scope first.");
    return;
  }
  try {
    const data = await lifecyclePost("/api/reviews/reopen-handoff", {
      review_id: reviewId,
      scope_confirmed: true,
    });
    const { artifact, ...displayHandoff } = data.handoff;
    setOutput("Fresh Reopened Jarvis Review Handoff", artifact);
    setDurableDetails({
      operation: "fresh_reopen_to_handoff",
      clipboard: "output_only",
      ...displayHandoff,
    });
    const copyError = await copyText(artifact);
    const message = `Git-metadata-matched handoff ${data.handoff.item_id} regenerated from ${reviewId}. Content evidence and approval were not restored.`;
    setStatus(copyError ? `${message} Clipboard copy failed: ${copyError}` : `${message} Copied to clipboard.`);
  } catch (error) {
    const blockingReasons = error.payload && Array.isArray(error.payload.blocking_reasons)
      ? error.payload.blocking_reasons
      : [];
    setOutput("Fresh Handoff Blocked", "");
    setDurableDetails({
      operation: "reopen_to_handoff_blocked",
      review_id: reviewId,
      error: error.message,
      blocking_reasons: blockingReasons,
      artifact_created: false,
    });
    const reasonText = blockingReasons.length ? ` ${blockingReasons.join("; ")}` : "";
    setStatus(`Fresh handoff blocked: ${error.message}.${reasonText}`);
  }
}

async function inspectRecovery() {
  const reviewId = requestedReviewId();
  if (!reviewId) {
    setStatus("Enter one exact Review ID to inspect.");
    return;
  }
  try {
    const data = await lifecyclePost("/api/reviews/recovery", { review_id: reviewId });
    setDurableDetails({ operation: "read_only_recovery", ...data.inspection });
    setStatus(`Recovery inspection for ${reviewId}: ${data.inspection.status}. No data was changed.`);
  } catch (error) {
    setDurableDetails({ operation: "recovery_blocked", review_id: reviewId, error: error.message });
    setStatus(`Recovery inspection blocked: ${error.message}`);
  }
}

async function previewExactDelete() {
  const reviewId = requestedReviewId();
  if (!reviewId) {
    setStatus("Enter or select one exact Review ID first.");
    return;
  }
  try {
    const data = await lifecyclePost("/api/reviews/delete-preview", { review_id: reviewId });
    state.deletePreview = Object.freeze(data.preview);
    elements.confirmDeleteReviewButton.disabled = false;
    elements.deleteConfirmationInput.value = "";
    elements.deleteConfirmationInput.placeholder = data.preview.confirmation_text;
    const { confirmation_token: ignoredToken, ...displayPreview } = data.preview;
    setDurableDetails({
      operation: "exact_delete_preview",
      result_summary_included: false,
      ...displayPreview,
    });
    setStatus(`Type exactly "${data.preview.confirmation_text}" and confirm to delete only this Review.`);
  } catch (error) {
    state.deletePreview = null;
    elements.confirmDeleteReviewButton.disabled = true;
    setDurableDetails({ operation: "delete_preview_blocked", review_id: reviewId, error: error.message });
    setStatus(`Delete preview blocked: ${error.message}`);
  }
}

async function confirmExactDelete() {
  if (!state.deletePreview) {
    setStatus("Preview one exact deletion first.");
    return;
  }
  const preview = state.deletePreview;
  state.deletePreview = null;
  elements.confirmDeleteReviewButton.disabled = true;
  try {
    const data = await lifecyclePost("/api/reviews/delete-confirm", {
      confirmation_token: preview.confirmation_token,
      confirmation_text: elements.deleteConfirmationInput.value,
    });
    elements.reviewIdInput.value = "";
    elements.deleteConfirmationInput.value = "";
    setDurableDetails({ operation: "delete_receipt", ...data.receipt });
    setStatus(`Deleted exactly ${data.receipt.review_id}. No other Review was changed.`);
    await refreshSavedReviews({ preserveDetails: true });
  } catch (error) {
    setDurableDetails({ operation: "delete_blocked", review_id: preview.review_id, error: error.message });
    setStatus(`Exact deletion blocked: ${error.message}. Preview again before another attempt.`);
  }
}

document.getElementById("prepareButton").addEventListener("click", prepareSession);
document.getElementById("continueToTaskPromptButton").addEventListener("click", continueToTaskPrompt);
document.getElementById("copyTaskPromptButton").addEventListener("click", () => renderPrompt("implementation-prompt", "Task Prompt for Codex"));
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
document.getElementById("refreshSavedReviewsButton").addEventListener("click", refreshSavedReviews);
document.getElementById("previewDurableSaveButton").addEventListener("click", previewDurableSave);
document.getElementById("confirmDurableSaveButton").addEventListener("click", confirmDurableSave);
document.getElementById("reopenSavedReviewButton").addEventListener("click", reopenSavedReview);
document.getElementById("copyReopenedHandoffButton").addEventListener("click", copyReopenedHandoff);
document.getElementById("inspectRecoveryButton").addEventListener("click", inspectRecovery);
document.getElementById("previewDeleteReviewButton").addEventListener("click", previewExactDelete);
document.getElementById("confirmDeleteReviewButton").addEventListener("click", confirmExactDelete);
elements.savedReviewSelect.addEventListener("change", () => {
  elements.reviewIdInput.value = elements.savedReviewSelect.value;
  elements.reopenScopeConfirmed.checked = false;
  state.deletePreview = null;
  elements.confirmDeleteReviewButton.disabled = true;
  elements.deleteConfirmationInput.value = "";
});
elements.reviewIdInput.addEventListener("input", () => {
  elements.reopenScopeConfirmed.checked = false;
  state.deletePreview = null;
  elements.confirmDeleteReviewButton.disabled = true;
  elements.deleteConfirmationInput.value = "";
});
elements.privacyAcknowledged.addEventListener("change", () => {
  state.savePreview = null;
  elements.confirmDurableSaveButton.disabled = true;
});
elements.retentionAcknowledged.addEventListener("change", () => {
  state.savePreview = null;
  elements.confirmDurableSaveButton.disabled = true;
});
elements.targetFilesInput.addEventListener("input", () => {
  state.scopeConfirmed = false;
  state.review = null;
  invalidateLifecyclePreviews();
  updateConfirmationWarning();
});
elements.targetFilesInput.addEventListener("input", updateTaskPromptSummary);
elements.commitMessage.addEventListener("input", updateTaskPromptSummary);

updateStep(1);
setOutput("No artifact yet", "");
initializeReviewLifecycle();

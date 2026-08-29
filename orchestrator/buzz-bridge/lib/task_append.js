"use strict";

/**
 * Minimal, append-only bridge between a Buzz Bridge run and its Jarvis task
 * file (memory/tasks/<taskId>.md), plus the one small same-machine guard
 * needed so two runs against the same taskId cannot interleave their
 * appends. No DB, no event log, no lock service/daemon - this is a plain
 * fs module used directly by orchestrator.js.
 *
 * appendRunRecord() never creates, edits, or deletes existing task
 * content: it opens the file in OS append mode (fs.appendFileSync, flag
 * "a"), so a failure partway through a write can never corrupt bytes that
 * were already there. It also never creates a new task file - a taskId
 * with no existing file is rejected, not auto-created. It never touches
 * the `- status:` line or any other existing line.
 *
 * Appended run-correlation fields (channel/run_id/status/...) are
 * deliberately rendered as `* field: \`value\`` (asterisk), never
 * `- field: \`value\`` (dash). Jarvis's task metadata parser treats every
 * line in the WHOLE file that starts with "- " (after stripping leading
 * whitespace) as a metadata candidate and rejects the file outright if it
 * does not match its fixed field allowlist - so a dash-bulleted run record
 * would make every later task-file metadata read/transition fail closed
 * for that task. The asterisk marker is invisible to that scan while
 * staying valid, readable Markdown. This is the one formatting rule this
 * module must never regress.
 *
 * acquireTaskLock() is a single exclusive marker file per taskId
 * (fs "wx" flag - atomic create-if-absent on NTFS and POSIX alike),
 * created and released entirely inside one process's try/finally. It does
 * not queue or retry a blocked run - a second run for the same taskId
 * fails closed immediately.
 */

const fs = require("fs");
const os = require("os");
const path = require("path");

// Same charset docs/task-file-creation.md defines for a real task filename
// (^task-(\d{4})-([a-z0-9]+(?:-[a-z0-9]+)*)\.md$). Reusing it here both
// validates the id AND is the path-traversal defense: no `.`, `/`, `\`, or
// any byte outside [a-z0-9-] can ever reach path.join below.
const TASK_ID_PATTERN = /^task-\d{4}-[a-z0-9]+(?:-[a-z0-9]+)*$/;

const TASKS_DIR = path.join(__dirname, "..", "..", "..", "memory", "tasks");
const LOCK_DIR = path.join(os.tmpdir(), "jarvis-buzz-bridge-task-locks");

function isValidTaskId(taskId) {
  return typeof taskId === "string" && TASK_ID_PATTERN.test(taskId);
}

function resolveTaskFilePath(taskId) {
  if (!isValidTaskId(taskId)) {
    throw new Error(`invalid taskId "${taskId}" - must match ${TASK_ID_PATTERN} (an existing memory/tasks file)`);
  }
  const resolved = path.resolve(TASKS_DIR, `${taskId}.md`);
  const tasksDirWithSep = path.resolve(TASKS_DIR) + path.sep;
  if (!resolved.startsWith(tasksDirWithSep)) {
    // Defense in depth - TASK_ID_PATTERN already makes this unreachable via
    // the public API, but a resolved-path check should not depend solely
    // on the regex staying correct forever.
    throw new Error(`resolved task file path escapes memory/tasks/: ${resolved}`);
  }
  return resolved;
}

function formatUtcTimestamp(date) {
  const iso = (date || new Date()).toISOString(); // 2026-08-29T12:00:00.000Z
  return `${iso.slice(0, 10)} ${iso.slice(11, 16)} UTC`;
}

/**
 * Appends one run record to an EXISTING task file. Throws (never creates
 * the file, never writes anything) if the taskId is invalid or the file
 * does not already exist. Callers must catch this themselves - an append
 * failure must never crash the run that produced the record.
 */
function appendRunRecord(taskId, record) {
  const filePath = resolveTaskFilePath(taskId);
  if (!fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) {
    throw new Error(`task file does not exist, refusing to create one: ${filePath}`);
  }

  const timestamp = formatUtcTimestamp();
  // Asterisk bullets, not dash bullets - see the module docstring above.
  // This is run-correlation data, not task lifecycle metadata: it never
  // changes, and must never be mistaken for, this task's own `- status:`.
  const lines = [
    "",
    "---",
    "",
    `## [${timestamp}] Buzz Bridge 실행 기록 — run ${record.runId}`,
    "",
    "이 섹션은 append-only 기록이다. 기존 내용은 수정하지 않았다. 이 항목은 task 상태를 변경하지 않으며, Buzz 메시지/응답을 승인으로 취급하지 않는다(orchestrator/buzz-bridge/README.md 보안 불변식 참고). 아래 값은 이 task의 상태(metadata)가 아니라 이번 Buzz 실행 1회의 상관관계 정보다.",
    "",
    `* channel: \`${record.channelName}\` (id \`${record.channelId}\`)`,
    `* run_id: \`${record.runId}\``,
    `* outgoing_event_id: \`${record.outgoingEventId}\``,
    `* status: \`${record.status}\``,
  ];
  if (record.responseEventId) lines.push(`* response_event_id: \`${record.responseEventId}\``);
  if (record.agentPubkey) lines.push(`* agent_pubkey: \`${record.agentPubkey}\``);
  if (record.reason) lines.push(`* reason: \`${record.reason}\``);
  lines.push("");

  fs.appendFileSync(filePath, lines.join("\n"), { encoding: "utf8" });
  return { filePath };
}

function lockPathFor(taskId) {
  return path.join(LOCK_DIR, `${taskId}.lock`);
}

/** Throws immediately if a run for this taskId is already in progress. */
function acquireTaskLock(taskId) {
  if (!isValidTaskId(taskId)) {
    throw new Error(`invalid taskId "${taskId}" - must match ${TASK_ID_PATTERN}`);
  }
  fs.mkdirSync(LOCK_DIR, { recursive: true });
  const lockPath = lockPathFor(taskId);
  try {
    fs.writeFileSync(lockPath, String(process.pid), { flag: "wx" });
  } catch (err) {
    if (err.code === "EEXIST") {
      throw new Error(`a run for taskId "${taskId}" is already in progress (lock file: ${lockPath})`);
    }
    throw err;
  }
  return {
    release() {
      try {
        fs.unlinkSync(lockPath);
      } catch (err) {
        if (err.code !== "ENOENT") throw err;
      }
    },
  };
}

module.exports = {
  TASK_ID_PATTERN,
  TASKS_DIR,
  LOCK_DIR,
  isValidTaskId,
  resolveTaskFilePath,
  appendRunRecord,
  acquireTaskLock,
  lockPathFor,
};

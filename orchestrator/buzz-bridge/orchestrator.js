"use strict";

/**
 * Minimal Jarvis orchestrator for the Phase 2 first slice: delegate ONE
 * approval-free question to the Claude agent over Buzz and wait for a
 * correlated response.
 *
 * Jarvis Orchestrator = task state + approval + delegation authority. This
 * script owns: channel creation, the run_id/task_id correlation record, and
 * response validation. It never treats an inbound Buzz message as an
 * approval or as execution permission (there is no approval flow in this
 * slice at all - see Design Revision APPROVAL_BOUNDARY).
 *
 * Usage:
 *   node orchestrator.js "<question for the agent>" [timeoutMs] [taskId]
 *
 * taskId (optional, P2-2) must be an existing memory/tasks/<taskId>.md id
 * (task-####-slug). When given, the run's correlation record is appended
 * to that file (lib/task_append.js) after the run finishes - never before,
 * never as a status change, never treated as approval. When omitted,
 * behavior is unchanged from the original slice-1 script: no task file is
 * read, created, or touched.
 */

const crypto = require("crypto");
const path = require("path");
const {
  connectAndWaitForChallenge,
  authenticate,
  publish,
  subscribeLive,
  ensureChannel,
  buildChannelMessage,
  tagValue,
  nextSinceFilter,
  verifyEvent,
} = require("./lib/nostr");
const { loadIdentities } = require("./lib/identities");
const { CHANNEL_NAME } = require("./lib/constants");
const { appendRunRecord, isValidTaskId, acquireTaskLock } = require("./lib/task_append");

function loadConfig() {
  require("./lib/env").loadEnvFile(path.join(__dirname, ".env"));
  if (!process.env.RELAY_URL) {
    throw new Error("missing required env var: RELAY_URL");
  }
  const identities = loadIdentities();
  return {
    relayUrl: process.env.RELAY_URL,
    privkeyHex: identities.orchestrator.privkeyHex,
    ownPubkey: identities.orchestrator.pubkeyHex,
    expectedAgentPubkey: identities.agentClaude.pubkeyHex,
  };
}

/**
 * Jarvis inbound response gate (Design Revision IDENTITY_AND_AUTH).
 * ALL FOUR must hold or the candidate event is rejected as an anomaly -
 * never treated as the run's answer, never treated as approval of anything.
 * verifyEvent is checked again here even though lib/nostr.js already drops
 * unverified events, so this function is correct standalone (audit
 * CRITICAL#1 - tag matches alone are not authentication).
 */
function passesResponseGate(candidate, { outgoingEventId, runId, expectedAgentPubkey }) {
  if (!verifyEvent(candidate)) {
    return { ok: false, reason: "invalid signature (verifyEvent failed)" };
  }
  const eTag = tagValue(candidate, "e");
  const runTag = tagValue(candidate, "jarvis-run");
  if (eTag !== outgoingEventId) return { ok: false, reason: `e tag (${eTag}) != outgoing event id` };
  if (runTag !== runId) return { ok: false, reason: `jarvis-run tag (${runTag}) != expected run_id` };
  if (candidate.pubkey !== expectedAgentPubkey) {
    return { ok: false, reason: `signer pubkey (${candidate.pubkey}) != expected agent for this run` };
  }
  return { ok: true };
}

/**
 * @param {string} [realTaskId] - an existing memory/tasks/<realTaskId>.md
 *   id (task-####-slug). Optional for backward compatibility: when
 *   omitted, behavior is byte-identical to the original slice-1 script -
 *   no task file is read, created, or appended to. When given, it must
 *   already exist as a task file; this function never creates one.
 */
async function delegateOneQuestion(question, timeoutMs, realTaskId) {
  if (realTaskId !== undefined && !isValidTaskId(realTaskId)) {
    throw new Error(`invalid taskId "${realTaskId}" - expected format task-####-slug (an existing memory/tasks file)`);
  }

  // Fails closed immediately if a run for this taskId is already in
  // progress - no queueing, no retry. Released in `finally` below no
  // matter how this run ends (success, failure, or timeout).
  const taskLock = realTaskId ? acquireTaskLock(realTaskId) : null;

  try {
    const cfg = loadConfig();
    // Wire-protocol task id: always non-empty so bridge.js's inbound gate
    // (which only checks the tag is present, not its specific value) keeps
    // working unchanged. Falls back to the original slice-1 placeholder
    // when no real task is given, so existing 2-arg callers see the same
    // behavior as before this change.
    const taskId = realTaskId || "task-buzz-slice-manual";
    const runId = `run-${crypto.randomBytes(8).toString("hex")}`;

    console.log(`[orchestrator] connecting to ${cfg.relayUrl}`);
    const { ws, challenge } = await connectAndWaitForChallenge(cfg.relayUrl);
    await authenticate(ws, cfg.privkeyHex, cfg.relayUrl, challenge);
    console.log(`[orchestrator] authenticated as ${cfg.ownPubkey}`);

    const channelResult = await ensureChannel(ws, cfg.privkeyHex, CHANNEL_NAME);
    const channelId = channelResult.channelId;
    console.log(`[orchestrator] channel "${CHANNEL_NAME}" ready (id ${channelId}, created=${channelResult.created})`);

    const outgoing = buildChannelMessage(cfg.privkeyHex, channelId, question, [
      ["p", cfg.expectedAgentPubkey],
      ["jarvis-task", taskId],
      ["jarvis-run", runId],
    ]);

    const result = await new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        unsubscribe();
        resolve({ status: "TIMEOUT", reason: `no valid response within ${timeoutMs}ms` });
      }, timeoutMs);

      const waitFilter = nextSinceFilter({ kinds: [9], "#h": [channelId] }, null);
      const unsubscribe = subscribeLive(ws, "orchestrator-live", waitFilter, (candidate) => {
        try {
          if (candidate.pubkey === cfg.ownPubkey) return; // ignore our own outgoing message
          const gate = passesResponseGate(candidate, {
            outgoingEventId: outgoing.id,
            runId,
            expectedAgentPubkey: cfg.expectedAgentPubkey,
          });
          if (!gate.ok) {
            console.log(`[orchestrator] ANOMALY: ignoring candidate ${candidate.id} - ${gate.reason}`);
            return;
          }
          clearTimeout(timer);
          unsubscribe();
          resolve({ status: "OK", responseEvent: candidate });
        } catch (err) {
          console.error(`[orchestrator] event processing error: ${err.stack || err.message}`);
        }
      });

      publish(ws, outgoing)
        .then(() => console.log(`[orchestrator] delegated run ${runId} (event ${outgoing.id}), waiting for response...`))
        .catch((err) => {
          clearTimeout(timer);
          unsubscribe();
          reject(err);
        });
    });

    ws.close();
    const outcome = { taskId, runId, channelId, outgoingEventId: outgoing.id, ...result };

    if (realTaskId) {
      // A failed append must never look like a failed run: it is reported
      // separately on the same outcome object, and only ever logged, never
      // thrown (Design constraint: append failure must not take down or
      // mask the actual run result).
      try {
        const { filePath } = appendRunRecord(realTaskId, {
          channelName: CHANNEL_NAME,
          channelId,
          runId,
          outgoingEventId: outgoing.id,
          status: outcome.status,
          responseEventId: outcome.responseEvent ? outcome.responseEvent.id : undefined,
          agentPubkey: outcome.responseEvent ? outcome.responseEvent.pubkey : undefined,
          reason: outcome.reason,
        });
        outcome.taskAppend = { ok: true, filePath };
      } catch (appendErr) {
        console.error(`[orchestrator] WARNING: run finished but task-file append failed for ${realTaskId}: ${appendErr.message}`);
        outcome.taskAppend = { ok: false, error: appendErr.message };
      }
    }

    return outcome;
  } finally {
    if (taskLock) taskLock.release();
  }
}

if (require.main === module) {
  const question = process.argv[2] || "이 문장을 한 문장으로 요약해줘: Jarvis-Core Phase 2 minimum slice smoke test.";
  const timeoutMs = Number(process.argv[3] || 120000);
  const taskId = process.argv[4] || undefined; // optional: existing memory/tasks/<taskId>.md
  delegateOneQuestion(question, timeoutMs, taskId)
    .then((result) => {
      console.log("\n=== ORCHESTRATOR RESULT ===");
      console.log(JSON.stringify(result, null, 2));
      process.exit(result.status === "OK" ? 0 : 1);
    })
    .catch((err) => {
      console.error(`[orchestrator] fatal: ${err.stack || err.message}`);
      process.exit(1);
    });
}

module.exports = { passesResponseGate, delegateOneQuestion };

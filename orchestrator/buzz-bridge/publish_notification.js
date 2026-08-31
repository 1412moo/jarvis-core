"use strict";

/**
 * Outbound-only Buzz notification publisher (P2-5).
 *
 * This process publishes ONE generic task-status notification event and
 * exits. That is its entire job.
 *
 * Boundary invariants (structural, not documentary):
 *   1. Outbound only. It never calls subscribeLive, never subscribes to
 *      kind 9, and closes the socket as soon as the publish is answered.
 *      The only relay->here data flow is ensureChannel's kind 39000
 *      metadata lookup, whose result is consumed solely as an opaque
 *      channel id string.
 *   2. It never reads or writes a task file, and never calls any Jarvis
 *      task-lifecycle function. Jarvis owns approval state; this file only
 *      reports a fact that Jarvis already committed.
 *   3. It never decides anything. `from`/`to` arrive as data on stdin and
 *      are echoed as data. There is no approval logic here, and the words
 *      approve/reject/grant/deny carry no meaning to this file.
 *   4. The published event can never be mistaken for work by bridge.js:
 *      buildNotificationTags() is the ONLY tag source and it is a fixed
 *      two-tag literal, so a `p` mention tag or a `jarvis-run` tag cannot
 *      be added through any code path. bridge.js's passesInboundGate
 *      requires both, so it rejects this event outright. The dedicated
 *      channel below is the second, independent layer: bridge.js filters
 *      on `#h` of its own channel, so it never even receives this event.
 *   5. It does not call orchestrator.js or bridge.js.
 *
 * Usage:  echo '<json>' | node publish_notification.js
 * stdin:  {"task_id","from","to","execution_status_transition_applied","ts"}
 * stdout: one JSON object. exit 0 on publish, 1 on any failure.
 */

const path = require("path");
const {
  connectAndWaitForChallenge,
  authenticate,
  publish,
  ensureChannel,
  buildChannelMessage,
} = require("./lib/nostr");
const { loadIdentities } = require("./lib/identities");

/**
 * Deliberately NOT lib/constants.js's CHANNEL_NAME. Notifications go to
 * their own channel so bridge.js's `#h` subscription filter never matches
 * them - otherwise every notification would print an "ANOMALY: rejected
 * inbound event" line and train the operator to ignore that log.
 * Only this file uses this name, so there is no cross-process drift risk
 * of the kind lib/constants.js exists to prevent.
 */
const NOTIFICATION_CHANNEL_NAME = "jarvis-task-status-notifications";

const STDIN_MAX_BYTES = 64 * 1024;
const REQUIRED_STRING_FIELDS = ["task_id", "from", "to", "ts"];

function readStdin() {
  return new Promise((resolve, reject) => {
    let data = "";
    let bytes = 0;
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (chunk) => {
      bytes += Buffer.byteLength(chunk, "utf8");
      if (bytes > STDIN_MAX_BYTES) {
        reject(new Error(`stdin exceeded ${STDIN_MAX_BYTES} bytes`));
        return;
      }
      data += chunk;
    });
    process.stdin.on("end", () => resolve(data));
    process.stdin.on("error", reject);
  });
}

/** Pure validation. Throws on anything malformed - never guesses a default. */
function parseNotificationInput(raw) {
  let parsed;
  try {
    parsed = JSON.parse(raw);
  } catch (err) {
    throw new Error(`invalid stdin JSON: ${err.message}`);
  }
  if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("stdin JSON must be an object");
  }
  for (const field of REQUIRED_STRING_FIELDS) {
    if (typeof parsed[field] !== "string" || parsed[field].trim() === "") {
      throw new Error(`missing or non-string field: ${field}`);
    }
  }
  if (typeof parsed.execution_status_transition_applied !== "boolean") {
    throw new Error("missing or non-boolean field: execution_status_transition_applied");
  }
  return {
    task_id: parsed.task_id,
    from: parsed.from,
    to: parsed.to,
    execution_status_transition_applied: parsed.execution_status_transition_applied,
    ts: parsed.ts,
  };
}

/**
 * Generic status fact - no instruction, no decision, no approval verb.
 * Whoever reads this learns that a transition happened, not what to do.
 */
function buildNotificationContent(input) {
  return JSON.stringify({
    notification_type: "task_status",
    task_id: input.task_id,
    from: input.from,
    to: input.to,
    execution_status_transition_applied: input.execution_status_transition_applied,
    ts: input.ts,
  });
}

/**
 * The ONLY place tags are produced. A fixed literal, so no caller, config,
 * or stdin field can inject a `p` or `jarvis-run` tag (invariant 4 above).
 */
function buildNotificationTags(taskId) {
  return [
    ["jarvis-task", taskId],
    ["jarvis-notification", "task_status"],
  ];
}

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
  };
}

async function publishNotification(input) {
  const cfg = loadConfig();
  const { ws, challenge } = await connectAndWaitForChallenge(cfg.relayUrl);
  try {
    await authenticate(ws, cfg.privkeyHex, cfg.relayUrl, challenge);
    const channelResult = await ensureChannel(ws, cfg.privkeyHex, NOTIFICATION_CHANNEL_NAME);
    const event = buildChannelMessage(
      cfg.privkeyHex,
      channelResult.channelId,
      buildNotificationContent(input),
      buildNotificationTags(input.task_id)
    );
    await publish(ws, event);
    return {
      status: "published",
      channel: NOTIFICATION_CHANNEL_NAME,
      channel_id: channelResult.channelId,
      event_id: event.id,
      task_id: input.task_id,
    };
  } finally {
    // Always closed, on the success path and on every throw above.
    ws.close();
  }
}

async function main() {
  let input;
  try {
    input = parseNotificationInput(await readStdin());
  } catch (err) {
    console.log(JSON.stringify({ status: "invalid_input", error: err.message }));
    process.exit(1);
    return;
  }
  try {
    console.log(JSON.stringify(await publishNotification(input)));
    process.exit(0);
  } catch (err) {
    console.log(JSON.stringify({ status: "publish_failed", error: String(err && err.message ? err.message : err) }));
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = {
  NOTIFICATION_CHANNEL_NAME,
  parseNotificationInput,
  buildNotificationContent,
  buildNotificationTags,
  publishNotification,
};

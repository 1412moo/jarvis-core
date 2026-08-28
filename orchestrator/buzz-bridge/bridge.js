"use strict";

/**
 * Claude agent bridge (Phase 2 minimum slice - Claude only, no Codex/agy).
 *
 * Responsibilities, and only these (Agent Bridge != policy engine):
 *   1. subscribe to the fixed Buzz channel
 *   2. accept an inbound event only if ALL of these hold (hard-coded here,
 *      independent of relay-side membership/allowlist config):
 *        a. event carries a valid Schnorr signature (verifyEvent) - checked
 *           again here even though lib/nostr.js already drops unverified
 *           events, so this function is correct standalone (audit CRITICAL#1)
 *        b. event.pubkey === JARVIS_ORCHESTRATOR_PUBKEY
 *        c. event has a ["p", <this bridge's own pubkey>] mention tag
 *        d. event has parseable ["jarvis-task", ...] and ["jarvis-run", ...] tags
 *   3. invoke the Claude CLI adapter (restricted, stdin, sandboxed, env
 *      whitelist - see claude_adapter.js) with the event content as prompt
 *   4. publish a signed response event carrying ["e", original_id] and
 *      ["jarvis-run", run_id] so Jarvis can correlate it
 *
 * No approval logic, no policy judgement, no direct connection to Jarvis
 * beyond the shared Buzz channel.
 */

const path = require("path");
const {
  connectAndWaitForChallenge,
  authenticate,
  publish,
  subscribeLive,
  findChannelByName,
  buildChannelMessage,
  tagValue,
  nextSinceFilter,
  verifyEvent,
} = require("./lib/nostr");
const { BoundedSeenSet } = require("./lib/dedupe");
const { invokeClaude } = require("./claude_adapter");
const { loadIdentities } = require("./lib/identities");
const { CHANNEL_NAME } = require("./lib/constants");

const FUTURE_CLOCK_SKEW_TOLERANCE_SECONDS = 60;
const CHANNEL_ERROR_CONTENT_MAX_CHARS = 200;

function loadConfig() {
  require("./lib/env").loadEnvFile(path.join(__dirname, ".env"));
  if (!process.env.RELAY_URL) {
    throw new Error("missing required env var: RELAY_URL");
  }
  const identities = loadIdentities();
  return {
    relayUrl: process.env.RELAY_URL,
    privkeyHex: identities.agentClaude.privkeyHex,
    ownPubkey: identities.agentClaude.pubkeyHex,
    orchestratorPubkey: identities.orchestrator.pubkeyHex,
  };
}

/** Read-only existence wait. Bridge never creates the channel - only the
 * Jarvis Orchestrator identity does (CHANNEL_LIFECYCLE §생성 identity). */
async function waitForChannel(ws, channelName, { attempts = 10, intervalMs = 1000 } = {}) {
  for (let i = 0; i < attempts; i += 1) {
    const found = await findChannelByName(ws, channelName);
    if (found) return found;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  throw new Error(`channel "${channelName}" did not appear within ${attempts * intervalMs}ms - bridge does not create channels itself`);
}

function passesInboundGate(event, { ownPubkey, orchestratorPubkey }) {
  if (!verifyEvent(event)) {
    return { ok: false, reason: "invalid signature (verifyEvent failed)" };
  }
  if (event.pubkey !== orchestratorPubkey) {
    return { ok: false, reason: "sender pubkey != JARVIS_ORCHESTRATOR_PUBKEY" };
  }
  const mentioned = (event.tags || []).some((t) => t[0] === "p" && t[1] === ownPubkey);
  if (!mentioned) {
    return { ok: false, reason: "no [p, own_pubkey] mention tag" };
  }
  const taskId = tagValue(event, "jarvis-task");
  const runId = tagValue(event, "jarvis-run");
  if (!taskId || !runId) {
    return { ok: false, reason: "missing jarvis-task/jarvis-run tags" };
  }
  return { ok: true, taskId, runId };
}

/** Truncated, generic content for the public Nostr channel - full detail
 * (stderr, stack traces, local paths) stays in the local console only
 * (audit LOW#3). */
function publicErrorSummary(error) {
  const oneLine = String(error).split("\n")[0];
  return oneLine.length > CHANNEL_ERROR_CONTENT_MAX_CHARS
    ? `${oneLine.slice(0, CHANNEL_ERROR_CONTENT_MAX_CHARS)}...`
    : oneLine;
}

async function processEvent(ws, cfg, event, gate) {
  if (!gate.ok) {
    console.log(`[bridge] ANOMALY: rejected inbound event ${event.id} - ${gate.reason}`);
    return;
  }

  console.log(`[bridge] accepted run ${gate.runId} (task ${gate.taskId}) from event ${event.id}`);
  const result = await invokeClaude(event.content);
  if (!result.success) {
    console.error(`[bridge] claude invocation failed for run ${gate.runId}: ${result.error}`);
  }

  const responseContent = result.success
    ? JSON.stringify({ status: "ok", claude_result: result.output })
    : JSON.stringify({ status: "run_failed", error: publicErrorSummary(result.error) });

  const responseEvent = buildChannelMessage(cfg.privkeyHex, cfg.channelId, responseContent, [
    ["e", event.id],
    ["p", event.pubkey],
    ["jarvis-task", gate.taskId],
    ["jarvis-run", gate.runId],
  ]);
  await publish(ws, responseEvent);
  console.log(`[bridge] published response ${responseEvent.id} for run ${gate.runId} (success=${result.success})`);
}

async function main() {
  const cfg = loadConfig();
  console.log(`[bridge] connecting to ${cfg.relayUrl}`);
  const { ws, challenge } = await connectAndWaitForChallenge(cfg.relayUrl);
  await authenticate(ws, cfg.privkeyHex, cfg.relayUrl, challenge);
  console.log(`[bridge] authenticated as ${cfg.ownPubkey}`);

  const channelMetadata = await waitForChannel(ws, CHANNEL_NAME);
  cfg.channelId = tagValue(channelMetadata, "d");
  console.log(`[bridge] channel "${CHANNEL_NAME}" confirmed to exist (id ${cfg.channelId})`);

  const seen = new BoundedSeenSet();
  let lastSeenCreatedAt = null; // reconnect cursor, see lib/nostr.js#nextSinceFilter
  const initialFilter = nextSinceFilter({ kinds: [9], "#h": [cfg.channelId] }, lastSeenCreatedAt);

  // Sequential queue (audit MEDIUM#3): events are processed one at a time,
  // not fanned out into N concurrent `claude` subprocesses sharing one
  // sandbox dir. Each step is wrapped in try/catch (audit HIGH#1) so one
  // failed publish()/invokeClaude() can never become an unhandled promise
  // rejection that kills the whole bridge process.
  let queue = Promise.resolve();

  const unsubscribe = subscribeLive(ws, "bridge-live", initialFilter, (event) => {
    if (event.pubkey === cfg.ownPubkey) return; // self-loop guard
    if (seen.hasSeen(event.id)) return;
    seen.markSeen(event.id);

    queue = queue
      .then(async () => {
        const gate = passesInboundGate(event, cfg);
        // Cursor only advances for events that pass the gate and are not
        // implausibly far in the future (audit MEDIUM#5: an attacker or a
        // clock-skewed event could otherwise pin the reconnect cursor past
        // every legitimate future message).
        const nowSeconds = Math.floor(Date.now() / 1000);
        if (gate.ok && event.created_at <= nowSeconds + FUTURE_CLOCK_SKEW_TOLERANCE_SECONDS) {
          if (lastSeenCreatedAt === null || event.created_at > lastSeenCreatedAt) {
            lastSeenCreatedAt = event.created_at;
          }
        }
        await processEvent(ws, cfg, event, gate);
      })
      .catch((err) => {
        console.error(`[bridge] event processing error for ${event.id}: ${err.stack || err.message}`);
      });
  });

  process.on("SIGINT", () => {
    unsubscribe();
    ws.close();
    process.exit(0);
  });
}

if (require.main === module) {
  main().catch((err) => {
    console.error(`[bridge] fatal: ${err.stack || err.message}`);
    process.exit(1);
  });
}

module.exports = { passesInboundGate, waitForChannel, publicErrorSummary };

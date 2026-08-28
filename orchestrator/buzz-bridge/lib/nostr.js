"use strict";

/**
 * Thin local Buzz Relay client: raw WebSocket + NIP-42 auth + channel
 * lifecycle helpers. Generalizes the hands-on pattern validated in
 * task-0047 (S3-S7, all PASS) into reusable functions for the Phase 2
 * minimum slice. No policy/approval logic lives here - this module only
 * knows how to talk to the relay.
 */

const WebSocket = require("ws");
const {
  generateSecretKey,
  getPublicKey,
  finalizeEvent,
  verifyEvent,
} = require("nostr-tools/pure");

const KIND_AUTH = 22242;
const KIND_CHANNEL_CREATE = 9007;
const KIND_CHANNEL_METADATA = 39000;
const KIND_CHANNEL_MESSAGE = 9;

function generateIdentity() {
  const sk = generateSecretKey();
  const pubkey = getPublicKey(sk);
  return { privkeyHex: Buffer.from(sk).toString("hex"), pubkeyHex: pubkey };
}

function skFromHex(hex) {
  return Uint8Array.from(Buffer.from(hex, "hex"));
}

/**
 * Connects and waits for the relay's proactive AUTH challenge
 * (task-0047 S4: challenge arrives unsolicited right after connect).
 */
function connectAndWaitForChallenge(relayUrl, { timeoutMs = 10000 } = {}) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(relayUrl);
    const timer = setTimeout(() => {
      ws.terminate();
      reject(new Error("timed out waiting for AUTH challenge"));
    }, timeoutMs);

    ws.once("open", () => {
      /* wait for the server-initiated AUTH frame */
    });
    ws.once("message", (raw) => {
      clearTimeout(timer);
      let msg;
      try {
        msg = JSON.parse(raw.toString());
      } catch (err) {
        reject(new Error(`non-JSON first frame: ${err.message}`));
        return;
      }
      if (msg[0] !== "AUTH" || typeof msg[1] !== "string") {
        reject(new Error(`expected first frame ["AUTH", challenge], got ${JSON.stringify(msg)}`));
        return;
      }
      resolve({ ws, challenge: msg[1] });
    });
    ws.once("error", (err) => {
      clearTimeout(timer);
      reject(err);
    });
  });
}

/** NIP-42 auth completion: sign kind 22242, send ["AUTH", event], wait for OK. */
function authenticate(ws, skHex, relayUrl, challenge, { timeoutMs = 10000 } = {}) {
  const sk = skFromHex(skHex);
  const event = finalizeEvent(
    {
      kind: KIND_AUTH,
      created_at: Math.floor(Date.now() / 1000),
      tags: [
        ["relay", relayUrl],
        ["challenge", challenge],
      ],
      content: "",
    },
    sk
  );

  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      reject(new Error("timed out waiting for AUTH OK"));
    }, timeoutMs);

    function onMessage(raw) {
      let msg;
      try {
        msg = JSON.parse(raw.toString());
      } catch {
        return;
      }
      if (msg[0] === "OK" && msg[1] === event.id) {
        clearTimeout(timer);
        ws.removeListener("message", onMessage);
        if (msg[2] === true) {
          resolve(event.id);
        } else {
          reject(new Error(`AUTH rejected: ${msg[3] || "no reason given"}`));
        }
      }
    }
    ws.on("message", onMessage);
    ws.send(JSON.stringify(["AUTH", event]));
  });
}

/** Publish an already-built, already-signed event and wait for relay OK. */
function publish(ws, event, { timeoutMs = 10000 } = {}) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      reject(new Error(`timed out waiting for OK on published event ${event.id}`));
    }, timeoutMs);

    function onMessage(raw) {
      let msg;
      try {
        msg = JSON.parse(raw.toString());
      } catch {
        return;
      }
      if (msg[0] === "OK" && msg[1] === event.id) {
        clearTimeout(timer);
        ws.removeListener("message", onMessage);
        if (msg[2] === true) {
          resolve(event);
        } else {
          reject(new Error(`publish rejected: ${msg[3] || "no reason given"}`));
        }
      }
    }
    ws.on("message", onMessage);
    ws.send(JSON.stringify(["EVENT", event]));
  });
}

function signEvent(skHex, template) {
  return finalizeEvent(template, skFromHex(skHex));
}

/**
 * One-shot REQ: collects matching events until EOSE, then closes the
 * subscription. Used for the channel-existence check.
 */
function queryOnce(ws, subId, filter, { timeoutMs = 10000 } = {}) {
  return new Promise((resolve, reject) => {
    const events = [];
    const timer = setTimeout(() => {
      cleanup();
      reject(new Error(`timed out waiting for EOSE on ${subId}`));
    }, timeoutMs);

    function cleanup() {
      clearTimeout(timer);
      ws.removeListener("message", onMessage);
    }

    function onMessage(raw) {
      let msg;
      try {
        msg = JSON.parse(raw.toString());
      } catch {
        return;
      }
      if (msg[0] === "EVENT" && msg[1] === subId) {
        if (!verifyEvent(msg[2])) {
          console.error(`[nostr] ANOMALY: dropped event ${msg[2] && msg[2].id} on ${subId} - Schnorr signature verification failed`);
          return;
        }
        events.push(msg[2]);
      } else if (msg[0] === "EOSE" && msg[1] === subId) {
        cleanup();
        ws.send(JSON.stringify(["CLOSE", subId]));
        resolve(events);
      } else if (msg[0] === "CLOSED" && msg[1] === subId) {
        cleanup();
        reject(new Error(`subscription closed: ${msg[2] || "no reason given"}`));
      }
    }
    ws.on("message", onMessage);
    ws.send(JSON.stringify(["REQ", subId, filter]));
  });
}

/**
 * Open-ended subscription. Calls onEvent for every matching EVENT frame
 * (including ones that arrive after EOSE - that is the live stream).
 * Returns an unsubscribe function.
 */
function subscribeLive(ws, subId, filter, onEvent) {
  function onMessage(raw) {
    let msg;
    try {
      msg = JSON.parse(raw.toString());
    } catch {
      return;
    }
    if (msg[0] === "EVENT" && msg[1] === subId) {
      if (!verifyEvent(msg[2])) {
        console.error(`[nostr] ANOMALY: dropped event ${msg[2] && msg[2].id} on ${subId} - Schnorr signature verification failed`);
        return;
      }
      onEvent(msg[2]);
    }
  }
  ws.on("message", onMessage);
  ws.send(JSON.stringify(["REQ", subId, filter]));
  return function unsubscribe() {
    ws.removeListener("message", onMessage);
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(["CLOSE", subId]));
    }
  };
}

/**
 * The relay does not adopt the client-supplied `h` tag as the channel's
 * identity - on kind 9007 it mints its OWN uuid, which is what ends up in
 * the `d` tag of the kind 39000 metadata sidecar (found during Phase 2
 * slice 1 e2e testing; not documented by task-0047). The relay also does
 * not index kind 39000 by `name`, so lookup-by-name has to pull recent
 * metadata events and match client-side. `channelName` (not a UUID) is
 * therefore the one stable, config-owned identifier - both ensureChannel
 * and any caller that just needs to find an existing channel use this.
 */
async function findChannelByName(ws, channelName, { sinceFloor, limit = 100 } = {}) {
  const filter = { kinds: [KIND_CHANNEL_METADATA], limit };
  if (typeof sinceFloor === "number") filter.since = sinceFloor;
  const events = await queryOnce(ws, `find-by-name-${Date.now()}-${Math.random().toString(36).slice(2)}`, filter);
  return events.find((e) => tagValue(e, "name") === channelName) || null;
}

/**
 * Channel lifecycle per Design Revision CHANNEL_LIFECYCLE:
 *   존재 확인 -> 없으면 생성(kind 9007) -> 생성 결과(kind 39000) 확인 -> 반환
 * Idempotent: safe to call every startup, from any process, in any order -
 * both branches converge on the same relay-assigned channelId as long as
 * `channelName` is the same string. Does not subscribe by itself - callers
 * subscribe separately after this resolves.
 */
async function ensureChannel(ws, skHex, channelName) {
  const existing = await findChannelByName(ws, channelName);
  if (existing) {
    return { created: false, channelId: tagValue(existing, "d"), metadataEvent: existing };
  }

  const createEvent = signEvent(skHex, {
    kind: KIND_CHANNEL_CREATE,
    created_at: Math.floor(Date.now() / 1000),
    tags: [
      ["h", channelName],
      ["name", channelName],
    ],
    content: "",
  });
  await publish(ws, createEvent);

  const confirmed = await findChannelByName(ws, channelName, { sinceFloor: createEvent.created_at - 2 });
  if (!confirmed) {
    throw new Error(
      `channel create published (event ${createEvent.id}, name="${channelName}") but no matching kind ${KIND_CHANNEL_METADATA} sidecar was found`
    );
  }
  return { created: true, channelId: tagValue(confirmed, "d"), metadataEvent: confirmed };
}

function buildChannelMessage(skHex, channelId, content, extraTags = []) {
  return signEvent(skHex, {
    kind: KIND_CHANNEL_MESSAGE,
    created_at: Math.floor(Date.now() / 1000),
    tags: [["h", channelId], ...extraTags],
    content,
  });
}

function tagValue(event, tagName) {
  const found = (event.tags || []).find((t) => t[0] === tagName);
  return found ? found[1] : undefined;
}

/**
 * Reconnect cursor: builds the `since` filter to use on a fresh REQ so a
 * reconnect (or the very first subscribe) does not replay the entire
 * channel history - only events at/after the last one this process is
 * known to have processed. `graceSeconds` guards against clock skew /
 * events published in the same second as the cursor.
 */
function nextSinceFilter(baseFilter, lastSeenCreatedAt, graceSeconds = 2) {
  const since = typeof lastSeenCreatedAt === "number" ? lastSeenCreatedAt - graceSeconds : Math.floor(Date.now() / 1000) - graceSeconds;
  return { ...baseFilter, since };
}

module.exports = {
  KIND_AUTH,
  KIND_CHANNEL_CREATE,
  KIND_CHANNEL_METADATA,
  KIND_CHANNEL_MESSAGE,
  generateIdentity,
  skFromHex,
  connectAndWaitForChallenge,
  authenticate,
  publish,
  signEvent,
  queryOnce,
  subscribeLive,
  findChannelByName,
  ensureChannel,
  buildChannelMessage,
  tagValue,
  nextSinceFilter,
  verifyEvent,
};

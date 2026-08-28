"use strict";

/**
 * Reads configs/buzz-agent-identities.json as the single source of truth
 * for pubkeys (audit MEDIUM#4: that file used to be dormant - bridge.js
 * and orchestrator.js each read their own separate *_PUBKEY env vars
 * instead, so the tracked config file and the real running identities
 * could silently drift apart). Private key VALUES still only ever come
 * from process.env, resolved through the `private_key_env` name each
 * identity record points at - this module never reads or returns a
 * private key that isn't already in process.env.
 */

const fs = require("fs");
const path = require("path");

const CONFIG_PATH = path.join(__dirname, "..", "..", "..", "configs", "buzz-agent-identities.json");

function loadIdentities() {
  const raw = fs.readFileSync(CONFIG_PATH, "utf8");
  const parsed = JSON.parse(raw);
  const byRole = {};
  for (const identity of parsed.identities || []) {
    const privkeyHex = process.env[identity.private_key_env];
    if (!privkeyHex) {
      throw new Error(
        `configs/buzz-agent-identities.json declares ${identity.jarvis_agent_id} with private_key_env="${identity.private_key_env}", but process.env.${identity.private_key_env} is not set (check .env)`
      );
    }
    byRole[identity.jarvis_agent_id] = {
      jarvisAgentId: identity.jarvis_agent_id,
      pubkeyHex: identity.buzz_pubkey,
      privkeyHex,
      cliProvider: identity.cli_provider,
    };
  }
  const orchestrator = byRole["jarvis-orchestrator"];
  const agentClaude = byRole["jarvis-agent-claude"];
  if (!orchestrator) throw new Error(`configs/buzz-agent-identities.json is missing the "jarvis-orchestrator" identity`);
  if (!agentClaude) throw new Error(`configs/buzz-agent-identities.json is missing the "jarvis-agent-claude" identity`);
  return { orchestrator, agentClaude };
}

module.exports = { loadIdentities, CONFIG_PATH };

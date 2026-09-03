"use strict";

/**
 * The tracked public key registry, configs/jarvis-role-signing-keys.json.
 *
 * This file is the single source of truth for "which public key belongs to
 * which role" (design section 6.4). Code deliberately does NOT derive the public
 * key from the private key file: audit MEDIUM#4 showed that a tracked config
 * which nothing reads goes dormant and silently drifts from the real identities.
 * Signing reads the registry, then checks the loaded private key against it.
 *
 * The registry holds public keys and status only. It never holds a secret, so
 * scripts/check_no_secrets.py has nothing to trip over - which is also why the
 * field is named `public_key` rather than anything matching key|secret|token.
 *
 * The registry path is a parameter, not an environment variable. An env override
 * would let anything relocate the trust root; tests pass a temp path explicitly
 * instead, and the CLI always uses the tracked file.
 */

const fs = require("fs");
const path = require("path");
const { RoleSigningError } = require("./errors");
const { UTC_TIMESTAMP_PATTERN } = require("./canonical");
const { HEX_32_PATTERN, HEX_64_PATTERN, ROLES, deriveKeyId } = require("./keystore");
const { REPO_ROOT } = require("./paths");

const REGISTRY_PATH = path.join(REPO_ROOT, "configs", "jarvis-role-signing-keys.json");

const REGISTRY_COMMENT =
  "Role-based Ed25519 public key registry (task-0042). Public keys and status " +
  "only - never a secret value. Private keys live outside the repository under " +
  "the signing-keys state directory; see " +
  "docs/task-0042-role-based-signing-keys-design.md.";

const STATUSES = Object.freeze(["active", "retired"]);
const ENTRY_FIELDS = Object.freeze([
  "role",
  "key_id",
  "public_key",
  "status",
  "created_at",
  "retired_at",
]);

function emptyRegistry() {
  return { $comment: REGISTRY_COMMENT, keys: [] };
}

function validateEntry(entry) {
  if (entry === null || typeof entry !== "object" || Array.isArray(entry)) {
    throw new RoleSigningError("registry_malformed");
  }
  for (const field of Object.keys(entry)) {
    if (!ENTRY_FIELDS.includes(field)) throw new RoleSigningError("registry_malformed");
  }
  for (const field of ENTRY_FIELDS) {
    if (!(field in entry)) throw new RoleSigningError("registry_malformed");
  }
  if (!ROLES.includes(entry.role)) throw new RoleSigningError("registry_malformed");
  if (!STATUSES.includes(entry.status)) throw new RoleSigningError("registry_malformed");
  if (typeof entry.public_key !== "string" || !HEX_64_PATTERN.test(entry.public_key)) {
    throw new RoleSigningError("registry_malformed");
  }
  if (typeof entry.key_id !== "string" || !HEX_32_PATTERN.test(entry.key_id)) {
    throw new RoleSigningError("registry_malformed");
  }
  // key_id is derived, so a mismatch means the file was hand-edited wrongly.
  if (deriveKeyId(entry.public_key) !== entry.key_id) {
    throw new RoleSigningError("registry_malformed");
  }
  if (typeof entry.created_at !== "string" || !UTC_TIMESTAMP_PATTERN.test(entry.created_at)) {
    throw new RoleSigningError("registry_malformed");
  }
  if (entry.status === "active" && entry.retired_at !== null) {
    throw new RoleSigningError("registry_malformed");
  }
  if (
    entry.status === "retired" &&
    (typeof entry.retired_at !== "string" || !UTC_TIMESTAMP_PATTERN.test(entry.retired_at))
  ) {
    throw new RoleSigningError("registry_malformed");
  }
  return entry;
}

/**
 * Load and fully validate the registry. A damaged registry fails everything
 * (design section 7.1, fail-closed) rather than degrading to "verify what we
 * can parse".
 */
function loadRegistry(registryPath = REGISTRY_PATH) {
  let raw;
  try {
    raw = fs.readFileSync(registryPath, "utf8");
  } catch (error) {
    if (error && error.code === "ENOENT") throw new RoleSigningError("registry_malformed");
    throw new RoleSigningError("registry_malformed");
  }

  let parsed;
  try {
    parsed = JSON.parse(raw);
  } catch {
    throw new RoleSigningError("registry_malformed");
  }
  if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new RoleSigningError("registry_malformed");
  }
  if (!Array.isArray(parsed.keys)) throw new RoleSigningError("registry_malformed");

  const entries = parsed.keys.map(validateEntry);

  const seenKeyIds = new Set();
  const seenPublicKeys = new Set();
  for (const entry of entries) {
    if (seenKeyIds.has(entry.key_id) || seenPublicKeys.has(entry.public_key)) {
      throw new RoleSigningError("registry_malformed");
    }
    seenKeyIds.add(entry.key_id);
    seenPublicKeys.add(entry.public_key);
  }

  // One key must not serve two roles (design section 3.1). Public keys are
  // already unique above, so this only needs the per-role active count.
  for (const role of ROLES) {
    const active = entries.filter((entry) => entry.role === role && entry.status === "active");
    if (active.length > 1) throw new RoleSigningError("role_has_multiple_active_keys");
  }

  return { path: registryPath, comment: parsed.$comment || REGISTRY_COMMENT, entries };
}

/** Write the registry back, sorted for a stable, reviewable git diff. */
function saveRegistry(registry, registryPath = REGISTRY_PATH) {
  const entries = [...registry.entries].sort((left, right) => {
    if (left.role !== right.role) return ROLES.indexOf(left.role) - ROLES.indexOf(right.role);
    if (left.created_at !== right.created_at) {
      return left.created_at < right.created_at ? -1 : 1;
    }
    return left.key_id < right.key_id ? -1 : 1;
  });
  const document = {
    $comment: registry.comment || REGISTRY_COMMENT,
    keys: entries.map((entry) => ({
      role: entry.role,
      key_id: entry.key_id,
      public_key: entry.public_key,
      status: entry.status,
      created_at: entry.created_at,
      retired_at: entry.retired_at,
    })),
  };
  fs.mkdirSync(path.dirname(registryPath), { recursive: true });
  fs.writeFileSync(registryPath, `${JSON.stringify(document, null, 2)}\n`, "utf8");
  return registryPath;
}

/** The single active key for one role, or a fail-closed error. */
function findActiveKey(registry, role) {
  const matches = registry.entries.filter(
    (entry) => entry.role === role && entry.status === "active"
  );
  if (matches.length > 1) throw new RoleSigningError("role_has_multiple_active_keys");
  if (matches.length === 0) {
    // A role whose only keys are retired gets the more precise code, so a
    // rotation left half-finished does not read as "never had a key".
    const retired = registry.entries.some(
      (entry) => entry.role === role && entry.status === "retired"
    );
    throw new RoleSigningError(retired ? "key_retired_for_signing" : "role_has_no_active_key");
  }
  return matches[0];
}

/**
 * Look a key up by id. A key that is not in the registry is rejected even when
 * its signature is mathematically valid (design section 7.1).
 */
function findKeyById(registry, keyId) {
  const match = registry.entries.find((entry) => entry.key_id === keyId);
  if (!match) throw new RoleSigningError("unknown_key_id");
  return match;
}

module.exports = {
  REGISTRY_COMMENT,
  REGISTRY_PATH,
  STATUSES,
  emptyRegistry,
  findActiveKey,
  findKeyById,
  loadRegistry,
  saveRegistry,
};

"use strict";

/**
 * The operations the CLI exposes: generate, rotate, verify-keys, sign-record,
 * verify-records.
 *
 * Everything here is a plain function taking explicit paths, so run_smoke_tests
 * can drive the same code against a temp state directory and a temp registry
 * without an environment override that would weaken the real trust root.
 *
 * Nothing in this module runs on import. Key creation happens only when a
 * caller invokes generateRoleKey() or rotateRoleKey(), which the CLI does only
 * for an explicit Owner-typed command (AGENTS.md principle 5 exception,
 * condition 1).
 */

const fs = require("fs");
const { RoleSigningError } = require("./errors");
const { utcNow } = require("./canonical");
const keystore = require("./keystore");
const registryModule = require("./registry");
const signingModule = require("./signing");

const { REGISTRY_PATH, loadRegistry, saveRegistry } = registryModule;

function readJsonFile(file, errorCode) {
  let raw;
  try {
    raw = fs.readFileSync(file, "utf8");
  } catch {
    throw new RoleSigningError(errorCode);
  }
  try {
    return JSON.parse(raw);
  } catch {
    throw new RoleSigningError(errorCode);
  }
}

/**
 * Generate the first key for a role.
 *
 * Order matters: the private key file is created first with O_EXCL, and only
 * then is the registry updated. If the registry write fails, verify-keys
 * reports the orphaned file rather than the two silently disagreeing.
 */
function generateRoleKey(options) {
  const { paths, role, registryPath = REGISTRY_PATH, now } = options;
  keystore.assertIssuableRole(role);

  const registry = loadRegistry(registryPath);
  const existing = registry.entries.filter(
    (entry) => entry.role === role && entry.status === "active"
  );
  if (existing.length > 0) {
    // Regeneration over a live key is refused; rotation is a separate command.
    throw new RoleSigningError("signing_key_already_exists");
  }

  const created = keystore.createRoleKey(paths, role);
  registry.entries.push({
    role,
    key_id: created.keyId,
    public_key: created.publicKeyHex,
    status: "active",
    created_at: utcNow(now),
    retired_at: null,
  });
  saveRegistry(registry, registryPath);

  return { role, key_id: created.keyId, public_key: created.publicKeyHex, status: "active" };
}

/**
 * Rotate a role key, in the order design section 8 fixes:
 * retire the registry entry, add the new one, then move the old file aside.
 *
 * Past records signed by the retired key stay valid and are never re-signed -
 * re-signing history with a new key is closer to forging it.
 */
function rotateRoleKey(options) {
  const { paths, role, registryPath = REGISTRY_PATH, now } = options;
  keystore.assertIssuableRole(role);

  const registry = loadRegistry(registryPath);
  const current = registryModule.findActiveKey(registry, role);
  const timestamp = utcNow(now);

  // Move the old private key aside first: it uses O_EXCL-style existence checks
  // and is the step most likely to fail, so failing here leaves the registry
  // untouched rather than half-rotated.
  const retiredFile = keystore.retireKeyFile(paths, role, current.key_id);

  let created;
  try {
    created = keystore.createRoleKey(paths, role);
  } catch (error) {
    // Put the old key back so the role is not left unable to sign at all.
    fs.renameSync(retiredFile, keystore.activeKeyFile(paths, role));
    throw error;
  }

  current.status = "retired";
  current.retired_at = timestamp;
  registry.entries.push({
    role,
    key_id: created.keyId,
    public_key: created.publicKeyHex,
    status: "active",
    created_at: timestamp,
    retired_at: null,
  });
  saveRegistry(registry, registryPath);

  return {
    role,
    retired_key_id: current.key_id,
    active_key_id: created.keyId,
    public_key: created.publicKeyHex,
  };
}

/**
 * Check that registry active entries and active/ key files correspond 1:1.
 *
 * Design section 8 chose verifiable over atomic: a rotation interrupted between
 * the file move and the registry write leaves a detectable mismatch, and this
 * is what detects it.
 */
function verifyKeys(options) {
  const { paths, registryPath = REGISTRY_PATH } = options;
  const registry = loadRegistry(registryPath);
  const rolesWithFiles = new Set(keystore.listActiveKeyRoles(paths));
  const problems = [];
  const checked = [];

  for (const role of keystore.ROLES) {
    const activeEntries = registry.entries.filter(
      (entry) => entry.role === role && entry.status === "active"
    );
    const hasFile = rolesWithFiles.has(role);

    if (activeEntries.length > 1) {
      problems.push({ role, reason: "role_has_multiple_active_keys" });
      continue;
    }
    if (activeEntries.length === 0 && !hasFile) continue;
    if (activeEntries.length === 0 && hasFile) {
      problems.push({ role, reason: "registry_key_file_mismatch" });
      continue;
    }
    if (!hasFile) {
      problems.push({ role, reason: "signing_key_not_found" });
      continue;
    }

    const entry = activeEntries[0];
    const file = keystore.activeKeyFile(paths, role);
    let permission;
    try {
      const loaded = keystore.readSeedFile(file, options);
      try {
        permission = loaded.permission;
        const derived = keystore.publicKeyHexFromPrivate(
          keystore.privateKeyFromSeed(loaded.seed)
        );
        if (derived !== entry.public_key) {
          problems.push({ role, reason: "signing_key_public_mismatch" });
          continue;
        }
      } finally {
        loaded.seed.fill(0);
      }
    } catch (error) {
      if (error instanceof RoleSigningError) {
        problems.push({ role, reason: error.code });
        continue;
      }
      throw error;
    }
    checked.push({
      role,
      key_id: entry.key_id,
      permission_enforced: permission.enforced,
      permission_basis: permission.basis,
    });
  }

  return { ok: problems.length === 0, checked, problems };
}

/** Sign one record file and return the envelope. */
function signRecordFile(options) {
  const { paths, role, recordPath, registryPath = REGISTRY_PATH, now } = options;
  const record = readJsonFile(recordPath, "record_malformed");
  const registry = loadRegistry(registryPath);
  return signingModule.signRecord({ ...options, record, registry, now });
}

/**
 * Verify record/envelope pairs. This is the manual check command Owner decision
 * 6 scoped the enforcement to - it is never wired into a save or read path.
 */
function verifyRecordFiles(options) {
  const { pairs, registryPath = REGISTRY_PATH } = options;
  const registry = loadRegistry(registryPath);
  const results = pairs.map((pair) => {
    try {
      const record = readJsonFile(pair.recordPath, "record_malformed");
      const envelope = readJsonFile(pair.signaturePath, "envelope_malformed");
      const outcome = signingModule.verifyEnvelope({ record, envelope, registry });
      return { record: pair.recordPath, signature: pair.signaturePath, ...outcome };
    } catch (error) {
      if (error instanceof RoleSigningError) {
        return {
          record: pair.recordPath,
          signature: pair.signaturePath,
          valid: false,
          reason: error.code,
        };
      }
      throw error;
    }
  });
  return { ok: results.every((result) => result.valid), results };
}

/** Registry contents for display. Public information only. */
function listKeys(options = {}) {
  const registry = loadRegistry(options.registryPath || REGISTRY_PATH);
  return registry.entries.map((entry) => ({ ...entry }));
}

module.exports = {
  generateRoleKey,
  listKeys,
  rotateRoleKey,
  signRecordFile,
  verifyKeys,
  verifyRecordFiles,
};

"use strict";

/**
 * Private key material on disk. Node stdlib `crypto` only - no third-party
 * package is required for Ed25519 (design section 2.2-1; the first draft claim
 * that a new crypto dependency was unavoidable was wrong).
 *
 * File format (design section 6.3): the 32-byte Ed25519 seed as 64 lowercase
 * hex characters plus one newline, nothing else. No PEM, no PKCS#8 on disk - a
 * one-line file makes "this file contains a secret" unmistakable and keeps a
 * parser out of the trust path.
 *
 * Node crypto wants DER, so we wrap/unwrap with the two fixed Ed25519 prefixes
 * below rather than pulling in an ASN.1 library.
 *
 * No function here ever returns, logs, or formats a seed. A seed lives in a
 * local Buffer for the duration of one operation and is zeroed afterwards.
 */

const crypto = require("crypto");
const fs = require("fs");
const path = require("path");
const { RoleSigningError } = require("./errors");

// SOP v0.1 role names (design section 3.1). Fixed set, never extended ad hoc.
const ROLES = Object.freeze(["implementer", "reviewer", "qa", "docs"]);

// Owner decision 5: only these roles get a key for now. implementer/docs stay in
// the model but have no record type to sign yet, and an unused key is pure risk.
const ISSUABLE_ROLES = Object.freeze(["reviewer", "qa"]);

// Fixed DER headers for Ed25519 (RFC 8410). Constants, not a parser.
const PKCS8_ED25519_PREFIX = Buffer.from("302e020100300506032b657004220420", "hex");
const SPKI_ED25519_PREFIX = Buffer.from("302a300506032b6570032100", "hex");

// design section 3.2
const KEY_ID_DIGEST_PREFIX = Buffer.from("jarvis-core/role-signing-key-id/v0.1\u0000", "utf8");

const SEED_FILE_PATTERN = /^([0-9a-f]{64})\n?$/;
const HEX_32_PATTERN = /^[0-9a-f]{32}$/;
const HEX_64_PATTERN = /^[0-9a-f]{64}$/;

function assertKnownRole(role) {
  if (!ROLES.includes(role)) throw new RoleSigningError("unknown_role");
}

function assertIssuableRole(role) {
  assertKnownRole(role);
  if (!ISSUABLE_ROLES.includes(role)) throw new RoleSigningError("role_not_issuable");
}

/** key_id = first 16 bytes of a domain-separated hash of the public key. */
function deriveKeyId(publicKeyHex) {
  if (!HEX_64_PATTERN.test(publicKeyHex)) throw new RoleSigningError("signing_key_malformed");
  return crypto
    .createHash("sha256")
    .update(KEY_ID_DIGEST_PREFIX)
    .update(Buffer.from(publicKeyHex, "hex"))
    .digest("hex")
    .slice(0, 32);
}

function privateKeyFromSeed(seed) {
  if (!Buffer.isBuffer(seed) || seed.length !== 32) {
    throw new RoleSigningError("signing_key_malformed");
  }
  try {
    return crypto.createPrivateKey({
      key: Buffer.concat([PKCS8_ED25519_PREFIX, seed]),
      format: "der",
      type: "pkcs8",
    });
  } catch {
    throw new RoleSigningError("signing_key_malformed");
  }
}

function publicKeyFromHex(publicKeyHex) {
  if (!HEX_64_PATTERN.test(publicKeyHex)) throw new RoleSigningError("signing_key_malformed");
  try {
    return crypto.createPublicKey({
      key: Buffer.concat([SPKI_ED25519_PREFIX, Buffer.from(publicKeyHex, "hex")]),
      format: "der",
      type: "spki",
    });
  } catch {
    throw new RoleSigningError("signing_key_malformed");
  }
}

function publicKeyHexFromPrivate(privateKey) {
  const spki = crypto.createPublicKey(privateKey).export({ type: "spki", format: "der" });
  return Buffer.from(spki.subarray(-32)).toString("hex");
}

function activeKeyFile(paths, role) {
  return path.join(paths.activeDir, `${role}.key`);
}

function retiredKeyFile(paths, role, keyId) {
  return path.join(paths.retiredDir, `${role}-${keyId}.key`);
}

/**
 * Create the 0700 directories. review_store.py sets the mode twice on purpose -
 * the mkdir mode argument is masked by umask - so we do the same.
 */
function ensureKeyDirectories(paths) {
  for (const dir of [paths.stateRoot, paths.keyDir, paths.activeDir, paths.retiredDir]) {
    fs.mkdirSync(dir, { recursive: true, mode: 0o700 });
    try {
      fs.chmodSync(dir, 0o700);
    } catch {
      // Windows does not enforce POSIX mode bits; see assertSafePermissions().
    }
  }
}

/**
 * On POSIX, refuse a key readable by group or other. On Windows the POSIX bits
 * are not meaningfully enforced, so protection rests on the user-profile ACL of
 * %LOCALAPPDATA%. We do not pretend otherwise (Owner decision 7, design 6.2).
 */
function assertSafePermissions(file, options = {}) {
  const isWindows =
    options.isWindows === undefined ? process.platform === "win32" : options.isWindows;
  if (isWindows) return { enforced: false, basis: "windows_user_profile_acl" };
  const stats = fs.statSync(file);
  if ((stats.mode & 0o077) !== 0) throw new RoleSigningError("signing_key_permission_unsafe");
  return { enforced: true, basis: "posix_mode_bits" };
}

/**
 * Write one seed with O_WRONLY|O_CREAT|O_EXCL and mode 0600. If the file
 * already exists this fails instead of overwriting - a silent overwrite would
 * destroy the only copy of a key.
 */
function writeSeedFile(file, seed) {
  let handle;
  try {
    handle = fs.openSync(file, "wx", 0o600);
  } catch (error) {
    if (error && error.code === "EEXIST") throw new RoleSigningError("signing_key_already_exists");
    throw new RoleSigningError("signing_key_path_not_safe");
  }
  try {
    fs.writeSync(handle, `${seed.toString("hex")}\n`);
    fs.fsyncSync(handle);
  } finally {
    fs.closeSync(handle);
  }
  try {
    fs.chmodSync(file, 0o600);
  } catch {
    // Same Windows caveat as ensureKeyDirectories().
  }
}

/** Read one seed. Only a signing operation may call this. */
function readSeedFile(file, options = {}) {
  let raw;
  try {
    raw = fs.readFileSync(file, "utf8");
  } catch (error) {
    if (error && error.code === "ENOENT") throw new RoleSigningError("signing_key_not_found");
    throw new RoleSigningError("signing_key_path_not_safe");
  }
  const permission = assertSafePermissions(file, options);
  const match = SEED_FILE_PATTERN.exec(raw);
  if (!match) throw new RoleSigningError("signing_key_malformed");
  return { seed: Buffer.from(match[1], "hex"), permission };
}

/**
 * Generate a fresh keypair and persist the seed. Reached only from an explicit
 * Owner-run CLI command - nothing in this module runs on import (AGENTS.md
 * principle 5 exception, condition 1).
 */
function createRoleKey(paths, role) {
  assertIssuableRole(role);
  ensureKeyDirectories(paths);
  const file = activeKeyFile(paths, role);
  if (fs.existsSync(file)) throw new RoleSigningError("signing_key_already_exists");

  const seed = crypto.randomBytes(32);
  try {
    const publicKeyHex = publicKeyHexFromPrivate(privateKeyFromSeed(seed));
    writeSeedFile(file, seed);
    return { role, publicKeyHex, keyId: deriveKeyId(publicKeyHex) };
  } finally {
    seed.fill(0);
  }
}

/** Move a retired key aside. Never deletes - manual deletion only. */
function retireKeyFile(paths, role, keyId) {
  ensureKeyDirectories(paths);
  const source = activeKeyFile(paths, role);
  if (!fs.existsSync(source)) throw new RoleSigningError("signing_key_not_found");
  const target = retiredKeyFile(paths, role, keyId);
  if (fs.existsSync(target)) throw new RoleSigningError("signing_key_already_exists");
  fs.renameSync(source, target);
  return target;
}

/** Roles that currently have an active private key file on disk. */
function listActiveKeyRoles(paths) {
  let entries;
  try {
    entries = fs.readdirSync(paths.activeDir);
  } catch (error) {
    if (error && error.code === "ENOENT") return [];
    throw new RoleSigningError("signing_key_path_not_safe");
  }
  return entries
    .filter((name) => name.endsWith(".key"))
    .map((name) => name.slice(0, -4))
    .filter((role) => ROLES.includes(role))
    .sort();
}

module.exports = {
  HEX_32_PATTERN,
  HEX_64_PATTERN,
  ISSUABLE_ROLES,
  ROLES,
  activeKeyFile,
  assertIssuableRole,
  assertKnownRole,
  assertSafePermissions,
  createRoleKey,
  deriveKeyId,
  ensureKeyDirectories,
  listActiveKeyRoles,
  privateKeyFromSeed,
  publicKeyFromHex,
  publicKeyHexFromPrivate,
  readSeedFile,
  retireKeyFile,
  retiredKeyFile,
  writeSeedFile,
};

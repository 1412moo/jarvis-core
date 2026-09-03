"use strict";

/**
 * Signing key storage paths.
 *
 * This reuses review_store.py:resolve_review_store_paths()'s three-tier policy
 * verbatim and only swaps the trailing segments, so signing keys land beside the
 * Review store rather than in a second, differently-governed location:
 *
 *   1. JARVIS_LOCAL_STATE_DIR (absolute path required)
 *   2. Windows + %LOCALAPPDATA% -> %LOCALAPPDATA%\Jarvis-Core
 *   3. otherwise -> ~/.jarvis-core
 *
 * The single most important line in this file is the isPathInside() guard: if
 * the resolved key directory lands inside the repository we fail closed. That
 * is the structural defence against the worst accident available here - a
 * private key getting committed (AGENTS.md principle 5 exception, condition 2).
 *
 * Resolving a path never creates it. Directory creation lives in keystore.js.
 */

const os = require("os");
const path = require("path");
const { RoleSigningError } = require("./errors");

// review_store.py:JARVIS_LOCAL_STATE_DIR_ENV / WINDOWS_STATE_ROOT_NAME
const JARVIS_LOCAL_STATE_DIR_ENV = "JARVIS_LOCAL_STATE_DIR";
const WINDOWS_STATE_ROOT_NAME = "Jarvis-Core";

// Sibling of review_store.py's ("hermes-manager", "reviews", "v1").
const SIGNING_KEY_SEGMENTS = ["signing-keys", "v1"];

// lib -> role-signing -> orchestrator -> repo root
const REPO_ROOT = path.resolve(__dirname, "..", "..", "..");

/** os.path.expandvars(), both %NAME% and $NAME / ${NAME} forms. */
function expandVars(value, env) {
  return value
    .replace(/%([^%]+)%/g, (match, name) => (env[name] === undefined ? match : env[name]))
    .replace(/\$\{([^}]+)\}/g, (match, name) => (env[name] === undefined ? match : env[name]))
    .replace(/\$([A-Za-z_]\w*)/g, (match, name) => (env[name] === undefined ? match : env[name]));
}

/** Path.expanduser() for the leading "~" only, matching pathlib's behaviour. */
function expandUser(value, homeDir) {
  if (value === "~") return homeDir;
  if (value.startsWith("~/") || value.startsWith("~\\")) {
    return path.join(homeDir, value.slice(2));
  }
  return value;
}

/** review_store.py:_is_path_inside(), with the same case folding on Windows. */
function isPathInside(target, root) {
  const normalize = (value) => {
    const resolved = path.resolve(value);
    return process.platform === "win32" ? resolved.toLowerCase() : resolved;
  };
  const normalizedTarget = normalize(target);
  const normalizedRoot = normalize(root);
  if (normalizedTarget === normalizedRoot) return true;
  const prefix = normalizedRoot.endsWith(path.sep) ? normalizedRoot : normalizedRoot + path.sep;
  return normalizedTarget.startsWith(prefix);
}

/**
 * Resolve the signing key directories without creating anything.
 *
 * @returns {{source: string, stateRoot: string, keyDir: string,
 *            activeDir: string, retiredDir: string}}
 */
function resolveSigningKeyPaths(options = {}) {
  const env = options.env || process.env;
  const homeDir = options.homeDir || os.homedir();
  const repoRoot = options.repoRoot || REPO_ROOT;
  const isWindows = options.isWindows === undefined ? process.platform === "win32" : options.isWindows;

  const override = String(env[JARVIS_LOCAL_STATE_DIR_ENV] || "").trim();
  const localAppData = String(env.LOCALAPPDATA || "").trim();

  let stateRoot;
  let source;
  if (override) {
    stateRoot = expandUser(expandVars(override, env), homeDir);
    source = "env_override";
    if (!path.isAbsolute(stateRoot)) {
      throw new RoleSigningError("signing_key_dir_must_be_absolute");
    }
  } else if (isWindows && localAppData) {
    stateRoot = path.join(expandVars(localAppData, env), WINDOWS_STATE_ROOT_NAME);
    source = "default_windows_localappdata";
  } else {
    stateRoot = path.join(homeDir, ".jarvis-core");
    source = "default_home";
  }

  let resolvedStateRoot;
  let keyDir;
  try {
    resolvedStateRoot = path.resolve(stateRoot);
    keyDir = path.resolve(resolvedStateRoot, ...SIGNING_KEY_SEGMENTS);
  } catch {
    throw new RoleSigningError("signing_key_path_not_safe");
  }

  // Fail closed before any caller can be tempted to write here.
  if (isPathInside(keyDir, repoRoot)) {
    throw new RoleSigningError("signing_key_dir_inside_repo");
  }

  return {
    source,
    stateRoot: resolvedStateRoot,
    keyDir,
    activeDir: path.join(keyDir, "active"),
    retiredDir: path.join(keyDir, "retired"),
  };
}

module.exports = {
  JARVIS_LOCAL_STATE_DIR_ENV,
  REPO_ROOT,
  SIGNING_KEY_SEGMENTS,
  WINDOWS_STATE_ROOT_NAME,
  isPathInside,
  resolveSigningKeyPaths,
};

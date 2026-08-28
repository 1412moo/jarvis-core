"use strict";

/**
 * Stdin-based Claude CLI adapter.
 *
 * Security invariants (Design Revision CLI_EXECUTION_BOUNDARY - all five are
 * hardcoded here, not configurable, and not read from any Buzz event):
 *   1. --permission-mode plan       (never applies edits/executes actions)
 *   2. --restricted                 (removes Bash/PowerShell/REPL/WebFetch,
 *                                    ignores project/local settings, confines
 *                                    file tools to --add-dir, refuses
 *                                    bypassPermissions)
 *   3. --disallowedTools Edit,Write,NotebookEdit,Bash  (belt-and-braces on
 *                                    top of --restricted)
 *   4. cwd / --add-dir is an isolated scratch directory outside the
 *      jarvis-core repository - never the repo working tree.
 *   5. prompt travels over stdin, never as a CLI argument (task-0047 found
 *      that argv + shell:true mangles special characters on Windows).
 *
 * --dangerously-skip-permissions / --allow-dangerously-skip-permissions are
 * never present in ARGS and must never be added.
 *
 * A sixth invariant added after security audit (CRITICAL#2): the child
 * process does NOT inherit process.env wholesale. bridge.js's process.env
 * holds AGENT_CLAUDE_PRIVKEY / JARVIS_ORCHESTRATOR_PRIVKEY / relay DB
 * passwords - a crash, verbose error dump, or unexpected tool inside the
 * CLI could otherwise leak them. Only a fixed whitelist of vars the CLI
 * actually needs to run on Windows is passed through.
 */

const { spawn } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const SANDBOX_DIR = path.join(os.tmpdir(), "jarvis-buzz-bridge-sandbox");

// Quoted defensively: shell:true concatenates ARGS into a single command
// string without escaping (Node DEP0190), so an unquoted path containing a
// space (e.g. a Windows username with a space) would be split into two
// arguments by cmd.exe.
const ARGS = [
  "-p",
  "--output-format",
  "json",
  "--permission-mode",
  "plan",
  "--restricted",
  "--disallowedTools",
  "Edit,Write,NotebookEdit,Bash",
  "--add-dir",
  `"${SANDBOX_DIR}"`,
];

const SUBPROCESS_ENV_WHITELIST = new Set(
  [
    "PATH",
    "SYSTEMROOT",
    "WINDIR",
    "TEMP",
    "TMP",
    "USERPROFILE",
    "APPDATA",
    "LOCALAPPDATA",
    "HOMEDRIVE",
    "HOMEPATH",
    "COMSPEC",
    "PATHEXT",
    "USERNAME",
    "USERDOMAIN",
    "NUMBER_OF_PROCESSORS",
    "PROCESSOR_ARCHITECTURE",
    "ANTHROPIC_API_KEY",
  ].map((k) => k.toUpperCase())
);

function buildSubprocessEnv() {
  const filtered = {};
  for (const [key, value] of Object.entries(process.env)) {
    if (SUBPROCESS_ENV_WHITELIST.has(key.toUpperCase())) {
      filtered[key] = value;
    }
  }
  return filtered;
}

function ensureSandboxDir() {
  fs.mkdirSync(SANDBOX_DIR, { recursive: true });
  return SANDBOX_DIR;
}

/**
 * Invokes `claude` with the prompt on stdin. Resolves to
 * { success, output, error } - never throws for a CLI-side failure (bad
 * exit code, non-JSON output, timeout); those are reported as
 * success: false so callers can turn them into a plain "run_failed" result
 * instead of crashing the bridge process.
 */
function invokeClaude(promptText, { timeoutMs = 120000 } = {}) {
  const cwd = ensureSandboxDir();

  return new Promise((resolve) => {
    let settled = false;
    const child = spawn("claude", ARGS, {
      cwd,
      shell: true,
      windowsHide: true,
      env: buildSubprocessEnv(),
    });

    let stdout = "";
    let stderr = "";
    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      child.kill();
      resolve({ success: false, output: null, error: `claude CLI timed out after ${timeoutMs}ms` });
    }, timeoutMs);

    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });

    child.on("error", (err) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve({ success: false, output: null, error: `spawn failed: ${err.message}` });
    });

    child.on("close", (code) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      if (code !== 0) {
        resolve({ success: false, output: null, error: `claude exited ${code}: ${stderr.slice(0, 2000)}` });
        return;
      }
      let parsed;
      try {
        parsed = JSON.parse(stdout);
      } catch (err) {
        resolve({ success: false, output: null, error: `non-JSON stdout: ${err.message}: ${stdout.slice(0, 500)}` });
        return;
      }
      resolve({ success: true, output: parsed, error: null });
    });

    child.stdin.write(promptText);
    child.stdin.end();
  });
}

module.exports = { invokeClaude, ARGS, SANDBOX_DIR, buildSubprocessEnv, SUBPROCESS_ENV_WHITELIST };

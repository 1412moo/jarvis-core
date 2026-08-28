"use strict";

/**
 * Minimal .env loader, mirroring adapters/discord/bot_minimal.py's
 * _load_env_file (no extra dependency, same semantics: KEY=VALUE lines,
 * '#' comments, existing process.env values are never overwritten).
 */

const fs = require("fs");

function loadEnvFile(envPath) {
  if (!fs.existsSync(envPath) || !fs.statSync(envPath).isFile()) return;
  const text = fs.readFileSync(envPath, "utf8");
  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#") || !line.includes("=")) continue;
    const idx = line.indexOf("=");
    const key = line.slice(0, idx).trim();
    let value = line.slice(idx + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    if (key && !(key in process.env)) {
      process.env[key] = value;
    }
  }
}

module.exports = { loadEnvFile };

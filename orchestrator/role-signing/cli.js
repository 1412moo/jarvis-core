#!/usr/bin/env node
"use strict";

/**
 * Role signing CLI.
 *
 * Key creation happens only here, only when the Owner types the command
 * (AGENTS.md principle 5 exception, condition 1). Nothing on this path runs
 * automatically from a bot start, a test, or an import.
 *
 * Commands:
 *   generate-key --role <reviewer|qa>
 *   rotate-key   --role <reviewer|qa>
 *   list-keys
 *   verify-keys
 *   sign-record   --role <role> --record <path> [--out <path>]
 *   verify-records --record <path> --signature <path> [...]  |  --dir <path>
 *
 * Output is JSON on stdout. Failures print {"error":"<code>"} and exit 1; the
 * code is a fixed category that never carries a key, a path, or internal state.
 */

const fs = require("fs");
const path = require("path");
const { RoleSigningError } = require("./lib/errors");
const { resolveSigningKeyPaths } = require("./lib/paths");
const operations = require("./lib/operations");

const USAGE = `jarvis role signing

  node cli.js generate-key --role <reviewer|qa>
  node cli.js rotate-key --role <reviewer|qa>
  node cli.js list-keys
  node cli.js verify-keys
  node cli.js sign-record --role <role> --record <path> [--out <path>]
  node cli.js verify-records --record <path> --signature <path> [--record ... --signature ...]
  node cli.js verify-records --dir <path>

Private keys are stored outside the repository and are never printed.`;

function parseArgs(argv) {
  const flags = { record: [], signature: [] };
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith("--")) throw new Error(`unexpected argument: ${token}`);
    const name = token.slice(2);
    const value = argv[index + 1];
    if (value === undefined || value.startsWith("--")) {
      throw new Error(`missing value for --${name}`);
    }
    index += 1;
    if (name === "record" || name === "signature") flags[name].push(value);
    else flags[name] = value;
  }
  return flags;
}

/**
 * Pair records with signatures. In --dir mode, X.json pairs with X.sig.json.
 */
function collectPairs(flags) {
  if (flags.dir) {
    const entries = fs.readdirSync(flags.dir).sort();
    return entries
      .filter((name) => name.endsWith(".json") && !name.endsWith(".sig.json"))
      .map((name) => ({
        recordPath: path.join(flags.dir, name),
        signaturePath: path.join(flags.dir, `${name.slice(0, -".json".length)}.sig.json`),
      }))
      .filter((pair) => fs.existsSync(pair.signaturePath));
  }
  if (flags.record.length === 0 || flags.record.length !== flags.signature.length) {
    throw new Error("verify-records needs matching --record and --signature values, or --dir");
  }
  return flags.record.map((recordPath, index) => ({
    recordPath,
    signaturePath: flags.signature[index],
  }));
}

function requireOne(values, name) {
  if (values.length !== 1) throw new Error(`--${name} must be given exactly once`);
  return values[0];
}

function run(argv) {
  const command = argv[0];
  if (!command || command === "--help" || command === "-h" || command === "help") {
    process.stdout.write(`${USAGE}\n`);
    return 0;
  }

  const flags = parseArgs(argv.slice(1));
  const paths = resolveSigningKeyPaths();

  let result;
  switch (command) {
    case "generate-key":
      result = operations.generateRoleKey({ paths, role: flags.role });
      break;
    case "rotate-key":
      result = operations.rotateRoleKey({ paths, role: flags.role });
      break;
    case "list-keys":
      result = { keys: operations.listKeys() };
      break;
    case "verify-keys":
      result = operations.verifyKeys({ paths });
      break;
    case "sign-record": {
      const recordPath = requireOne(flags.record, "record");
      const envelope = operations.signRecordFile({ paths, role: flags.role, recordPath });
      if (flags.out) {
        fs.writeFileSync(flags.out, `${JSON.stringify(envelope, null, 2)}\n`, "utf8");
      }
      result = envelope;
      break;
    }
    case "verify-records":
      result = operations.verifyRecordFiles({ pairs: collectPairs(flags) });
      break;
    default:
      throw new Error(`unknown command: ${command}`);
  }

  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
  const failed =
    (command === "verify-keys" && !result.ok) || (command === "verify-records" && !result.ok);
  return failed ? 1 : 0;
}

function main() {
  try {
    process.exitCode = run(process.argv.slice(2));
  } catch (error) {
    if (error instanceof RoleSigningError) {
      process.stdout.write(`${JSON.stringify({ error: error.code }, null, 2)}\n`);
    } else {
      // Usage errors are the operator's own typing, so the message is safe to
      // show. Anything else is a bug and must not leak state into stdout.
      process.stderr.write(`${error && error.message ? error.message : "unexpected failure"}\n`);
    }
    process.exitCode = 1;
  }
}

if (require.main === module) main();

module.exports = { run, parseArgs, collectPairs, USAGE };

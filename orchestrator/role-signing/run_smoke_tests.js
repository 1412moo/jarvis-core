#!/usr/bin/env node
"use strict";

/**
 * Deterministic smoke tests for task-0042 role signing.
 *
 * Everything runs against a throwaway state directory and a throwaway registry
 * under the OS temp dir, so the test never touches the real signing keys, never
 * writes the tracked registry, and never leaves key material behind.
 */

const assert = require("assert");
const crypto = require("crypto");
const fs = require("fs");
const os = require("os");
const path = require("path");

const canonical = require("./lib/canonical");
const keystore = require("./lib/keystore");
const operations = require("./lib/operations");
const pathsModule = require("./lib/paths");
const registryModule = require("./lib/registry");
const signing = require("./lib/signing");
const qaRecord = require("./lib/qa_record");

let passed = 0;
let failed = 0;

function test(name, fn) {
  try {
    fn();
    passed += 1;
    process.stdout.write(`  ok   ${name}\n`);
  } catch (error) {
    failed += 1;
    process.stdout.write(`  FAIL ${name}\n       ${error && error.message}\n`);
  }
}

function expectCode(fn, code) {
  try {
    fn();
  } catch (error) {
    assert.strictEqual(error.code, code, `expected ${code}, got ${error.code || error.message}`);
    return;
  }
  assert.fail(`expected ${code}, but the call succeeded`);
}

function makeQaRecord(overrides = {}) {
  return {
    contract_type: "jarvis_qa_result",
    version: "0.1A",
    qa_id: `qa_${"a".repeat(24)}`,
    project_id: "jarvis-core",
    task_id: "task-0042-role-based-signing-keys",
    candidate_commit: "f".repeat(40),
    qa_kind: "smoke",
    commands: ["node run_smoke_tests.js"],
    outcome: "pass",
    reason: null,
    evidence_digest: null,
    created_at: "2026-09-03T00:00:00Z",
    ...overrides,
  };
}

const workspace = fs.mkdtempSync(path.join(os.tmpdir(), "jarvis-role-signing-"));
const stateDir = path.join(workspace, "state");
const registryPath = path.join(workspace, "registry.json");
const paths = pathsModule.resolveSigningKeyPaths({ env: { JARVIS_LOCAL_STATE_DIR: stateDir } });

function resetRegistry() {
  fs.writeFileSync(registryPath, `${JSON.stringify(registryModule.emptyRegistry(), null, 2)}\n`);
}

process.stdout.write("task-0042 role signing smoke tests\n\n");

// --- canonical JSON -------------------------------------------------------
process.stdout.write("canonical JSON (review_record.py parity)\n");

test("sorts keys and uses compact separators", () => {
  assert.strictEqual(canonical.canonicalize({ b: 1, a: [1, 2] }), '{"a":[1,2],"b":1}');
});

test("sorts keys by code point, not UTF-16 code unit", () => {
  // U+FF21 is above the surrogate range by code point but below it in UTF-16.
  const out = canonical.canonicalize({ "\u{1F600}": 1, "Ａ": 2 });
  assert.strictEqual(out, '{"Ａ":2,"\u{1F600}":1}');
});

test("rejects floats, NaN and Infinity rather than signing divergent bytes", () => {
  expectCode(() => canonical.canonicalize({ a: 1.5 }), "record_not_canonicalizable");
  expectCode(() => canonical.canonicalize({ a: NaN }), "record_not_canonicalizable");
  expectCode(() => canonical.canonicalize({ a: Infinity }), "record_not_canonicalizable");
});

test("rejects lone surrogates", () => {
  expectCode(() => canonical.canonicalize({ a: "\uD800" }), "record_not_canonicalizable");
});

// --- path policy ----------------------------------------------------------
process.stdout.write("\npath policy (review_store.py reuse)\n");

test("refuses a key directory inside the repository", () => {
  expectCode(
    () =>
      pathsModule.resolveSigningKeyPaths({
        env: { JARVIS_LOCAL_STATE_DIR: path.join(pathsModule.REPO_ROOT, "state") },
      }),
    "signing_key_dir_inside_repo"
  );
});

test("refuses a relative override", () => {
  expectCode(
    () => pathsModule.resolveSigningKeyPaths({ env: { JARVIS_LOCAL_STATE_DIR: "state" } }),
    "signing_key_dir_must_be_absolute"
  );
});

test("falls back to the home directory without an override", () => {
  const resolved = pathsModule.resolveSigningKeyPaths({
    env: {},
    homeDir: path.join(workspace, "home"),
    isWindows: false,
  });
  assert.strictEqual(resolved.source, "default_home");
  assert.ok(resolved.keyDir.endsWith(path.join("signing-keys", "v1")));
});

// --- role model -----------------------------------------------------------
process.stdout.write("\nrole model (Owner decision 5)\n");

test("only reviewer and qa keys may be issued", () => {
  keystore.assertIssuableRole("reviewer");
  keystore.assertIssuableRole("qa");
  expectCode(() => keystore.assertIssuableRole("implementer"), "role_not_issuable");
  expectCode(() => keystore.assertIssuableRole("docs"), "role_not_issuable");
  expectCode(() => keystore.assertIssuableRole("owner"), "unknown_role");
});

// --- QA record schema -----------------------------------------------------
process.stdout.write("\njarvis_qa_result v0.1A schema (Owner decision 3)\n");

test("accepts a well-formed pass record", () => {
  qaRecord.validateQaRecord(makeQaRecord());
});

test("not_required demands a reason and forbids commands", () => {
  qaRecord.validateQaRecord(
    makeQaRecord({ outcome: "not_required", commands: [], reason: "docs-only change" })
  );
  expectCode(
    () => qaRecord.validateQaRecord(makeQaRecord({ outcome: "not_required", commands: [] })),
    "record_malformed"
  );
  expectCode(
    () =>
      qaRecord.validateQaRecord(
        makeQaRecord({ outcome: "not_required", reason: "why", commands: ["npm test"] })
      ),
    "record_malformed"
  );
});

test("pass must not carry a reason, fail must", () => {
  expectCode(() => qaRecord.validateQaRecord(makeQaRecord({ reason: "looks fine" })), "record_malformed");
  qaRecord.validateQaRecord(makeQaRecord({ outcome: "fail", reason: "assertion failed" }));
  expectCode(() => qaRecord.validateQaRecord(makeQaRecord({ outcome: "fail" })), "record_malformed");
});

test("rejects unknown fields and unknown qa_kind", () => {
  expectCode(() => qaRecord.validateQaRecord(makeQaRecord({ extra: 1 })), "record_malformed");
  expectCode(() => qaRecord.validateQaRecord(makeQaRecord({ qa_kind: "vibes" })), "record_malformed");
});

// --- generation and registry ---------------------------------------------
process.stdout.write("\nkey generation and registry\n");

resetRegistry();
const generated = operations.generateRoleKey({ paths, role: "reviewer", registryPath });

test("generate-key writes the seed outside the repository", () => {
  const file = keystore.activeKeyFile(paths, "reviewer");
  assert.ok(fs.existsSync(file));
  assert.ok(!pathsModule.isPathInside(file, pathsModule.REPO_ROOT));
  assert.match(fs.readFileSync(file, "utf8"), /^[0-9a-f]{64}\n$/);
});

test("generate-key records only the public key in the registry", () => {
  const raw = fs.readFileSync(registryPath, "utf8");
  assert.ok(raw.includes(generated.public_key));
  const seedHex = fs.readFileSync(keystore.activeKeyFile(paths, "reviewer"), "utf8").trim();
  assert.ok(!raw.includes(seedHex), "registry must never contain the seed");
});

test("key_id is derived from the public key", () => {
  assert.strictEqual(keystore.deriveKeyId(generated.public_key), generated.key_id);
});

test("regenerating over an active key is refused", () => {
  expectCode(
    () => operations.generateRoleKey({ paths, role: "reviewer", registryPath }),
    "signing_key_already_exists"
  );
});

test("implementer and docs cannot be generated", () => {
  expectCode(
    () => operations.generateRoleKey({ paths, role: "implementer", registryPath }),
    "role_not_issuable"
  );
});

operations.generateRoleKey({ paths, role: "qa", registryPath });

test("verify-keys sees a consistent registry and key directory", () => {
  const outcome = operations.verifyKeys({ paths, registryPath });
  assert.strictEqual(outcome.ok, true, JSON.stringify(outcome.problems));
  assert.strictEqual(outcome.checked.length, 2);
});

// --- signing and verification --------------------------------------------
process.stdout.write("\nsigning and verification\n");

const record = makeQaRecord();
const registry = registryModule.loadRegistry(registryPath);
const envelope = signing.signRecord({ record, role: "qa", paths, registry });

test("envelope carries the expected shape and no secret", () => {
  assert.strictEqual(envelope.contract_type, "jarvis_role_signature");
  assert.strictEqual(envelope.record_type, "jarvis_qa_result");
  assert.strictEqual(envelope.role, "qa");
  assert.match(envelope.signature, /^[0-9a-f]{128}$/);
  const seedHex = fs.readFileSync(keystore.activeKeyFile(paths, "qa"), "utf8").trim();
  assert.ok(!JSON.stringify(envelope).includes(seedHex));
});

test("a genuine signature verifies", () => {
  const outcome = signing.verifyEnvelope({ record, envelope, registry });
  assert.deepStrictEqual(outcome, {
    valid: true,
    role: "qa",
    key_id: envelope.key_id,
    key_status: "active",
  });
});

test("a single changed byte in the record fails verification", () => {
  const tampered = { ...record, outcome: "fail", reason: "forged" };
  const outcome = signing.verifyEnvelope({ record: tampered, envelope, registry });
  assert.strictEqual(outcome.valid, false);
  assert.strictEqual(outcome.reason, "payload_digest_mismatch");
});

test("a tampered signature fails with signature_invalid", () => {
  const forged = { ...envelope, signature: `${"0".repeat(126)}ff` };
  const outcome = signing.verifyEnvelope({ record, envelope: forged, registry });
  assert.deepStrictEqual(outcome, { valid: false, reason: "signature_invalid" });
});

test("a mathematically valid signature from an unregistered key is rejected", () => {
  const seed = crypto.randomBytes(32);
  const privateKey = keystore.privateKeyFromSeed(seed);
  const publicKeyHex = keystore.publicKeyHexFromPrivate(privateKey);
  const signingInput = signing.buildSigningInput(record, "jarvis_qa_result");
  const rogue = {
    ...envelope,
    key_id: keystore.deriveKeyId(publicKeyHex),
    public_key: publicKeyHex,
    signature: crypto.sign(null, signingInput, privateKey).toString("hex"),
  };
  // The signature itself is valid; registry membership is what refuses it.
  assert.ok(crypto.verify(null, signingInput, keystore.publicKeyFromHex(publicKeyHex), Buffer.from(rogue.signature, "hex")));
  assert.deepStrictEqual(signing.verifyEnvelope({ record, envelope: rogue, registry }), {
    valid: false,
    reason: "unknown_key_id",
  });
});

test("a reviewer envelope claiming the qa key fails role_key_mismatch", () => {
  const swapped = { ...envelope, role: "reviewer" };
  const outcome = signing.verifyEnvelope({ record, envelope: swapped, registry });
  assert.deepStrictEqual(outcome, { valid: false, reason: "role_key_mismatch" });
});

test("cross-record-type replay is blocked by domain separation", () => {
  const reviewShaped = { ...record, contract_type: "hermes_review_record", review_id: "review_x" };
  const outcome = signing.verifyEnvelope({ record: reviewShaped, envelope, registry });
  assert.strictEqual(outcome.valid, false);
  assert.strictEqual(outcome.reason, "record_type_mismatch");
});

test("a role with no key cannot sign", () => {
  expectCode(
    () => signing.signRecord({ record, role: "docs", paths, registry }),
    "role_has_no_active_key"
  );
});

test("a swapped key file is caught before signing", () => {
  const file = keystore.activeKeyFile(paths, "qa");
  const original = fs.readFileSync(file, "utf8");
  fs.rmSync(file);
  keystore.writeSeedFile(file, crypto.randomBytes(32));
  try {
    expectCode(
      () => signing.signRecord({ record, role: "qa", paths, registry }),
      "signing_key_public_mismatch"
    );
    const outcome = operations.verifyKeys({ paths, registryPath });
    assert.strictEqual(outcome.ok, false);
    assert.ok(outcome.problems.some((problem) => problem.reason === "signing_key_public_mismatch"));
  } finally {
    fs.rmSync(file);
    fs.writeFileSync(file, original, { mode: 0o600 });
  }
});

// --- rotation -------------------------------------------------------------
process.stdout.write("\nrotation (design section 8)\n");

const rotated = operations.rotateRoleKey({ paths, role: "qa", registryPath });

test("rotation retires the old entry without deleting it", () => {
  const after = registryModule.loadRegistry(registryPath);
  const old = after.entries.find((entry) => entry.key_id === rotated.retired_key_id);
  assert.ok(old, "the retired entry must remain in the registry");
  assert.strictEqual(old.status, "retired");
  assert.match(old.retired_at, /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/);
});

test("the retired private key is moved aside, not deleted", () => {
  assert.ok(fs.existsSync(keystore.retiredKeyFile(paths, "qa", rotated.retired_key_id)));
});

test("records signed by the retired key still verify", () => {
  const after = registryModule.loadRegistry(registryPath);
  const outcome = signing.verifyEnvelope({ record, envelope, registry: after });
  assert.strictEqual(outcome.valid, true);
  assert.strictEqual(outcome.key_status, "retired");
});

test("new records are signed by the new active key", () => {
  const after = registryModule.loadRegistry(registryPath);
  const fresh = signing.signRecord({ record, role: "qa", paths, registry: after });
  assert.strictEqual(fresh.key_id, rotated.active_key_id);
  assert.notStrictEqual(fresh.key_id, rotated.retired_key_id);
});

test("verify-keys stays consistent after rotation", () => {
  const outcome = operations.verifyKeys({ paths, registryPath });
  assert.strictEqual(outcome.ok, true, JSON.stringify(outcome.problems));
});

// --- registry trust -------------------------------------------------------
process.stdout.write("\nregistry trust (design section 7.1)\n");

test("a damaged registry fails everything closed", () => {
  const broken = path.join(workspace, "broken.json");
  fs.writeFileSync(broken, "{ not json");
  expectCode(() => registryModule.loadRegistry(broken), "registry_malformed");
});

test("a hand-edited key_id is rejected", () => {
  const tampered = path.join(workspace, "tampered.json");
  const current = JSON.parse(fs.readFileSync(registryPath, "utf8"));
  current.keys[0].key_id = "0".repeat(32);
  fs.writeFileSync(tampered, JSON.stringify(current, null, 2));
  expectCode(() => registryModule.loadRegistry(tampered), "registry_malformed");
});

test("two active keys for one role are rejected", () => {
  const duplicated = path.join(workspace, "duplicated.json");
  const current = JSON.parse(fs.readFileSync(registryPath, "utf8"));
  const active = current.keys.find((entry) => entry.status === "active");
  const clone = JSON.parse(JSON.stringify(active));
  const seed = crypto.randomBytes(32);
  clone.public_key = keystore.publicKeyHexFromPrivate(keystore.privateKeyFromSeed(seed));
  clone.key_id = keystore.deriveKeyId(clone.public_key);
  current.keys.push(clone);
  fs.writeFileSync(duplicated, JSON.stringify(current, null, 2));
  expectCode(() => registryModule.loadRegistry(duplicated), "role_has_multiple_active_keys");
});

test("the tracked repository registry parses and holds no key material", () => {
  const tracked = registryModule.loadRegistry();
  assert.ok(Array.isArray(tracked.entries));
  for (const entry of tracked.entries) {
    assert.strictEqual(keystore.deriveKeyId(entry.public_key), entry.key_id);
  }
});

// --- end-to-end through operations ---------------------------------------
process.stdout.write("\nverify-records manual command (Owner decision 6)\n");

test("sign-record then verify-records round trip", () => {
  const recordPath = path.join(workspace, "qa-result.json");
  const signaturePath = path.join(workspace, "qa-result.sig.json");
  fs.writeFileSync(recordPath, JSON.stringify(record, null, 2));
  const produced = operations.signRecordFile({ paths, role: "qa", recordPath, registryPath });
  fs.writeFileSync(signaturePath, JSON.stringify(produced, null, 2));

  const outcome = operations.verifyRecordFiles({
    pairs: [{ recordPath, signaturePath }],
    registryPath,
  });
  assert.strictEqual(outcome.ok, true, JSON.stringify(outcome.results));
  assert.strictEqual(outcome.results[0].role, "qa");
});

test("verify-records reports a missing signature file as a code, not a crash", () => {
  const outcome = operations.verifyRecordFiles({
    pairs: [
      {
        recordPath: path.join(workspace, "qa-result.json"),
        signaturePath: path.join(workspace, "absent.sig.json"),
      },
    ],
    registryPath,
  });
  assert.strictEqual(outcome.ok, false);
  assert.strictEqual(outcome.results[0].reason, "envelope_malformed");
});

fs.rmSync(workspace, { recursive: true, force: true });

process.stdout.write(`\n${passed} passed, ${failed} failed\n`);
process.exitCode = failed === 0 ? 0 : 1;

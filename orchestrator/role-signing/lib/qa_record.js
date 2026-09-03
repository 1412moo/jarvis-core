"use strict";

/**
 * jarvis_qa_result v0.1A - the QA counterpart to review_record.py.
 *
 * Owner decision 3: a minimal new schema that inherits the review_record.py
 * conventions rather than inventing its own. Inherited as-is: the
 * contract_type + version pair, the UTC timestamp format, canonical JSON, and
 * the 64 KiB ceiling. Nothing new is introduced beyond the QA fields.
 *
 * Two SOP rules are promoted from prose into schema-level enforcement:
 *   - "record not_required together with the reason" -> reason is mandatory,
 *     and commands must be empty, when outcome is not_required.
 *   - "choose the lightest sufficient QA"            -> qa_kind is a closed set.
 *
 * Unknown fields are rejected. Silently ignoring them would let the signer and
 * the verifier disagree about what was actually signed.
 */

const { RoleSigningError } = require("./errors");
const { UTC_TIMESTAMP_PATTERN } = require("./canonical");

const CONTRACT_TYPE = "jarvis_qa_result";
const VERSION = "0.1A";

const QA_KINDS = Object.freeze(["unit", "smoke", "deterministic", "manual"]);
const OUTCOMES = Object.freeze(["pass", "fail", "not_required"]);

const FIELDS = Object.freeze([
  "contract_type",
  "version",
  "qa_id",
  "project_id",
  "task_id",
  "candidate_commit",
  "qa_kind",
  "commands",
  "outcome",
  "reason",
  "evidence_digest",
  "created_at",
]);

const QA_ID_PATTERN = /^qa_[0-9a-f]{24}$/;
const COMMIT_PATTERN = /^([0-9a-f]{40}|[0-9a-f]{64})$/;
const DIGEST_PATTERN = /^[0-9a-f]{64}$/;

const MAX_COMMANDS = 32;
const MAX_COMMAND_LENGTH = 512;
const MAX_REASON_LENGTH = 4096;

function fail() {
  throw new RoleSigningError("record_malformed");
}

function assertBoundedString(value, maxLength) {
  if (typeof value !== "string" || value.length === 0 || value.length > maxLength) fail();
  return value;
}

/**
 * Validate one QA record and return it unchanged. Never mutates the input - the
 * bytes that get signed must be exactly the bytes the caller supplied.
 */
function validateQaRecord(record) {
  if (record === null || typeof record !== "object" || Array.isArray(record)) fail();
  for (const field of Object.keys(record)) {
    if (!FIELDS.includes(field)) fail();
  }
  for (const field of FIELDS) {
    if (!(field in record)) fail();
  }

  if (record.contract_type !== CONTRACT_TYPE) fail();
  if (record.version !== VERSION) fail();
  if (typeof record.qa_id !== "string" || !QA_ID_PATTERN.test(record.qa_id)) fail();
  assertBoundedString(record.project_id, 64);
  assertBoundedString(record.task_id, 128);
  if (typeof record.candidate_commit !== "string" || !COMMIT_PATTERN.test(record.candidate_commit)) {
    fail();
  }
  if (!QA_KINDS.includes(record.qa_kind)) fail();
  if (!OUTCOMES.includes(record.outcome)) fail();
  if (typeof record.created_at !== "string" || !UTC_TIMESTAMP_PATTERN.test(record.created_at)) {
    fail();
  }

  if (!Array.isArray(record.commands) || record.commands.length > MAX_COMMANDS) fail();
  for (const command of record.commands) {
    assertBoundedString(command, MAX_COMMAND_LENGTH);
  }

  if (record.evidence_digest !== null) {
    if (typeof record.evidence_digest !== "string" || !DIGEST_PATTERN.test(record.evidence_digest)) {
      fail();
    }
  }

  if (record.outcome === "not_required") {
    // The SOP requires a reason, and a skipped QA cannot have run commands.
    if (record.commands.length !== 0) fail();
    assertBoundedString(record.reason, MAX_REASON_LENGTH);
  } else if (record.outcome === "fail") {
    if (record.commands.length === 0) fail();
    assertBoundedString(record.reason, MAX_REASON_LENGTH);
  } else {
    // pass: a reason would only blur the verdict.
    if (record.commands.length === 0) fail();
    if (record.reason !== null) fail();
  }

  return record;
}

module.exports = {
  CONTRACT_TYPE,
  FIELDS,
  MAX_COMMANDS,
  OUTCOMES,
  QA_KINDS,
  VERSION,
  validateQaRecord,
};

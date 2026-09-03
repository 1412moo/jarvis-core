"use strict";

/**
 * Signature envelopes (design section 5).
 *
 * The signature never touches the record. It goes into a separate envelope
 * beside it - the P2-3 task_append.js lesson: slipping a new field into a
 * structure existing parsers already read breaks them quietly.
 *
 * What gets signed (design section 5.3):
 *   signing_input = domain_prefix + canonical_utf8_bytes(record)
 * Ed25519 is PureEdDSA, so the message is signed directly with no pre-hash. The
 * payload_digest in the envelope is for correlation and human-readable logs
 * only; verification is by signature, never by digest. A digest match is a
 * necessary condition, not authentication - the same principle that stops
 * passesInboundGate from accepting a tag match as identity.
 *
 * IMPORTANT (design section 7.2): a valid signature proves authorship, not
 * approval. Valid signature != approval, exactly as Buzz message != approval.
 * Approval authority stays entirely with /approve and Owner identity checks.
 */

const crypto = require("crypto");
const { RoleSigningError } = require("./errors");
const {
  canonicalBytes,
  constantTimeEqualHex,
  sha256Hex,
  utcNow,
  UTC_TIMESTAMP_PATTERN,
} = require("./canonical");
const {
  HEX_32_PATTERN,
  HEX_64_PATTERN,
  ROLES,
  activeKeyFile,
  assertKnownRole,
  deriveKeyId,
  privateKeyFromSeed,
  publicKeyFromHex,
  publicKeyHexFromPrivate,
  readSeedFile,
} = require("./keystore");
const { findActiveKey, findKeyById } = require("./registry");

const ENVELOPE_CONTRACT_TYPE = "jarvis_role_signature";
const ENVELOPE_VERSION = "0.1A";

const SIGNATURE_PATTERN = /^[0-9a-f]{128}$/;

/**
 * Per-record-type domain separation, the change_evidence.py pattern. Distinct
 * prefixes stop a signature made for one purpose being replayed as another.
 */
const RECORD_TYPES = Object.freeze({
  hermes_review_record: {
    domainPrefix: Buffer.from(
      "jarvis-core/role-signature/hermes-review-record/v0.1A\u0000",
      "utf8"
    ),
  },
  jarvis_qa_result: {
    domainPrefix: Buffer.from("jarvis-core/role-signature/qa-result/v0.1A\u0000", "utf8"),
  },
});

const ENVELOPE_FIELDS = Object.freeze([
  "contract_type",
  "version",
  "record_type",
  "record_version",
  "role",
  "key_id",
  "public_key",
  "correlation_id",
  "payload_digest",
  "signed_at",
  "signature",
]);

function recordTypeOf(record) {
  if (record === null || typeof record !== "object" || Array.isArray(record)) {
    throw new RoleSigningError("record_malformed");
  }
  const recordType = record.contract_type;
  if (typeof recordType !== "string" || !(recordType in RECORD_TYPES)) {
    throw new RoleSigningError("record_type_unsupported");
  }
  return recordType;
}

/**
 * Validate the record just enough to sign it. QA records get the full schema
 * check; review records are owned by review_record.py, which we do not
 * reimplement here - we only confirm the envelope-relevant fields exist.
 */
function validateSignableRecord(record) {
  const recordType = recordTypeOf(record);
  if (typeof record.version !== "string" || record.version.length === 0) {
    throw new RoleSigningError("record_malformed");
  }
  if (recordType === "jarvis_qa_result") {
    // Required lazily so qa_record.js can stay independent of this module.
    require("./qa_record").validateQaRecord(record);
  }
  return recordType;
}

function correlationIdOf(record, recordType) {
  const value = recordType === "hermes_review_record" ? record.review_id : record.task_id;
  if (typeof value !== "string" || value.length === 0 || value.length > 128) {
    throw new RoleSigningError("record_malformed");
  }
  return value;
}

/** signing_input = domain_prefix + canonical bytes. */
function buildSigningInput(record, recordType) {
  const canonical = canonicalBytes(record);
  return Buffer.concat([RECORD_TYPES[recordType].domainPrefix, canonical]);
}

/**
 * Sign one record with the active key of one role.
 *
 * The private key is read at this moment and dropped straight after; it is
 * never held for the life of the process and never appears in the result.
 */
function signRecord(options) {
  const { record, role, paths, registry, now } = options;
  assertKnownRole(role);
  const recordType = validateSignableRecord(record);
  const correlationId = correlationIdOf(record, recordType);

  const registryEntry = findActiveKey(registry, role);
  const signingInput = buildSigningInput(record, recordType);

  const { seed } = readSeedFile(activeKeyFile(paths, role), options);
  let signatureHex;
  try {
    const privateKey = privateKeyFromSeed(seed);
    // Design section 4, "public key lookup": confirm the on-disk key is the one
    // the registry vouches for, so a swapped file cannot sign as this role.
    const derivedPublicKeyHex = publicKeyHexFromPrivate(privateKey);
    if (!constantTimeEqualHex(derivedPublicKeyHex, registryEntry.public_key)) {
      throw new RoleSigningError("signing_key_public_mismatch");
    }
    signatureHex = crypto.sign(null, signingInput, privateKey).toString("hex");
  } finally {
    seed.fill(0);
  }

  return {
    contract_type: ENVELOPE_CONTRACT_TYPE,
    version: ENVELOPE_VERSION,
    record_type: recordType,
    record_version: record.version,
    role,
    key_id: registryEntry.key_id,
    public_key: registryEntry.public_key,
    correlation_id: correlationId,
    payload_digest: sha256Hex(signingInput),
    signed_at: utcNow(now),
    signature: signatureHex,
  };
}

function validateEnvelopeShape(envelope) {
  if (envelope === null || typeof envelope !== "object" || Array.isArray(envelope)) return false;
  for (const field of Object.keys(envelope)) {
    if (!ENVELOPE_FIELDS.includes(field)) return false;
  }
  for (const field of ENVELOPE_FIELDS) {
    if (!(field in envelope)) return false;
  }
  if (envelope.contract_type !== ENVELOPE_CONTRACT_TYPE) return false;
  if (envelope.version !== ENVELOPE_VERSION) return false;
  if (!(envelope.record_type in RECORD_TYPES)) return false;
  if (typeof envelope.record_version !== "string" || envelope.record_version.length === 0) {
    return false;
  }
  if (!ROLES.includes(envelope.role)) return false;
  if (typeof envelope.key_id !== "string" || !HEX_32_PATTERN.test(envelope.key_id)) return false;
  if (typeof envelope.public_key !== "string" || !HEX_64_PATTERN.test(envelope.public_key)) {
    return false;
  }
  if (typeof envelope.correlation_id !== "string" || envelope.correlation_id.length === 0) {
    return false;
  }
  if (typeof envelope.payload_digest !== "string" || !HEX_64_PATTERN.test(envelope.payload_digest)) {
    return false;
  }
  if (typeof envelope.signed_at !== "string" || !UTC_TIMESTAMP_PATTERN.test(envelope.signed_at)) {
    return false;
  }
  if (typeof envelope.signature !== "string" || !SIGNATURE_PATTERN.test(envelope.signature)) {
    return false;
  }
  return true;
}

/**
 * Verify one envelope against one record.
 *
 * Returns {valid:true, role, key_id, key_status} or {valid:false, reason}. One
 * boolean, no partial pass and no warning state; the reason is a stable code
 * that discloses no path, key, or internal state (design section 5.4).
 *
 * signed_at is never used to decide anything - it is written by the signer, so
 * it proves nothing (design section 7.3). A retired key still verifies; trust
 * comes from registry membership alone.
 */
function verifyEnvelope(options) {
  const { record, envelope, registry } = options;
  try {
    if (!validateEnvelopeShape(envelope)) throw new RoleSigningError("envelope_malformed");

    const recordType = recordTypeOf(record);
    if (recordType !== envelope.record_type) throw new RoleSigningError("record_type_mismatch");
    if (record.version !== envelope.record_version) {
      throw new RoleSigningError("record_type_mismatch");
    }

    const registryEntry = findKeyById(registry, envelope.key_id);
    if (registryEntry.role !== envelope.role) throw new RoleSigningError("role_key_mismatch");
    if (!constantTimeEqualHex(registryEntry.public_key, envelope.public_key)) {
      throw new RoleSigningError("role_key_mismatch");
    }
    if (deriveKeyId(envelope.public_key) !== envelope.key_id) {
      throw new RoleSigningError("role_key_mismatch");
    }

    const signingInput = buildSigningInput(record, recordType);
    const expectedDigest = sha256Hex(signingInput);
    if (!constantTimeEqualHex(expectedDigest, envelope.payload_digest)) {
      throw new RoleSigningError("payload_digest_mismatch");
    }

    const publicKey = publicKeyFromHex(envelope.public_key);
    const signature = Buffer.from(envelope.signature, "hex");
    if (!crypto.verify(null, signingInput, publicKey, signature)) {
      throw new RoleSigningError("signature_invalid");
    }

    return {
      valid: true,
      role: registryEntry.role,
      key_id: registryEntry.key_id,
      key_status: registryEntry.status,
    };
  } catch (error) {
    if (error instanceof RoleSigningError) return { valid: false, reason: error.code };
    throw error;
  }
}

module.exports = {
  ENVELOPE_CONTRACT_TYPE,
  ENVELOPE_FIELDS,
  ENVELOPE_VERSION,
  RECORD_TYPES,
  buildSigningInput,
  recordTypeOf,
  signRecord,
  validateEnvelopeShape,
  validateSignableRecord,
  verifyEnvelope,
};

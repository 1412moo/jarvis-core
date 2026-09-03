"use strict";

/**
 * Canonical JSON that reproduces, byte for byte, what
 * review_record.py:serialize_review_record() produces:
 *
 *   json.dumps(obj, ensure_ascii=False, sort_keys=True,
 *              separators=(",", ":"), allow_nan=False)
 *
 * We do NOT invent a new canonicalization rule (design section 5.3-1). Where
 * JavaScript and Python could disagree we reject the input instead of guessing,
 * because a signature over bytes the two sides serialize differently is worse
 * than a refusal:
 *
 *   - non-integer numbers: Python repr(1.0) is "1.0" but JS String(1.0) is "1",
 *     so any float would sign different bytes on each side -> rejected.
 *   - NaN/Infinity: allow_nan=False rejects these in Python -> rejected here.
 *   - lone surrogates: JS escapes them, Python emits raw and then fails strict
 *     UTF-8 encoding -> rejected here.
 *
 * Key order uses Unicode code point order (Python's str comparison), not
 * JavaScript's default UTF-16 code unit order. They differ above the BMP.
 */

const crypto = require("crypto");
const { RoleSigningError } = require("./errors");

// review_record.py:MAX_JSON_BYTES
const MAX_CANONICAL_BYTES = 64 * 1024;

// review_record.py:_UTC_TIMESTAMP_PATTERN
const UTC_TIMESTAMP_PATTERN = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/;

const HEX_64_PATTERN = /^[0-9a-f]{64}$/;

function compareCodePoints(a, b) {
  const left = Array.from(a);
  const right = Array.from(b);
  const shared = Math.min(left.length, right.length);
  for (let i = 0; i < shared; i += 1) {
    const delta = left[i].codePointAt(0) - right[i].codePointAt(0);
    if (delta !== 0) return delta;
  }
  return left.length - right.length;
}

function encodeString(value) {
  if (!value.isWellFormed()) {
    // Python would emit a raw lone surrogate and then fail UTF-8 strict
    // encoding; JS would escape it. Neither side may silently win.
    throw new RoleSigningError("record_not_canonicalizable");
  }
  // JSON.stringify escapes exactly what json.dumps(ensure_ascii=False) escapes:
  // the quote, the backslash, and C0 controls (short forms where they exist).
  return JSON.stringify(value);
}

function canonicalize(value) {
  if (value === null) return "null";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "string") return encodeString(value);
  if (typeof value === "number") {
    if (!Number.isSafeInteger(value)) {
      throw new RoleSigningError("record_not_canonicalizable");
    }
    return String(value);
  }
  if (Array.isArray(value)) {
    return `[${value.map((item) => canonicalize(item)).join(",")}]`;
  }
  if (typeof value === "object") {
    const prototype = Object.getPrototypeOf(value);
    if (prototype !== Object.prototype && prototype !== null) {
      throw new RoleSigningError("record_not_canonicalizable");
    }
    const keys = Object.keys(value).sort(compareCodePoints);
    const parts = keys.map((key) => {
      const child = value[key];
      if (child === undefined) {
        // Python has no `undefined`; JSON.stringify would drop the key and
        // change the signed bytes. Refuse rather than drop.
        throw new RoleSigningError("record_not_canonicalizable");
      }
      return `${encodeString(key)}:${canonicalize(child)}`;
    });
    return `{${parts.join(",")}}`;
  }
  throw new RoleSigningError("record_not_canonicalizable");
}

/** Canonical JSON bytes for one record, bounded by review_record.py's limit. */
function canonicalBytes(value) {
  const bytes = Buffer.from(canonicalize(value), "utf8");
  if (bytes.length > MAX_CANONICAL_BYTES) {
    throw new RoleSigningError("record_not_canonicalizable");
  }
  return bytes;
}

/**
 * Domain-separated SHA-256, the change_evidence.py pattern:
 * hashlib.sha256(_DIGEST_PREFIX + canonical_bytes).
 */
function domainDigestHex(domainPrefix, canonical) {
  return crypto.createHash("sha256").update(domainPrefix).update(canonical).digest("hex");
}

/** Plain SHA-256 over already-domain-separated bytes. */
function sha256Hex(bytes) {
  return crypto.createHash("sha256").update(bytes).digest("hex");
}

/** Current UTC time in review_record.py's timestamp format. */
function utcNow(now = new Date()) {
  return `${now.toISOString().slice(0, 19)}Z`;
}

/** Constant-time comparison, the hmac.compare_digest() equivalent. */
function constantTimeEqualHex(left, right) {
  if (typeof left !== "string" || typeof right !== "string") return false;
  if (left.length !== right.length) return false;
  return crypto.timingSafeEqual(Buffer.from(left, "utf8"), Buffer.from(right, "utf8"));
}

module.exports = {
  MAX_CANONICAL_BYTES,
  UTC_TIMESTAMP_PATTERN,
  HEX_64_PATTERN,
  canonicalize,
  canonicalBytes,
  compareCodePoints,
  constantTimeEqualHex,
  domainDigestHex,
  sha256Hex,
  utcNow,
};

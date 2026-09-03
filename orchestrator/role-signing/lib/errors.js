"use strict";

/**
 * Fixed-category failures for role signing, mirroring the
 * `ReviewStoreError("local_state_dir_inside_repo")` style used by
 * apps/hermes-manager-pilot/hermes_manager_pilot/review_store.py.
 *
 * Every failure is a stable string code and nothing else. Codes never carry a
 * private key value, a filesystem path, or internal state - see
 * docs/task-0042-role-based-signing-keys-design.md section 5.4 (and AGENTS.md
 * principle 5 exception condition 5, "private key values never appear in logs,
 * errors, or artifacts").
 */

const ERROR_CODES = Object.freeze([
  // storage / path policy (design section 6)
  "signing_key_dir_inside_repo",
  "signing_key_dir_must_be_absolute",
  "signing_key_path_not_safe",
  "signing_key_not_found",
  "signing_key_already_exists",
  "signing_key_permission_unsafe",
  "signing_key_malformed",
  "signing_key_public_mismatch",
  // registry / role model (design sections 3, 6.4, 7.1)
  "registry_malformed",
  "unknown_role",
  "role_not_issuable",
  "role_has_no_active_key",
  "role_has_multiple_active_keys",
  "unknown_key_id",
  "key_retired_for_signing",
  "role_key_mismatch",
  "registry_key_file_mismatch",
  // record / envelope (design sections 5.1, 5.2, 5.3)
  "record_malformed",
  "record_not_canonicalizable",
  "record_type_unsupported",
  "record_type_mismatch",
  "envelope_malformed",
  "payload_digest_mismatch",
  "signature_invalid",
]);

const ERROR_CODE_SET = new Set(ERROR_CODES);

class RoleSigningError extends Error {
  constructor(code) {
    if (!ERROR_CODE_SET.has(code)) {
      // A typo must not degrade into a vague message that leaks context.
      throw new Error(`unknown role signing error code: ${code}`);
    }
    super(code);
    this.name = "RoleSigningError";
    this.code = code;
  }
}

module.exports = { RoleSigningError, ERROR_CODES };

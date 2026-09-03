# task-0042: 역할별(Implementer/Reviewer/QA/Docs) Ed25519 서명키 설계

[Document Type]
- design + approved implementation (구현 승인: 2026-09-03, §10)

## 1. 목적/배경

task-0038(Buzz/AI-agent 생태계 조사) Phase 1 항목 3. Buzz의 "역할별 신원이 각자 키를 갖고
결과에 서명한다"는 아이디어만 차용한다 — **Nostr, relay, 외부 의존성은 필요 없고 로컬
Ed25519 키로 충분하다**는 것이 보고서의 명시적 판단이다.

목표: Implementer / Reviewer / QA / Docs 네 역할이 각각 로컬 Ed25519 키페어를 갖고,
리뷰 결과와 QA 결과 기록에 서명하도록 한다. 그래서 "이 리뷰 결과는 정말 Reviewer 역할이
만든 것인가"를 사후에 암호학적으로 확인할 수 있게 된다.

이 문서의 초판은 **설계만** 다뤘다. task-0042가 "착수 전 설계 문서로 먼저 합의 필요"를
게이트로 명시했기 때문이며, 그 게이트는 **2026-09-03 Owner 결정 1~7(§10)로 통과되었다.**
따라서 이 문서는 이제 설계와 **승인된 구현 계약**을 함께 담는다. 여전히 범위 밖인 것은
§9에 남겨 두었다(키 생성 실행, 소급 마이그레이션 등).

## 2. 현재 구조 분석

### 2.1 재사용할 수 있는 것이 이미 상당히 갖춰져 있다

| 필요한 것 | 기존 자산 | 위치 |
| --- | --- | --- |
| 저장소 밖 상태 경로 정책 | `resolve_review_store_paths()` — `JARVIS_LOCAL_STATE_DIR` override → Windows `%LOCALAPPDATA%\Jarvis-Core` → `~/.jarvis-core` | `review_store.py:112` |
| **저장소 안 저장 금지 가드** | `_is_path_inside()` → `local_state_dir_inside_repo` 오류로 fail-closed | `review_store.py:147` |
| 디렉터리/파일 권한 | `mkdir(mode=0o700)` + `os.chmod(0o700)`, `os.open(..., O_CREAT\|O_EXCL, 0o600)` | `review_store.py:402,593` |
| canonical JSON | `json.dumps(..., ensure_ascii=False, sort_keys=True, separators=(",",":"), allow_nan=False)` | `review_record.py:serialize_review_record` |
| 도메인 분리 해시 | `hashlib.sha256(_DIGEST_PREFIX + canonical_bytes)`, prefix는 `b"jarvis-core/<영역>/<목적>/<버전>\x00"` | `change_evidence.py:53-58` |
| 상수시간 비교 | `hmac.compare_digest()` | `change_evidence.py:450` |
| 공개 식별자 tracked / 비밀은 밖 | `configs/buzz-agent-identities.json`이 pubkey만 tracked로 두고 privkey는 이름 참조 | `configs/`, `lib/identities.js` |
| 설정 drift 방지 교훈 | audit MEDIUM#4 — tracked config가 dormant해지면 실제 신원과 조용히 어긋난다 | `lib/identities.js` 주석 |

**따라서 이 설계의 핵심은 새 메커니즘 발명이 아니라 위 패턴들의 조합이다.**

### 2.2 없는 것 (신규로 정해야 하는 것)

1. **비대칭 서명 수단 — Node.js stdlib `crypto`로 해결되며 신규 의존성은 0개다.**

   > **정정(2026-09-03).** 이 문서 초판은 "Python 표준 라이브러리에 Ed25519가 없으므로
   > **신규 암호 의존성 추가가 불가피하다**"고 적었다. **이 전제는 틀렸다.** 관찰(Python
   > stdlib에 Ed25519가 없고 저장소 암호 사용이 `hashlib`/`hmac`뿐이다)은 사실이지만,
   > 거기서 "그러므로 신규 의존성이 불가피하다"는 결론은 **저장소가 이미 Node.js를 쓰고
   > 있다는 사실**(`orchestrator/buzz-bridge/`)을 빠뜨린 것이다. Node stdlib `crypto`는
   > Ed25519를 기본 지원한다 — `crypto.generateKeyPairSync("ed25519")`,
   > `crypto.sign(null, msg, key)`, `crypto.verify(null, msg, key, sig)`.
   > 로컬 확인: Node v24.15.0에서 raw 32바이트 seed ↔ PKCS#8/SPKI DER 왕복과
   > sign/verify가 정상 동작함을 검증했다. 따라서 **선택지는 "Python 의존성 추가 vs 착수
   > 불가"가 아니라 "Node stdlib로 의존성 없이 구현"이었다.**

   Owner 결정 2(§10)에 따라 **Node stdlib `crypto` 경로**를 택한다. `cryptography`/
   `PyNaCl` 등 신규 Python 암호 의존성은 추가하지 않는다. Node 쪽 기존 의존성인
   `nostr-tools`는 secp256k1 Schnorr이라 Ed25519에 쓸 수 없으므로 **여기에 쓰지 않으며,
   서명 코드는 어떤 서드파티 패키지에도 의존하지 않는다(stdlib 전용).**
2. 🔴 **QA 결과의 canonical record 구조가 존재하지 않는다.** `review_record.py`는 Review
   입력 스냅샷 스키마이고, QA는 SOP 문서상 역할·단계로만 정의되어 있을 뿐 서명할 대상
   레코드가 없다. 무엇에 서명할지부터 정해야 한다(§5.1).
3. 역할별 키 레지스트리(어떤 공개키가 어떤 역할의 것인지)가 없다.
4. task-0041의 append-only 이벤트 로그는 **설계만 확정되고 구현되지 않았다**(코드에
   `prev_hash`/이벤트 로그 없음). 따라서 이 설계는 **task-0041에 의존해서는 안 된다.**

### 2.3 구현 언어와 패턴 대응 (Owner 결정 2)

서명 코드는 **Node.js(stdlib `crypto` 전용)**로 구현한다. §4·§6이 Python API 이름으로
서술한 것은 **정책**이며, 그 정책을 Node에서 다음과 같이 동일하게 구현한다. 정책 자체는
바뀌지 않는다.

| 정책(§4·§6 서술) | Python 원본 | Node 구현 |
| --- | --- | --- |
| 상태 경로 3단 우선순위 | `resolve_review_store_paths()` | `lib/paths.js` 동일 규칙 재구현 |
| 저장소-안-금지 가드 | `_is_path_inside()` + `os.path.normcase/normpath` | `path.resolve()` + 대소문자 정규화 후 접두 비교 |
| 0700 디렉터리 | `mkdir(mode=0o700)` + `os.chmod(0o700)` | `fs.mkdirSync(dir,{mode:0o700})` + `fs.chmodSync(dir,0o700)` |
| 0600 원자적 생성 | `os.open(..., O_CREAT\|O_EXCL, 0o600)` | `fs.openSync(path,"wx",0o600)` (`wx` = `O_WRONLY\|O_CREAT\|O_EXCL`) |
| canonical JSON | `json.dumps(..., sort_keys=True, separators=(",",":"))` | `lib/canonical.js` — 코드포인트 정렬 후 수동 직렬화(§5.3-1 각주) |
| 도메인 분리 해시 | `hashlib.sha256(prefix + bytes)` | `crypto.createHash("sha256").update(prefix).update(bytes)` |
| 상수시간 비교 | `hmac.compare_digest()` | `crypto.timingSafeEqual()` |
| Ed25519 서명/검증 | (없음 — 의존성 필요) | `crypto.sign(null, ...)` / `crypto.verify(null, ...)` **의존성 0** |

키 파일은 raw 32바이트 seed(hex)이고 Node `crypto`는 DER을 요구하므로, 고정 접두사로
변환한다 — PKCS#8 `302e020100300506032b657004220420 + seed`,
SPKI `302a300506032b6570032100 + pubkey`. 둘 다 Ed25519 전용 고정 상수이며 ASN.1 파서를
새로 들이지 않기 위한 선택이다.

## 3. Role model

### 3.1 역할과 키의 관계

- 역할은 **`implementer` / `reviewer` / `qa` / `docs` 4개로 고정**한다. SOP v0.1의 역할
  이름과 일치시키고 임의 확장하지 않는다.
- **키 발급은 `reviewer` / `qa`부터**다(Owner 결정 5). 4역할 모델은 스키마·레지스트리에
  그대로 두되, 생성 명령은 이 두 역할만 받는다. `implementer`/`docs`는 서명 대상 레코드가
  정의될 때 별도로 결정한다 — 쓸 곳 없는 키를 미리 만들어 두지 않는다.
- 역할은 **사람이 아니라 직무**다. "누가 리뷰했는가"가 아니라 "Reviewer 역할로서 서명된
  결과인가"를 증명한다. 이는 Jarvis-Core가 1인 + AI 에이전트 구성이라는 현실과 맞고,
  개인정보를 키에 결부시키지 않는다.
- **역할당 활성 키는 정확히 1개**다. 0개면 그 역할은 서명할 수 없고(fail-closed), 2개
  이상이면 레지스트리 오류로 거부한다.
- 시간축으로는 역할 → 키가 **1:N**이다(로테이션 이력). 과거 기록 검증을 위해 은퇴한 키의
  공개키는 **영구 보존**한다.
- 하나의 키가 두 역할을 겸할 수 없다. Implementer가 자기 작업을 Reviewer로 서명하는 것을
  구조적으로 막기 위함이며, 이는 SOP의 역할 분리 원칙과 같은 방향이다.

### 3.2 식별자

- `role`: 위 4개 소문자 리터럴 중 하나.
- `key_id`: 공개키에서 파생한다 — `sha256(b"jarvis-core/role-signing-key-id/v0.1\x00" + public_key_bytes)`의 앞 16바이트를 hex로 표현(32자). 공개키 자체(64자 hex)와 구분되며 짧게 참조할 수 있다. 파생값이므로 별도 관리가 필요 없고 위조해도 공개키와 대조하면 드러난다.

## 4. Key lifecycle

| 단계 | 정책 |
| --- | --- |
| 최초 생성 | **Owner가 명시적으로 실행하는 CLI 1회 동작**으로만 생성한다. 어떤 자동 경로도(봇 기동, 테스트, import 시점) 키를 생성하지 않는다. 이미 활성 키가 있는 역할에 대한 재생성은 거부한다(로테이션은 별도 명령, §8) |
| 로컬 저장 | §6. 저장소 **밖** 0700 디렉터리에 0600 파일, `O_CREAT\|O_EXCL`로 원자적 생성. 이미 존재하면 덮어쓰지 않고 실패 |
| 로딩 | 서명이 필요한 시점에만 개인키 파일을 읽는다. 프로세스 수명 내내 상주시키지 않고 사용 후 참조를 버린다. 파일이 없거나 권한이 다르거나 형식이 어긋나면 **거부**(자동 생성 금지) |
| public key 조회 | tracked 레지스트리(`configs/`)에서 읽는다. 개인키 파일에서 유도하지 않는다 — 유도하면 레지스트리가 dormant해져 audit MEDIUM#4와 같은 drift가 생긴다. 단 서명 직전 1회, 로드한 개인키의 공개키가 레지스트리 값과 **일치하는지 대조**하고 불일치면 거부한다 |
| private key 사용 | 서명 생성 **한 가지 용도로만** 쓴다. 암호화·인증·토큰 발급에 재사용하지 않는다. 값은 로그·예외 메시지·stdout·레코드 어디에도 나타나지 않는다 |
| permission/error | 모든 오류는 **fail-closed**이며 안정적인 문자열 코드로 보고한다(§4.1). "키가 없으니 새로 만든다", "검증 실패지만 통과시킨다"는 경로를 두지 않는다 |
| rotation | §8 |
| retired key | 개인키 파일은 **삭제하지 않고** `retired/`로 이동(수동 삭제만 허용, `review_store.py`의 `manual_delete_only` 보존 정책과 동일 사상). 공개키는 레지스트리에 `status: retired`로 영구 잔류 |
| 기존 signature 검증 | 은퇴 키로 서명된 과거 기록은 **계속 유효**하다. 검증은 서명 시각이 아니라 키의 레지스트리 등재 여부로 판단한다(§7.3) |

### 4.1 오류 코드 (확정)

`review_store.py`의 `ReviewStoreError("local_state_dir_inside_repo")` 스타일을 그대로 따른다.

구현된 전체 목록은 `orchestrator/role-signing/lib/errors.js`의 `ERROR_CODES`가 단일 원천이며,
알 수 없는 코드로 오류를 만들면 그 자체가 예외가 된다(오타가 모호한 메시지로 새지 않도록).

| 분류 | 코드 |
| --- | --- |
| 저장/경로 (§6) | `signing_key_dir_inside_repo`, `signing_key_dir_must_be_absolute`, `signing_key_path_not_safe`, `signing_key_not_found`, `signing_key_already_exists`, `signing_key_permission_unsafe`, `signing_key_malformed`, `signing_key_public_mismatch` |
| 레지스트리/역할 (§3, §6.4, §7.1) | `registry_malformed`, `unknown_role`, `role_not_issuable`, `role_has_no_active_key`, `role_has_multiple_active_keys`, `unknown_key_id`, `key_retired_for_signing`, `role_key_mismatch`, `registry_key_file_mismatch` |
| 레코드/봉투 (§5) | `record_malformed`, `record_not_canonicalizable`, `record_type_unsupported`, `record_type_mismatch`, `envelope_malformed`, `payload_digest_mismatch`, `signature_invalid` |

초판 목록 대비 추가된 코드와 이유:

- `signing_key_path_not_safe` — 경로 해석·파일 접근 자체가 실패한 경우. OS 오류 메시지를
  그대로 흘리지 않기 위해 하나의 코드로 접는다.
- `unknown_role` / `role_not_issuable` — 4역할 밖의 이름과, 역할은 맞지만 아직 발급 대상이
  아닌 경우(Owner 결정 5)를 구분한다.
- `registry_key_file_mismatch` — `verify-keys`가 레지스트리에는 없는데 `active/`에 파일만
  남은 고아 상태를 보고한다(§8의 "원자적 대신 검증 가능하게").
- `record_malformed` / `record_not_canonicalizable` — 스키마 위반과, 스키마는 맞지만 Python과
  바이트가 갈릴 수 있어 직렬화를 거부하는 경우(§5.3-1 각주)를 구분한다.
- `record_type_unsupported` / `record_type_mismatch` — 서명 대상이 아닌 `contract_type`과,
  봉투가 주장하는 타입이 실제 레코드와 다른 경우를 구분한다.
- `envelope_malformed` / `payload_digest_mismatch` — 봉투 형식 위반과, 봉투가 다른 레코드를
  가리키는 경우.
- `key_retired_for_signing`은 "그 역할의 키가 전부 은퇴 상태"일 때 쓴다. 키가 애초에 없었던
  경우(`role_has_no_active_key`)와 구분해야 로테이션이 중간에 멈춘 상황이 드러난다.

## 5. Signed record

### 5.1 무엇에 서명하는가 — 두 종류

**(a) Review 결과** — 기존 `ReviewRecord`(`review_record.py`, `contract_type:
hermes_review_record`)를 그대로 대상으로 삼는다. 이미 canonical JSON과
`review_record_digest()`가 있어 추가 스키마가 필요 없다.

**(b) QA 결과** — 대상 구조가 없으므로 신규 정의한다. **Owner 결정 3에 따라
`review_record.py`의 규약을 상속하는 최소 신규 스키마**로 확정한다(`contract_type` +
`version` 쌍, UTC 타임스탬프 형식, canonical JSON, 64KiB 상한을 그대로 물려받고 새 규약을
만들지 않는다).

```
{
  "contract_type": "jarvis_qa_result",
  "version": "0.1A",
  "qa_id": "qa_<24hex>",
  "project_id": "<1..64자>",
  "task_id": "<1..128자>",
  "candidate_commit": "<40 또는 64자 소문자 hex>",
  "qa_kind": "unit" | "smoke" | "deterministic" | "manual",
  "commands": ["<실행한 검증 명령>", ...],     // outcome != not_required이면 1개 이상
  "outcome": "pass" | "fail" | "not_required",
  "reason": "<사유>" | null,                  // fail·not_required이면 필수
  "evidence_digest": "<64자 hex>" | null,     // 선택
  "created_at": "YYYY-MM-DDTHH:MM:SSZ"
}
```

- `qa_kind` 허용값은 위 4개로 고정하며 임의 확장하지 않는다. SOP §QA의 "가장 가벼운 충분한
  QA를 선택"을 표현하기 위한 최소 집합이다.
- `outcome == "not_required"`이면 `commands`는 **비어 있어야** 하고 `reason`이 **필수**다.
  SOP의 "`not_required`와 이유를 기록"을 스키마 수준의 강제로 승격한 것이다.
- `outcome == "fail"`이면 `reason`이 필수다. `pass`이면 `reason`은 `null`이어야 한다 —
  통과에 사유를 달아 판정을 흐리지 않기 위함이다.
- 알려지지 않은 필드는 **거부**한다(fail-closed). 조용히 무시하면 서명 대상이 서명자와
  검증자 사이에서 달라질 수 있다.

서명은 **원본 레코드를 변형하지 않는다.** 서명 봉투(envelope)를 레코드 옆에 따로 만든다.
`task_append.js`의 P2-3 교훈과 같은 이유다 — 기존 파서가 읽는 구조에 새 필드를 끼워 넣으면
조용히 깨진다.

### 5.2 서명 봉투 스키마

```
{
  "contract_type": "jarvis_role_signature",
  "version": "0.1A",
  "record_type": "hermes_review_record" | "jarvis_qa_result",
  "record_version": "<서명 대상 레코드의 version>",
  "role": "implementer" | "reviewer" | "qa" | "docs",
  "key_id": "<32자 hex>",
  "public_key": "<64자 hex>",
  "correlation_id": "<review_id 또는 task_id>",
  "payload_digest": "<64자 hex>",
  "signed_at": "YYYY-MM-DDTHH:MM:SSZ",
  "signature": "<128자 hex>"
}
```

### 5.3 정확히 무엇의 바이트에 서명하는가

1. **canonicalization**: 대상 레코드를 기존 규칙으로 직렬화한다 —
   `json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",",":"), allow_nan=False)`.
   `review_record.py`가 이미 쓰는 규칙 그대로이며 새 규칙을 만들지 않는다.
2. **encoding**: 그 문자열을 UTF-8(`errors="strict"`)로 인코딩해 `canonical_bytes`를 얻는다.
3. **도메인 분리**: 목적별 prefix를 앞에 붙인다. `change_evidence.py` 패턴 그대로다.
   - Review: `b"jarvis-core/role-signature/hermes-review-record/v0.1A\x00"`
   - QA: `b"jarvis-core/role-signature/qa-result/v0.1A\x00"`
   서로 다른 목적의 서명이 교차 재사용되는 것을 막는다.
4. **서명**: `Ed25519(signing_input)`, `signing_input = domain_prefix + canonical_bytes`.
   Ed25519는 PureEdDSA라 **사전 해시가 필요 없다** — 메시지에 직접 서명한다.
5. **hash 필요 여부**: 서명에는 불필요하지만, 상관관계·중복탐지·사람이 읽는 로그를 위해
   `payload_digest = sha256(signing_input).hexdigest()`를 봉투에 **함께 기록**한다.
   검증은 digest가 아니라 서명으로 한다(digest 일치는 필요조건일 뿐 인증이 아니다 —
   `passesInboundGate`가 태그 일치만으로 인증을 인정하지 않는 것과 같은 원칙).
6. **signature algorithm**: Ed25519 (RFC 8032), 64바이트 → 128자 소문자 hex.
7. **encoding 규약**: 모든 바이트 값은 **소문자 hex**. `configs/buzz-agent-identities.json`이
   pubkey를 hex로 쓰는 기존 관례와 일치시킨다(base64 혼용 금지).
8. **timestamp**: `signed_at`은 UTC `YYYY-MM-DDTHH:MM:SSZ`.
   `review_record.py:_UTC_TIMESTAMP_PATTERN`과 동일 형식. **timestamp는 신뢰의 근거가
   아니라 기록일 뿐이다** — 검증 판정에 쓰지 않는다(§7.3).

### 5.4 verification 결과 형식

```
{"valid": true,  "role": "...", "key_id": "...", "key_status": "active"|"retired"}
{"valid": false, "reason": "<§4.1 오류 코드 하나>"}
```

`valid`는 boolean 하나이며 "부분 통과"나 경고 상태를 두지 않는다. 실패 사유는 코드로만
표현하고 개인키·경로·내부 상태를 노출하지 않는다(P2-4의 `unauthorized` 일반화와 동일 사상).

**검증 강제 시점(Owner 결정 6):** 이 검증은 **`verify-records` 수동 점검 명령으로만**
호출된다. 리뷰 기록 저장 시점이나 조회 시점에 자동으로 끼워 넣지 않는다 — 강제 지점을
넓히면 기존 흐름에 fail-closed 지점이 늘어나고, 아직 서명되지 않은 과거 기록이 전부
막힌다. 자동 강제로의 확대는 별도 Owner 결정 사항이다.

## 6. Storage

### 6.1 경로 정책 (기존 정책 재사용)

`resolve_review_store_paths()`의 3단 우선순위를 **그대로** 쓰고 마지막 세그먼트만 바꾼다.

1. `JARVIS_LOCAL_STATE_DIR` 환경변수(절대경로 필수, 상대경로면 거부)
2. Windows + `%LOCALAPPDATA%` → `%LOCALAPPDATA%\Jarvis-Core\`
3. 그 외 → `~/.jarvis-core/`

여기에 `SIGNING_KEY_SEGMENTS = ("signing-keys", "v1")`을 덧붙인다
(`("hermes-manager","reviews","v1")`과 형제 관계).

```
<state_root>/signing-keys/v1/
  active/<role>.key          # 개인키, 0600
  retired/<role>-<key_id>.key
```

🔴 **`_is_path_inside(resolved_dir, repo_root)` 가드를 반드시 재사용한다.** 해석된 경로가
저장소 안이면 `signing_key_dir_inside_repo`로 즉시 거부한다. 이것이 "개인키가 실수로
커밋되는" 최악의 사고를 구조적으로 막는 단일 방어선이다.

### 6.2 권한

- 디렉터리: `mkdir(mode=0o700)` + 생성 후 `os.chmod(0o700)` (기존 코드가 두 번 다 하는
  이유는 umask 때문이며 그대로 따른다)
- 파일: `os.open(path, O_WRONLY|O_CREAT|O_EXCL|O_BINARY, 0o600)`
- 로드 시 권한 확인: POSIX에서 group/other 비트가 있으면 `signing_key_permission_unsafe`로
  거부. **Windows에서는 POSIX 모드 비트가 의미 있게 강제되지 않으므로**, 부모 디렉터리가
  `%LOCALAPPDATA%` 아래(사용자 프로필 ACL로 보호)라는 사실에 의존하고 이 한계를 문서에
  명시한다 — 강제되지 않는 것을 강제된다고 기록하지 않는다.

### 6.3 파일 형식

- **개인키**: 32바이트 Ed25519 seed를 **소문자 hex 64자 + 개행 1개**, 그 외 아무것도 없음.
  PEM/PKCS#8을 쓰지 않는 이유는 파서 의존성을 늘리지 않기 위함이고, 형식이 단순할수록
  "이 파일에 비밀이 들어 있다"가 명확해서다.
- **공개키**: 개인키 파일에 넣지 않는다. tracked 레지스트리에만 둔다(§6.4).
- **plaintext secret 취급**: 개인키 파일은 **평문 비밀**이다. 암호화(passphrase)를 이번
  범위에서 도입하지 않는다 — 로컬 1인 환경에서 passphrase는 결국 어딘가에 평문으로
  저장되기 쉬워 실익 없이 복잡도만 늘린다. 대신 (a) 저장소 밖, (b) 0600/0700,
  (c) 저장소-안-금지 가드, (d) 로그·에러 미노출 네 가지로 방어한다. **이 판단은 Owner
  확인이 필요한 항목이다(§7.4).**
- **backup**: 자동 백업을 만들지 **않는다.** 백업은 비밀의 사본을 늘리는 행위다. 키를
  잃으면 로테이션으로 새 키를 발급하면 되고, 과거 기록은 레지스트리의 은퇴 공개키로
  계속 검증된다 — 즉 개인키 분실은 복구 불가능한 사고가 아니다. 클라우드 동기화
  폴더(OneDrive/Dropbox 등)에 state_root를 두는 것은 금지 사항으로 문서화한다.

### 6.4 공개키 레지스트리 (tracked)

`configs/buzz-agent-identities.json`의 "공개 식별자는 tracked, 비밀은 저장소 밖" 패턴을
그대로 복제해 `configs/jarvis-role-signing-keys.json`(신규, tracked)을 둔다.

```
{
  "$comment": "역할별 Ed25519 공개키 레지스트리. 공개키와 상태만 담으며 비밀 값은 절대 넣지 않는다.",
  "keys": [
    {"role":"reviewer","key_id":"<32hex>","public_key":"<64hex>",
     "status":"active","created_at":"...Z","retired_at":null}
  ]
}
```

- 비밀 값을 담지 않으므로 `scripts/check_no_secrets.py`의 탐지 패턴(`key|secret|token|
  password` 할당)에 걸리지 않는다. 필드명을 `public_key`로 두는 것이 그 점에서도 안전하다.
- 이 파일이 **신뢰의 단일 원천**이다. 코드가 개인키에서 공개키를 유도해 쓰지 않는 이유가
  여기 있다(§4 "public key 조회").

## 7. Trust model

### 7.1 신뢰 규칙

| 상황 | 판정 |
| --- | --- |
| 레지스트리에 있고 `active` | 서명 생성 ✅ / 검증 ✅ |
| 레지스트리에 있고 `retired` | 서명 생성 ❌ `key_retired_for_signing` / 검증 ✅ |
| 레지스트리에 없는 키 | ❌ `unknown_key_id` — 서명이 수학적으로 유효해도 **거부**한다 |
| 서명 검증 실패 | ❌ `signature_invalid` |
| 봉투의 `role`과 레지스트리의 `role` 불일치 | ❌ `role_key_mismatch` |
| 봉투의 `public_key`와 레지스트리의 `public_key` 불일치 | ❌ `role_key_mismatch` |
| 한 역할에 `active` 키가 0개 / 2개 이상 | ❌ `role_has_no_active_key` / `role_has_multiple_active_keys` |
| 개인키 파일 변조(형식 불량, 길이 불일치) | ❌ `signing_key_malformed` |
| 개인키 파일이 레지스트리 공개키와 불일치 | ❌ `signing_key_public_mismatch` |
| 레지스트리 파일 자체가 손상/파싱 불가 | ❌ `registry_malformed` — 이 경우 **모든 검증이 실패**한다(fail-closed) |

### 7.2 신뢰 경계에서 명확히 해 둘 것

- **서명은 "누가 만들었는가"만 증명한다. 승인이 아니다.** 서명된 리뷰 결과가 곧 승인이
  되어서는 안 된다 — Jarvis의 승인 권한은 P2-4/P2-5에서 확립한 대로 `/approve`와 Owner
  신원 검증이 100% 소유한다. `Buzz message ≠ approval`과 같은 층위의 불변식으로
  **`Valid signature ≠ approval`**을 명문화한다.
- 레지스트리는 저장소에 tracked이므로, 레지스트리를 고칠 수 있는 사람은 신뢰 집합을 고칠 수
  있다. 이는 git 이력에 남는다는 것이 방어책이며(감사 추적), 이 설계는 저장소 쓰기 권한을
  가진 공격자를 위협 모델에 포함하지 않는다. 그런 공격자는 검증 코드 자체를 고칠 수 있다.
- 이 설계는 **로컬 단일 사용자** 모델이다. 키를 여러 기기에 배포하거나 원격에서 검증하는
  것은 범위 밖이다.

### 7.3 시각(timestamp)을 신뢰하지 않는 이유

`signed_at`은 서명자가 자기 봉투에 써 넣는 값이라 자기 증명이 아니다. 따라서 "은퇴 시각
이전에 서명되었는가"로 판정하지 않고, **키가 레지스트리에 등재되어 있는가**로만 판정한다.
시각 기반 판정을 하려면 신뢰할 수 있는 타임스탬프 원천이 필요한데 그것은 이 범위 밖이다.

## 8. Rotation

로테이션은 **Owner가 명시적으로 실행하는 별도 명령**이며, 서명 경로에서 자동으로 일어나지
않는다. 순서를 지킨다.

1. **새 키 생성** — 새 keypair를 만들고 `active/<role>.key`가 이미 있으면 먼저 4번을 수행한
   뒤에만 쓴다(덮어쓰기 금지, `O_EXCL`).
2. **기존 키 retired 처리** — 레지스트리에서 해당 역할의 기존 항목을 `status: "retired"`,
   `retired_at: "<UTC>"`로 바꾼다. **항목을 삭제하지 않는다.**
3. **새 키 등록** — 레지스트리에 `status: "active"` 항목을 추가한다. 이 시점에 그 역할의
   active 키는 정확히 1개여야 하며 아니면 전체 연산을 실패시킨다.
4. **개인키 파일 이동** — 기존 `active/<role>.key` → `retired/<role>-<old_key_id>.key`.
   삭제하지 않는다(수동 삭제만).
5. **기존 기록 검증** — 은퇴 키로 서명된 과거 기록은 §7.1에 따라 **계속 유효**하다.
   재서명하지 않는다. 과거 기록을 새 키로 다시 서명하는 것은 이력 위조에 가깝다.
6. **현재 기록 서명** — 로테이션 이후의 새 기록은 새 active 키로만 서명된다.
7. **rotation metadata** — 레지스트리 항목의 `created_at`/`retired_at`과 git 이력이
   로테이션 기록 그 자체다. 별도 로테이션 로그 파일을 만들지 않는다(단일 원천 유지).

레지스트리 갱신과 파일 이동 사이에 실패하면 불일치가 생길 수 있다. 이를 원자적으로 만드는
대신 **검증 가능하게** 만든다 — `verify-keys` 점검 명령이 (레지스트리 active 키) ↔
(`active/` 파일)의 1:1 대응을 확인하고 어긋나면 fail-closed로 보고한다.

## 9. 범위 밖 (승인 이후에도 유지)

Owner 결정 1~7(§10)로 **구현은 승인되었다.** 아래 항목은 승인 이후에도 여전히 범위 밖이며,
별도 Owner 결정 없이 착수하지 않는다.

- ~~**실제 키 생성 실행.**~~ **2026-09-03 Owner의 명시적 지시로 실행 완료**
  (`reviewer` / `qa` 각 1개 active). 불변식은 그대로다 — 구현은 키를 만들어 두지 않으며,
  생성은 Owner가 CLI를 직접 실행할 때만 일어난다(AGENTS.md 원칙 5 예외 조건 1).
  스모크 테스트를 포함한 어떤 자동 경로도 실제 키를 만들거나 건드리지 않는다.
- **`implementer` / `docs` 키 발급** — Owner 결정 5에 따라 `reviewer` / `qa`만 우선
  발급한다. 4역할 모델은 스키마에 남기되 생성 명령은 두 역할만 허용한다.
- **passphrase 암호화** — Owner 결정 4에 따라 도입하지 않는다.
- **검증의 자동 강제** — Owner 결정 6에 따라 `verify-records` **수동 점검 명령으로만**
  시작한다. 리뷰 기록 저장·조회 경로에 fail-closed 검증 지점을 심지 않는다.
- 기존 리뷰/QA 기록의 **소급 서명 또는 마이그레이션**.
- 기존 Python 모듈 수정 — `review_store.py`/`review_record.py`/`change_evidence.py`는
  **읽기 전용 참조**이며 이번 구현에서 한 줄도 바꾸지 않는다.
- 신규 서드파티 의존성 — Python·Node 양쪽 모두 0개(Owner 결정 2).
- Nostr/Relay를 키 관리에 사용하는 것 — 보고서가 명시적으로 불필요하다고 판정.
- task-0038 §6-④(Reviewer/QA를 Buzz 에이전트로 등록 + worktree 격리) 착수.
  **task-0042가 ④의 선행조건인 것은 사실이나, 이 승인이 ④를 승인하지 않는다.**
- Discord intake 연결, inbound approval, supervisor, Director Dashboard, 새 DB, 새 UI,
  외부 KMS.
- task-0044(감사 해시체인)와의 통합 — 별개 task이며 여기서 `prev_hash`를 정의하지 않는다.

## 10. Owner 결정 (2026-09-03 승인)

초판 §10의 미해결 질문 7건은 모두 결정되었다. 아래가 확정된 계약이다.

| # | 질문 | 결정 | 반영 위치 |
| --- | --- | --- | --- |
| 1 | AGENTS.md 원칙 5 충돌 | **승인.** 원칙 5에 "Jarvis 자체 신원·서명용 로컬 키페어" 예외를 명문화하되, 5개 조건을 모두 만족할 때만 허용 | `AGENTS.md` 원칙 5, §9 |
| 2 | 암호 라이브러리 선택 | **Node.js stdlib `crypto`의 Ed25519 경로.** 신규 Python 암호 의존성 추가 금지. 초판의 "Python 의존성 추가가 불가피" 전제는 **틀렸으며 정정됨** | §2.2-1, §2.3 |
| 3 | QA 결과 스키마 | **`review_record.py` 규약을 상속하는 최소 신규 스키마**(`jarvis_qa_result` v0.1A) | §5.1(b) |
| 4 | 개인키 passphrase | **없음.** 저장소 밖 + 0600/0700 + 저장소-안-금지 가드 + 미노출 4중 방어로 충분하다고 판단 | §6.3 |
| 5 | 서명 대상·키 발급 범위 | **`reviewer` / `qa` 키만 우선 발급.** `implementer`/`docs`는 대상 레코드가 생길 때 별도 결정 | §3.1, §9 |
| 6 | 검증 강제 시점 | **`verify-records` 수동 점검 명령으로 시작.** 저장·조회 경로에 자동 강제를 심지 않는다 | §5.4, §9 |
| 7 | Windows 권한 한계 | **수용하되 문서에 명시.** POSIX 모드 비트가 강제되지 않으므로 `%LOCALAPPDATA%` 사용자 프로필 ACL에 의존한다는 사실을 숨기지 않는다 | §6.2 |

### 10.1 결정 1의 5개 조건 (AGENTS.md 예외의 성립 요건)

예외는 아래를 **모두** 만족할 때만 성립한다. 하나라도 어긋나면 원칙 5가 그대로 적용된다.

1. Owner가 명시적으로 실행할 때만 생성한다 — 자동 생성 경로 없음(§4 "최초 생성").
2. 저장소 완전 밖에 저장한다 — 저장소-안-금지 가드로 fail-closed(§6.1).
3. 사용자 전용 권한으로 보호한다 — 0700 디렉터리 / 0600 파일(§6.2).
4. 공개키만 저장소에 기록한다 — tracked 레지스트리는 공개키·상태만(§6.4).
5. 개인키 값은 로그·에러·산출물에 절대 노출하지 않는다 — 오류는 §4.1의 코드로만 보고(§5.4).

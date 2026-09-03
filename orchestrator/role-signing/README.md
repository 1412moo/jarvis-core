# orchestrator/role-signing

task-0042 구현. Reviewer / QA 역할이 각자 로컬 Ed25519 키페어를 갖고 결과 레코드에
서명한다. 설계와 확정된 결정사항은
[`docs/task-0042-role-based-signing-keys-design.md`](../../docs/task-0042-role-based-signing-keys-design.md)에 있다.

## 의존성 없음

Node.js stdlib `crypto`만 쓴다(Owner 결정 2). `npm install`이 필요 없고
`package.json`에 `dependencies`가 없다. Python 쪽에도 새 암호 의존성을 추가하지 않았다.

> 설계 초판은 "Python에 Ed25519가 없으므로 신규 암호 의존성 추가가 불가피하다"고 적었으나
> **이 전제는 틀렸다.** 저장소가 이미 Node를 쓰고 있고 Node stdlib `crypto`는 Ed25519를
> 기본 지원한다. 설계 문서 §2.2-1에 정정 기록이 남아 있다.

## 안전 불변식

이 코드가 지키는 것, 그리고 지키지 않는 것을 먼저 읽는 편이 좋다.

- **유효한 서명은 승인이 아니다.** `Valid signature != approval`은 `Buzz message != approval`과
  같은 층위의 불변식이다. 승인 권한은 `/approve`와 Owner 신원 검증이 100% 소유하며 이
  모듈은 그 경로에 관여하지 않는다. 서명이 증명하는 것은 **작성자**뿐이다.
- **개인키는 저장소 밖에만 있다.** 해석된 키 디렉터리가 저장소 안이면
  `signing_key_dir_inside_repo`로 즉시 거부한다. 이것이 "개인키가 실수로 커밋되는" 사고를
  막는 구조적 방어선이다.
- **키는 Owner가 명령을 칠 때만 생긴다.** import 시점·봇 기동·테스트 중 어떤 경로도 키를
  만들지 않는다. 스모크 테스트는 임시 디렉터리와 임시 레지스트리에서만 동작한다.
- **개인키 값은 어디에도 나타나지 않는다.** 반환값·로그·오류·서명 봉투 모두. 오류는
  `lib/errors.js`의 고정 코드 하나로만 보고하며 경로나 내부 상태를 담지 않는다.
- **레지스트리에 없는 키는 거부한다.** 서명이 수학적으로 유효해도 마찬가지다.
- **검증은 수동 명령뿐이다.** 기록 저장·조회 경로에 자동 강제를 심지 않았다(Owner 결정 6).

## 저장 위치

`review_store.py:resolve_review_store_paths()`의 3단 우선순위를 그대로 쓰고 마지막
세그먼트만 바꾼다.

1. `JARVIS_LOCAL_STATE_DIR`(절대경로 필수)
2. Windows + `%LOCALAPPDATA%` → `%LOCALAPPDATA%\Jarvis-Core`
3. 그 외 → `~/.jarvis-core`

```
<state_root>/signing-keys/v1/
  active/<role>.key           # 0600, 32바이트 seed의 hex 64자 + 개행
  retired/<role>-<key_id>.key
```

공개키는 저장소 안 `configs/jarvis-role-signing-keys.json`(tracked)에만 있고, 이 파일이
신뢰의 단일 원천이다. 코드는 개인키에서 공개키를 유도해 쓰지 않는다 — 그렇게 하면
레지스트리가 dormant해져 audit MEDIUM#4와 같은 drift가 생긴다.

### Windows 권한 한계 (Owner 결정 7)

POSIX에서는 group/other 비트가 있으면 `signing_key_permission_unsafe`로 거부한다.
**Windows에서는 POSIX 모드 비트가 의미 있게 강제되지 않는다.** 그래서 Windows에서의 보호는
`%LOCALAPPDATA%`가 사용자 프로필 ACL 아래 있다는 사실에 의존한다. `verify-keys`는 이 사실을
`permission_enforced: false`, `permission_basis: "windows_user_profile_acl"`로 그대로
보고한다 — 강제되지 않는 것을 강제된다고 기록하지 않는다.

state_root를 OneDrive/Dropbox 같은 클라우드 동기화 폴더 아래에 두지 않는다. 자동 백업도
만들지 않는다 — 백업은 비밀의 사본을 늘리는 행위이고, 키를 잃어도 로테이션으로 새 키를
발급하면 되며 과거 기록은 은퇴 공개키로 계속 검증된다.

## 명령

```bash
node cli.js generate-key --role reviewer      # Owner만 실행. reviewer/qa만 허용
node cli.js generate-key --role qa
node cli.js list-keys                          # 공개 정보만
node cli.js verify-keys                        # 레지스트리 <-> active/ 파일 1:1 점검
node cli.js sign-record --role qa --record qa-result.json --out qa-result.sig.json
node cli.js verify-records --record qa-result.json --signature qa-result.sig.json
node cli.js verify-records --dir ./records     # X.json <-> X.sig.json 짝
node run_smoke_tests.js                        # 임시 디렉터리에서만 동작
```

`verify-keys`와 `verify-records`는 실패 시 exit code 1을 낸다. 나머지 실패는
`{"error":"<code>"}`를 출력하고 1로 끝난다.

`generate-key`는 이미 활성 키가 있는 역할에 대해서는 거부한다. 키 교체는 `rotate-key`다.

## 서명 대상

| record_type | 정의 위치 | 서명 도메인 접두사 |
| --- | --- | --- |
| `hermes_review_record` | `apps/hermes-manager-pilot/.../review_record.py` (기존, 수정 없음) | `jarvis-core/role-signature/hermes-review-record/v0.1A\0` |
| `jarvis_qa_result` | `lib/qa_record.js` (신규 v0.1A) | `jarvis-core/role-signature/qa-result/v0.1A\0` |

서명은 **원본 레코드를 변형하지 않는다.** 봉투(`*.sig.json`)를 레코드 옆에 따로 만든다 —
기존 파서가 읽는 구조에 새 필드를 끼워 넣으면 조용히 깨진다는 P2-3 `task_append.js` 교훈이다.

### canonical JSON 동등성

`lib/canonical.js`는 `review_record.py:serialize_review_record()`의
`json.dumps(..., ensure_ascii=False, sort_keys=True, separators=(",",":"), allow_nan=False)`와
**바이트 단위로 동일한** 출력을 만든다(제어문자 이스케이프, 비ASCII 원문 유지, astral 키
정렬까지 대조 확인함).

Python과 갈릴 수 있는 입력은 **추측하지 않고 거부한다.** 두 언어가 다르게 직렬화하는
바이트에 서명하는 것보다 거부가 낫기 때문이다.

- 정수가 아닌 수 — Python `repr(1.0)`은 `"1.0"`, JS `String(1.0)`은 `"1"`
- `NaN`/`Infinity` — `allow_nan=False`
- 짝 없는 surrogate — JS는 이스케이프하고 Python은 원문을 낸 뒤 UTF-8 strict에서 실패

## 검증 상태

`reviewer` / `qa` 키는 2026-09-03 Owner 지시로 생성되었고 `verify-keys` PASS다. 실제 키로
다음을 확인했다.

- 실제 `hermes_review_record`(Python `review_record.py`가 생성한 942바이트)를 `reviewer`
  키로 서명 → 검증 통과. Node가 만든 canonical 바이트가 Python `serialize_review_record()`
  출력과 **완전히 동일**하고 SHA-256이 `review_record_digest()`와 일치했다.
- Python이 그 레코드를 다시 파싱·재직렬화해도 같은 서명이 계속 검증된다.
- `jarvis_qa_result`를 `qa` 키로 서명 → 검증 통과.
- 변조 거부 4종: 레코드 1글자 변경(`payload_digest_mismatch`), 서명 1바이트 변경
  (`signature_invalid`), 역할 위장(`role_key_mismatch`), 타입 교차 재사용
  (`record_type_mismatch`). 실패 시 exit code 1.

재현 절차(산출물은 저장소 밖 임시 디렉터리에만 만들 것):

```bash
node cli.js sign-record --role qa --record <record>.json --out <record>.sig.json
node cli.js verify-records --record <record>.json --signature <record>.sig.json
```

## 아직 하지 않은 것

- `implementer` / `docs` 키 발급 — 서명 대상 레코드가 정의될 때 별도 결정(Owner 결정 5).
- passphrase 암호화(Owner 결정 4), 자동 백업.
- 저장·조회 경로에서의 검증 자동 강제(Owner 결정 6).
- 기존 리뷰/QA 기록의 소급 서명·마이그레이션.
- task-0044(감사 해시체인)와의 통합 — 별개 task이며 `prev_hash`를 정의하지 않는다.

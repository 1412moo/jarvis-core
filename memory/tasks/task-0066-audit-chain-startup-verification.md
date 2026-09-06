# task-0066-audit-chain-startup-verification

- id: `task-0066-audit-chain-startup-verification`
- title: `기동 시 감사 체인 읽기 전용 검증(warning) + /status 상태 노출`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-06 18:16 UTC`
- updated_at: `2026-09-06 18:16 UTC`
- summary: `Owner 결정에 따라 기동 시 감사 체인을 읽기 전용으로 검증하되 손상돼도 봇은 기동한다. 기동 거부는 감사가 승인을 인질로 잡는 구조라는 task-0044 결정 6과 같은 이유로 택하지 않았다. 대신 /status에 체인 상태를 중첩 필드로 노출했다. 구현 전 두 함수의 실제 예외 계약을 실측했고, 기존 /status 출력이 바이트 단위로 보존됨을 HEAD 버전과 직접 비교해 증명했다. 검증은 아무것도 만들지 않는다 — 실제 상태 디렉터리에 audit 폴더가 생기지 않는다.`
- source_command: `task-0065 조사 후 Owner 결정 — A는 warning, B를 같은 작업에 포함`

## 기준선

HEAD `3a2560a` = `origin/main`. 변경은 `adapters/discord/bot_minimal.py` **한 파일**과
이 기록뿐이다. **+267 / -0**, 삭제 0줄.

## Owner 결정

> 감사 체인 손상은 봇 전체 기동을 막지 않는다.

task-0065에서 fail-closed / warning을 양쪽 다 분석했고 Owner가 warning을 택했다. 근거는
task-0044 **결정 6**과 같은 형태다 — *"fail-closed 상한은 감사 기능이 승인 기능을 인질로
잡는 구조가 된다."* 기동 거부는 보존 상한보다 강한 인질이고, P2-4가 의도적으로 전원에게
열어 둔 읽기 전용 6종까지 함께 죽는다.

## 구현 전에 실제 예외 계약을 코드에서 확인했다

추측으로 쓰지 않았다. 임시 state 디렉터리로 전부 실측했다.

| 호출 | 실제 동작 |
| --- | --- |
| `resolve_audit_chain_paths()` 상대 경로 | `AuditChainError(local_state_dir_must_be_absolute)` |
| 같은 함수, 저장소 내부 경로 | `AuditChainError(local_state_dir_inside_repo)` |
| 같은 함수, 존재하지 않는 절대경로 | **정상 반환** — 아무것도 만들지 않는다 |
| `verify_audit_chain()` 없는 파일 / 디렉터리 | **예외 없이** `{'valid': True, 'length': 0, ...}` |

`verify_audit_chain`은 사실상 total이지만 **두 호출 모두 `except Exception`으로 감쌌다.**
기동 경로에서 예외가 새면 봇이 죽고, 그건 Owner 결정과 정반대 결과가 된다.

## 반환 shape — 어휘를 둘로 만들지 않았다

`verify_audit_chain` 자신의 계약을 그대로 따랐다.

```
{"valid": true,  "length": N, "head_hash": "..."|null}
{"valid": false, "reason": "<stable code>"}
```

`first_bad_seq`·`detail`·경로·OS 오류는 **stderr로만** 나간다(결정 5의 2계층 계약).
경로를 못 읽는 모든 경우는 새 상수 `audit_chain_unavailable` 하나로 수렴시켰다.

## 기동 검증

`main()`에서 env 검증 **뒤**, `asyncio.run()` **앞**.

`_validate_required_env()` **안에는 넣지 않았다.** 그 함수의 계약은 "기동 거부"인데 이번
결정은 그 반대다. 분리해 두면 나중에 정책이 바뀌어도 호출 지점이 움직이지 않는다.

```
정상   [audit] chain ok: length=22
빈것   [audit] chain ok: empty (no audit entries recorded yet)
손상   [audit] WARNING: chain verification failed (missing_trailing_newline).
       The bot will start and read-only commands keep working; approvals still
       fail closed. Check /status for the current chain state.
```

실행 후 실제 상태 디렉터리는 `signing-keys` 하나 그대로다 — **`audit/`가 생기지 않았다.**
소급 기록 금지 원칙대로 읽기만 한다.

## /status

`payload["audit_chain"]`을 **중첩 dict**로 추가했다. 체인은 전역인데 나머지는 task 단위라
의미가 다르고, 중첩 키는 지금도 앞으로도 task 필드와 충돌할 수 없다.

```
audit chain:
- valid: `true`
- length: `0`
- note: `empty`          <- 첫 기동이 정상/empty 로 명확히 표현된다
```

손상 시 `- valid: false` / `- reason: hash_mismatch`. `/status`는 체인을 재기록하거나
repair하지 않으며 전용 테스트가 바이트 동일성을 확인한다.

### 기존 출력 계약 보존을 기계적으로 증명했다

`git show HEAD:` 버전을 같은 `__file__`로 로드해 신·구를 직접 비교했다.

| 대상 | 결과 |
| --- | --- |
| task 3건의 reply(task 부분) | **바이트 동일** |
| payload 키 | 추가 `audit_chain` 1개, **제거 0 / 변경 0** |
| `/status` usage · not_found · invalid | payload·reply **완전 동일** |

## 구현 중 잡은 것 둘

1. **첫 초안의 변조가 잘못됐다.** `"applied":true` → `"applied":fals`는 JSON이 깨져
   `hash_mismatch`가 아니라 파싱 오류를 낸다. `"decision":"approve"` → `"reject"`로 바꿔
   **JSON도 스키마도 유효하고 해시만 어긋나는** 진짜 변조로 만들었다.
2. **`inside_repo` 케이스가 처음엔 통과하지 못했다.** self-check가 `REPO_ROOT`를 임시
   트리로 바꿔치기하는데 `resolve_audit_chain_paths`는 **audit_store 자신의 REPO_ROOT**로
   판정한다. 패치되지 않는 `THIS_DIR.parent.parent`를 쓰도록 고쳤다.

## 검증

self-check 79 → **92**. 신규 13건 전원 PASS.

| 검증 | 결과 |
| --- | --- |
| `bot_minimal` self-check | **92/92 PASS** |
| `audit-chain` | **7/7 PASS** |
| `discord-intake` | **86/86 PASS** |
| canonical 전수 | **63/63 PASS** |
| `jarvis-console` + self-test | PASS |
| `discord-nl-intent` | 35/35 PASS |
| `buzz-bridge` | **37/37 PASS** |
| `validate_multi_agent_sop` | `status=PASS` |
| `check_no_secrets --self-test` | `status=PASS` |
| 변경 파일 secret scan | **findings 0** |
| `git diff --check` | clean |
| 실제 체인 | **무변경** — exists false, `audit/` 미생성 |

신규 검사가 덮는 것: 첫 기동 / 빈 파일 / 정상 / hash 변조 / 잘린 마지막 줄 /
잘못된 state dir 3종 / 읽기가 파일을 만들지 않음 / 검증 전후 바이트 동일 /
`/status` 정상·손상 노출 / `/status`가 체인을 쓰지 않음.

## 보고해 둘 것 — /status 비용이 체인 길이에 비례한다

매 호출마다 전체를 검증하므로 실측상 0건 1.0ms, 100건 5.5ms, 1000건 41.8ms,
5000건 206.1ms다. 지금은 체인이 비어 있어 1ms다.

캐시하면 빨라지지만 표시값이 낡는다. **"현재 체인 상태"라는 요구에 맞추려면 라이브가
맞다고 판단해 정확성을 택했다.** 다른 판단이 필요하면 별도 결정 사항이다.

## 이번 단계 비범위

- append 경로 fail-closed — 무변경
- `transition_applied_without_audit` 의미 — 무변경(관련 검사 3건 계속 PASS)
- 콘솔 status transition은 계속 감사 범위 밖(task-0063/0064) — 콘솔 코드 0줄
- audit schema / kind / actor — 무변경
- 소급 audit 생성 · cross-check 도구 · append O(n제곱) 최적화 · signing key — 전부 없음
- `jarvis.bat` — 건드리지 않았다

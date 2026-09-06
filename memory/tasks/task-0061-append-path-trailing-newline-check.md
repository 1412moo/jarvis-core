# task-0061-append-path-trailing-newline-check

- id: `task-0061-append-path-trailing-newline-check`
- title: `감사 체인 append 경로에 잘린 마지막 줄 검사 추가 (verifier와 판정 일치)`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-06 16:29 UTC`
- updated_at: `2026-09-06 16:29 UTC`
- summary: `감사 체인의 두 검증기 중 append 경로만 마지막 줄 종결자 검사를 빠뜨리고 있었다. 크래시로 마지막 쓰기가 잘리면 다음 승인이 O_APPEND로 두 항목을 한 줄에 병합해 체인이 영구 파싱 불가가 되고, 그 뒤 모든 승인이 감사 없이 진행된다. verifier와 술어·위치·open 모드를 맞춘 검사 4줄을 넣어 병합 전에 fail closed 시켰다. 회귀 테스트는 수정 전 구현에 monkeypatch로 돌려 실제로 실패하는 것까지 확인했다. 기동 시 검증과 status 노출은 범위 밖이다.`
- source_command: `감사 체인 운영 경로 검증 분석 후 후보 C만 승인 (Owner)`

## 기준선

HEAD `0762c51` = `origin/main`. 변경은 `orchestrator/audit-chain/`의 두 파일과 이 기록뿐이며
**삭제 0줄**, 프로덕션 로직 추가는 4줄이다.

## 분석 단계에서 내 이전 보고를 정정했다

후보를 처음 올릴 때 나는 "감사 체인을 운영 경로에서 아무도 검증하지 않는다"고 적었다.
**틀렸다.** `append_audit_entry()`는 매 append마다 락 안에서 `read_chain_head()`를 부르고,
그 함수는 파일 전체를 훑으며 항목별 해시 재계산·seq 연속성·prev_hash 연결을 모두 확인한다.
`parse_audit_entry_json()`이 해시를 재계산해 `hash_mismatch`를 던지는 것도 실측했다.

정확한 진술은 "`verify_audit_chain()`이라는 **함수**가 운영 경로에서 안 불린다"이지
"검증이 안 된다"가 아니다. 그래서 이번 task의 근거는 처음 제시한 것과 다르다 — 아래가
실제로 남아 있던 공백이다.

## 진짜 결함 — 잘린 마지막 줄이 체인을 영구히 깨뜨린다

두 검증기의 검사 항목이 딱 하나 달랐다. `verify_audit_chain`에는
`missing_trailing_newline` 검사가 있고 `read_chain_head`에는 없었다.

크래시로 마지막 줄이 잘린 상태를 임시 체인에서 재현한 결과:

| 단계 | 수정 전 |
| --- | --- |
| 잘린 직후 | verifier는 `missing_trailing_newline`, **append 경로는 통과** |
| 다음 승인 | **성공** — O_APPEND가 종결자 없는 줄 뒤에 그대로 이어 붙인다 |
| 결과 | 두 항목이 **한 줄로 병합**, 체인이 `json_parse_failed`로 **영구 파싱 불가** |
| 그 이후 | 모든 승인이 `transition_applied_without_audit`로 진행 |

한 번의 잘린 쓰기가 아무 경고 없이 감사 기록 전체를 무효화한다. 승인 경로는 결정 1(ii-b)에
따라 전이 먼저·감사 나중·롤백 없음이라 **승인이 막히지도 않는다.**

## 수정 — 4줄

`read_chain_head()`의 줄 루프 맨 앞에 검사를 넣었다.

```python
if not line.endswith("\n"):
    raise AuditChainError(
        "audit_chain_corrupt_missing_trailing_newline",
        detail=f"line_{line_no}",
    )
```

`verify_audit_chain()`과 **판정이 일치하도록** 세 가지를 맞췄다.

| | verify | read_chain_head (수정 후) |
| --- | --- | --- |
| 술어 | `not raw_line.endswith("\n")` | 동일 |
| 루프 내 위치 | 빈 줄 검사·파싱보다 앞 | 동일 |
| open 모드 | `open("r", encoding="utf-8", errors="strict")` | 동일 |

open 모드가 같다는 게 핵심이다. 둘 다 universal newline 변환을 쓰므로 `\r\n`도 단독
`\r`도 `\n`로 변환돼 통과하고, **종결자가 아예 없는 줄에서만** 발동한다. 같은 바이트에
같은 판정이 나온다.

### 에러 코드 명명

`missing_trailing_newline`을 그대로 쓰지 않았다. 이 파일의 두 함수는 이미 **평행하되
구분되는 어휘**를 쓰기 때문이다.

| verify 어휘 | read_chain_head 어휘 |
| --- | --- |
| `unexpected_blank_line` | `audit_chain_corrupt_empty_line` |
| `seq_not_contiguous` | `audit_chain_corrupt_seq_broken` |
| `prev_hash_mismatch` | `audit_chain_corrupt_prev_hash_mismatch` |
| `unicode_decode_error` | `audit_chain_corrupt_unicode_decode` |
| `missing_trailing_newline` | `audit_chain_corrupt_missing_trailing_newline` (추가) |

기존 fail-closed 테스트가 `audit_chain_corrupt`를 **부분 문자열**로 단언하므로 그 계약도
유지된다. 결정 5의 "code는 값을 담지 않는다"도 지켰다 — 줄 번호는 `detail`에 있다.

## 회귀 테스트

`test_truncated_final_line_blocks_append`를 추가했다(audit-chain 6 → 7건). 단언 내용:

1. 정상 체인 2건이 valid — 사전조건
2. 종결자 제거 후 verifier가 `missing_trailing_newline`
3. `read_chain_head`가 `audit_chain_corrupt_missing_trailing_newline`, `detail == "line_2"`
4. `record_owner_approval`이 같은 코드로 거부
5. **거부 후 파일이 바이트 단위로 동일** — "쓰고 나서 보고"가 아니라 진짜 fail-closed
6. `\n` 체인과 `\r\n` 체인 **양쪽** 모두 verifier·append 경로 통과, `length == 2`

6번은 저장소가 Windows text mode 탓에 디스크에 `\r\n`을 쓰는 사실 때문에 넣었다.
그게 절단으로 오인되면 안 된다.

### 테스트가 결함을 실제로 잡는지 확인했다

저장소를 건드리지 않고 수정 전 `read_chain_head`를 재구성해 monkeypatch로 갈아끼운 뒤
새 테스트를 돌렸다.

```
PRE-FIX : FAIL -> Expected AuditChainError with code
                  'audit_chain_corrupt_missing_trailing_newline' but none was raised
POST-FIX: ok   test_truncated_final_line_blocks_append
```

## 수정 후 연쇄가 멈춘다

| | 수정 전 | 수정 후 |
| --- | --- | --- |
| 잘린 뒤 다음 승인 | 성공 (병합) | **거부** |
| 그 뒤 체인 상태 | `json_parse_failed` — 영구 파싱 불가 | `missing_trailing_newline` — 복구 가능 |

체인이 손상 직전에서 멈추므로 마지막 줄 종결자만 복구하면 살아난다.

## 검증

| 검증 | 결과 |
| --- | --- |
| **audit-chain** | **7/7 PASS** (기존 6건 무변경 통과 + 신규 1건) |
| canonical 전수 | **61/61 PASS** |
| `discord-intake` | **84/84 PASS** |
| `bot_minimal` self-check | **79/79 PASS** |
| `buzz-bridge` | **37/37 PASS** |
| `jarvis-console` + self-test | PASS |
| `discord-nl-intent` | 35/35 PASS |
| `validate_multi_agent_sop` | `status=PASS` |
| `check_no_secrets --self-test` | `status=PASS` |
| `git diff --check` | clean |
| 실제 체인 | **무변경** — exists false, length 0. 모든 probe는 임시 state 디렉터리 |

## 이번 단계 비범위

Owner가 명시적으로 제외한 항목들이며 한 줄도 손대지 않았다.

- **A. 기동 시 검증** — fail-closed 여부가 Owner 결정 사항으로 남아 있다
- **B. `/status`에 체인 상태 노출**
- **background/주기 검증** — master-plan 6절이 scheduler를 잠긴 기능으로 명시한다
- **append의 O(n제곱) 누적** — 분석에서 실측했으나(1000건 22초 누적, 건당 28ms) 이번 범위 밖
- `jarvis.bat` — 건드리지 않았다

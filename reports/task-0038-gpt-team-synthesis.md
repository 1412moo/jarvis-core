# task-0038 부속 자료: GPT 종합 리뷰 (Codex/Gemini/Claude 3자 조사 결과 종합)

- 관련 task: `task-0038-ai-agent-collaboration-platform-buzz-research`
- 원본: `reports/task-0038-ai-agent-collaboration-platform-buzz-research.md` (Claude Code 조사 결과)
- 이 문서의 위치: Owner가 동일 주제를 Codex, Gemini, Claude Code에 각각 조사시킨 뒤 GPT에게 3자 결과 종합을 요청한 결과물. Owner가 대화에서 그대로 붙여넣은 원문을 기록 보존 목적으로 그대로 저장한다(Claude Code가 내용을 재작성/재해석하지 않음).
- 기록일: `2026-08-27`
- 상태: 참고 자료 — 최종 승인/실행 여부는 task-0039에서 별도 처리

---

## 원문 (Owner가 전달한 GPT 답변 그대로)

응. **결과 전체를 확인해봤고, 결론은 꽤 명확해.**

## 결론부터

> **Jarvis-Core를 버리는 게 아니라 `Buzz + Jarvis-Core`로 가는 게 가장 좋다는 결론이 나왔어.**

클로드와 Codex 쪽 분석이 거의 같은 결론이고, 조사 기준일도 **2026-08-27**로 맞춰져 있어.

핵심 역할을 나누면:

```text
        👤 나
         │
         ▼
   ┌─────────────┐
   │    Buzz     │  ← 사람 + AI가 일하는 사무실
   │ 채널/DM/Thread│
   │ Agent 표시   │
   │ 실시간 협업  │
   └──────┬──────┘
          │
          ▼
   ┌─────────────┐
   │ Jarvis-Core │  ← 실제 업무를 통제하는 두뇌
   │             │
   │ Task        │
   │ Orchestration│
   │ Research    │
   │ Evidence    │
   │ Review      │
   │ Approval    │
   │ Governance  │
   │ Memory      │
   └──────┬──────┘
          │
    ┌─────┼─────┐
    ▼     ▼     ▼
 Claude  Codex  Gemini
```

이게 제일 중요한 결론이야.

---

# 1. 네가 "내가 생각한 게 구현된 것 같다"고 느낀 게 맞음

조사 결과 AI-agent 생태계를 크게 나누면:

* **Buzz / OpenAgents / Threads / Team9** → 사람+Agent가 같이 일하는 workspace
* **AgentConnect / open-tag / Patchwork / CircleChat / TaskWraith** → task/orchestration 쪽
* **Canopy / Rundock** → privacy/local-first
* **Relaycast** → headless agent communication

등으로 나뉘어.

특히 조사에서는

> **Buzz = 가장 완성도 높은 workspace/relay/event substrate**

> **AgentConnect = orchestration에 가장 가까움**

> **open-tag / CircleChat = Jarvis-Core의 Task/Memory/Approval 모델과 유사**

하다고 평가했어.

그러니까 **네 아이디어가 완전히 뜬금없는 게 아니었던 것**도 확인된 셈이야.

---

# 2. 그런데 Jarvis-Core를 버리면 안 되는 이유

여기가 핵심이야.

Buzz가 잘하는 건:

* 채널
* Thread
* DM
* Agent identity
* 실시간 메시지
* signed event
* relay
* ACP
* 협업 UI
* Git/workflow 이벤트

야.

반면 네 Jarvis-Core가 만든 건:

* Task Model
* deterministic orchestration
* Research Council
* Evidence
* Review
* Approval
* Governance
* Memory
* Benchmark
* Audit
* Git 정책

이쪽이야.

이건 **Buzz가 대신해주는 영역이 아님.**

특히 조사에서 Jarvis의 **Research Council, Evidence, Review/Approval, Governance, deterministic SOP**가 핵심 차별점이라고 판단했어.

---

# 3. 그래서 지금까지 만든 것 중 상당수는 그대로 가져가면 됨

### 🟢 KEEP

| Jarvis 기능                   | 판단     |
| --------------------------- | ------ |
| Task Model                  | 유지     |
| Task draft/file writer      | 유지     |
| Deterministic orchestration | 유지     |
| Research Council            | **핵심** |
| Evidence                    | **핵심** |
| Review                      | 유지     |
| Approval                    | **핵심** |
| Governance                  | **핵심** |
| Memory/tasks                | 유지     |
| Benchmark                   | 유지     |
| Smoke/Audit                 | 유지     |
| Git policy                  | 유지     |

조사 결과도 거의 그대로 이렇게 분류했어.

---

# 4. 반대로 이건 직접 만들지 않는 게 좋음

이게 이번 조사에서 **가장 돈 되는 결과**라고 봐.

네가 앞으로 Jarvis에 만들려고 했던:

> "AI 직원들이 모여서 사용하는 멋진 채팅 UI"

이걸 **직접 만들 필요가 없어짐.**

### 🔴 REPLACE

```text
Jarvis 자체 Chat UI
        ↓
      Buzz

Channel
Thread
DM
Agent Presence
기본 Agent Chat
Desktop/Web UI
기본 notification
        ↓
      Buzz
```

조사 결과도 이 영역을 Buzz로 대체하라고 명시하고 있어.

그리고 특히 **Director Dashboard를 계속 만드는 것은 보류**하라는 결론까지 나왔어. Buzz Desktop과 기능이 정면으로 겹치기 때문이야.

이건 꽤 중요한 판단임.

---

# 5. 그러면 Buzz를 어떻게 붙이냐?

이게 실제 목표 구조야.

```text
                 ┌──────────────┐
                 │    Human     │
                 └──────┬───────┘
                        │
              ┌─────────▼─────────┐
              │       Buzz        │
              │                   │
              │ Channel / Thread  │
              │ DM / Agent        │
              │ Collaboration     │
              └─────────┬─────────┘
                        │
                   Event / ACP
                        │
              ┌─────────▼─────────┐
              │    Jarvis-Core    │
              │                   │
              │ Task              │
              │ Orchestrator      │
              │ Research Council  │
              │ Evidence          │
              │ Review            │
              │ Approval          │
              │ Governance        │
              │ Memory            │
              └─────────┬─────────┘
                        │
              ┌─────────┼─────────┐
              ▼         ▼         ▼
           Claude     Codex     Gemini
```

**Buzz가 사무실이고 Jarvis가 팀장/업무관리 시스템인 셈.**

---

# 6. Discord도 버리지 않음

이것도 중요해.

지금 Discord가 잘 작동하고 있으니까:

```text
Discord ─────┐
             │
             ▼
          Jarvis-Core
             ▲
             │
Buzz ────────┘
```

두 개를 동시에 받을 수 있게 하는 게 좋다는 결론이야.

조사에서는 Discord를 **external intake/notification channel**로 계속 유지하는 방향을 제안했어.

즉:

**Discord = 밖에서 Jarvis에게 명령하는 입구**

**Buzz = AI 직원들과 실제로 일하는 사무실**

이렇게 만들 수도 있음.

---

# 7. Claude / Codex / Gemini도 같이 넣을 수 있음

조사 결과:

* Claude → ACP
* Codex → ACP
* Gemini → ACP 또는 별도 adapter

방향으로 연결 가능하다고 판단했어.

그러면 네가 원래 상상했던 게 진짜로 가능해져.

예를 들어:

```text
# jarvis-core

👤 석영:
이번 PR 검토해줘.

🤖 Jarvis:
Task #184 생성.
Claude에게 구현을 할당합니다.

🤖 Claude:
구현 완료. PR #221 생성했습니다.

🤖 Jarvis:
Evidence 수집 완료.
Research Council 검토를 시작합니다.

🤖 Gemini:
Architecture review 완료.

🤖 Codex:
Code review 완료.

🤖 Jarvis:
2/3 승인.
Human approval이 필요합니다.

👤 석영:
승인.

🤖 Jarvis:
Merge 조건 충족.
```

**이게 네가 원래 만들고 싶었던 시스템에 상당히 가까워.**

---

# 8. 대신 절대 하면 안 되는 것

이 부분은 꼭 기억해야 함.

### ❌ Buzz를 fork해서 Jarvis를 다시 만들기

비추천.

Rust 기반 Buzz를 포크해서 네 Python Jarvis 기능을 전부 집어넣으면 **upstream과 divergence 지옥**이 될 가능성이 높다고 분석했어.

### ❌ Buzz를 Task DB로 사용

Buzz의 event log ≠ Jarvis Task Model.

### ❌ Buzz의 Approval만 믿기

실제 보안 gate는 Jarvis가 가져야 함.

### ❌ 모든 Agent가 같은 key/API key 사용

Agent별 credential isolation 필요.

### ❌ Agent가 무제한으로 다른 Agent 호출

Jarvis가 delegation budget/DAG를 통제해야 함.

이런 금지사항까지 보고서에 명시돼 있어.

---

# 9. 그래서 Jarvis-Core의 방향 자체가 바뀜

기존에는 아마 이런 느낌이었잖아.

```text
Jarvis-Core
 ├─ Backend
 ├─ Chat
 ├─ Dashboard
 ├─ Agent
 ├─ Task
 ├─ Memory
 └─ Research
```

앞으로는:

```text
Jarvis-Core
 │
 ├── Task Engine
 ├── Orchestrator
 ├── Research Council
 ├── Evidence
 ├── Review
 ├── Approval
 ├── Governance
 ├── Memory
 └── Agent Policy
          │
          ▼
       ACP/API
          │
          ▼
       Buzz
```

**Jarvis가 UI 플랫폼이 아니라 "AI 직원 조직의 운영체제"가 되는 거야.**

나는 이게 네 프로젝트에 훨씬 맞다고 봐.

---

# 10. 지금 당장 뭘 해야 하냐

보고서에서 추천한 단계도 이거야.

### Phase 1 — 지금

**Buzz를 실제로 붙이지 않고 architecture만 차용.**

즉 외부 의존성 없이:

* Event envelope 정의
* correlation ID
* Agent identity 모델
* ACP adapter interface
* Buzz ↔ Jarvis 경계 정의

부터 잡음.

### Phase 2

실제 연결:

```text
Buzz
 ↕
Jarvis
 ↕
Claude/Codex/Gemini
```

그리고:

* `task.created`
* `evidence.added`
* `review.requested`
* `approval.requested`
* `pr.opened`

같은 이벤트를 연결.

GitHub PR과 Research Council도 연결.

### Phase 3

Buzz를 실제 기본 workspace로 승격.

Discord는 외부 입력/알림으로 유지.

---

## 🔥 내가 보기엔 제일 중요한 결론

**이번 조사는 "Buzz를 써볼까?" 수준이 아니라 Jarvis의 역할을 다시 정의할 수 있는 발견이야.**

네가 지금까지 만든 Jarvis-Core를 보면 **채팅 프로그램을 만드는 게 아니라 AI 직원들이 일을 제대로 하게 만드는 통제 시스템**을 만들고 있었음.

Buzz는 그중에서 네가 직접 만들면 엄청난 시간 낭비가 될:

> **"사람 + AI가 함께 일하는 공간"**

을 이미 만들어 놓은 것.

그래서:

> **Buzz를 사무실로 쓰고, Jarvis-Core를 그 사무실의 업무 운영체제로 만든다.**

이 방향이 현재 조사 결과의 최종 답이야.

그리고 **중요한 건 아직 코딩 들어가면 안 됨.** 보고서 자체도 `Phase 1 → 게이트 3개 통과 → Phase 2`로 단계적으로 가라고 되어 있어. 먼저 네가 승인할 건 **① Dashboard 개발 보류, ② Jarvis Console을 승인 전용으로 축소, ③ Phase 1 착수** 이 세 가지야.

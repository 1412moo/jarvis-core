# Research Council Local Launcher User Guide

이 문서는 비개발자가 Research Council Local Launcher를 이해하고 직접 실행할 수
있도록 만든 제품 설명서이자 사용 설명서입니다.

## 1. Research Council Local Launcher란?

Research Council Local Launcher는 제품 아이디어나 업무 개선 아이디어를 로컬
컴퓨터에서만 검토하는 작은 데스크톱 실행기입니다.

사용자가 입력한 idea, goal, context, constraints, provided evidence를 바탕으로
deterministic rules만 사용해 `report.md`와 `result.json`을 만듭니다. 웹 조사,
외부 API, 외부 LLM 호출은 하지 않습니다.

핵심 목적은 "이 아이디어가 검증되었다"라고 말하는 것이 아니라, "다음에 무엇을
검증해야 하는가"를 명확히 정리하는 것입니다.

## 2. 무엇을 할 수 있나?

- 아이디어를 구조화된 claims로 나눕니다.
- 사용자가 준 evidence와 아직 없는 missing evidence를 구분합니다.
- technical, market, safety/regulatory, red-team 관점의 critique를 만듭니다.
- 가장 먼저 해볼 minimum viable experiment를 제안합니다.
- 결과를 사람이 읽을 수 있는 `report.md`와 기계가 읽을 수 있는 `result.json`으로
  저장합니다.
- idea만 입력해도 safe default prompt를 사용해 최소 실행을 할 수 있습니다.

## 3. 무엇을 할 수 없나?

- 웹 검색, 경쟁사 조사, 시장 규모 조사, 최신 뉴스 확인을 하지 않습니다.
- 외부 LLM/API를 호출하지 않습니다.
- 실제 고객 인터뷰, 실제 시장 데이터, 법률/의료/투자 판단을 대신하지 않습니다.
- report를 검증 완료 문서나 확정 결론으로 만들지 않습니다.
- 사용자가 주지 않은 근거를 citation처럼 만들어내지 않습니다.

## 4. 실행 방법

### Git Bash

Git Bash에서는 Windows 경로 구분자 `\` 대신 `/`를 쓰는 것이 안전합니다.

```bash
cd /c/work/jarvis-core
python -B apps/research-council/run_local_app.py
```

headless self-test를 실행하려면:

```bash
python -B apps/research-council/run_local_app.py --self-test --output-dir /c/work/rc-local-app-smoke
```

### PowerShell

```powershell
cd C:\work\jarvis-core
python -B apps\research-council\run_local_app.py
```

headless self-test를 실행하려면:

```powershell
python -B apps\research-council\run_local_app.py --self-test --output-dir C:\work\rc-local-app-smoke
```

### 바탕화면 bat 파일 예시

아래 내용을 예를 들어 `ResearchCouncilLauncher.bat` 파일로 만들면 더블클릭으로
실행할 수 있습니다.

```bat
@echo off
cd /d C:\work\jarvis-core
python -B apps\research-council\run_local_app.py
pause
```

Python이 PATH에 잡혀 있지 않으면 `python` 대신 실제 Python 실행 파일 경로를
넣어야 합니다.

## 5. UI 항목 설명

### Idea

검토할 아이디어를 적는 곳입니다. 예: "CareNote assistant for family caregivers".
이 필드만 입력해도 실행할 수 있습니다.

### Goal

이번 report가 답해야 할 질문입니다. 비워두면 기본 goal이 자동으로 들어갑니다:

```text
Evaluate whether this idea can become a viable MVP and identify the next validation step.
```

### Context

아이디어의 배경, 대상 사용자, 사용 상황을 적습니다. 비워두면 기본 context가
자동으로 들어갑니다:

```text
The user is exploring this as a product or workflow opportunity. The report should identify assumptions, evidence gaps, risks, and minimum viable experiments.
```

### Constraints

반드시 지켜야 할 조건을 한 줄에 하나씩 적습니다. 비워두면 다음 기본 constraints가
들어갑니다:

```text
Human review required
No external services
Treat outputs as validation planning, not final proof
```

### Provided evidence

이미 알고 있거나 사용자가 직접 제공하는 근거를 한 줄에 하나씩 적습니다. 비워둬도
실행 가능합니다. 이 경우 report는 missing evidence를 더 명확하게 표시합니다.

### Profile

아이디어를 어느 관점으로 볼지 정하는 deterministic profile입니다. 예:
`ai_saas`, `medical_device`, `marketplace`, `enterprise_b2b`, `developer_tool`.
잘 모르겠으면 기본값으로 시작해도 됩니다.

### LLM augmentation mode

기본값은 `off`입니다. `test_safe`와 `test_noisy`는 외부 LLM이 아니라 로컬
deterministic fixture를 사용하는 sandbox mode입니다. 실제 외부 LLM/API 호출은
없습니다.

### Output directory

결과 파일이 저장될 폴더입니다. repo 내부가 아닌 외부 폴더를 선택해야 합니다. 예:
`C:\Users\<you>\ResearchCouncilRuns` 또는 `C:\work\rc-local-runs`.

### Run

입력값으로 deterministic Research Council pass를 실행합니다.

### Open report

가장 최근 실행에서 생성된 `report.md`를 엽니다.

### Open output folder

가장 최근 실행 결과가 들어 있는 run folder를 엽니다.

## 6. 처음 실행 예시

### CareNote 예시

처음에는 Idea만 넣고 실행해도 됩니다.

```text
Idea:
CareNote assistant for family caregivers
```

나머지 필드는 비워두면 기본 goal/context/constraints가 사용됩니다. 결과 report는
caregiver workflow가 실제로 반복되는지, 누가 비용을 지불할지, 어떤 evidence가
빠졌는지를 중심으로 다음 검증 단계를 제안합니다.

조금 더 명확히 쓰고 싶다면:

```text
Goal:
Evaluate whether caregiver daily logging can become a viable local MVP.

Context:
Family caregivers often need repeatable notes for care coordination and reimbursement conversations.

Provided evidence:
Manual daily logs create repeated admin work.
Caregivers need a simple way to summarize care activities.
```

### Internal audit evidence readiness 예시

```text
Idea:
Internal audit evidence readiness assistant for operations teams

Goal:
Evaluate whether a lightweight evidence-readiness workflow can reduce audit preparation risk.

Context:
Operations teams collect screenshots, approvals, logs, and policy acknowledgements before internal audits.

Constraints:
No external services
Human review required before any audit claim is accepted
Do not treat generated output as compliance proof

Provided evidence:
Audit preparation often requires repeated evidence requests across teams.
Evidence owners lose time finding the latest approved artifact.
```

이 예시는 report가 evidence ownership, missing proof, human review boundary, 그리고
작은 workflow experiment를 중심으로 나오게 하는 데 도움이 됩니다.

## 7. 결과 파일 설명

각 실행은 output directory 아래에 timestamp가 붙은 새 run folder를 만들고 다음
파일을 저장합니다.

### input.json

실행에 사용된 최종 입력값입니다. Goal, Context, Constraints를 비워두었다면 여기에
자동 기본값이 들어간 것을 확인할 수 있습니다.

### report.md

사람이 읽기 위한 Markdown report입니다. 보통 이 파일을 먼저 읽으면 됩니다.

### result.json

구조화된 전체 결과입니다. claims, evidence ledger, critiques, experiments,
recommendation, profile metadata, warnings 등이 JSON으로 들어 있습니다.

## 8. report.md 읽는 법

### Executive Summary

전체 결과 요약입니다. claims 수, provided/missing evidence 수, critique 수,
minimum viable experiment 수, recommendation decision을 빠르게 봅니다.

### Evidence Ledger

사용자가 제공한 evidence와 missing evidence를 나눠 보여줍니다. 중요한 점은
missing evidence가 많다는 것이 실패가 아니라 "다음 검증 항목이 드러났다"는
뜻이라는 점입니다.

### Reviewer Critiques

technical, market, safety/regulatory, red-team 관점에서 어떤 위험이나 약한
가정이 있는지 봅니다. severity가 high인 항목은 다음 실험 전에 먼저 읽어야 합니다.

### Minimum Viable Experiments

가장 작게 실행할 수 있는 검증 실험 목록입니다. method, success metric, minimum
sample, risk를 확인합니다.

### Recommendation

지금 당장 무엇을 해야 하는지 정리한 결론입니다. 이 결론은 검증 완료 판정이 아니라
다음 검증 행동을 고르기 위한 planning output입니다.

## 9. 자주 하는 실수

- Git Bash에서 Windows 경로의 `\`를 그대로 쓰면 경로가 깨질 수 있습니다. Git Bash는
  `/c/work/jarvis-core`처럼 `/`를 쓰세요.
- Output directory를 repo 안으로 지정하면 launcher가 거부합니다. 결과 폴더는 repo
  밖으로 두세요.
- 이 도구는 external LLM/API 호출이 없습니다. `LLM augmentation mode`도 로컬
  deterministic sandbox입니다.
- `report.md`는 검증 완료 문서가 아니라 검증 계획입니다. 고객, 시장, 법률, 의료,
  투자 판단은 별도 검증이 필요합니다.
- Provided evidence를 비워두면 report가 약해지는 것이 아니라 missing evidence가 더
  많이 드러납니다.

## 10. 현재 한계

- 웹 조사나 경쟁사 자동 검색이 없습니다.
- 실제 시장 데이터, 최신 가격, 고객 인터뷰 결과를 가져오지 않습니다.
- 사용자가 준 정보와 deterministic rules를 기반으로만 작동합니다.
- 법률, 의료, 투자 판단이 아닙니다.
- citation을 생성하지 않습니다.
- DB, API server, web server, async worker 없이 로컬 실행만 지원합니다.

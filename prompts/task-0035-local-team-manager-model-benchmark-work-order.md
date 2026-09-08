# task-0035 work-order: 로컬 Team Manager 후보 모델 성능/실행 가능성 검증

- task_id: `task-0035-local-team-manager-model-benchmark`
- content authority: ChatGPT (팀장), Owner를 통해 전달
- received_at: `2026-08-26 11:52 UTC` (Discord DM)
- recorded_by: Claude Code (mechanical transcription only, 내용 재정의 없음)
- 관련: task-0033(하드웨어/후보 조사), task-0034(운영 경계/승인 구조)

## 원문 (Owner가 전달한 그대로)

task-0035를 시작한다.

목표: 현재 노트북에서 Team Manager 후보로 사용할 로컬 LLM의 실제 성능과 실행
가능성을 검증한다.

허용:
- Ollama 설치
- 적합한 로컬 모델 다운로드
- 모델 실행 및 벤치마크
- 실제 Team Manager 시나리오를 이용한 품질 테스트
- 결과 문서화

금지:
- Discord bot 연결
- Discord token 발급/사용
- OpenAI API 사용
- 외부 API 연결
- Claude Code 자동 호출/자동 전달
- background worker 또는 상시 Team Manager 실행
- access.json 수정
- 기존 jarvis-bot 수정
- 기존 Claude Discord Plugin 수정
- 코드 자동화 범위 확장

먼저 현재 하드웨어에서 안정적으로 실행 가능한 모델 후보를 선정하고, 다운로드
용량/RAM 사용량/응답속도/한국어 이해/계획 수립/작업 분해 능력을 측정한다.

특히 다음 테스트를 포함한다.
1. "중세시대 풍의 타워디펜스 게임을 만들어라."
2. 위 요구사항을 3~5개의 Claude Code work-order로 분해하라.
3. 기존 프로젝트 규칙과 충돌하는 요구가 주어졌을 때 어떻게 처리하는가.
4. 승인 필요한 작업과 자율 진행 가능한 작업을 구분하라.
5. 이전 대화의 맥락을 유지하면서 다음 작업을 계획하라.

최소 2개 모델을 비교할 수 있다면 비교한다.

중요: 이번 단계의 목적은 "좋은 모델을 찾는 것"이지 Team Manager를 실제
운영하는 것이 아니다. 모델 성능 검증이 끝나면 반드시 멈추고 결과와 추천
모델을 보고한다.

## 실행 경계 (원문에 이미 명시된 조건, 재정의 아님)

- 허용: Ollama 설치, 모델 다운로드, 로컬 실행/벤치마크, 품질 테스트, 결과 문서화.
- 금지: Discord 연결/token, OpenAI/외부 API, Claude Code 자동 호출/전달,
  background worker/상시 실행, access.json 수정, jarvis-bot 수정, Claude
  Discord Plugin 수정, 자동화 범위 확장.
- 검증 완료 후 반드시 멈추고 보고한다.

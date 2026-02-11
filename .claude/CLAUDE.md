# Project: [프로젝트명]
[무엇을 하는 프로젝트인지, 누구를 위한 것인지 2-3문장]
<!-- 예: 사용자 인증 마이크로서비스. REST API로 JWT 기반 인증 제공. SaaS 고객 대상 -->

## Tech Stack
- **Language**: [Python 3.11/TypeScript 5.0/Go 1.21]
- **Framework**: [FastAPI/React/Next.js/Gin]
- **Database**: [PostgreSQL/MongoDB/Redis]
- **Testing**: [pytest/Jest/Vitest/go test]
- **Linting**: [ruff/eslint/golangci-lint]

## Commands
<!-- 표준 명령어(npm test, go build)는 생략 - Claude가 추론 가능 -->
<!-- 비표준/특수 인자가 필요한 명령어만 기록 -->
```bash
# [프로젝트 특화 명령어만]
# 예: npm run db:migrate -- --env=production
# 예: pytest -m "not slow" --cov=src
```

## Code Style

### We Use
- [사용 패턴] <!-- 예: 함수형 컴포넌트 + hooks -->
- [사용 패턴] <!-- 예: interface로 타입 정의 -->
- [사용 패턴] <!-- 예: async/await -->

### We Avoid
- [피하는 패턴]: [대안] <!-- 예: any → unknown + 타입 가드 -->
- [피하는 패턴]: [대안] <!-- 예: class 컴포넌트 → 함수형 + hooks -->
- [피하는 패턴]: [대안] <!-- 예: callback hell → async/await -->

## Terminology
<!-- 도메인 용어 정의 - Claude가 코드에서 올바른 이름 사용 -->
- [용어]: [정의] <!-- 예: Athlete = 시스템 내 사용자 (User와 동의어) -->
- [용어]: [정의] <!-- 예: Workout = 운동 세션 기록 -->

## Architecture
```
src/
├── [디렉토리]/  # [역할] <!-- 예: components/ # UI 컴포넌트 -->
├── [디렉토리]/  # [역할] <!-- 예: services/   # 비즈니스 로직 -->
└── [디렉토리]/  # [역할] <!-- 예: utils/      # 유틸리티 함수 -->
```

## Gotchas
<!-- Claude가 실수하기 쉬운 함정 + 반드시 대안 제시 -->
- **[함정]**: [대안] <!-- 예: --foo-bar 금지 → --baz 사용 -->
- **[함정]**: [대안] <!-- 예: ORM lazy load → eager load로 N+1 방지 -->

## Compact Instructions
<!-- /compact 시에도 보존할 절대 규칙 (3-5개) -->
- [핵심 규칙] <!-- 예: ES modules (import/export) 사용 -->
- [핵심 규칙] <!-- 예: 타입체크 완료 후 코드 변경 확정 -->
- [핵심 규칙] <!-- 예: 단일 테스트 실행 선호 -->

## Lessons Learned
<!-- /wrap 스킬로 자동 축적 - 수동 편집 지양 -->

## References
<!-- Progressive Disclosure: 상세 정보는 별도 파일 참조 -->
- 아키텍처 상세: `docs/architecture.md`
- API 스펙: `docs/api.md`
- 테스트 패턴: `tests/README.md`

## Memory Setup
<!-- Auto Memory 설정 안내 -->
<!-- MEMORY.md: ~/.claude/projects/<project-path-encoded>/memory/MEMORY.md -->
<!-- 200줄 이내, 프로젝트 핵심 지식 기록 → 매 세션 자동 로드 -->
<!-- CLAUDE.local.md: 개인 설정 (Git 미추적), cp CLAUDE.local.md.example CLAUDE.local.md -->
<!-- 에이전트 memory frontmatter: name, description, memory (project|user) -->

## Workflow
1. `/plan` → 작업 계획
2. 구현 (자동 린트)
3. `/verify` → 검증
4. `/wrap` → 학습 정리
5. `/commit` → 커밋

## Agent Teams
<!-- 실험적 기능 (선택 사항) -->
<!-- 활성화: settings.json → "env": {"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"} -->
<!-- 에이전트 정의: .claude/agents/*.md (frontmatter: tools, model, permissionMode) -->
<!-- 비용: 일반 대비 ~7배 토큰, 팀원 수에 비례 -->
<!-- 권장: 다중 파일 병렬 편집, 리뷰+구현 동시, 대규모 리팩토링 -->
<!-- 비권장: 단순 작업, 단일 파일, 탐색/질문 -->
<!-- 훅 스크립트: .claude/hooks/scripts/ (TeammateIdle, TaskCompleted 핸들러) -->
<!-- 알림 설정: HOOK_NOTIFY_DESKTOP=1 (데스크톱), SLACK_WEBHOOK_URL (Slack) -->
<!-- 로그 위치: .claude/logs/agent-team.jsonl (JSONL 형식, tail -f로 모니터링) -->
<!-- 상세: docs/AGENT-TEAMS-GUIDE.md, docs/TEAMMATE-HOOKS-GUIDE.md -->

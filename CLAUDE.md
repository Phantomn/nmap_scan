# claude-project-config
Claude Code 범용 프로젝트 템플릿 저장소. Skills, Agents, Hooks 제공.
**중요**: 이 파일은 이 프로젝트 자체의 설정. `.claude/CLAUDE.md`는 복사용 템플릿.

## Tech Stack
- **Language**: Markdown, Shell (Bash), Python 3.10+, JSON
- **Linting**: shellcheck, ruff, py_compile, markdownlint, jq, yamllint

## Commands
```bash
# Shell 스크립트 검증
find .claude/skills -name "*.sh" -exec shellcheck {} \;
shellcheck .claude/hooks/scripts/*.sh

# Python 구문 검증
find .claude -name "*.py" -exec python -m py_compile {} \;

# JSON 유효성
jq empty .claude/*.json

# 전체 검증 (순차)
shellcheck .claude/skills/verify/scripts/*.sh && \
shellcheck .claude/hooks/scripts/*.sh && \
python -m py_compile .claude/skills/wrap/scripts/*.py && \
jq empty .claude/*.json
```

## Code Style

### We Use
- **Shell**: `set -euo pipefail`, 색상 변수, 함수 분리
- **Python**: 타입 힌트, pathlib, dataclass, 3.10+ 호환
- **SKILL.md**: YAML frontmatter (name, description, triggers) 필수

### We Avoid
- **Shell**: Bash 전용 → POSIX 호환 권장 (`[[` → `[`, `echo -e` → `printf`)
  - 현재 verify-*.sh에 `[[` 사용 중 - 점진적 마이그레이션 예정
- **Python**: `os.path` → `pathlib.Path`, 3.12+ 전용 문법 지양
- **하드코딩된 경로**: `$(dirname "$0")` 또는 `pathlib.Path(__file__).parent` 사용

## Architecture
```
.claude/
├── CLAUDE.md           # 복사용 템플릿 (수정 시 영향 범위 확인!)
├── hooks.json          # 확장자별 자동 린트 (case문 구조)
├── hooks/scripts/      # Agent Teams 훅 스크립트 (settings.json에서 참조)
│   ├── hooks-common.sh     # 공통 유틸 (로깅, 알림, 진행률)
│   ├── on-teammate-idle.sh # TeammateIdle 핸들러
│   └── on-task-completed.sh # TaskCompleted 핸들러
├── logs/               # 훅 로그 (JSONL, .gitignore 처리)
├── agents/             # 역할 기반 에이전트 (7개, Agent Teams 지원)
│   ├── implementer.md  # 구현 (sonnet, acceptEdits)
│   ├── reviewer.md     # 리뷰 (sonnet, plan)
│   ├── planner.md      # 계획 (opus, plan)
│   ├── code-analyzer.md # Serena+Sequential 분석 (sonnet, plan)
│   ├── docs-researcher.md # Context7 문서 조회 (haiku, plan)
│   ├── web-researcher.md  # Tavily 웹 검색 (haiku, plan)
│   └── doc-writer.md   # 문서 작성 (sonnet, acceptEdits)
└── skills/             # Progressive Disclosure 스킬 (8개)
    ├── plan/           # /plan 작업 계획
    ├── verify/scripts/ # 언어별 검증 스크립트
    ├── wrap/scripts/   # 학습 추출 Python
    └── [mcp-*/]        # MCP 격리 스킬
```

## Gotchas

### 템플릿 vs 실제 설정 혼동
- **함정**: `.claude/CLAUDE.md`를 이 프로젝트용으로 수정
- **대안**: 루트 `CLAUDE.md`(이 파일)가 이 프로젝트 설정

### Skills/Agents 무분별 수정
- **함정**: 다른 프로젝트에서 사용 중인 스킬/에이전트 임의 수정
- **대안**: 수정 전 영향 범위 확인, 범용성 유지

### hooks.json 언어 추가
- **함정**: case문 구조 손상, `;;` 누락
- **대안**: 기존 패턴 복사, `esac` 직전에 추가, `jq empty` 검증

### Shell 스크립트 Bash 전용 문법
- **함정**: `[[ ]]`, `echo -e`, array 사용 (현재 verify-*.sh에 존재)
- **대안**: 신규 스크립트는 POSIX 호환 권장, 기존은 점진적 마이그레이션

### Python 버전 호환
- **함정**: match-case, 새 타입 힌트 등 3.12+ 전용 문법
- **대안**: 3.10+ 호환 유지, `from __future__ import annotations`

### MEMORY.md vs CLAUDE.md Lessons Learned 혼동
- **함정**: MEMORY.md에 팀 공유 규칙 작성, 또는 CLAUDE.md에 로컬 메모리 작성
- **대안**: CLAUDE.md Lessons Learned = 팀 공유 (Git 추적), MEMORY.md = Claude 자동 참조 지식 (로컬, 200줄 제한)

### Agent Teams 비용
- **함정**: 팀원 5명 스폰 시 토큰 ~7배 증가
- **대안**: 최소 팀원 수 유지, Sonnet/Haiku 모델 사용, 완료 후 즉시 정리

### hooks.json vs settings.json 훅 스키마 차이
- **함정**: `hooks.json`(파일 저장 훅)과 `settings.json`(Agent Teams 훅)의 구조를 혼동
- **대안**: `hooks.json` = 파일 확장자별 린트 (`PreToolUse` 등), `settings.json` = 팀 이벤트 (`TeammateIdle`/`TaskCompleted`)

## Compact Instructions
- `.claude/CLAUDE.md`는 템플릿 - 이 프로젝트 설정은 루트 `CLAUDE.md`
- Skills/Agents 수정 전 다른 프로젝트 영향 고려
- Scripts: shellcheck/py_compile 검증 필수, JSON: jq 검증 필수

## Workflow
1. 수정 전 영향 범위 확인 (다른 프로젝트에서 사용 여부)
2. 스크립트 수정 시 `shellcheck` / `python -m py_compile`
3. JSON 수정 시 `jq empty` 검증
4. `/verify` → `/wrap` → `/commit`

## References
- 가이드: `docs/CLAUDE-MD-GUIDE.md`
- Auto Memory 가이드: `docs/AUTO-MEMORY-GUIDE.md`
- 스킬 상세: `.claude/skills/*/SKILL.md`
- 에이전트 상세: `.claude/agents/*.md`
- 검증 도구: `.claude/skills/verify/references/LANGUAGES.md`
- 훅 가이드: `docs/TEAMMATE-HOOKS-GUIDE.md`

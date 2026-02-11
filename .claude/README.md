# 프로젝트 단위 Claude Code 설정

Progressive Disclosure 패턴 기반 토큰 효율적 프로젝트 설정

## 📁 디렉토리 구조

```
.claude/
├── agents/ (7개)          # 역할 기반 에이전트
├── skills/ (8개)           # 재사용 가능 스킬
│   ├── verify/
│   │   ├── SKILL.md
│   │   ├── scripts/        # 실행 스크립트 (5개)
│   │   └── references/     # 상세 문서 (1개)
│   ├── wrap/
│   │   ├── SKILL.md
│   │   └── scripts/        # 학습 추출 (1개)
│   └── [기타 스킬]/
├── hooks.json              # Hook 설정
├── memory/                 # Auto Memory (MEMORY.md 저장 위치: ~/.claude/projects/...)
└── CLAUDE.md               # 프로젝트 지식 (범용 템플릿)

docs/                       # 가이드 문서
├── PROJECT-SETUP.md        # 프로젝트 초기화
└── SKILL-SELECTION.md      # 스킬 선택 가이드
```

## 🚀 빠른 시작

### 1. CLAUDE.md 커스터마이징
`.claude/CLAUDE.md`를 프로젝트에 맞게 수정

### 2. 검증 스크립트 실행
```bash
# Python 프로젝트
.claude/skills/verify/scripts/verify-python.sh

# TypeScript 프로젝트
.claude/skills/verify/scripts/verify-typescript.sh

# Go 프로젝트
.claude/skills/verify/scripts/verify-go.sh

# Rust 프로젝트
.claude/skills/verify/scripts/verify-rust.sh
```

## 📋 주요 스킬

### 핵심 스킬 (모든 프로젝트)
- **`/plan`**: 작업 계획 수립 및 분해
- **`/verify`**: 린트/타입/테스트 자동 검증
- **`/wrap`**: 세션 학습 내용 정리
- **`/commit`**: 커밋 메시지 자동 생성

### MCP 격리 스킬 (토큰 효율)
- **`/mcp-docs`**: Context7 공식 문서 조회
- **`/mcp-search`**: Tavily 웹 검색
- **`/mcp-analyze`**: Serena 코드 분석
- **`/mcp-test`**: Playwright E2E 테스트

## 💡 토큰 효율성

### Progressive Disclosure
- 초기 로드: ~1K 토큰 (SKILL.md만)
- 필요 시: scripts/references 로드
- 절감율: **95%** (50K → 1K)

### MCP 격리
- 직접 호출: 15-20K 토큰
- 서브에이전트 격리: 1.5-2K 토큰
- 절감율: **90%**

## 📚 문서

- [프로젝트 초기화](../docs/PROJECT-SETUP.md)
- [스킬 선택 가이드](../docs/SKILL-SELECTION.md)
- [검증 도구 상세](skills/verify/references/LANGUAGES.md)

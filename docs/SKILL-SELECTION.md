# 스킬 선택 가이드

## 프로젝트 규모별 권장 스킬

### 소규모 (1-3명)
**핵심 5개**:
- `/plan` - 작업 계획
- `/verify` - 검증 자동화
- `/wrap` - 학습 기록
- `/commit` - 커밋 관리
- `/mcp-docs` - 공식 문서

### 중규모 (5-20명)
**확장 10개** (소규모 + 추가):
- `/mcp-search` - 웹 검색
- `/mcp-analyze` - 코드 분석
- `/mcp-test` - E2E 테스트

### 대규모 (20+명)
전체 스킬 + 커스텀 스킬

## 기술 스택별 필수 스킬

### Python
- `/verify` (ruff, mypy, pytest)
- `/plan`
- `/wrap`

### TypeScript
- `/verify` (eslint, tsc, vitest)
- `/mcp-docs` (프레임워크 문서)
- `/mcp-test` (Playwright)

### Go
- `/verify` (gofmt, golangci-lint)
- `/plan`
- `/commit`

## 워크플로우별 스킬 조합

### 백엔드 API 개발
```
/plan → /mcp-docs → 구현 → /verify → /wrap → /commit
```

### 프론트엔드 컴포넌트
```
/plan → /mcp-docs → 구현 → /mcp-test → /verify → /commit
```

### 풀스택 기능
```
/plan → /mcp-docs (양쪽) → 구현 → /mcp-test → /verify → /wrap
```

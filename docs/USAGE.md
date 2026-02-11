# Skills & Agents 사용 가이드

> **Quick Start**: 5분 내 첫 스킬 실행 | **토큰 효율**: MCP 격리로 90% 절감

## Quick Start

### 1단계: 복사
```bash
cp -r .claude/ your-project/
```

### 2단계: 설정
`your-project/.claude/CLAUDE.md`에서 Tech Stack, Commands 섹션 수정

### 3단계: 실행
```bash
cd your-project
claude  # Claude Code 시작

# 첫 스킬 실행
/plan "JWT 인증 시스템 구현"
```

### 핵심 스킬 3개
| 스킬 | 용도 | 예시 |
|------|------|------|
| `/plan` | 작업 계획 수립 | `/plan "로그인 기능"` |
| `/verify` | 린트/타입/테스트 | `/verify` |
| `/commit` | Git 커밋 | `/commit` |

---

## 스킬 레퍼런스

### Core 스킬 (4개)

| 스킬 | 용도 | When | Output |
|------|------|------|--------|
| `/plan` | 작업 계획 수립 | 3단계 이상 복잡한 작업 | `.claude/plans/*.md` + TodoWrite |
| `/verify` | 린트/타입/테스트/빌드 검증 | 커밋 전, 구현 완료 후 | ✅/❌ 결과 요약 |
| `/wrap` | 세션 학습 정리 | 세션 종료 전, 주요 작업 후 | CLAUDE.md 업데이트 제안 |
| `/commit` | Git 커밋/PR 생성 | /verify 통과 후 | Conventional Commits 메시지 |

**상세**: `.claude/skills/[name]/SKILL.md`

### MCP 격리 스킬 (4개)

| 스킬 | MCP | 용도 | 토큰 절감 |
|------|-----|------|----------|
| `/docs` | Context7 | 공식 문서 조회 | 15K → 800 (95%) |
| `/search` | Tavily | 웹 검색 | 12K → 1.2K (90%) |
| `/analyze` | Serena+Sequential | 코드 분석 | 15K → 1.5K (90%) |
| `/test` | Playwright | E2E 테스트 | 8K → 1.2K (85%) |

**사용 예시**:
```bash
/docs react "useEffect cleanup"     # React 공식 문서 조회
/search "TypeScript 5.5 features"   # 최신 정보 검색
/analyze auth.py dependency         # 의존성 분석
/test login                         # 로그인 플로우 테스트
```

---

## 에이전트 레퍼런스

| 에이전트 | 역할 | 자동 활성화 |
|----------|------|-------------|
| `implementer` | 기능 구현 | 구현 요청 시 |
| `reviewer` | 보안/품질/성능 리뷰 | /verify 내부 |
| `planner` | 계획 수립 | /plan 내부 |
| `doc-writer` | 문서 작성 | 문서화 요청 시 |
| `docs-researcher` | 문서 조회 | /docs 내부 |
| `web-researcher` | 웹 검색 | /search 내부 |
| `code-analyzer` | 코드 분석 | /analyze 내부 |

**상세**: `.claude/agents/*.md`

---

## 워크플로우 패턴

### 패턴 1: 기능 개발
```
/plan "JWT 인증 구현"    # 계획 수립
↓
[구현]                   # 자동 린트 (hooks.json)
↓
/verify                  # 린트/타입/테스트 검증
↓
/wrap                    # 학습 정리
↓
/commit                  # 커밋/PR
```

### 패턴 2: 버그 수정
```
/analyze auth.py:120 bug    # 버그 원인 추적
↓
[수정]
↓
/verify                     # 검증
↓
/commit
```

### 패턴 3: 라이브러리 학습
```
/docs fastapi "dependency injection"    # 공식 문서
↓
/search "fastapi di best practices"     # 최신 패턴
↓
[적용]
```

### 패턴 4: E2E 테스트
```
/test login                    # 로그인 플로우
↓
/test accessibility            # 접근성 검증
↓
/test form --browser firefox   # 크로스 브라우저
```

---

## 토큰 효율

### 문제: 직접 호출 시 토큰 폭발
```
MCP 직접 호출:
- Context7: 15,000+ 토큰
- Tavily: 12,000+ 토큰
- Serena+Sequential: 15,000+ 토큰
- Playwright: 8,000+ 토큰

→ 세션 3-4개 작업 후 컨텍스트 압박
```

### 해결: MCP 격리 스킬
```
격리 실행 (서브에이전트):
- /docs:    15,000 → 800 토큰 (95% 절감)
- /search:  12,000 → 1,200 토큰 (90% 절감)
- /analyze: 15,000 → 1,500 토큰 (90% 절감)
- /test:    8,000 → 1,200 토큰 (85% 절감)
```

### 동작 원리
```
메인 세션                    격리된 서브에이전트
    │                              │
    ├─ /docs react hooks ───────→ │
    │                              ├─ Context7 호출
    │                              ├─ 전체 문서 로드 (15K 토큰)
    │                              ├─ 핵심만 추출
    │  ←─ 요약 반환 (800 토큰) ───┤
    │                              │ (컨텍스트 폐기)
    ▼
  메인 세션은 800 토큰만 증가
```

---

## FAQ

### Q: 스킬이 인식되지 않아요
**A**: `.claude/skills/*/SKILL.md` 파일 존재 확인
```bash
ls .claude/skills/*/SKILL.md
```

### Q: /verify 실행 시 도구가 없다고 나와요
**A**: 프로젝트 타입별 도구 설치
```bash
# Python
pip install ruff mypy pytest

# TypeScript
npm install -D eslint typescript
```

### Q: MCP 스킬이 작동하지 않아요
**A**: MCP 서버 설정 확인
```bash
# Context7, Tavily, Serena, Playwright MCP 서버가
# Claude Code에 연결되어 있는지 확인
```

### Q: 토큰이 너무 빨리 소모돼요
**A**: MCP 격리 스킬 사용
```bash
# 직접 호출 대신
❌ "React useEffect 문서 찾아줘"

# 격리 스킬 사용
✅ /docs react "useEffect cleanup"
```

### Q: 커스텀 스킬 추가하려면?
**A**: `.claude/skills/[name]/SKILL.md` 생성
```markdown
---
name: my-skill
description: 커스텀 스킬 설명
triggers: ["/my-skill", "my skill"]
---

# /my-skill - 스킬 제목

## What
[기능 설명]

## When
[사용 시점]

## Workflow
[실행 단계]
```

### Q: 에이전트 역할을 변경하려면?
**A**: `.claude/agents/*.md` 수정
- 각 에이전트의 Role, Responsibilities 섹션 조정
- 새 에이전트 추가 시 동일 포맷으로 생성

---

## References

| 문서 | 경로 | 내용 |
|------|------|------|
| 스킬 상세 | `.claude/skills/[name]/SKILL.md` | 각 스킬 워크플로우 |
| 에이전트 상세 | `.claude/agents/*.md` | 역할별 행동 가이드 |
| CLAUDE.md 작성법 | `docs/CLAUDE-MD-GUIDE.md` | 설정 파일 베스트 프랙티스 |
| 검증 도구 | `.claude/skills/verify/references/LANGUAGES.md` | 언어별 검증 명령어 |

---

## Workflow Summary

```
1. /plan      → 작업 계획 (복잡한 작업)
2. 구현        → 자동 린트 (hooks.json)
3. /verify    → 검증 (린트/타입/테스트)
4. /wrap      → 학습 정리 (세션 종료 전)
5. /commit    → 커밋/PR
```

**MCP 격리 스킬**: 토큰 절감이 필요할 때
```
/docs    → 공식 문서 (Context7)
/search  → 웹 검색 (Tavily)
/analyze → 코드 분석 (Serena)
/test    → E2E 테스트 (Playwright)
```

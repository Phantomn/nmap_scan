# CLAUDE.md 최적 작성 가이드

> **핵심 원칙**: 간결함 > 완전함 | 구체성 > 일반성 | 대안 제시 > 금지만

## 📐 권장 길이

| 위치 | 권장 길이 | 초과 시 조치 |
|------|----------|-------------|
| Root CLAUDE.md | 100-200줄 | @import로 분리 |
| 하위 디렉토리 CLAUDE.md | 50-100줄 | 필수 내용만 |
| 300줄 초과 | ❌ 지양 | 리팩토링 필요 |

## 🎯 5가지 핵심 원칙

### 1. Less is More
```markdown
❌ 모든 정보를 CLAUDE.md에 작성
✅ Claude가 실수하는 것만 문서화
```

### 2. Progressive Disclosure
```markdown
❌ @-file docs/api.md  (매번 전체 로드)
✅ "API 사용법은 docs/api.md 참조"
```

### 3. 구체적 지시
```markdown
❌ "컴포넌트 스타일 일관성 유지"
✅ "컴포넌트는 MUI v7 사용, sx prop 우선, styled() 지양"
```

### 4. 대안 제시
```markdown
❌ "--foo-bar 플래그 사용 금지"
✅ "--foo-bar 사용 금지; 대신 --baz 사용"
```

### 5. 살아있는 문서
```markdown
# PR 리뷰에서 업데이트
@claude add to CLAUDE.md: enum 대신 string literal unions 사용

# 주기적 검토
"CLAUDE.md 검토하고 오래된 규칙 정리해줘"
```

---

## 📋 필수 섹션 구조

```markdown
# Project Name
[한 줄 프로젝트 설명]

## Tech Stack
- **Language**: [언어 + 버전]
- **Framework**: [프레임워크]
- **Database**: [DB]
- **Testing**: [테스트 도구]
- **Linting**: [린터]

## Commands
```bash
npm run build    # 빌드
npm test         # 테스트
npm run lint     # 린트
```

## Code Style
- [구체적이고 실행 가능한 규칙]

## Architecture
```
src/
├── components/  # [설명]
└── services/    # [설명]
```

## Gotchas
- [함정]: [대안]

## References
복잡한 API 사용법은 `docs/api.md` 참조
```

---

## 🚫 피해야 할 패턴

| 안티패턴 | 문제점 | 해결책 |
|----------|--------|--------|
| 300줄+ 장문 | 중요 규칙이 묻힘 | 핵심만 유지 |
| @-file 남용 | 매번 전체 로드 | 경로 참조 |
| "절대 ~하지 마" | 에이전트 막힘 | 대안 제시 |
| 모든 것 문서화 | 토큰 낭비 | 실수만 기록 |
| 업데이트 안 함 | 오래된 규칙 | 월 1회 검토 |

---

## 🔧 고급 패턴

### 계층적 로드 순서
```
1. ~/.claude/CLAUDE.md           (전역, 모든 프로젝트)
2. 프로젝트/.claude/CLAUDE.md    (프로젝트 설정)
3. 서브디렉토리/CLAUDE.md        (디렉토리별)
4. .claude/rules/*.md            (모듈화된 규칙)
```

### 모듈화 (대규모 프로젝트)
```
.claude/
├── CLAUDE.md           # 핵심 규칙만 (100줄)
└── rules/
    ├── code-style.md   # 코드 스타일
    ├── testing.md      # 테스트 규칙
    └── security.md     # 보안 요구사항
```

### Compact Instructions
컨텍스트 압축 시에도 보존할 핵심:
```markdown
## Compact Instructions
- ES modules (import/export) 사용
- 타입체크 완료 후 코드 변경 확정
- 단일 테스트 실행 선호
```

---

## ✅ 품질 체크리스트

작성 후 검증:

- [ ] 100-200줄 이하인가?
- [ ] 모든 규칙이 구체적이고 실행 가능한가?
- [ ] 금지 규칙에 대안이 있는가?
- [ ] Commands 섹션이 있는가?
- [ ] Gotchas 섹션이 있는가?
- [ ] Progressive Disclosure (참조) 사용하는가?
- [ ] 플레이스홀더가 남아있지 않은가?

---

## 📊 예시: Before/After

### Before (문제점)
```markdown
# My Project

## Rules
- 좋은 코드를 작성하세요
- 테스트를 작성하세요
- 보안에 신경쓰세요
- console.log 절대 사용 금지

## Documentation
@-file docs/api.md
@-file docs/architecture.md
@-file docs/contributing.md
```

### After (개선)
```markdown
# My Project
사용자 인증 마이크로서비스

## Tech Stack
- **Language**: TypeScript 5.0
- **Framework**: Express 4.x
- **Database**: PostgreSQL 15
- **Testing**: Jest
- **Linting**: ESLint + Prettier

## Commands
```bash
npm run dev      # 개발 서버
npm test         # 테스트
npm run lint     # 린트
```

## Code Style
- 함수형 우선, 클래스는 DI 컨테이너만
- 타입은 interface 사용 (type은 union만)
- async/await 사용 (Promise chain 금지)

## Gotchas
- **console.log 금지**: `logger.info()` 사용
- **any 타입 금지**: unknown 후 타입 가드

## References
- API 스펙: `docs/api.md`
- 아키텍처: `docs/architecture.md`
```

---

## 🔄 유지보수 워크플로우

### 1. 실패에서 학습
```
Claude가 실수하면 → CLAUDE.md에 해당 규칙 추가
```

### 2. 월간 검토
```
"CLAUDE.md 검토하고 다음 확인:
- 오래되거나 충돌하는 규칙
- 통합 가능한 중복 규칙
- 불명확한 지시사항"
```

### 3. PR에서 즉시 업데이트
```
@claude add to CLAUDE.md: API 응답은 camelCase 사용
```

---

## 📚 참고 자료

- [Anthropic Engineering Blog](https://www.anthropic.com/engineering/claude-code-best-practices)
- [Claude Code Docs](https://code.claude.com/docs/en/best-practices)
- [builder.io Guide](https://www.builder.io/blog/claude-md-guide)

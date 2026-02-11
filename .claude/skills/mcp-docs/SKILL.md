---
name: mcp-docs
description: Context7 MCP 격리 실행으로 공식 문서 조회 (토큰 효율)
triggers: ["/docs", "/mcp-docs", "공식 문서"]
---

# /mcp-docs - Context7 격리 문서 조회

## What
Context7 MCP를 서브에이전트로 격리 실행하여 공식 문서 조회 후 요약만 반환

## Why
**문제**: Context7 직접 호출 시 전체 문서가 메인 컨텍스트에 쌓임
- 라이브러리 3-4개 조회 → 20,000+ 토큰 소모
- 긴 세션에서 컨텍스트 압박

**해결**: 격리 실행 → 95% 토큰 절감 (15,000 → 800)

## When
- 프레임워크/라이브러리 공식 문서 필요
- API 사용법, 베스트 프랙티스 확인
- 버전별 차이점 조회
- Breaking Changes 확인

## Workflow

### 단계 1: 명령어 파싱
```bash
/docs <library> [query]

예시:
/docs react useEffect
/docs fastapi "dependency injection"
/docs nextjs "app router"
```

### 단계 2: docs-researcher 서브에이전트 실행 (격리)
```
격리된 컨텍스트에서:
1. Context7 MCP 호출
2. 전체 문서 로드 (15,000 토큰, 격리 컨텍스트)
3. 쿼리 관련 내용만 추출
4. 코드 예시 포함한 요약 생성 (800 토큰)
```

### 단계 3: 메인 세션에 요약 반환
```markdown
## 📚 [Library] 문서 조회 결과

**쿼리**: [검색어]

### 핵심 내용
- [핵심 포인트 1]
- [핵심 포인트 2]

### 코드 예시
```[language]
[실행 가능한 코드]
```

### 주의사항
- [경고/Deprecated/Breaking Changes]

### 참고 링크
- [공식 문서 URL]
```

## Examples

### Example 1: React Hooks
```bash
사용자: /docs react useEffect cleanup

메인 세션 반환 (800 토큰):
## 📚 React 문서 조회 결과

**쿼리**: useEffect cleanup

### 핵심 내용
- useEffect는 cleanup 함수를 반환하여 구독/타이머 정리
- cleanup은 컴포넌트 언마운트 또는 재실행 전 호출
- cleanup 없으면 메모리 누수 가능

### 코드 예시
```jsx
useEffect(() => {
  const timer = setInterval(() => console.log('tick'), 1000);
  return () => clearInterval(timer); // cleanup
}, []);
```

### 주의사항
- 의존성 배열 누락 시 매 렌더링마다 실행

### 참고 링크
- https://react.dev/reference/react/useEffect
```

### Example 2: FastAPI Dependency
```bash
사용자: /docs fastapi "dependency injection"

메인 세션 반환 (1,000 토큰):
## 📚 FastAPI 문서 조회 결과

**쿼리**: dependency injection

### 핵심 내용
- Depends()로 의존성 주입
- yield로 cleanup 보장 (DB 세션 등)
- 동일 요청 내 자동 캐싱

### 코드 예시
```python
from fastapi import Depends

async def get_db():
    async with async_session() as session:
        yield session  # cleanup 자동 호출

@app.get("/users")
async def get_users(db = Depends(get_db)):
    return await db.execute(select(User)).scalars().all()
```

### 주의사항
- async/await 일관성 유지
- yield 이후 코드는 cleanup

### 참고 링크
- https://fastapi.tiangolo.com/tutorial/dependencies/
```

## Token Efficiency

| 방식 | 메인 컨텍스트 증가 | 절감율 |
|------|------------------|--------|
| Context7 직접 호출 | 15,000 토큰 | - |
| /docs (격리 실행) | 800 토큰 | 95% |

## Quality Standards

### 좋은 요약 (docs-researcher 출력)
✅ 요청에 직접 답변하는 내용만
✅ 실행 가능한 코드 예시
✅ 버전 호환성 명시
✅ 주요 경고 포함
✅ 공식 문서 링크

### 나쁜 요약
❌ 문서 전체 복사
❌ 요청과 무관한 정보
❌ 코드 예시 없음
❌ 너무 추상적

## Integration

### 자동 활성화
```
사용자: "React useEffect cleanup 사용법 알려줘"

↓ (자동 감지)

/docs react "useEffect cleanup"
```

### 수동 호출
```
/docs <library> [query]
```

## Supported Libraries

Context7 MCP가 지원하는 주요 라이브러리:
- **Frontend**: React, Vue, Angular, Svelte, Next.js, Nuxt
- **Backend**: FastAPI, Django, Flask, Express, NestJS
- **Database**: SQLAlchemy, Prisma, TypeORM, Mongoose
- **Testing**: Jest, Pytest, Vitest, Playwright
- **Others**: TypeScript, Tailwind CSS, etc.

## Implementation Notes

- **서브에이전트**: `@docs-researcher` 자동 호출
- **격리 보장**: 서브에이전트 컨텍스트는 메인에 영향 없음
- **캐싱**: 동일 라이브러리 재조회 시 캐시 활용 (1시간)
- **병렬 실행**: 여러 라이브러리 동시 조회 가능

## Advanced Usage

### 여러 라이브러리 동시 조회
```bash
/docs react hooks && /docs fastapi async
```

### 특정 버전 명시
```bash
/docs "react@18" server components
```

### 비교 조회
```bash
/docs "react vs vue" state management
```

## Troubleshooting

### Q: 조회 결과가 너무 짧아요
**A**: 쿼리를 더 구체적으로 지정하세요.
```
❌ /docs react
✅ /docs react useEffect cleanup
```

### Q: 오래된 정보가 나와요
**A**: Context7은 최신 공식 문서 기반입니다. 라이브러리 버전 명시:
```
/docs "react@18" features
```

### Q: 특정 라이브러리가 지원 안 돼요
**A**: Context7 지원 라이브러리 목록 확인 또는 WebSearch 사용:
```
/search "[library] official documentation"
```

## See Also
- `/mcp-search` - 웹 검색 (Tavily MCP 격리)
- `/mcp-analyze` - 코드 분석 (Serena+Sequential 격리)
- `@docs-researcher` - 문서 조회 전문 에이전트

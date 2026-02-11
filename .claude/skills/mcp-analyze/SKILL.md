---
name: mcp-analyze
description: Serena+Sequential MCP 격리 실행으로 코드 분석 (토큰 효율)
triggers: ["/analyze", "/mcp-analyze", "코드 분석"]
---

# /mcp-analyze - Serena+Sequential 격리 코드 분석

## What
Serena와 Sequential MCP를 서브에이전트로 격리 실행하여 코드 분석 후 핵심 인사이트만 반환

## Why
**문제**: Serena/Sequential 직접 호출 시 전체 분석 과정이 메인 컨텍스트에 쌓임
- 심볼 분석 3-4개 → 15,000+ 토큰 소모
- 중간 추론 과정까지 메인 컨텍스트 적재

**해결**: 격리 실행 → 90% 토큰 절감 (15,000 → 1,500)

## When
- 코드 구조 이해 (심볼, 함수, 클래스)
- 의존성 추적 (모듈 간 관계)
- 아키텍처 분석 (시스템 전체 구조)
- 버그 원인 추적 (다층 의존성)
- 리팩토링 영향도 평가

## Workflow

### 단계 1: 명령어 파싱
```bash
/analyze <target> <type> [--depth shallow|deep]

타입:
- symbol: 심볼 구조 분석
- dependency: 의존성 추적
- architecture: 아키텍처 분석
- bug: 버그 원인 추적

예시:
/analyze auth.py symbol
/analyze auth.py dependency --depth deep
/analyze src/ architecture
/analyze auth.py:120 bug
```

### 단계 2: code-analyzer 서브에이전트 실행 (격리)
```
격리된 컨텍스트에서:
1. Serena MCP: 심볼 분석, 의존성 추적
2. Sequential MCP: 다단계 추론, 가설 검증
3. 전체 분석 (15,000 토큰, 격리 컨텍스트)
4. 핵심 인사이트 + 액션 아이템 생성 (1,500 토큰)
```

### 단계 3: 메인 세션에 요약 반환
```markdown
## 🔬 코드 분석 결과: [대상]

**분석 유형**: [symbol/dependency/architecture/bug]
**분석 깊이**: [shallow/deep]

### 핵심 발견
1. **[발견 1]**
   - 위치: [파일:라인]
   - 영향도: High/Medium/Low
   - 설명: [1-2문장]

### 의존성 그래프
```
[핵심 의존성만]
```

### 리스크 평가
| 항목 | 리스크 | 설명 |
|------|--------|------|

### 액션 아이템
- [ ] [구체적 작업] (우선순위: High/Medium/Low)
```

## Analysis Types

### Symbol Analysis (심볼 분석)
**목적**: 함수/클래스 구조 이해
```bash
/analyze auth.py symbol

출력:
- 심볼 계층 (클래스, 메서드, 함수)
- 타입 시그니처
- docstring/주석
- 복잡도 평가
```

### Dependency Analysis (의존성 분석)
**목적**: 모듈 간 관계 추적
```bash
/analyze auth.py dependency

출력:
- 의존성 그래프
- 순환 의존성 탐지
- 결합도 평가
- 리팩토링 제안
```

### Architecture Analysis (아키텍처 분석)
**목적**: 시스템 전체 구조
```bash
/analyze src/ architecture

출력:
- 레이어 구조
- 패턴 인식 (MVC, 클린 아키텍처 등)
- 아키텍처 다이어그램
- 개선 제안
```

### Bug Analysis (버그 분석)
**목적**: 버그 원인 추적
```bash
/analyze auth.py:120 bug

출력:
- 근본 원인 분석
- 호출 체인
- 수정 계획
- 회귀 방지 테스트 제안
```

## Examples

### Example 1: 심볼 분석
```bash
사용자: /analyze auth.py symbol

메인 세션 반환 (1,000 토큰):
## 🔬 코드 분석 결과: auth.py

**분석 유형**: symbol
**분석 깊이**: shallow

### 핵심 발견
1. **TokenManager 클래스**
   - 위치: auth.py:45
   - 영향도: High
   - 설명: JWT 토큰 생성/검증, 15개 메서드, 복잡도 높음

2. **verify_token 함수**
   - 위치: auth.py:120
   - 영향도: High
   - 설명: 3개 외부 모듈 의존, 예외 처리 미흡

### 심볼 계층
```
auth.py
├── TokenManager (class)
│   ├── __init__
│   ├── create_token
│   ├── verify_token (메서드)
│   └── refresh_token
└── verify_token (함수)
```

### 액션 아이템
- [ ] TokenManager.verify_token과 verify_token 함수 통합 (중복 제거)
- [ ] verify_token 함수에 에러 핸들링 추가
- [ ] TokenManager 단위 테스트 작성
```

### Example 2: 의존성 분석
```bash
사용자: /analyze auth.py dependency --depth deep

메인 세션 반환 (1,500 토큰):
## 🔬 코드 분석 결과: auth.py

**분석 유형**: dependency
**분석 깊이**: deep

### 핵심 발견
1. **순환 의존성 감지**
   - 위치: auth.py ↔ user.py
   - 영향도: High
   - 설명: TokenManager가 User 모델 참조, User가 TokenManager 사용

2. **과도한 결합**
   - 위치: auth.py → database.py, config.py, utils.py
   - 영향도: Medium
   - 설명: 4개 모듈에 강하게 결합, 테스트 어려움

### 의존성 그래프
```
auth.py ←→ user.py (순환!)
auth.py → database.py
auth.py → config.py
auth.py → utils.py
```

### 리스크 평가
| 항목 | 리스크 | 설명 |
|------|--------|------|
| 순환 의존성 | High | 리팩토링 어려움, 테스트 복잡 |
| 과도한 결합 | Medium | 변경 파급 효과 큼 |

### 액션 아이템
- [ ] auth-user 간 인터페이스 분리 (High)
- [ ] 의존성 주입으로 database/config 결합 완화 (Medium)
- [ ] utils 기능을 auth 내부로 이동 (Low)

### 코드 예시 (개선안)
```python
# 인터페이스 분리로 순환 의존성 해결
from abc import ABC, abstractmethod

class UserProvider(ABC):
    @abstractmethod
    def get_user(self, user_id: str) -> dict: ...
```
```

### Example 3: 버그 분석
```bash
사용자: /analyze auth.py:120 bug

메인 세션 반환 (1,500 토큰):
## 🔬 코드 분석 결과: verify_token 버그

**분석 유형**: bug
**분석 깊이**: deep

### 핵심 발견
1. **예외 처리 누락**
   - 위치: auth.py:125
   - 영향도: High
   - 설명: jwt.decode() 실패 시 500 에러 노출

2. **타임존 불일치**
   - 위치: auth.py:130
   - 영향도: Medium
   - 설명: UTC vs Local 시간 비교로 토큰 만료 오판

### 근본 원인
```
verify_token()
├── jwt.decode() → 예외 핸들링 없음 ❌
└── exp 시간 비교 → 타임존 불일치 ❌
```

### 액션 아이템
- [ ] jwt.decode()에 try-except 추가, 401 반환 (High)
- [ ] 모든 시간을 UTC로 통일 (High)
- [ ] 단위 테스트 추가 (만료 토큰, 잘못된 토큰) (Medium)

### 코드 예시 (수정안)
```python
from datetime import datetime, timezone

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    if exp < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Token expired")

    return payload
```
```

## Token Efficiency

| 방식 | 메인 컨텍스트 증가 | 절감율 |
|------|------------------|--------|
| Serena+Sequential 직접 호출 | 15,000 토큰 | - |
| /analyze (격리 실행) | 1,500 토큰 | 90% |

## Quality Standards

### 좋은 분석 결과 (code-analyzer 출력)
✅ 실행 가능한 액션 아이템
✅ 구체적 파일:라인 위치
✅ 리스크 정량화 (High/Medium/Low)
✅ 최소한의 코드 스니펫
✅ 우선순위 명시

### 나쁜 분석 결과
❌ 추상적 발견 ("코드가 복잡함")
❌ 위치 불명확
❌ 액션 아이템 없음
❌ 과도한 코드 인용

## Integration

### 자동 활성화
```
사용자: "auth.py의 의존성 분석해줘"

↓ (자동 감지)

/analyze auth.py dependency
```

### 수동 호출
```
/analyze <target> <type> [--depth shallow|deep]
```

## Advanced Usage

### 여러 파일 동시 분석
```bash
/analyze "auth.py,user.py" dependency
```

### 특정 심볼 분석
```bash
/analyze auth.py::TokenManager symbol
```

### 프로젝트 전체 아키텍처
```bash
/analyze src/ architecture --depth deep
```

## Implementation Notes

- **서브에이전트**: `@code-analyzer` 자동 호출
- **격리 보장**: 서브에이전트 컨텍스트는 메인에 영향 없음
- **Serena 메모리**: 프로젝트 컨텍스트 활용
- **Sequential 추론**: 다단계 분석 자동화

## Troubleshooting

### Q: 분석 결과가 너무 추상적이에요
**A**: --depth deep으로 상세 분석:
```
/analyze target type --depth deep
```

### Q: 특정 심볼만 보고 싶어요
**A**: :: 구문으로 심볼 지정:
```
/analyze file.py::ClassName symbol
```

### Q: Serena MCP 활성화 오류
**A**: Serena 프로젝트 활성화 확인:
```
list_memories()  # 프로젝트 컨텍스트 확인
```

### Q: 의존성 그래프가 너무 복잡해요
**A**: shallow 분석으로 핵심만:
```
/analyze target dependency --depth shallow
```

## See Also
- `/mcp-docs` - 공식 문서 조회 (Context7 MCP 격리)
- `/mcp-search` - 웹 검색 (Tavily MCP 격리)
- `@code-analyzer` - 코드 분석 전문 에이전트

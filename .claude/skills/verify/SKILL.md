---
name: verify
description: 작업 결과 검증 루프 (린트/타입/테스트/빌드)
triggers: ["/verify", "검증해줘", "테스트 실행"]
---

# /verify - 검증 루프 스킬

## What
코드 품질 검증을 위한 자동화된 검사 파이프라인 실행

## When
- 코드 작성/수정 후
- 커밋 전 (/commit 호출 전)
- PR 생성 전
- 세션 종료 전 (/wrap 호출 전)

## Workflow

### 1단계: 환경 감지
프로젝트 타입 자동 감지:
```bash
# 병렬 실행
ls pyproject.toml setup.py requirements.txt 2>/dev/null
ls package.json tsconfig.json 2>/dev/null
ls Makefile docker-compose.yml 2>/dev/null
```

### 2단계: 검증 파이프라인 (순차 실행)

#### A. 린트 검사
**Python**:
```bash
python -m ruff check . --output-format=concise
```

**TypeScript/JavaScript**:
```bash
npx eslint . --format=compact
```

**결과 수집**:
- ✅ 통과 / ❌ 실패
- 에러 개수 및 위치
- 자동 수정 가능 여부

#### B. 타입 검사
**Python**:
```bash
mypy . --show-error-codes --no-error-summary 2>&1 || true
```

**TypeScript**:
```bash
npx tsc --noEmit
```

**결과 수집**:
- 타입 에러 개수
- 에러 파일 및 라인

#### C. 테스트 실행
**Python**:
```bash
pytest -v --tb=short --cov=. --cov-report=term-missing:skip-covered
```

**TypeScript/JavaScript**:
```bash
npm test -- --coverage --passWithNoTests
```

**결과 수집**:
- 테스트 통과/실패 개수
- 커버리지 비율
- 실패한 테스트 상세

#### D. 빌드 검사 (선택)
프로젝트에 빌드 단계가 있는 경우:
```bash
# Docker
docker build -t test-build . 2>&1

# Python package
python -m build 2>&1

# TypeScript
npm run build 2>&1
```

### 3단계: 결과 요약

**성공 시**:
```markdown
# ✅ 검증 통과

## 린트
✅ 0 errors, 0 warnings

## 타입 체크
✅ No type errors

## 테스트
✅ 42 passed
📊 Coverage: 87%

## 빌드
✅ Build successful

---
💡 /commit으로 커밋하거나 /wrap으로 세션 정리 가능
```

**실패 시**:
```markdown
# ❌ 검증 실패

## 린트
❌ 3 errors
- `src/auth.py:15`: F401 'jwt' imported but unused
- `src/db.py:42`: E501 line too long (92 > 88)

💡 자동 수정: ruff check --fix

## 타입 체크
❌ 2 errors
- `src/models.py:23`: Argument 1 to "create" has incompatible type "str"; expected "int"

## 테스트
⚠️ 2 failed, 40 passed
- `tests/test_auth.py::test_refresh_token` - AssertionError

## 빌드
⏭️ Skipped (이전 단계 실패)

---
🔧 수정 필요 항목:
1. 린트 에러 수정 (자동 수정 가능)
2. 타입 에러 해결
3. 실패한 테스트 수정
```

### 4단계: 자동 수정 제안
수정 가능한 항목 제안:
```
🔧 자동 수정 가능:
1. 린트 에러 자동 수정 (ruff --fix)
2. Import 정리 (unused imports 제거)

실행할까요? (y/n): _
```

## Output Example
```markdown
# 🔍 검증 실행 중...

✅ 린트 검사 완료 (0.3초)
✅ 타입 체크 완료 (1.2초)
🔄 테스트 실행 중...
✅ 테스트 완료 (5.4초)
✅ 빌드 검사 완료 (2.1초)

---

# ✅ 모든 검증 통과

**린트**: 0 errors
**타입**: No errors
**테스트**: 42/42 passed (87% coverage)
**빌드**: Success

**총 소요 시간**: 9.0초

---
💡 다음 단계:
- `/commit`: 변경사항 커밋
- `/wrap`: 세션 정리 및 학습 추출
```

## Edge Cases
1. **도구 미설치**: 설치 안내 및 대안 제시
2. **설정 파일 없음**: 기본 설정으로 실행 제안
3. **타임아웃**: 장시간 테스트는 백그라운드 실행
4. **부분 실패**: 중요도 구분 (린트 < 타입 < 테스트)

## Configuration
프로젝트 루트에 `.claude/verify.json` 생성 가능:
```json
{
  "lint": true,
  "typecheck": true,
  "test": true,
  "build": false,
  "autofix": false,
  "timeout": 300
}
```

## Integration
- Hook에서 커밋 전 자동 호출 제안
- /commit 실행 전 자동 검증
- /wrap에서 선택적 호출

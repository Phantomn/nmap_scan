---
name: wrap
description: 세션 종료 시 학습 내용 정리 및 CLAUDE.md 업데이트
triggers: ["/wrap", "세션 정리", "마무리"]
---

# /wrap - 세션 정리 스킬

## What
세션 내 작업 요약, 학습 추출, 자동화 기회 탐지, CLAUDE.md 업데이트

## When
- 세션 종료 전
- 컨텍스트 사용률 80% 도달 시
- 주요 작업 완료 후
- 실수 발생 후 복기가 필요할 때

## Workflow

### 1단계: 병렬 분석 (Phase 1 - 4개 관점)
다음 4개 분석을 **병렬**로 실행:

#### A. doc-updater (문서 업데이트)
**목적**: CLAUDE.md 업데이트 항목 추출
**분석 내용**:
- Lessons Learned: 이번 세션에서 배운 것
- Common Mistakes: 발생한 실수/버그 패턴
- Rules: 새로 추가할 규칙

**출력 형식**:
```markdown
## 📝 CLAUDE.md 업데이트 제안

**Lessons Learned 추가**:
- [학습 내용 1]
- [학습 내용 2]

**Common Mistakes 추가**:
- [실수 패턴 1]
- [실수 패턴 2]

**Rules 추가/수정**:
- [규칙 제안 1]
```

#### B. automation-scout (자동화 탐지)
**목적**: 반복 패턴 → 자동화 기회 발견
**분석 내용**:
- 3회 이상 반복된 명령어/작업
- Hook으로 자동화 가능한 검증 작업
- Skill로 만들 수 있는 워크플로우

**출력 형식**:
```markdown
## 🤖 자동화 기회

**Hook 추가 제안**:
- 패턴: [반복된 작업]
- 제안: [Hook 설정]

**새 Skill 제안**:
- 이름: [skill-name]
- 목적: [자동화할 워크플로우]
```

#### C. learning-extractor (학습 추출)
**목적**: 기술적 배움과 발견 정리
**분석 내용**:
- 새로 배운 기술/패턴
- 해결한 문제와 방법
- 발견한 버그/이슈
- 개선한 코드 품질

**출력 형식**:
```markdown
## 💡 학습 내용

**배운 것**:
- [기술/패턴 1]
- [기술/패턴 2]

**해결한 문제**:
- 문제: [문제 설명]
  해결: [해결 방법]

**발견**:
- [버그/이슈/개선사항]
```

#### D. followup-suggester (후속 작업)
**목적**: 미완성 작업 및 다음 단계 제안
**분석 내용**:
- 완료하지 못한 작업
- TODO 주석/이슈
- 다음 세션 권장 작업
- 테스트/문서화 누락 항목

**출력 형식**:
```markdown
## 🔜 다음 작업

**미완성**:
- [ ] [작업 1]
- [ ] [작업 2]

**권장 순서**:
1. [우선순위 1]
2. [우선순위 2]

**주의사항**:
- [작업 시 주의할 점]
```

### 2단계: 중복 검증 (Phase 2 - duplicate-checker)
Phase 1의 4개 분석 결과를 받아서 검증:

#### E. duplicate-checker (중복 검증 및 통합)
**목적**: Phase 1 결과의 중복 제거 및 일관성 검증
**분석 내용**:
- 동일한 학습/실수는 하나로 병합
- 상충되는 제안 조정
- 우선순위 재정렬
- 실행 가능성 검증
- 기존 CLAUDE.md와 중복 확인

**출력 형식**:
```markdown
## 🔍 중복 검증 결과

**중복 제거**:
- [항목 A]와 [항목 B] 병합 → [통합 항목]

**우선순위 조정**:
- [항목 X]: Medium → High (영향도 재평가)

**기존 CLAUDE.md 중복**:
- [항목 Y]는 이미 Lessons Learned에 존재 → 스킵

**최종 제안**:
- CLAUDE.md 업데이트: 3개 항목
- 자동화 설정: 2개 항목
- 후속 작업: 5개 항목
```

**Phase 2 실행 방식**:
- Phase 1 완료 후 순차 실행 (Phase 1 결과 의존)
- Phase 1의 4개 출력을 입력으로 받음
- 기존 CLAUDE.md 읽고 중복 확인

### 3단계: 사용자 선택
다음 작업을 제안:
```
✅ 선택 가능한 작업:
1. CLAUDE.md 업데이트 (팀 공유 규칙)
2. MEMORY.md 업데이트 (프로젝트 메모리)
3. 자동화 설정 추가 (Hook/Skill)
4. Git 커밋 (/commit으로 연결)
5. 모두 건너뛰기

어떤 작업을 수행할까요?
```

## Output Example
```markdown
# 🎁 세션 정리 결과

## 📝 CLAUDE.md 업데이트 제안
**Lessons Learned**:
- FastAPI 비동기 DB 연결 시 `async with` 사용 필수
- SQLAlchemy 2.0 스타일로 마이그레이션 완료

**Common Mistakes**:
- await 없이 비동기 함수 호출 → RuntimeWarning

**Rules 추가**:
- 모든 DB 세션은 컨텍스트 매니저 사용

## 🤖 자동화 기회
**Hook 추가**:
- 패턴: pytest 실행 전 DB 마이그레이션 체크
- 제안: preToolUse hook에 `alembic check` 추가

## 💡 학습 내용
- Pydantic v2의 `model_validator` 사용법 학습
- PostgreSQL JSONB 인덱싱으로 쿼리 성능 10배 개선

## 🔜 다음 작업
- [ ] 인증 미들웨어 테스트 작성
- [ ] API 문서화 (OpenAPI 스펙)

---
✅ 선택: 1, 2, 3, 4, 5
```

## Implementation Notes
- **Phase 1**: 4개 분석을 병렬 실행 (단일 메시지)
- **Phase 2**: duplicate-checker가 Phase 1 결과 검증 (순차 실행)
- CLAUDE.md는 Git에 커밋되므로 팀원과 공유
- 자동화 제안은 즉시 적용하지 않고 사용자 확인 필요
- 2-phase 접근으로 중복 제거 및 일관성 보장

### MEMORY.md 업데이트 가이드
**역할 분리**:
- CLAUDE.md Lessons Learned = 팀 공유 규칙 (Git 추적)
- MEMORY.md = Claude 자동 참조 지식 (로컬, 200줄 제한)

**MEMORY.md에 적합한 내용**:
- 프로젝트 구조 지식 (모듈 간 의존성, 숨겨진 관계)
- 반복적으로 참조하는 경로/명령어
- 디버깅 시 유용했던 패턴

**부적합한 내용** (CLAUDE.md에 넣을 것):
- 명시적 코딩 규칙 ("await 필수" 등)
- 팀원에게 공유해야 할 교훈

**저장 위치**: `~/.claude/projects/<project-path-encoded>/memory/MEMORY.md`
**제약**: 200줄 초과 시 잘림, 중요 항목을 앞에 배치

## Two-Phase Architecture

### Why Two Phases?
**문제**: 4개 에이전트가 병렬로 동시 실행되면 서로의 출력을 모름
- 동일한 발견을 중복 보고
- 상충되는 제안 (예: A는 "삭제", B는 "수정" 제안)
- 우선순위 불일치

**해결**: Phase 2에서 통합 검증
- Phase 1: 각 관점에서 독립 분석 (병렬)
- Phase 2: 전체 결과 통합 및 중복 제거 (순차)

### Execution Flow
```
세션 컨텍스트
     ↓
Phase 1 (병렬):
  ├─ doc-updater
  ├─ automation-scout
  ├─ learning-extractor
  └─ followup-suggester
     ↓ (4개 출력)
Phase 2 (순차):
  └─ duplicate-checker
     ├─ 중복 병합
     ├─ 충돌 조정
     ├─ CLAUDE.md 비교
     └─ 최종 제안
     ↓
사용자 선택
```

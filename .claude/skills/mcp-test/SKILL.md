---
name: mcp-test
description: Playwright MCP 격리 실행으로 E2E 테스트 (토큰 효율)
triggers: ["/test", "/mcp-test", "E2E 테스트"]
---

# /mcp-test - Playwright 격리 E2E 테스트

## What
Playwright MCP를 서브에이전트로 격리 실행하여 브라우저 테스트 후 결과만 반환

## Why
**문제**: Playwright 직접 호출 시 전체 실행 로그가 메인 컨텍스트에 쌓임
- 테스트 3-4개 실행 → 8,000+ 토큰 소모
- 스크린샷, 상세 로그까지 메인 컨텍스트 적재

**해결**: 격리 실행 → 85% 토큰 절감 (8,000 → 1,200)

## When
- E2E 테스트 실행 (로그인, 폼 제출 등)
- 시각적 테스트 (스크린샷 비교)
- 접근성 검증 (WCAG 준수)
- 성능 테스트 (페이지 로드 시간)
- 크로스 브라우저 테스트

## Workflow

### 단계 1: 명령어 파싱
```bash
/test <scenario> [--browser chrome|firefox|webkit]

시나리오:
- login: 로그인 플로우
- form: 폼 제출
- navigation: 네비게이션 테스트
- accessibility: 접근성 검증
- custom: 커스텀 시나리오

예시:
/test login
/test form --browser firefox
/test "signup flow" --screenshot
/test accessibility
```

### 단계 2: test-runner 서브에이전트 실행 (격리)
```
격리된 컨텍스트에서:
1. Playwright MCP 호출
2. 브라우저 시작 및 시나리오 실행
3. 상세 로그, 스크린샷 수집 (8,000 토큰)
4. 성공/실패 + 핵심 정보만 요약 (1,200 토큰)
```

### 단계 3: 메인 세션에 결과 반환
```markdown
## 🧪 E2E 테스트 결과: [시나리오]

**브라우저**: [chrome/firefox/webkit]
**실행 시간**: [duration]
**상태**: ✅ 성공 / ❌ 실패

### 테스트 단계
1. ✅ [단계 1] - [duration]
2. ✅ [단계 2] - [duration]
3. ❌ [단계 3] - [에러 메시지]

### 실패 상세 (있을 경우)
- **위치**: [요소 selector]
- **에러**: [에러 메시지]
- **스크린샷**: [경로]

### 성능 메트릭
- 페이지 로드: [time]ms
- First Contentful Paint: [time]ms
- Time to Interactive: [time]ms

### 접근성 이슈 (있을 경우)
- [WCAG 위반 항목]
```

## Test Scenarios

### Login Flow
```bash
/test login

시나리오:
1. 로그인 페이지 접속
2. 이메일/비밀번호 입력
3. 로그인 버튼 클릭
4. 대시보드 리디렉션 확인
```

### Form Submission
```bash
/test form

시나리오:
1. 폼 페이지 접속
2. 필드 입력 (텍스트, 드롭다운, 체크박스)
3. 유효성 검사 확인
4. 제출 및 성공 메시지 확인
```

### Navigation
```bash
/test navigation

시나리오:
1. 홈페이지 접속
2. 네비게이션 메뉴 클릭
3. 각 페이지 로드 확인
4. 뒤로 가기/앞으로 가기 테스트
```

### Accessibility
```bash
/test accessibility

검증 항목:
- ARIA 라벨 존재
- 키보드 네비게이션 가능
- 색상 대비 충분
- Alt 텍스트 존재
- 폼 라벨 연결
```

## Examples

### Example 1: 로그인 테스트
```bash
사용자: /test login

메인 세션 반환 (1,000 토큰):
## 🧪 E2E 테스트 결과: Login Flow

**브라우저**: chrome
**실행 시간**: 3.2s
**상태**: ✅ 성공

### 테스트 단계
1. ✅ 로그인 페이지 접속 - 450ms
2. ✅ 이메일 입력 (test@example.com) - 120ms
3. ✅ 비밀번호 입력 - 100ms
4. ✅ 로그인 버튼 클릭 - 850ms
5. ✅ 대시보드 리디렉션 확인 - 1680ms

### 성능 메트릭
- 페이지 로드: 450ms
- First Contentful Paint: 320ms
- Time to Interactive: 680ms

### 스크린샷
- 성공 화면: /tmp/screenshots/login-success-2024-02-05.png
```

### Example 2: 폼 테스트 (실패)
```bash
사용자: /test form --browser firefox

메인 세션 반환 (1,200 토큰):
## 🧪 E2E 테스트 결과: Form Submission

**브라우저**: firefox
**실행 시간**: 2.8s
**상태**: ❌ 실패

### 테스트 단계
1. ✅ 폼 페이지 접속 - 380ms
2. ✅ 이름 필드 입력 - 90ms
3. ✅ 이메일 필드 입력 - 85ms
4. ❌ 제출 버튼 클릭 - 타임아웃

### 실패 상세
- **위치**: button[type="submit"]
- **에러**: Timeout 5000ms exceeded waiting for element to be clickable
- **원인**: 버튼이 disabled 상태로 남아있음
- **스크린샷**: /tmp/screenshots/form-error-2024-02-05.png

### 디버깅 제안
- [ ] 폼 유효성 검사 로직 확인
- [ ] 버튼 활성화 조건 검증
- [ ] console 에러 로그 확인

### 재현 단계
```javascript
// Playwright 코드
await page.goto('/form');
await page.fill('#name', 'Test User');
await page.fill('#email', 'test@example.com');
await page.click('button[type="submit"]'); // 여기서 실패
```
```

### Example 3: 접근성 테스트
```bash
사용자: /test accessibility

메인 세션 반환 (1,500 토큰):
## 🧪 E2E 테스트 결과: Accessibility Check

**브라우저**: chrome
**실행 시간**: 4.5s
**상태**: ⚠️ 경고 (3개 이슈)

### 접근성 이슈
1. **Missing Alt Text** (심각도: High)
   - 위치: img.logo
   - 설명: 로고 이미지에 alt 속성 없음
   - 수정: `<img src="logo.png" alt="Company Logo">`

2. **Color Contrast** (심각도: Medium)
   - 위치: .btn-secondary
   - 설명: 배경(#CCCCCC)과 텍스트(#999999) 대비 3.2:1 (최소 4.5:1 필요)
   - 수정: 텍스트 색상을 #666666으로 변경

3. **Form Label** (심각도: High)
   - 위치: input#phone
   - 설명: 입력 필드에 연결된 label 없음
   - 수정: `<label for="phone">Phone Number</label>`

### WCAG 준수율
- Level A: 90% (18/20 기준 통과)
- Level AA: 75% (12/16 기준 통과)
- Level AAA: 60% (6/10 기준 통과)

### 액션 아이템
- [ ] 모든 이미지에 alt 속성 추가 (High)
- [ ] 버튼 색상 대비 개선 (Medium)
- [ ] 폼 필드에 label 연결 (High)

### 참고 문서
- https://www.w3.org/WAI/WCAG21/quickref/
```

## Token Efficiency

| 방식 | 메인 컨텍스트 증가 | 절감율 |
|------|------------------|--------|
| Playwright 직접 호출 | 8,000 토큰 | - |
| /test (격리 실행) | 1,200 토큰 | 85% |

## Quality Standards

### 좋은 테스트 결과
✅ 각 단계 명시 (소요 시간 포함)
✅ 실패 시 명확한 에러 메시지
✅ 스크린샷 경로 제공
✅ 재현 단계 또는 수정 제안
✅ 성능 메트릭 포함

### 나쁜 테스트 결과
❌ "테스트 실패" 만 반환
❌ 에러 위치 불명확
❌ 스크린샷 없음
❌ 수정 방향 없음

## Integration

### 자동 활성화
```
사용자: "로그인 플로우 테스트해줘"

↓ (자동 감지)

/test login
```

### 수동 호출
```
/test <scenario> [--browser chrome|firefox|webkit]
```

## Advanced Usage

### 커스텀 시나리오
```bash
/test "checkout flow: add item → cart → payment"
```

### 특정 URL 테스트
```bash
/test login --url https://staging.example.com
```

### 스크린샷 모드
```bash
/test navigation --screenshot
```

### 병렬 브라우저 테스트
```bash
/test login --browsers chrome,firefox,webkit
```

## Implementation Notes

- **서브에이전트**: `@test-runner` 자동 호출 (격리)
- **격리 보장**: 서브에이전트 컨텍스트는 메인에 영향 없음
- **스크린샷**: /tmp/screenshots/ 저장, 경로만 반환
- **헤드리스**: 기본 헤드리스 모드 (--headed로 변경 가능)

## Troubleshooting

### Q: 브라우저가 시작되지 않아요
**A**: Playwright 설치 확인:
```bash
npx playwright install
```

### Q: 타임아웃 에러가 자주 발생해요
**A**: 타임아웃 증가:
```
/test scenario --timeout 30000
```

### Q: 특정 요소를 찾지 못해요
**A**: 선택자 확인 또는 대기 시간 추가:
```
/test scenario --wait-for-selector "#element"
```

### Q: 스크린샷이 너무 커요
**A**: 스크린샷은 자동 압축되며, 메인 세션에는 경로만 반환됩니다.

## See Also
- `/mcp-docs` - 공식 문서 조회 (Context7 MCP 격리)
- `/mcp-search` - 웹 검색 (Tavily MCP 격리)
- `/mcp-analyze` - 코드 분석 (Serena+Sequential 격리)
- `/verify` - 린트/타입/테스트/빌드 검증

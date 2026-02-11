# 프로젝트 초기화 가이드

## 1. CLAUDE.md 커스터마이징

`.claude/CLAUDE.md`를 프로젝트에 맞게 수정:

### 필수 수정 항목
- **프로젝트명**: 첫 줄 `[프로젝트명]` 교체
- **Tech Stack**: 실제 사용 기술 스택
- **Project Rules**: 팀 코딩 규칙 반영

### 선택 수정 항목
- **Lessons Learned**: 초기엔 비워둠 (세션마다 추가)
- **Common Mistakes**: 발견 시 추가

## 2. hooks.json 프로젝트 맞춤 설정

기본 hooks 활성화 후 프로젝트별 추가

## 3. 팀 공유 (Git 체크인)

```bash
git add .claude/
git commit -m "chore: Initialize Claude Code project config"
```

## 검증 체크리스트

- [ ] CLAUDE.md 프로젝트명 교체
- [ ] Tech Stack 실제 기술 반영
- [ ] 팀 코딩 규칙 추가
- [ ] hooks.json 프로젝트 맞춤 설정
- [ ] Git에 체크인 완료

#!/usr/bin/env bash
# on-task-completed.sh - TaskCompleted 이벤트 핸들러
# 팀 태스크가 완료될 때 실행됨
# 입력: stdin JSON + 환경변수 ($FROM, $TASK_ID, $TASK_SUBJECT 등)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=hooks-common.sh
source "${SCRIPT_DIR}/hooks-common.sh"

# stdin JSON 읽기
read_stdin_json

# 환경변수 우선, stdin JSON 폴백
agent="${FROM:-$(json_field from)}"
task_id="${TASK_ID:-$(json_field taskId)}"
task_subject="${TASK_SUBJECT:-$(json_field taskSubject)}"
timestamp="${TIMESTAMP:-$(json_field timestamp)}"

# 필수 값 확인
if [ -z "$task_id" ]; then
    log_warning "TaskCompleted: task_id(TASK_ID) 없음, 건너뜀"
    exit 0
fi

# 1. 구조화된 JSONL 로그 기록
log_event "task_completed" \
    "agent" "${agent:-unknown}" \
    "task_id" "$task_id" \
    "task_subject" "${task_subject:-}" \
    "timestamp" "${timestamp:-}"

# 2. 누적 활동 요약
progress=$(calculate_progress)
summary=$(agent_summary)

# 완료 비율 계산
completed="${progress%%/*}"
total="${progress##*/}"
if [ "$total" -gt 0 ] 2>/dev/null; then
    pct=$(( completed * 100 / total ))
    log_success "[${progress} 완료] ${pct}% | ${summary}"
else
    log_success "[${progress} 완료] ${summary}"
fi

# 3. 전체 완료 감지
if [ "$total" -gt 0 ] 2>/dev/null && [ "$completed" -eq "$total" ]; then
    log_success "모든 태스크 완료!"
    send_notification "Agent Teams" "모든 태스크 완료! (${total}개)"
else
    send_notification "Agent Teams" "태스크 #${task_id} 완료 (${task_subject:-})"
fi

# 4. GitHub 이슈 자동 닫기 (HOOK_GITHUB_AUTOCLOSE=1 + 태스크 제목에 #숫자)
if [ "${HOOK_GITHUB_AUTOCLOSE:-0}" = "1" ] && [ -n "${task_subject:-}" ]; then
    issue_num=$(printf '%s' "$task_subject" | grep -oE '#[0-9]+' | head -1 | tr -d '#' || true)
    if [ -n "$issue_num" ] && command_exists gh; then
        if gh issue close "$issue_num" 2>/dev/null; then
            log_info "GitHub 이슈 #${issue_num} 자동 닫기 완료"
        else
            log_warning "GitHub 이슈 #${issue_num} 닫기 실패"
        fi
    fi
fi

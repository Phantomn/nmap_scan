#!/usr/bin/env bash
# on-teammate-idle.sh - TeammateIdle 이벤트 핸들러
# 팀원이 유휴 상태가 될 때 실행됨
# 입력: stdin JSON + 환경변수 ($FROM, $COMPLETED_TASK_ID 등)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=hooks-common.sh
source "${SCRIPT_DIR}/hooks-common.sh"

# stdin JSON 읽기
read_stdin_json

# 환경변수 우선, stdin JSON 폴백
agent="${FROM:-$(json_field from)}"
completed_task="${COMPLETED_TASK_ID:-$(json_field completedTaskId)}"
completed_status="${COMPLETED_STATUS:-$(json_field completedStatus)}"
timestamp="${TIMESTAMP:-$(json_field timestamp)}"

# 필수 값 확인
if [ -z "$agent" ]; then
    log_warning "TeammateIdle: agent(FROM) 없음, 건너뜀"
    exit 0
fi

# 1. 구조화된 JSONL 로그 기록
log_event "teammate_idle" \
    "agent" "$agent" \
    "completed_task_id" "${completed_task:-}" \
    "completed_status" "${completed_status:-}" \
    "timestamp" "${timestamp:-}"

# 2. 진행률 표시
progress=$(calculate_progress)
log_info "[${progress} 완료] ${agent} 유휴"

# 3. 알림 발송 (환경변수로 제어)
send_notification "Agent Teams" "[${progress} 완료] ${agent} 유휴 상태"

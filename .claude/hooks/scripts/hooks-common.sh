#!/usr/bin/env bash
# hooks-common.sh - Agent Teams 훅 공통 유틸리티
# 다른 훅 스크립트에서 source로 사용
set -euo pipefail

# 색상 정의
export RED='\033[0;31m'
export GREEN='\033[0;32m'
export YELLOW='\033[1;33m'
export BLUE='\033[0;34m'
export NC='\033[0m'

# 로그 디렉토리 (CWD 기반, 폴백: /tmp)
HOOK_LOG_DIR="${CWD:-.}/.claude/logs"
HOOK_LOG_FILE="${HOOK_LOG_DIR}/agent-team.jsonl"

# 로깅 함수
log_info() {
    printf '%b\n' "${BLUE}[hooks] $1${NC}" >&2
}

log_success() {
    printf '%b\n' "${GREEN}[hooks] $1${NC}" >&2
}

log_warning() {
    printf '%b\n' "${YELLOW}[hooks] $1${NC}" >&2
}

log_error() {
    printf '%b\n' "${RED}[hooks] $1${NC}" >&2
}

# 명령어 존재 확인
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# stdin에서 JSON 읽기 → 전역 변수 STDIN_JSON에 저장
read_stdin_json() {
    STDIN_JSON=""
    if ! [ -t 0 ]; then
        STDIN_JSON=$(cat)
    fi
}

# JSON 필드 추출 (jq 있으면 사용, 없으면 grep 폴백)
json_field() {
    local field="$1"
    local json="${2:-$STDIN_JSON}"

    if command_exists jq; then
        printf '%s' "$json" | jq -r ".$field // empty" 2>/dev/null || true
    else
        # jq 없을 때 간이 추출 (단순 문자열 값만)
        printf '%s' "$json" | grep -o "\"$field\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" \
            | head -1 | sed 's/.*":\s*"//;s/"$//' || true
    fi
}

# 구조화된 JSONL 로그 기록
log_event() {
    local event_type="$1"
    shift

    # 로그 디렉토리 확인/생성
    if [ ! -d "$HOOK_LOG_DIR" ]; then
        mkdir -p "$HOOK_LOG_DIR" 2>/dev/null || {
            log_warning "로그 디렉토리 생성 실패: $HOOK_LOG_DIR"
            return 0
        }
    fi

    if command_exists jq; then
        # jq로 안전한 JSON 생성
        local -a jq_args=(--arg event "$event_type" --arg log_ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)")
        local jq_obj='{event: $event, log_ts: $log_ts'

        while [ $# -ge 2 ]; do
            local key="$1"
            local val="$2"
            jq_args+=(--arg "$key" "$val")
            jq_obj+=", ${key}: \$${key}"
            shift 2
        done
        jq_obj+='}'

        jq -nc "${jq_args[@]}" "$jq_obj" >> "$HOOK_LOG_FILE" 2>/dev/null || true
    else
        # jq 없을 때 수동 JSON 생성 (값 이스케이프 간소화)
        local line
        local log_ts
        log_ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
        line="{\"event\":\"$event_type\",\"log_ts\":\"$log_ts\""
        while [ $# -ge 2 ]; do
            line+=",\"$1\":\"$2\""
            shift 2
        done
        line+="}"
        printf '%s\n' "$line" >> "$HOOK_LOG_FILE" 2>/dev/null || true
    fi
}

# 로그 파일에서 완료/전체 태스크 진행률 계산
# 출력: "완료수/전체수" (전체수는 추정값 - 고유 태스크 ID 기반)
calculate_progress() {
    if [ ! -f "$HOOK_LOG_FILE" ] || ! command_exists jq; then
        printf '0/0'
        return 0
    fi

    local completed
    completed=$(jq -r 'select(.event == "task_completed") | .task_id' "$HOOK_LOG_FILE" 2>/dev/null \
        | sort -u | wc -l | tr -d ' ')

    local total
    total=$(jq -r 'select(.event == "task_completed" or .event == "teammate_idle") | .task_id // .completed_task_id // empty' \
        "$HOOK_LOG_FILE" 2>/dev/null | sort -u | wc -l | tr -d ' ')

    # 전체가 완료보다 작으면 보정
    if [ "$total" -lt "$completed" ]; then
        total=$completed
    fi

    printf '%s/%s' "$completed" "$total"
}

# 에이전트별 완료 태스크 수 집계
# 출력: "agent1: N, agent2: M"
agent_summary() {
    if [ ! -f "$HOOK_LOG_FILE" ] || ! command_exists jq; then
        printf 'N/A'
        return 0
    fi

    jq -r 'select(.event == "task_completed") | .agent' "$HOOK_LOG_FILE" 2>/dev/null \
        | sort | uniq -c | sort -rn \
        | awk '{printf "%s: %s, ", $2, $1}' \
        | sed 's/, $//' || printf 'N/A'
}

# 데스크톱 알림 (환경변수 HOOK_NOTIFY_DESKTOP=1 시 활성화)
send_desktop_notification() {
    local title="$1"
    local message="$2"

    if [ "${HOOK_NOTIFY_DESKTOP:-0}" != "1" ]; then
        return 0
    fi

    if command_exists notify-send; then
        notify-send "$title" "$message" 2>/dev/null || true
    elif command_exists osascript; then
        osascript -e "display notification \"$message\" with title \"$title\"" 2>/dev/null || true
    fi
}

# Slack 알림 (환경변수 SLACK_WEBHOOK_URL 설정 시 활성화)
send_slack_notification() {
    local message="$1"

    if [ -z "${SLACK_WEBHOOK_URL:-}" ]; then
        return 0
    fi

    if command_exists curl; then
        curl -s -X POST -H 'Content-type: application/json' \
            -d "{\"text\":\"$message\"}" \
            "$SLACK_WEBHOOK_URL" >/dev/null 2>&1 || true
    fi
}

# 통합 알림 발송 (데스크톱 + Slack)
send_notification() {
    local title="$1"
    local message="$2"
    send_desktop_notification "$title" "$message"
    send_slack_notification "[$title] $message"
}

# 스크립트가 직접 실행되었을 때
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    echo "hooks-common.sh - Agent Teams 훅 공통 유틸리티"
    echo "이 스크립트는 다른 훅 스크립트에서 source로 사용됩니다."
    echo ""
    echo "제공 함수:"
    echo "  read_stdin_json   - stdin에서 JSON 읽기"
    echo "  json_field        - JSON 필드 추출"
    echo "  log_event         - 구조화된 JSONL 로그 기록"
    echo "  calculate_progress - 진행률 계산"
    echo "  agent_summary     - 에이전트별 완료 집계"
    echo "  send_notification - 데스크톱/Slack 알림"
    echo ""
    echo "환경변수:"
    echo "  CWD                  - 프로젝트 루트 (로그 위치 결정)"
    echo "  HOOK_NOTIFY_DESKTOP  - 1로 설정 시 데스크톱 알림"
    echo "  SLACK_WEBHOOK_URL    - 설정 시 Slack 알림"
fi

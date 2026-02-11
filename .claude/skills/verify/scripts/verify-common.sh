#!/usr/bin/env bash
# verify-common.sh - 공통 유틸리티 함수들
# 다른 검증 스크립트에서 source로 사용

# 색상 정의
export RED='\033[0;31m'
export GREEN='\033[0;32m'
export YELLOW='\033[1;33m'
export BLUE='\033[0;34m'
export NC='\033[0m'

# 로깅 함수
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 명령어 존재 확인
command_exists() {
    command -v "$1" &> /dev/null
}

# 파일 존재 확인
file_exists() {
    [[ -f "$1" ]]
}

# 디렉토리 존재 확인
dir_exists() {
    [[ -d "$1" ]]
}

# Git 저장소 확인
is_git_repo() {
    git rev-parse --is-inside-work-tree &> /dev/null
}

# Git 변경 사항 확인
has_git_changes() {
    ! git diff --exit-code "$@" &> /dev/null
}

# 프로젝트 타입 감지
detect_project_type() {
    if file_exists "package.json"; then
        if file_exists "tsconfig.json"; then
            echo "typescript"
        else
            echo "javascript"
        fi
    elif file_exists "pyproject.toml" || file_exists "setup.py" || file_exists "requirements.txt"; then
        echo "python"
    elif file_exists "go.mod"; then
        echo "go"
    elif file_exists "Cargo.toml"; then
        echo "rust"
    elif file_exists "pom.xml" || file_exists "build.gradle"; then
        echo "java"
    elif file_exists "Gemfile"; then
        echo "ruby"
    elif file_exists "composer.json"; then
        echo "php"
    else
        echo "unknown"
    fi
}

# 결과 요약
print_summary() {
    local errors=$1
    local warnings=$2

    echo ""
    echo "============================================"
    if [[ $errors -eq 0 ]]; then
        log_success "전체 검증 완료: 에러 ${errors}개, 경고 ${warnings}개"
        return 0
    else
        log_error "검증 실패: 에러 ${errors}개, 경고 ${warnings}개"
        return 1
    fi
}

# 실행 시간 측정
measure_time() {
    local start_time=$1
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    echo "${duration}초"
}

# 병렬 실행 래퍼
run_parallel() {
    local -a pids=()
    local -a commands=("$@")
    local failed=0

    for cmd in "${commands[@]}"; do
        eval "$cmd" &
        pids+=($!)
    done

    for pid in "${pids[@]}"; do
        if ! wait "$pid"; then
            ((failed++))
        fi
    done

    return $failed
}

# 의존성 확인
check_dependencies() {
    local -a deps=("$@")
    local missing=0

    for dep in "${deps[@]}"; do
        if ! command_exists "$dep"; then
            log_warning "$dep 미설치"
            ((missing++))
        fi
    done

    return $missing
}

# 환경 변수 확인
check_env_var() {
    local var_name=$1
    if [[ -z "${!var_name:-}" ]]; then
        log_warning "환경 변수 $var_name 미설정"
        return 1
    fi
    return 0
}

# 파일 백업
backup_file() {
    local file=$1
    if file_exists "$file"; then
        cp "$file" "${file}.backup.$(date +%Y%m%d_%H%M%S)"
        log_info "$file 백업 완료"
    fi
}

# 임시 디렉토리 생성
create_temp_dir() {
    local temp_dir
    temp_dir=$(mktemp -d)
    echo "$temp_dir"
}

# 정리 함수 (trap 사용)
cleanup_on_exit() {
    local temp_dir=$1
    if dir_exists "$temp_dir"; then
        rm -rf "$temp_dir"
        log_info "임시 디렉토리 정리 완료"
    fi
}

# 스크립트 실행 권한 확인
check_executable() {
    local script=$1
    if [[ ! -x "$script" ]]; then
        log_warning "$script 실행 권한 없음"
        chmod +x "$script"
        log_success "$script 실행 권한 부여"
    fi
}

# JSON 파싱 (jq 필요)
parse_json() {
    local json_file=$1
    local query=$2
    if command_exists jq; then
        jq -r "$query" "$json_file"
    else
        log_error "jq 미설치 (JSON 파싱 불가)"
        return 1
    fi
}

# URL 유효성 검사
validate_url() {
    local url=$1
    if curl --output /dev/null --silent --head --fail "$url"; then
        return 0
    else
        log_error "URL 접근 실패: $url"
        return 1
    fi
}

# 포트 사용 확인
is_port_in_use() {
    local port=$1
    if lsof -Pi ":$port" -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# 디스크 공간 확인
check_disk_space() {
    local required_mb=$1
    local available_mb
    available_mb=$(df . | tail -1 | awk '{print $4}')
    available_mb=$((available_mb / 1024))

    if [[ $available_mb -lt $required_mb ]]; then
        log_error "디스크 공간 부족: ${available_mb}MB (필요: ${required_mb}MB)"
        return 1
    fi
    return 0
}

# 사용 예시 출력
print_usage_example() {
    cat << 'EOF'

사용 예시:
  # 공통 함수 로드
  source verify-common.sh

  # 프로젝트 타입 감지
  PROJECT_TYPE=$(detect_project_type)

  # 결과 요약 출력
  print_summary $ERRORS $WARNINGS
EOF
}

# 스크립트가 직접 실행되었을 때
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "verify-common.sh - 공통 유틸리티 함수"
    echo "이 스크립트는 다른 검증 스크립트에서 source로 사용됩니다."
    print_usage_example
fi

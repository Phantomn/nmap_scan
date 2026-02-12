#!/bin/bash
set -euo pipefail

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
info() { echo -e "${GREEN}[INFO]${NC} $(date '+%H:%M:%S') $*"; }
progress() { echo -e "${CYAN}[PROG]${NC} $(date '+%H:%M:%S') $*"; }
phase_header() {
    local PHASE=$1 DESC=$2 SUBNET=$3
    echo -e "\n${BOLD}${BLUE}══ Phase ${PHASE}: ${DESC} ══${NC}"
    echo -e "${BOLD}${BLUE}   서브넷: ${SUBNET}${NC}\n"
}
elapsed() {
    local SECS=$(( $(date +%s) - $1 ))
    printf "%dm%02ds" $((SECS/60)) $((SECS%60))
}

sudo_run() {
    echo "$SUDO_PASSWORD" | sudo -S "$@"
}

select_nse_scripts() {
    local PORTS="$1"
    local SCRIPTS=""
    local SCRIPT_PARTS=()
    local HAS_HTTP=false HAS_HTTPS=false HAS_MYSQL=false HAS_MSSQL=false
    local HAS_MONGODB=false HAS_POSTGRES=false HAS_SSH=false HAS_RDP=false
    local HAS_VNC=false HAS_SAP=false HAS_SMB=false

    echo "$PORTS" | grep -qE '(^|,)(80|8080)(,|$)' && HAS_HTTP=true
    echo "$PORTS" | grep -qE '(^|,)(443|8443)(,|$)' && HAS_HTTPS=true
    echo "$PORTS" | grep -qE '(^|,)3306(,|$)' && HAS_MYSQL=true
    echo "$PORTS" | grep -qE '(^|,)1433(,|$)' && HAS_MSSQL=true
    echo "$PORTS" | grep -qE '(^|,)27017(,|$)' && HAS_MONGODB=true
    echo "$PORTS" | grep -qE '(^|,)5432(,|$)' && HAS_POSTGRES=true
    echo "$PORTS" | grep -qE '(^|,)22(,|$)' && HAS_SSH=true
    echo "$PORTS" | grep -qE '(^|,)3389(,|$)' && HAS_RDP=true
    echo "$PORTS" | grep -qE '(^|,)5900(,|$)' && HAS_VNC=true
    echo "$PORTS" | grep -qE '(^|,)(3200|3300|8000|50000)(,|$)' && HAS_SAP=true
    echo "$PORTS" | grep -qE '(^|,)445(,|$)' && HAS_SMB=true

    [ "$HAS_HTTP" = true ] && SCRIPT_PARTS+=("(http-title or http-server-header or http-methods or http-robots.txt or http-headers or http-enum or http-vuln-*)")
    [ "$HAS_HTTPS" = true ] && SCRIPT_PARTS+=("(ssl-cert or ssl-date or ssl-heartbleed or ssl-poodle or ssl-dh-params or ssl-enum-ciphers)")
    [ "$HAS_HTTPS" = true ] && [ "$HAS_HTTP" = false ] && SCRIPT_PARTS+=("(http-title or http-server-header)")
    [ "$HAS_MYSQL" = true ] && SCRIPT_PARTS+=("(mysql-info or mysql-audit or mysql-empty-password)")
    [ "$HAS_MSSQL" = true ] && SCRIPT_PARTS+=("(ms-sql-info or ms-sql-ntlm-info or ms-sql-empty-password)")
    [ "$HAS_MONGODB" = true ] && SCRIPT_PARTS+=("(mongodb-info or mongodb-databases)")
    [ "$HAS_POSTGRES" = true ] && SCRIPT_PARTS+=("(pgsql-brute or postgresql-info)")
    [ "$HAS_SSH" = true ] && SCRIPT_PARTS+=("(ssh-hostkey or ssh-auth-methods)")
    [ "$HAS_RDP" = true ] && SCRIPT_PARTS+=("(rdp-enum-encryption or rdp-ntlm-info or rdp-vuln-ms12-020)")
    [ "$HAS_VNC" = true ] && SCRIPT_PARTS+=("(vnc-info or vnc-title)")
    [ "$HAS_SAP" = true ] && SCRIPT_PARTS+=("(http-sap-netweaver-leak)")
    [ "$HAS_SMB" = true ] && SCRIPT_PARTS+=("(smb-os-discovery or smb-vuln-*)")

    if [ ${#SCRIPT_PARTS[@]} -eq 0 ]; then
        echo "vuln and safe"
        return
    fi

    local FIRST=true
    for PART in "${SCRIPT_PARTS[@]}"; do
        if [ "$FIRST" = true ]; then
            SCRIPTS="$PART"
            FIRST=false
        else
            SCRIPTS="$SCRIPTS or $PART"
        fi
    done

    SCRIPTS="($SCRIPTS) and (safe or (discovery and not intrusive) or (vuln and safe))"
    echo "$SCRIPTS"
}

sanitize_subnet_name() {
    echo "$1" | tr './' '_'
}

calculate_subnet_hosts() {
    local PREFIX="${1##*/}"
    echo $(( 1 << (32 - PREFIX) ))
}

load_targets_from_json() {
    local JSON_FILE="$1"
    [ ! -f "$JSON_FILE" ] && return 1
    command -v jq &>/dev/null || { error "jq 설치 필요"; exit 1; }
    jq empty "$JSON_FILE" 2>/dev/null || { error "JSON 형식 오류"; exit 1; }

    # 형식 감지: 배열(구형식) vs 객체(신형식)
    local IS_ARRAY=$(jq -r 'type' "$JSON_FILE")

    if [ "$IS_ARRAY" = "array" ]; then
        # 구형식: ["172.20.1.0/24", ...]
        local json_subnets=$(jq -r '.[]' "$JSON_FILE" 2>/dev/null)
        [ -n "$json_subnets" ] && mapfile -t SUBNETS < <(echo "$json_subnets")
        EXCLUDE_IPS=()
    else
        # 신형식: {"targets": [...], "exclude": [...]}
        local json_subnets=$(jq -r '.targets[]' "$JSON_FILE" 2>/dev/null)
        [ -n "$json_subnets" ] && mapfile -t SUBNETS < <(echo "$json_subnets")

        local json_excludes=$(jq -r '.exclude[]?' "$JSON_FILE" 2>/dev/null)
        if [ -n "$json_excludes" ]; then
            mapfile -t EXCLUDE_IPS < <(echo "$json_excludes")
            info "제외 목록: ${#EXCLUDE_IPS[@]}개 항목"
        else
            EXCLUDE_IPS=()
        fi
    fi

    [ ${#SUBNETS[@]} -eq 0 ] && return 1
    return 0
}

calculate_total_hosts() {
    local total=0
    for subnet in "${SUBNETS[@]}"; do
        local prefix="${subnet##*/}"
        local hosts=$(( 1 << (32 - prefix) ))
        total=$((total + hosts))
    done
    echo "$total"
}

profile_rtt() {
    local HOST=$1
    local RTT=$(ping -c 5 -W 2 "$HOST" 2>/dev/null | grep 'time=' | awk -F'time=' '{print $2}' | awk '{print $1}' | awk '{sum+=$1; n++} END {if(n>0) print sum/n; else print 999}')
    echo "$HOST:$RTT" > "rtt_${HOST}.tmp"
    echo "$RTT"
}

calculate_avg_rtt() {
    local RTT_FILE="$1"
    [ ! -f "$RTT_FILE" ] || [ ! -s "$RTT_FILE" ] && { error "RTT 파일 없음: $RTT_FILE"; exit 1; }
    awk -F: '{sum+=$2; n++} END {if(n>0) print int(sum/n); else exit 1}' "$RTT_FILE"
}

optimize_rustscan_params() {
    local AVG_RTT=$1
    # 보수적 설정: WSL 안정성 우선 (BATCH↓ TIMEOUT↑ PARALLEL↓)
    local BATCH_SIZE=1000 TIMEOUT=4000 PARALLEL=2
    [ "$AVG_RTT" -lt 10 ] && BATCH_SIZE=2000 && TIMEOUT=2000 && PARALLEL=4
    [ "$AVG_RTT" -lt 50 ] && [ "$AVG_RTT" -ge 10 ] && BATCH_SIZE=1500 && TIMEOUT=3000 && PARALLEL=3
    [ "$AVG_RTT" -lt 150 ] && [ "$AVG_RTT" -ge 50 ] && BATCH_SIZE=1000 && TIMEOUT=4000 && PARALLEL=2
    [ "$AVG_RTT" -ge 150 ] && BATCH_SIZE=500 && TIMEOUT=6000 && PARALLEL=2
    echo "$BATCH_SIZE $TIMEOUT $PARALLEL"
}

# Phase 1 Health Check 하이브리드 병렬 실행
#
# 전략:
#   1. fping (ICMP) + nmap -sn (ICMP+TCP+ARP) 병렬 실행
#   2. max(fping_time, nmap_time)으로 총 시간 결정
#   3. 시간 단축: 35% (85초 → 55초)
health_check_hybrid() {
    local SUBNET=$1 LABEL=$2 EXCLUDE_FILE=$3
    local START=$(date +%s)

    progress "Health Check 병렬 실행 시작: $SUBNET"

    local FPING_OUT="fping_${LABEL}.txt"
    local NMAP_OUT="nmap_ping_${LABEL}.txt"
    local PID_FPING="" PID_NMAP=""

    # 1-A. fping 백그라운드 실행
    if command -v fping >/dev/null 2>&1; then
        progress "  [1/2] fping 시작 (백그라운드, 예상 30초)"
        fping -a -c 2 -q -r 0 -t 500 -g "$SUBNET" 2>/dev/null > "$FPING_OUT" &
        PID_FPING=$!
    else
        warn "  fping 미설치 - nmap만 사용"
        touch "$FPING_OUT"
        PID_FPING=""
    fi

    # 1-B. nmap -sn 백그라운드 실행
    progress "  [2/2] nmap -sn 시작 (백그라운드, 예상 60초)"

    local NMAP_CMD=(
        nmap -sn -PE -PP -PS80,443 -PA80,443
        -T4 --max-retries 2 --host-timeout 5s
        --min-parallelism 32
        "$SUBNET"
    )

    # exclude 파일 처리
    if [ -f "$EXCLUDE_FILE" ] && [ -s "$EXCLUDE_FILE" ]; then
        NMAP_CMD+=(--excludefile "$EXCLUDE_FILE")
    fi

    sudo_run "${NMAP_CMD[@]}" 2>/dev/null | \
        awk '/Nmap scan report for/{print $NF}' | \
        tr -d '()' > "$NMAP_OUT" &
    PID_NMAP=$!

    # 1-C. 두 작업 완료 대기
    if [ -n "$PID_FPING" ]; then
        wait $PID_FPING || warn "  fping 실행 실패 - nmap 결과만 사용"
    fi
    wait $PID_NMAP || { error "nmap -sn 실행 실패 (sudo 권한 확인)"; return 1; }

    # 1-D. 결과 카운트 및 로그
    local FPING_COUNT=$(wc -l < "$FPING_OUT" 2>/dev/null || echo 0)
    local NMAP_COUNT=$(wc -l < "$NMAP_OUT" 2>/dev/null || echo 0)
    progress "  [완료] fping: ${FPING_COUNT}개, nmap: ${NMAP_COUNT}개 ($(elapsed $START))"

    # 1-E. 병합 (중복 제거) + exclude 재필터링
    cat "$FPING_OUT" "$NMAP_OUT" 2>/dev/null | sort -u > "alive_hosts_${LABEL}.txt.tmp"

    # exclude IP 재필터링 (fping이 exclude를 무시하므로 필요)
    if [ -f "$EXCLUDE_FILE" ] && [ -s "$EXCLUDE_FILE" ]; then
        # 단순 IP만 추출 (CIDR 제외, nmap에서 이미 처리됨)
        grep -v '/' "$EXCLUDE_FILE" > "exclude_ips_only_${LABEL}.tmp" 2>/dev/null || touch "exclude_ips_only_${LABEL}.tmp"

        if [ -s "exclude_ips_only_${LABEL}.tmp" ]; then
            grep -vFf "exclude_ips_only_${LABEL}.tmp" "alive_hosts_${LABEL}.txt.tmp" > "alive_hosts_${LABEL}.txt"
            local EXCLUDED_COUNT=$(( $(wc -l < "alive_hosts_${LABEL}.txt.tmp") - $(wc -l < "alive_hosts_${LABEL}.txt") ))
            [ "$EXCLUDED_COUNT" -gt 0 ] && progress "  제외된 호스트 (fping): ${EXCLUDED_COUNT}개"
        else
            mv "alive_hosts_${LABEL}.txt.tmp" "alive_hosts_${LABEL}.txt"
        fi
        rm -f "exclude_ips_only_${LABEL}.tmp"
    else
        mv "alive_hosts_${LABEL}.txt.tmp" "alive_hosts_${LABEL}.txt"
    fi
    rm -f "$FPING_OUT" "$NMAP_OUT" "alive_hosts_${LABEL}.txt.tmp"

    local TOTAL_COUNT=$(wc -l < "alive_hosts_${LABEL}.txt")
    if [ "$TOTAL_COUNT" -eq 0 ]; then
        warn "⚠ Health Check 완료: 0개 발견 ($(elapsed $START)) - 다음 대역으로 진행"
    else
        progress "✓ Health Check 완료: ${TOTAL_COUNT}개 호스트 ($(elapsed $START))"
    fi
}

verify_and_increase_ulimit() {
    local REQUIRED_ULIMIT=$1 CURRENT_ULIMIT=$(ulimit -n)
    [ "$CURRENT_ULIMIT" -ge "$REQUIRED_ULIMIT" ] && return 0
    ulimit -n "$REQUIRED_ULIMIT" 2>/dev/null && return 0
    error "ulimit 증가 실패: sudo를 사용하거나 /etc/security/limits.conf 수정"
    exit 1
}

phase1_single_subnet() {
    local SUBNET=$1 LABEL=$2
    local START=$(date +%s)

    phase_header "1" "호스트 발견 + RTT 프로파일링" "$SUBNET"

    # Exclude 파일 준비
    local EXCLUDE_FILE="exclude_list_${LABEL}.txt"
    if [ ${#EXCLUDE_IPS[@]} -gt 0 ]; then
        printf "%s\n" "${EXCLUDE_IPS[@]}" > "$EXCLUDE_FILE"
        info "Exclude 목록: ${#EXCLUDE_IPS[@]}개 항목"
    else
        touch "$EXCLUDE_FILE"
    fi

    # === 핵심 변경: 하이브리드 Health Check ===
    health_check_hybrid "$SUBNET" "$LABEL" "$EXCLUDE_FILE"

    local ALIVE_COUNT=$(wc -l < "alive_hosts_${LABEL}.txt")

    [ "$ALIVE_COUNT" -eq 0 ] && {
        warn "⏭ Phase 1 종료: 활성 호스트 없음 ($SUBNET) - 다음 대역으로 이동"
        return
    }

    progress "활성 호스트: ${ALIVE_COUNT}개"

    # Phase 1 XML 생성 (xml_to_markdown.py 호환)
    info "Phase 1 XML 생성 (포트 22,80,443)"
    if [ ${#EXCLUDE_IPS[@]} -gt 0 ]; then
        # exclude 목록이 있으면 --excludefile 사용
        sudo_run nmap -sS -p 22,80,443 -T5 --open -iL "alive_hosts_${LABEL}.txt" --excludefile "exclude_list_${LABEL}.txt" -oX "phase1_${LABEL}.xml" > /dev/null 2>&1
    else
        sudo_run nmap -sS -p 22,80,443 -T5 --open -iL "alive_hosts_${LABEL}.txt" -oX "phase1_${LABEL}.xml" > /dev/null 2>&1
    fi

    # RTT 프로파일링
    local SAMPLE_COUNT=$([ "$ALIVE_COUNT" -lt 10 ] && echo "$ALIVE_COUNT" || echo 10)
    shuf -n "$SAMPLE_COUNT" "alive_hosts_${LABEL}.txt" > "rtt_sample_${LABEL}.txt"

    info "RTT 프로파일링 (샘플 ${SAMPLE_COUNT}개)"
    while read -r HOST; do
        profile_rtt "$HOST" &
    done < "rtt_sample_${LABEL}.txt"
    wait

    cat rtt_*.tmp 2>/dev/null > "rtt_profile_${LABEL}.txt"
    rm -f rtt_*.tmp

    local AVG_RTT=$(calculate_avg_rtt "rtt_profile_${LABEL}.txt")
    echo "$AVG_RTT" > "avg_rtt_${LABEL}.txt"
    progress "평균 RTT: ${AVG_RTT}ms"

    info "Phase 1 완료: $(elapsed "$START") - ${ALIVE_COUNT}개 호스트"
}

phase2_single_subnet() {
    local SUBNET=$1 LABEL=$2
    local START=$(date +%s)

    phase_header "2" "전체 포트 스캔 + SAP 재검증" "$SUBNET"

    # alive_hosts 파일 체크 (Phase 1에서 0개 발견 시 skip)
    [ ! -f "alive_hosts_${LABEL}.txt" ] || [ ! -s "alive_hosts_${LABEL}.txt" ] && {
        warn "⏭ Phase 2 건너뜀: 활성 호스트 없음 ($SUBNET)"
        return
    }

    [ ! -f "avg_rtt_${LABEL}.txt" ] && { error "avg_rtt_${LABEL}.txt 없음"; exit 1; }
    local AVG_RTT=$(cat "avg_rtt_${LABEL}.txt")

    read -r BATCH_SIZE TIMEOUT PARALLEL_LIMIT <<< "$(optimize_rustscan_params "$AVG_RTT")"
    local REQUIRED_ULIMIT=$(( PARALLEL_LIMIT * BATCH_SIZE + 5000 ))
    verify_and_increase_ulimit "$REQUIRED_ULIMIT"

    info "RTT ${AVG_RTT}ms → Batch=${BATCH_SIZE}, Timeout=${TIMEOUT}ms, 병렬=${PARALLEL_LIMIT}"

    local ALIVE_COUNT=$(wc -l < "alive_hosts_${LABEL}.txt")
    local PROCESSED=0

    # Main Scan
    progress "Main 스캔 시작 (${ALIVE_COUNT}개 호스트)"
    while read -r HOST; do
        local HOST_SAFE=$(echo "$HOST" | tr './' '_')
        rustscan -a "$HOST" -b "$BATCH_SIZE" -t "$TIMEOUT" --tries 1 --no-banner -g > "phase2_rustscan_${HOST_SAFE}.txt" 2>/dev/null &
        PROCESSED=$((PROCESSED + 1))
        [ $((PROCESSED % 10)) -eq 0 ] && progress "Main 진행: ${PROCESSED}/${ALIVE_COUNT}"
        while [ "$(jobs -r | wc -l)" -ge "$PARALLEL_LIMIT" ]; do wait -n 2>/dev/null || sleep 0.1; done
    done < "alive_hosts_${LABEL}.txt"
    wait

    # SAP Scan
    PROCESSED=0
    progress "SAP 스캔 시작 (${SAP_PORTS})"
    while read -r HOST; do
        local HOST_SAFE=$(echo "$HOST" | tr './' '_')
        rustscan -a "$HOST" -p "$SAP_PORTS" -b 2000 -t 1000 --tries 1 --no-banner -g > "phase2_sap_${HOST_SAFE}.txt" 2>/dev/null &
        PROCESSED=$((PROCESSED + 1))
        [ $((PROCESSED % 10)) -eq 0 ] && progress "SAP 진행: ${PROCESSED}/${ALIVE_COUNT}"
        while [ "$(jobs -r | wc -l)" -ge "$PARALLEL_LIMIT" ]; do wait -n 2>/dev/null || sleep 0.1; done
    done < "alive_hosts_${LABEL}.txt"
    wait

    # 결과 통합
    info "결과 통합 중..."
    true > "phase2_all_ports_${LABEL}.txt"
    for file in phase2_rustscan_*.txt; do
        [ -f "$file" ] && grep -oP '[\d.]+ -> \[\K[^\]]+' "$file" | tr ',' '\n' | while read -r PORT; do
            local IP=$(grep -oP '[\d.]+(?= ->)' "$file" | head -1)
            echo "${IP}:${PORT}"
        done >> "phase2_all_ports_${LABEL}.txt" 2>/dev/null || true
    done
    for file in phase2_sap_*.txt; do
        [ -f "$file" ] && [ -s "$file" ] && grep -oP '[\d.]+ -> \[\K[^\]]+' "$file" | tr ',' '\n' | while read -r PORT; do
            local IP=$(grep -oP '[\d.]+(?= ->)' "$file" | head -1)
            echo "${IP}:${PORT}"
        done >> "phase2_all_ports_${LABEL}.txt" 2>/dev/null || true
    done

    sort -u "phase2_all_ports_${LABEL}.txt" -o "phase2_all_ports_${LABEL}.txt"
    [ -s "phase2_all_ports_${LABEL}.txt" ] && \
        awk -F: '{ports[$1]=ports[$1]","$2} END {for(ip in ports) print ip":"substr(ports[ip],2)}' "phase2_all_ports_${LABEL}.txt" > "phase2_port_map_${LABEL}.txt" || \
        true > "phase2_port_map_${LABEL}.txt"

    local TOTAL_PORTS=$(wc -l < "phase2_all_ports_${LABEL}.txt" 2>/dev/null || echo 0)
    progress "발견 포트: ${TOTAL_PORTS}개"

    info "Phase 2 완료: $(elapsed "$START") - ${TOTAL_PORTS}개 포트"
}

phase3_single_subnet() {
    local SUBNET=$1 LABEL=$2
    local START=$(date +%s)

    phase_header "3" "서비스 버전 + OS 탐지" "$SUBNET"

    # alive_hosts 파일 체크
    [ ! -f "alive_hosts_${LABEL}.txt" ] || [ ! -s "alive_hosts_${LABEL}.txt" ] && {
        warn "⏭ Phase 3 건너뜀: 활성 호스트 없음 ($SUBNET)"
        return
    }

    local PARALLEL_DETAIL=5  # 보수적 설정: nmap -sV는 리소스 집약적
    local HOST_COUNT=$(wc -l < "phase2_port_map_${LABEL}.txt" 2>/dev/null || echo 0)

    [ "$HOST_COUNT" -eq 0 ] && { warn "⏭ Phase 3 건너뜀: 포트 맵 없음 ($SUBNET)"; return; }

    [ "$HOST_COUNT" -lt 50 ] && local NMAP_TIMING="-T5" || \
        [ "$HOST_COUNT" -lt 200 ] && local NMAP_TIMING="-T4" || \
        local NMAP_TIMING="-T3"

    info "nmap 서비스 스캔 시작 (${HOST_COUNT}개 호스트, 타이밍=${NMAP_TIMING})"

    local PROCESSED=0
    while IFS=: read -r IP PORTS; do
        local IP_SAFE=$(echo "$IP" | tr './' '_')
        local PORT_COUNT=$(echo "$PORTS" | tr ',' '\n' | wc -l)

        [ "$PORT_COUNT" -le 5 ] && local VERSION_INTENSITY="--version-all" || \
            [ "$PORT_COUNT" -le 20 ] && local VERSION_INTENSITY="--version-intensity 7" || \
            local VERSION_INTENSITY="--version-intensity 5"

        sudo_run nmap -sS -sV -sC "$VERSION_INTENSITY" "$NMAP_TIMING" -p "$PORTS" "$IP" -oA "phase3_detail_${IP_SAFE}" --host-timeout 10m --reason -v > /dev/null 2>&1 &
        PROCESSED=$((PROCESSED + 1))
        [ $((PROCESSED % 5)) -eq 0 ] && progress "서비스 스캔: ${PROCESSED}/${HOST_COUNT}"
        while [ "$(jobs -r | wc -l)" -ge "$PARALLEL_DETAIL" ]; do sleep 3; done
    done < "phase2_port_map_${LABEL}.txt"
    wait

    # OS 스캔
    awk -F: '$2 ~ /,/ {print $1}' "phase2_port_map_${LABEL}.txt" > "phase3_os_candidates_${LABEL}.txt" || touch "phase3_os_candidates_${LABEL}.txt"
    local OS_CANDIDATES=$(wc -l < "phase3_os_candidates_${LABEL}.txt")

    if [ "$OS_CANDIDATES" -gt 0 ]; then
        info "OS 탐지 시작 (${OS_CANDIDATES}개 호스트)"
        PROCESSED=0
        while read -r OS_HOST; do
            local OS_HOST_SAFE=$(echo "$OS_HOST" | tr './' '_')
            sudo_run nmap -O --osscan-guess -T4 "$OS_HOST" -oA "phase3_os_${OS_HOST_SAFE}" > /dev/null 2>&1 &
            PROCESSED=$((PROCESSED + 1))
            [ $((PROCESSED % 5)) -eq 0 ] && progress "OS 탐지: ${PROCESSED}/${OS_CANDIDATES}"
            while [ "$(jobs -r | wc -l)" -ge 3 ]; do sleep 3; done  # 보수적 설정: OS 스캔 병렬 축소
        done < "phase3_os_candidates_${LABEL}.txt"
        wait
    fi

    info "Phase 3 완료: $(elapsed "$START") - ${HOST_COUNT}개 호스트, OS ${OS_CANDIDATES}개"
}

phase4_single_subnet() {
    local SUBNET=$1 LABEL=$2
    local START=$(date +%s)

    phase_header "4" "취약점 스캔 (Critical Hosts)" "$SUBNET"

    # alive_hosts 파일 체크
    [ ! -f "alive_hosts_${LABEL}.txt" ] || [ ! -s "alive_hosts_${LABEL}.txt" ] && {
        warn "⏭ Phase 4 건너뜀: 활성 호스트 없음 ($SUBNET)"
        return
    }

    # phase2_port_map 파일 체크
    [ ! -f "phase2_port_map_${LABEL}.txt" ] || [ ! -s "phase2_port_map_${LABEL}.txt" ] && {
        warn "⏭ Phase 4 건너뜀: 포트 맵 없음 ($SUBNET)"
        return
    }

    true > "phase4_critical_hosts_${LABEL}.txt"

    # 버그 수정: 마지막 포트 매칭 위해 정규식 개선
    grep -E ':(22|3389|5900)(,|$)' "phase2_port_map_${LABEL}.txt" 2>/dev/null | cut -d: -f1 >> "phase4_critical_hosts_${LABEL}.txt" || true
    grep -E ':(80|443|8080|8443)(,|$)' "phase2_port_map_${LABEL}.txt" 2>/dev/null | cut -d: -f1 >> "phase4_critical_hosts_${LABEL}.txt" || true
    grep -E ':(3306|5432|1433|27017)(,|$)' "phase2_port_map_${LABEL}.txt" 2>/dev/null | cut -d: -f1 >> "phase4_critical_hosts_${LABEL}.txt" || true
    grep -E ':(3200|3300|8000|50000)(,|$)' "phase2_port_map_${LABEL}.txt" 2>/dev/null | cut -d: -f1 >> "phase4_critical_hosts_${LABEL}.txt" || true
    sort -u "phase4_critical_hosts_${LABEL}.txt" -o "phase4_critical_hosts_${LABEL}.txt"

    local CRITICAL_COUNT=$(wc -l < "phase4_critical_hosts_${LABEL}.txt")

    [ "$CRITICAL_COUNT" -eq 0 ] && { info "Critical 호스트 없음"; return; }

    info "NSE 스캔 시작 (${CRITICAL_COUNT}개 호스트)"
    true > "phase4_nse_selection_${LABEL}.log"

    local PROCESSED=0
    while read -r IP; do
        local IP_SAFE=$(echo "$IP" | tr './' '_')
        local PORTS=$(grep "^$IP:" "phase2_port_map_${LABEL}.txt" | cut -d: -f2)
        [ -z "$PORTS" ] && continue

        local NSE_SCRIPTS=$(select_nse_scripts "$PORTS")
        echo "[$IP] Ports: $PORTS" >> "phase4_nse_selection_${LABEL}.log"
        echo "[$IP] Scripts: $NSE_SCRIPTS" >> "phase4_nse_selection_${LABEL}.log"
        echo "" >> "phase4_nse_selection_${LABEL}.log"

        sudo_run nmap --script "$NSE_SCRIPTS" -sV -p "$PORTS" "$IP" -oA "phase4_vuln_${IP_SAFE}" --host-timeout 10m > /dev/null 2>&1 &
        PROCESSED=$((PROCESSED + 1))
        [ $((PROCESSED % 3)) -eq 0 ] && progress "NSE 스캔: ${PROCESSED}/${CRITICAL_COUNT}"
        while [ "$(jobs -r | wc -l)" -ge 3 ]; do sleep 5; done  # 보수적 설정: NSE 스캔 병렬 축소
    done < "phase4_critical_hosts_${LABEL}.txt"
    wait

    info "Phase 4 완료: $(elapsed "$START") - ${CRITICAL_COUNT}개 호스트"
}

SCAN_TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
SCAN_DIR="$HOME/nmap/scans/rustscan_massive_${SCAN_TIMESTAMP}"
declare -a SUBNETS=()
declare -a EXCLUDE_IPS=()
readonly SAP_PORTS="3200,3300,3600,8000,8001,50000,50013,50014"

SKIP_VULN=false
RESUME=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JSON_FILE="$SCRIPT_DIR/targets.json"

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-vuln) SKIP_VULN=true; shift ;;
        --resume)
            LATEST_DIR=$(find "$HOME/nmap/scans/" -maxdepth 1 -type d -name "rustscan_massive_*" -printf "%T@ %p\n" 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)
            [ -n "$LATEST_DIR" ] && SCAN_DIR="$LATEST_DIR"
            shift ;;
        *) error "알 수 없는 인자: $1"; exit 1 ;;
    esac
done

load_targets_from_json "$JSON_FILE" || { error "targets.json 로드 실패"; exit 1; }
[ ${#SUBNETS[@]} -eq 0 ] && { error "대역 정보 없음"; exit 1; }

read -rsp "sudo 비밀번호: " SUDO_PASSWORD
echo
export SUDO_PASSWORD

mkdir -p "$SCAN_DIR"
cd "$SCAN_DIR" || exit 1

# 구 형식 체크포인트 경고
if [ -f ".phase1_complete" ] || [ -f ".phase2_complete" ] || [ -f ".phase3_complete" ] || [ -f ".phase4_complete" ]; then
    warn "구 형식 체크포인트 발견 (.phase*_complete) - 새 형식으로 재실행 권장"
    warn "기존 체크포인트 무시하고 진행합니다"
fi

GLOBAL_START=$(date +%s)
TOTAL_SUBNETS=${#SUBNETS[@]}
TOTAL_HOSTS=$(calculate_total_hosts)

info "===== 대규모 스캔 시작 ====="
info "대상: ${TOTAL_SUBNETS}개 서브넷, ${TOTAL_HOSTS} 호스트"
info "스캔 디렉토리: $SCAN_DIR"
[ "$SKIP_VULN" = true ] && info "Phase 4 (취약점 스캔) 건너뜀"

# 서브넷별 순차 처리
for i in "${!SUBNETS[@]}"; do
    subnet="${SUBNETS[$i]}"
    SUBNET_LABEL=$(sanitize_subnet_name "$subnet")
    SUBNET_NUM=$((i + 1))

    # 완료된 서브넷 스킵
    if [ -f ".subnet_${SUBNET_LABEL}_complete" ]; then
        info "서브넷 ${SUBNET_NUM}/${TOTAL_SUBNETS}: ${subnet} 완료됨 → 건너뜀"
        continue
    fi

    info "===== 서브넷 ${SUBNET_NUM}/${TOTAL_SUBNETS}: ${subnet} ====="
    SUBNET_START=$(date +%s)

    # Phase 1: 호스트 발견 + RTT 프로파일링
    if [ ! -f ".subnet_${SUBNET_LABEL}_phase1" ]; then
        phase1_single_subnet "$subnet" "$SUBNET_LABEL"
        touch ".subnet_${SUBNET_LABEL}_phase1"
    else
        info "Phase 1 완료됨 → 건너뜀"
    fi

    # Phase 2: 전체 포트 스캔
    if [ ! -f ".subnet_${SUBNET_LABEL}_phase2" ]; then
        phase2_single_subnet "$subnet" "$SUBNET_LABEL"
        touch ".subnet_${SUBNET_LABEL}_phase2"
    else
        info "Phase 2 완료됨 → 건너뜀"
    fi

    # Phase 3: 서비스 버전 + OS 탐지
    if [ ! -f ".subnet_${SUBNET_LABEL}_phase3" ]; then
        phase3_single_subnet "$subnet" "$SUBNET_LABEL"
        touch ".subnet_${SUBNET_LABEL}_phase3"
    else
        info "Phase 3 완료됨 → 건너뜀"
    fi

    # Phase 4: 취약점 스캔
    if [ "$SKIP_VULN" = false ]; then
        if [ ! -f ".subnet_${SUBNET_LABEL}_phase4" ]; then
            phase4_single_subnet "$subnet" "$SUBNET_LABEL"
            touch ".subnet_${SUBNET_LABEL}_phase4"
        else
            info "Phase 4 완료됨 → 건너뜀"
        fi
    fi

    touch ".subnet_${SUBNET_LABEL}_complete"
    info "서브넷 ${subnet} 완료 ($(elapsed "$SUBNET_START"))"
done

# 전역 집계
aggregate_results() {
    info "===== 전체 결과 집계 및 정리 ====="

    # 환경변수 export (Python heredoc용)
    export SCAN_DIR JSON_FILE

    # 임시 파일 경로 (PID로 고유성 보장)
    local TMP_PORT_MERGE="$SCAN_DIR/raw/.phase2_merged.$$"

    # 1. 디렉토리 구조 생성
    mkdir -p "$SCAN_DIR/reports/vulnerabilities"
    mkdir -p "$SCAN_DIR/raw"
    mkdir -p "$SCAN_DIR/logs"
    mkdir -p "$SCAN_DIR/.checkpoints"

    # 2. 체크포인트 이동
    mv "$SCAN_DIR"/.subnet_* "$SCAN_DIR/.checkpoints/" 2>/dev/null || true

    # 3. 중간 파일을 raw/로 이동
    mv "$SCAN_DIR"/alive_hosts_*.txt "$SCAN_DIR/raw/" 2>/dev/null || true
    mv "$SCAN_DIR"/phase2_all_ports_*.txt "$SCAN_DIR/raw/" 2>/dev/null || true
    mv "$SCAN_DIR"/phase1_*.xml "$SCAN_DIR/raw/" 2>/dev/null || true
    mv "$SCAN_DIR"/phase3_*.xml "$SCAN_DIR/raw/" 2>/dev/null || true
    mv "$SCAN_DIR"/phase3_*.nmap "$SCAN_DIR/raw/" 2>/dev/null || true
    mv "$SCAN_DIR"/phase3_*.gnmap "$SCAN_DIR/raw/" 2>/dev/null || true
    mv "$SCAN_DIR"/phase4_*.xml "$SCAN_DIR/raw/" 2>/dev/null || true
    mv "$SCAN_DIR"/phase4_*.nmap "$SCAN_DIR/raw/" 2>/dev/null || true
    mv "$SCAN_DIR"/phase4_*.gnmap "$SCAN_DIR/raw/" 2>/dev/null || true
    mv "$SCAN_DIR"/avg_rtt_*.txt "$SCAN_DIR/raw/" 2>/dev/null || true
    mv "$SCAN_DIR"/rtt_profile_*.txt "$SCAN_DIR/raw/" 2>/dev/null || true
    mv "$SCAN_DIR"/rtt_sample_*.txt "$SCAN_DIR/raw/" 2>/dev/null || true
    mv "$SCAN_DIR"/exclude_list_*.txt "$SCAN_DIR/raw/" 2>/dev/null || true

    # 4. 활성 호스트 통합
    cat "$SCAN_DIR"/raw/alive_hosts_*.txt 2>/dev/null | sort -u -V > "$SCAN_DIR/reports/alive_hosts.txt" || touch "$SCAN_DIR/reports/alive_hosts.txt"

    # 5. Exclude IP 목록 생성
    if [ ${#EXCLUDE_IPS[@]} -gt 0 ]; then
        printf "%s\n" "${EXCLUDE_IPS[@]}" > "$SCAN_DIR/reports/excluded_hosts.txt"
    else
        touch "$SCAN_DIR/reports/excluded_hosts.txt"
    fi

    # 6. 탐지되지 않은 IP 계산 (Python)
    python3 <<'PYPYTHON'
import ipaddress
import json
import sys
import os

# 환경변수에서 경로 가져오기
try:
    scan_dir = os.environ['SCAN_DIR']
    json_file = os.environ['JSON_FILE']
except KeyError as e:
    print(f'[ERROR] 필수 환경변수 누락: {e}', file=sys.stderr)
    sys.exit(1)

reports_dir = os.path.join(scan_dir, 'reports')

# Exclude IP 세트 (Shell이 생성한 파일 사용)
exclude_ips = set()
excluded_hosts_file = os.path.join(reports_dir, 'excluded_hosts.txt')
try:
    with open(excluded_hosts_file) as f:
        for line in f:
            item = line.strip()
            if not item:
                continue
            try:
                if '/' in item:
                    network = ipaddress.ip_network(item, strict=False)
                    exclude_ips.update(network.hosts())
                else:
                    exclude_ips.add(ipaddress.ip_address(item))
            except Exception as e:
                print(f'[WARN] Invalid exclude item {item}: {e}', file=sys.stderr)
except FileNotFoundError:
    pass

# targets.json 로드 (targets만)
try:
    with open(json_file) as f:
        data = json.load(f)
except FileNotFoundError:
    print('[ERROR] targets.json 파일을 찾을 수 없습니다', file=sys.stderr)
    sys.exit(1)

# 구형식(배열) vs 신형식(객체)
if isinstance(data, list):
    target_cidrs = data
else:
    target_cidrs = data.get('targets', [])

# 전체 IP 세트
all_ips = set()
for cidr_str in target_cidrs:
    try:
        network = ipaddress.ip_network(cidr_str, strict=False)
        all_ips.update(network.hosts())
    except Exception as e:
        print(f'[WARN] Invalid CIDR {cidr_str}: {e}', file=sys.stderr)

# Alive IP 세트
alive_ips = set()
alive_hosts_file = os.path.join(reports_dir, 'alive_hosts.txt')
try:
    with open(alive_hosts_file) as f:
        for line in f:
            ip_str = line.strip()
            if ip_str:
                try:
                    alive_ips.add(ipaddress.ip_address(ip_str))
                except Exception:
                    pass
except FileNotFoundError:
    pass

# 탐지되지 않은 IP = 전체 - exclude - alive
undetected_ips = all_ips - exclude_ips - alive_ips

# 저장
undetected_hosts_file = os.path.join(reports_dir, 'undetected_hosts.txt')
with open(undetected_hosts_file, 'w') as f:
    for ip in sorted(undetected_ips):
        f.write(f'{ip}\n')

print(f'[INFO] Exclude: {len(exclude_ips)}, Alive: {len(alive_ips)}, Undetected: {len(undetected_ips)}', file=sys.stderr)
PYPYTHON

    # 7. 포트 맵 생성
    cat "$SCAN_DIR"/raw/phase2_all_ports_*.txt 2>/dev/null | sort -u > "$TMP_PORT_MERGE" || touch "$TMP_PORT_MERGE"
    if [ -s "$TMP_PORT_MERGE" ]; then
        awk -F: '{ports[$1]=ports[$1]","$2} END {for(ip in ports) print ip":"substr(ports[ip],2)}' "$TMP_PORT_MERGE" > "$SCAN_DIR/reports/port_map.txt"
    else
        touch "$SCAN_DIR/reports/port_map.txt"
    fi
    rm -f "$TMP_PORT_MERGE"

    # 8. Phase 4 취약점 정보 파싱
    if ls "$SCAN_DIR"/raw/phase4_vuln_*.nmap 1> /dev/null 2>&1; then
        mkdir -p "$SCAN_DIR/reports/vulnerabilities"
        grep -h 'VULNERABLE' "$SCAN_DIR"/raw/phase4_vuln_*.nmap 2>/dev/null | sort -u > "$SCAN_DIR/reports/vulnerabilities/vulnerable_summary.txt" || touch "$SCAN_DIR/reports/vulnerabilities/vulnerable_summary.txt"
        grep -hPo 'CVE-\d{4}-\d+' "$SCAN_DIR"/raw/phase4_vuln_*.nmap 2>/dev/null | sort -u > "$SCAN_DIR/reports/vulnerabilities/cve_list.txt" || touch "$SCAN_DIR/reports/vulnerabilities/cve_list.txt"
        grep -h 'Subject:' "$SCAN_DIR"/raw/phase4_vuln_*.nmap 2>/dev/null > "$SCAN_DIR/reports/vulnerabilities/ssl_info.txt" || touch "$SCAN_DIR/reports/vulnerabilities/ssl_info.txt"
        grep -h 'empty password' "$SCAN_DIR"/raw/phase4_vuln_*.nmap 2>/dev/null > "$SCAN_DIR/reports/vulnerabilities/db_services.txt" || touch "$SCAN_DIR/reports/vulnerabilities/db_services.txt"
        grep -h 'SAP' "$SCAN_DIR"/raw/phase4_vuln_*.nmap 2>/dev/null > "$SCAN_DIR/reports/vulnerabilities/sap_services.txt" || touch "$SCAN_DIR/reports/vulnerabilities/sap_services.txt"
        grep -h 'OS:' "$SCAN_DIR"/raw/phase4_vuln_*.nmap 2>/dev/null > "$SCAN_DIR/reports/vulnerabilities/smb_info.txt" || touch "$SCAN_DIR/reports/vulnerabilities/smb_info.txt"
    fi

    # 9. summary.json 생성 (Python)
    python3 <<'PYPYTHON'
import json
import os
import sys
from datetime import datetime

# 환경변수에서 경로 가져오기
try:
    scan_dir = os.environ['SCAN_DIR']
except KeyError as e:
    print(f'[ERROR] 필수 환경변수 누락: {e}', file=sys.stderr)
    sys.exit(1)

scan_id = os.path.basename(scan_dir)
reports_dir = os.path.join(scan_dir, 'reports')
vuln_dir = os.path.join(reports_dir, 'vulnerabilities')

def count_lines(path):
    try:
        with open(path) as f:
            return sum(1 for line in f if line.strip())
    except Exception:
        return 0

summary = {
    'scan_id': scan_id,
    'timestamp': datetime.now().isoformat(),
    'statistics': {
        'alive_hosts': count_lines(os.path.join(reports_dir, 'alive_hosts.txt')),
        'excluded_hosts': count_lines(os.path.join(reports_dir, 'excluded_hosts.txt')),
        'undetected_hosts': count_lines(os.path.join(reports_dir, 'undetected_hosts.txt')),
        'open_ports': count_lines(os.path.join(reports_dir, 'port_map.txt')),
        'vulnerabilities': count_lines(os.path.join(vuln_dir, 'vulnerable_summary.txt')),
        'cve_count': count_lines(os.path.join(vuln_dir, 'cve_list.txt'))
    },
    'files': {
        'report': os.path.relpath(os.path.join(reports_dir, 'FINAL_REPORT.md')),
        'raw_xml': os.path.relpath(os.path.join(scan_dir, 'raw')),
        'logs': os.path.relpath(os.path.join(scan_dir, 'logs', 'scan.log'))
    }
}

summary_file = os.path.join(reports_dir, 'summary.json')
with open(summary_file, 'w') as f:
    json.dump(summary, f, indent=2)

print(f'[INFO] summary.json 생성 완료', file=sys.stderr)
PYPYTHON

    progress "집계 완료: reports/ 디렉토리 생성됨"
}

aggregate_results

# 최종 리포트 생성
info "===== 최종 리포트 생성 ====="
python3 "$SCRIPT_DIR/scripts/utils/xml_to_markdown.py" \
    --scan-dir "$SCAN_DIR" \
    --output "$SCAN_DIR/reports/FINAL_REPORT.md" \
    2>&1 | tee -a "$SCAN_DIR/logs/scan.log" | grep -E "SUCCESS|ERROR" || true

# 최종 요약
GLOBAL_END=$(date +%s)
ALIVE_COUNT=$(wc -l < "$SCAN_DIR/reports/alive_hosts.txt" 2>/dev/null || echo 0)
HOSTS_WITH_PORTS=$(wc -l < "$SCAN_DIR/reports/port_map.txt" 2>/dev/null || echo 0)
TOTAL_PORTS=$(awk -F: '{if(NF>=2) {split($2,a,","); n+=length(a)}} END {print n+0}' "$SCAN_DIR/reports/port_map.txt" 2>/dev/null || echo 0)
CVE_COUNT=$(wc -l < "$SCAN_DIR/reports/vulnerabilities/cve_list.txt" 2>/dev/null || echo 0)
ALIVE_RATE=$(echo "scale=2; $ALIVE_COUNT / $TOTAL_HOSTS * 100" | bc 2>/dev/null || echo 0)

echo ""
echo "========================================="
echo "         대규모 스캔 완료"
echo "========================================="
echo "총 실행 시간: $(elapsed "$GLOBAL_START")"
echo "서브넷: ${TOTAL_SUBNETS}개"
echo "활성 호스트: ${ALIVE_COUNT} / ${TOTAL_HOSTS} (${ALIVE_RATE}%)"
echo "포트 보유 호스트: ${HOSTS_WITH_PORTS}개"
echo "발견 포트: ${TOTAL_PORTS}개"
echo "발견 CVE: ${CVE_COUNT}개"
echo "디렉토리: $SCAN_DIR"
echo "========================================="

exit 0

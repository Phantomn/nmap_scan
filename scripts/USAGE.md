# rustscan_massive_4phase.sh 사용 가이드

## 개요

`rustscan_massive_4phase.sh`는 대규모 네트워크 대역에 대한 4단계 포트 스캔을 자동화하는 스크립트입니다.

- **입력**: `targets.json` (CIDR 배열)
- **출력**: `FINAL_REPORT.md` + 상세 스캔 결과
- **예상 시간**: 25-35분
- **특징**: 서브넷별 순차 처리, 진행 상황 출력, RTT 기반 최적화, 세분화된 체크포인트

### 4단계 프로세스 (서브넷별)

| Phase | 목표 | 도구 | 시간 (서브넷당) |
|-------|------|------|----------------|
| 1 | 호스트 발견 + RTT 프로파일링 + XML | `fping` + `nmap -sn` (하이브리드 **병렬**) | **50-60초** ⚡ |
| 2 | 전체 포트 스캔 + SAP 재검증 | `rustscan` (최적화) | 1-5분 |
| 3 | 서비스 버전 + OS 탐지 | `nmap -sV -sC` | 1-3분 |
| 4 | 취약점 스캔 | `nmap --script` | 1-2분 |

### 최신 개선 사항 (Phase 1-2) - v2.1

**Phase 1: 하이브리드 Health Check 병렬 실행** ⚡ **정확도 + 속도**
- **v2.0 (순차)**: fping (30초) → nmap (60초) = 85초
- **v2.1 (병렬)**: fping (30초) ∥ nmap (60초) = **55초** (35% 단축)
- **전략**:
  1. `fping` + `nmap -sn` **동시 실행** (백그라운드)
  2. 두 작업 완료 대기 (wait)
  3. 결과 병합 및 중복 제거
- **이유**: 포트 기반 탐지의 false negative 최소화 (0개 결과 → 정확한 호스트 발견)
- **효과**: 정확도 극대화 + 시간 단축 (전체 워크플로우 성공)

**Phase 2: 병렬 스캔 최적화**
- **변경 1**: `--scan-order random` 제거 (단일 IP 스캔 시 불필요)
- **변경 2**: `sleep 2` → `wait -n` (즉시 다음 작업, 20-30% 속도 향상)
- **효과**: 불필요한 오버헤드 제거, 병렬 효율 개선

**핵심 철학**: 서브넷을 **순차 처리** (한 번에 1개)하여 네트워크/fd 부하를 대폭 감소. 각 서브넷 내부에서는 병렬 처리 유지.

---

## 필수 환경

### 시스템 요구사항

```bash
# 필수 의존성 설치
sudo apt update
sudo apt install -y nmap jq

# rustscan 설치 (Cargo 필요)
cargo install rustscan
# 또는
sudo apt install -y rustscan  # 일부 배포판

# 권장: fping 설치 (Phase 1 속도 향상)
sudo apt install -y fping
```

**fping 미설치 시**: nmap -sn만 사용 (동작하지만 Phase 1이 더 느림)

### 권한

- `sudo` 권한 필수 (nmap, ulimit 조정)
- 스크립트 실행 권한: `chmod +x rustscan_massive_4phase.sh`

### 시스템 설정

```bash
# ulimit 확인 (권장: >= 70000, 서브넷별 순차 처리 기준)
ulimit -n

# 필요시 영구 설정 (/etc/security/limits.conf)
* soft nofile 131072
* hard nofile 131072
```

**변경**: 서브넷별 순차 처리로 피크 fd 요구량이 ~988,000 → ~70,000으로 감소.

---

## 설정

### 1. targets.json 작성

**위치**: `scripts/targets.json`

**형식 1 (구형식)**: IP 대역 배열 (CIDR 표기법)

```json
[
  "172.20.1.0/24",
  "172.20.2.0/24",
  "172.20.3.0/24",
  "100.103.28.0/24",
  "100.103.30.0/24"
]
```

**형식 2 (신형식, 권장)**: 객체 형식 + exclude 지원

```json
{
  "targets": [
    "172.20.1.0/24",
    "172.20.2.0/24",
    "172.20.3.0/24",
    "100.103.28.0/24",
    "100.103.30.0/24"
  ],
  "exclude": [
    "172.20.1.1",
    "172.20.1.254",
    "172.20.2.0/28"
  ]
}
```

**exclude 기능**:
- **단일 IP**: `"172.20.1.1"` - 특정 IP 제외 (게이트웨이, DNS 서버 등)
- **CIDR 대역**: `"172.20.2.0/28"` - IP 대역 전체 제외
- **사용 사례**: 관리 호스트, 프로덕션 서버, 민감한 시스템 제외

> **하위 호환성**: 구형식(배열) 사용 시 exclude 없이 전체 대역 스캔

**CIDR 범위 계산**

| CIDR | 호스트 수 |
|------|-----------|
| /32 | 1 |
| /30 | 4 |
| /28 | 16 |
| /25 | 128 |
| /24 | 256 |
| /16 | 65,536 |
| /8 | 16,777,216 |

> **팁**: 작은 대역부터 테스트 (1-2개 /24 CIDR 권장)

### 2. JSON 검증

```bash
# 유효성 확인
jq empty scripts/targets.json
```

---

## 실행

### 기본 사용법

```bash
./scripts/rustscan_massive_4phase.sh
```

**1단계: sudo 비밀번호 입력**

```
sudo 비밀번호: [마스킹된 입력]
```

**2단계: 자동 실행 (진행 출력 포함)**

```
[INFO] 14:32:01 ===== 대규모 스캔 시작 =====
[INFO] 14:32:01 대상: 9개 서브넷, 2304 호스트

══ Phase 1: 호스트 발견 + RTT 프로파일링 ══
   서브넷: 172.20.1.0/24

[INFO] 14:32:02 Exclude 목록: 3개 항목
[PROG] 14:32:02 Health Check 시작: 172.20.1.0/24
[PROG] 14:32:25   [1/2] fping: 20개 발견 (0m23s)
[PROG] 14:32:26   [2/2] nmap -sn 심층 스캔 중... (256 IPs, ~60초)
[PROG] 14:33:12   nmap -sn: 25개 발견 (1m10s)
[PROG] 14:33:12 ✓ Health Check 완료: 25개 호스트 (1m10s)
[PROG] 14:33:12 활성 호스트: 25개
[INFO] 14:33:13 Phase 1 XML 생성 (포트 22,80,443)
[INFO] 14:33:15 RTT 프로파일링 (샘플 10개)
[PROG] 14:33:19 평균 RTT: 8ms
[INFO] 14:33:19 Phase 1 완료: 1m17s - 25개 호스트

══ Phase 2: 전체 포트 스캔 + SAP 재검증 ══
   서브넷: 172.20.1.0/24

[INFO] 14:32:13 RTT 8ms → Batch=65535, Timeout=500ms, 병렬=15
[PROG] 14:32:14 Main 스캔 시작 (25개 호스트)
[PROG] 14:32:48 Main 진행: 10/25
[PROG] 14:33:22 SAP 스캔 시작 (3200,3300,3600,8000,8001,50000,50013,50014)
[INFO] 14:34:01 결과 통합 중...
[PROG] 14:34:03 발견 포트: 87개
[INFO] 14:34:03 Phase 2 완료: 1m50s - 87개 포트
```

- 서브넷별 순차 진행 (Phase 1→2→3→4 완료 후 다음 서브넷)
- 세분화된 체크포인트 자동 저장 (`.subnet_*_phase*`)
- 최종 결과: `$HOME/nmap/scans/rustscan_massive_YYYYMMDD_HHMMSS/`

### 명령줄 옵션

```bash
# 취약점 스캔 제외 (Phase 4 건너뛰기)
./scripts/rustscan_massive_4phase.sh --skip-vuln

# 중단 후 재개 (자동 감지)
./scripts/rustscan_massive_4phase.sh --resume
```

**변경**: `--force-retry` 옵션 제거 (서브넷별 체크포인트로 재실행 간편화).

### 사용 사례

**사례 1: 기본 전체 스캔**

```bash
cd ~/nmap
./scripts/rustscan_massive_4phase.sh
# 입력: sudo 비밀번호
# 출력: 완전한 네트워크 맵핑
```

**사례 2: 빠른 검색 (취약점 제외)**

```bash
./scripts/rustscan_massive_4phase.sh --skip-vuln
# 시간: ~25분 (Phase 1-3만)
```

**사례 3: 중단 후 재개**

```bash
# Ctrl+C로 중단
./scripts/rustscan_massive_4phase.sh --resume
# .phase1_complete ~ .phase3_complete 파일 기반 자동 복구
```

---

## Phase별 상세 설명

### Phase 1: 호스트 발견 (3-10초)

**목표**
- 대역 내 활성 호스트 식별 (포트 응답 기반)
- 네트워크 지연(RTT) 프로파일링

**기술**

```bash
rustscan -a <SUBNET> -r 1-1000 -b 5000 -t 1000 --tries 1 --scan-order random --no-banner -g
```

- `-r 1-1000`: 상위 1000개 포트 스캔 (호스트 발견 목적)
- `-b 5000`: 배치 크기 5000 (빠른 스캔)
- `-t 1000`: 타임아웃 1초
- `-g`: Greppable 출력 (파싱용)

**장점** (기존 nmap -sn 대비)
- 속도: 30초 → 3초 (10배 단축)
- 정확도: 포트 응답 호스트만 선별 (ICMP 차단 호스트도 탐지)
- 일관성: rustscan 중심 아키텍처

**출력**

- `alive_hosts_<LABEL>.txt`: 서브넷별 활성 호스트 목록
- `avg_rtt_<LABEL>.txt`: 서브넷별 평균 RTT (밀리초)
- `phase1_<LABEL>.txt`: 서브넷별 rustscan 결과
- **`phase1_<LABEL>.xml`**: 서브넷별 nmap XML (포트 22,80,443) - xml_to_markdown.py 호환

**체크포인트**: `.subnet_<LABEL>_phase1`

---

### Phase 2: 전체 포트 스캔 (12-35분)

**목표**
- 모든 활성 호스트의 65,535 포트 스캔
- SAP 표준 포트 재검증

**기술**

```bash
rustscan -a <HOST> -b <BATCH_SIZE> -t <TIMEOUT> --tries 1
```

**동적 최적화** (RTT 기반)

| RTT | 배치 크기 | 타임아웃 | 병렬 |
|-----|---------|---------|------|
| < 10ms | 65,535 | 500ms | 15 |
| 10-50ms | 10,000 | 1,500ms | 12 |
| 50-150ms | 8,000 | 2,000ms | 10 |
| ≥ 150ms | 5,000 | 5,000ms | 8 |

**SAP 포트 (rustscan 재검증)**

```
3200, 3300, 3600, 8000, 8001, 50000, 50013, 50014
```

> SAP 포트 재검증도 rustscan으로 실행 (기존 nmap -sS에서 전환)
> SAP 재검증은 Main Scan과 동시 실행되어 별도 대기 없이 병렬 처리됨

**출력**

- `phase2_all_ports_<LABEL>.txt`: 서브넷별 IP:포트 형식 모든 포트
- `phase2_port_map_<LABEL>.txt`: 서브넷별 호스트별 포트 매핑
- `phase2_rustscan_*.txt`: 호스트별 상세 결과 (IP 기반)

**체크포인트**: `.subnet_<LABEL>_phase2`

**검증**

- 포트 0개 발견 시 실패 (방화벽 차단 가능)
- 예상 포트 수 미만 시 경고

---

### Phase 3: 서비스 분석 (10-20분)

**목표**
- 열린 포트의 서비스 버전 탐지
- OS 식별 (다중 포트 보유 호스트)

**기술**

```bash
nmap -sV -sC <-T3|T4|T5> -p <PORTS>
```

**동적 타이밍** (호스트 수 기반)

| 호스트 수 | 타이밍 | 특징 |
|----------|--------|------|
| < 50 | -T5 | Insane (매우 빠름) |
| 50-200 | -T4 | Aggressive (빠름) |
| > 200 | -T3 | Normal (안정적) |

**동적 Version Intensity** (포트 수 기반)

| 포트 수 | Intensity | 프로브 수 |
|--------|-----------|---------|
| ≤ 5 | --version-all | 9 |
| 6-20 | --version-intensity 7 | 기본 |
| > 20 | --version-intensity 5 | 빠르게 |

**병렬 처리**
- 동시 15개 호스트 (메모리 관리)

**출력**

- `phase3_detail_*.xml`: 서비스 정보 (IP 기반, 포트별)
- `phase3_os_*.xml`: OS 탐지 결과 (IP 기반)

**체크포인트**: `.subnet_<LABEL>_phase3`

---

### Phase 4: 취약점 스캔 (10-15분, 선택사항)

**목표**
- 중요 호스트의 알려진 취약점 탐지
- 프로토콜별 상세 정보 추출

**우선순위 선별**

1. 관리 서비스: SSH(22), RDP(3389), VNC(5900)
2. 웹 서버: HTTP(80, 8080), HTTPS(443, 8443)
3. 데이터베이스: MySQL(3306), PostgreSQL(5432), MSSQL(1433), MongoDB(27017)
4. SAP: 포트 3200, 3300, 8000, 50000

**프로토콜별 NSE 스크립트**

```
HTTP  → http-title, http-methods, http-robots.txt, http-vuln-*
HTTPS → ssl-cert, ssl-heartbleed, ssl-poodle, ssl-enum-ciphers
SSH   → ssh-hostkey, ssh-auth-methods
DB    → mysql-info, ms-sql-info, postgresql-info
SAP   → http-sap-netweaver-leak
SMB   → smb-os-discovery, smb-vuln-*
```

**제약**
- `safe` 카테고리만 사용 (비파괴)
- 병렬 5개 제한 (보수적)
- 체크포인트 기반 스킵 가능

**출력**

- `phase4_vuln_*.xml`: 취약점 스캔 결과
- `phase4_cve_list.txt`: 발견된 CVE
- `phase4_ssl_certs.txt`: SSL 인증서 정보
- `phase4_db_empty_pass.txt`: 빈 패스워드 DB
- `phase4_sap_info.txt`: SAP 서비스 정보
- `phase4_smb_os.txt`: SMB OS 정보

**체크포인트**: `.phase4_complete`

---

## 결과 분석

### 최종 리포트 생성

```bash
# 자동 생성 (Phase 4 후)
cd $HOME/nmap/scans/rustscan_massive_YYYYMMDD_HHMMSS/
cat FINAL_REPORT.md
```

### FINAL_REPORT.md 구조

```markdown
# 대규모 네트워크 스캔 보고서

## 실행 요약
- 활성 호스트: N개
- 열린 포트: M개
- 발견된 CVE: K개

## 위험도 요약
- 🔴 Critical
- 🟡 High
- 🟢 Medium

## 프로토콜별 분석
- HTTP: N개 호스트
- HTTPS: M개 호스트
- SSH, Database, SAP 등

## 취약점 상세
- CVE 목록 (Top 10)
- Critical 발견 상세

## 권장 조치사항
- 즉시 조치 (Critical)
- 단기 조치 (High)
- 장기 조치 (Medium)
```

### 중간 파일 활용

| 파일 | 용도 |
|------|------|
| `alive_hosts.txt` | 활성 호스트 목록 (재스캔, 추가 분석용) |
| `phase2_port_map.txt` | 호스트별 포트 (서비스 접근성 확인) |
| `phase4_cve_list.txt` | CVE 패치 계획 수립 |
| `phase4_ssl_certs.txt` | 인증서 만료 모니터링 |
| `phase4_nse_selection.log` | NSE 스크립트 선택 기록 (감사용) |

---

## 체크포인트 및 복구

### 자동 체크포인트

스크립트는 각 Phase 완료 후 마커 파일 생성:

```bash
.phase1_complete → .phase2_complete → .phase3_complete → .phase4_complete
```

### 중단 후 재개

**방법 1: 자동 감지**

```bash
./scripts/rustscan_massive_4phase.sh
# 마지막 완료된 Phase 이후부터 자동 시작
```

**방법 2: 명시적 재개**

```bash
./scripts/rustscan_massive_4phase.sh --resume
```

**방법 3: 특정 Phase부터 시작** (수동)

```bash
# .phase2_complete까지 완료된 상태에서
# Phase 3부터 시작하려면 .phase2_complete 파일만 유지
cd $HOME/nmap/scans/rustscan_massive_YYYYMMDD_HHMMSS/
rm -f .phase3_complete .phase4_complete
# 다시 스크립트 실행
```

### 처음부터 다시 시작

```bash
cd $HOME/nmap/scans/rustscan_massive_YYYYMMDD_HHMMSS/
rm -f .phase*_complete
./scripts/rustscan_massive_4phase.sh --resume
```

---

## 성능 최적화

### RTT 기반 동적 조정

스크립트는 자동으로:

1. **Phase 1**: 샘플 호스트 10개 선택
2. **측정**: ping으로 평균 RTT 계산
3. **최적화**: RTT 범위에 따라 파라미터 조정
4. **Phase 2+**: 최적화된 설정으로 실행

### 병렬 처리

| Phase | 동시 개수 | 제약 |
|-------|----------|------|
| 1 | 최대 5개 (ulimit 검증) | 서브넷별 병렬, fd 누수 방지 |
| 2 | 8-15개 (RTT 기반) | Main + SAP 동시 실행, 단일 throttle |
| 3 | 15개 | nmap 프로세스 |
| 4 | 5개 | 보수적 (취약점 스캔) |

### 최적화 팁

1. **작은 테스트부터**: 1-2개 /24 CIDR로 검증
2. **로컬 네트워크**: RTT < 10ms → 가장 빠름
3. **원격 스캔**: RTT > 50ms → 타임아웃 증가, 배치 감소
4. **Phase 3 시간 단축**: 호스트 수 제한 (주요 호스트만)

---

## 문제 해결

### ulimit 오류

```
ERROR: ulimit 증가 실패
```

**해결책**

```bash
# 방법 1: 현재 세션 임시 설정
ulimit -n 65535

# 방법 2: 영구 설정 (재부팅 필요)
sudo nano /etc/security/limits.conf
# 추가:
# * soft nofile 65535
# * hard nofile 65535

# 다시 로그인 후 확인
ulimit -n
```

### 포트 0개 발견

```
ERROR: 포트 0개
```

**원인**
- 방화벽 차단
- 호스트 오프라인
- 스캔 타임아웃

**해결책**

```bash
# 방화벽 재시도 (SYN 기반)
./scripts/rustscan_massive_4phase.sh --force-retry

# 또는 ACK 스캔으로 재검증
nmap -sA -p 80,443 <HOST>
```

### 낮은 활성 호스트 비율

```
WARN: 활성 호스트 적음: 10개
```

**원인**
- 대역 오프라인
- 네트워크 단절
- 방화벽 ICMP 차단

**확인**

```bash
# 수동 ping 테스트
ping -c 1 172.20.1.1

# nmap -Pn (모든 호스트 가정)
nmap -Pn -p 22 172.20.1.0/24
```

### Phase 2 False Negative

```
WARN: 포트 수 적음: 50 < 150
```

**원인**
- rustscan 타임아웃 부족
- 패킷 손실

**해결책**

```bash
# 신뢰성 모드 실행
./scripts/rustscan_massive_4phase.sh --force-retry
# → tries=2, timeout 1.5배 증가
```

### JSON 형식 오류

```
ERROR: JSON 형식 오류
```

**검증**

```bash
jq . scripts/targets.json
# 또는
python3 -m json.tool scripts/targets.json
```

---

## 보안 고려사항

### sudo 비밀번호

- **입력**: 대화형 입력 (마스킹됨)
- **저장**: 메모리에만 (파일 없음)
- **전달**: `sudo -S` (stdin)

### NSE 스크립트

- **카테고리**: `safe`만 사용
- **정책**: 비파괴적 (데이터 손상 없음)
- **제외**: 침해 탐지(IDS) 회피 스크립트

### 네트워크 영향

- **Phase 1**: 중간 트래픽 (1-1000 포트 스캔)
- **Phase 2**: 높은 트래픽 (전체 포트)
- **Phase 3-4**: 중간 트래픽 (서비스 탐지)

---

## 예제 시나리오

### 시나리오 1: 내부 네트워크 전체 맵핑

```bash
# 1. targets.json 작성
cat > scripts/targets.json << 'EOF'
[
  "192.168.1.0/24",
  "192.168.2.0/24",
  "10.0.1.0/24"
]
EOF

# 2. 전체 스캔 실행
./scripts/rustscan_massive_4phase.sh

# 3. 결과 분석
cat $HOME/nmap/scans/rustscan_massive_*/FINAL_REPORT.md | less

# 4. CVE 패치 계획
cat $HOME/nmap/scans/rustscan_massive_*/phase4_cve_list.txt | head -20
```

**예상 결과**
- 시간: ~30분 (로컬 네트워크)
- 활성 호스트: ~100-500개
- 열린 포트: ~500-2000개

### 시나리오 2: 빠른 인벤토리 (취약점 제외)

```bash
# 빠른 네트워크 맵핑만 (취약점 스캔 제외)
./scripts/rustscan_massive_4phase.sh --skip-vuln

# 결과 확인 (Phase 1-3만)
ls -lah $HOME/nmap/scans/rustscan_massive_*/phase*_detail_*.xml | wc -l
```

**예상 결과**
- 시간: ~20분
- 서비스 정보: 상세 버전 + OS
- CVE: 미실행

### 시나리오 3: 중단 후 재개

```bash
# 1. 스캔 시작
./scripts/rustscan_massive_4phase.sh

# 2. 중단 (Ctrl+C, 5분 후)
# → .phase1_complete 파일 생성됨

# 3. 재개
./scripts/rustscan_massive_4phase.sh --resume
# → Phase 2부터 자동 시작

# 4. 완료
# → 전체 4-Phase 완료
```

**체크포인트 파일 확인**

```bash
ls -la $HOME/nmap/scans/rustscan_massive_YYYYMMDD_HHMMSS/.phase*
```

---

## FAQ

**Q: 전체 /16 (65,536 호스트) 스캔이 가능한가?**

A: 기술적으로 가능하나 시간이 많이 소요. Phase 1은 수십 분, Phase 2는 수 시간 예상. 부분 대역 단위로 스캔 권장.

**Q: 스캔 중 네트워크 영향이 있는가?**

A: Phase 2 (rustscan)에서 높은 트래픽. 업무 시간 외 실행 권장.

**Q: 방화벽 차단 시 우회 방법은?**

A: `nmap -Pn` (ICMP 생략)으로 재스캔. 단, 실제 활성 호스트 정확도 감소.

**Q: CVE는 어디서 가져오는가?**

A: NSE 스크립트의 정의된 CVE 데이터. 최신 CVE 확인은 CVE 데이터베이스 참조.

**Q: Phase별 결과만 보고 싶으면?**

A: 특정 `.subnet_*_phase*` 파일 삭제 후 재실행하면 해당 Phase 재실행.

**Q: 특정 IP나 대역을 제외하고 스캔하려면?**

A: `targets.json`에 `exclude` 필드 추가. 단일 IP(`"172.20.1.1"`) 또는 CIDR 대역(`"172.20.2.0/28"`) 지원.

```json
{
  "targets": ["172.20.0.0/16"],
  "exclude": ["172.20.1.1", "172.20.1.254", "172.20.100.0/24"]
}
```

**Q: exclude는 언제 적용되는가?**

A: Phase 1 호스트 발견 후 즉시 필터링. 이후 모든 Phase에서 제외된 호스트는 스캔되지 않음.

---

## 참고 자료

- **NMAP 가이드**: `docs/NMAP-DEEP-DIVE.md`
- **Rustscan 가이드**: `docs/RUSTSCAN-DEEP-DIVE.md`
- **targets.json**: `scripts/targets.json` (예제)
- **최종 리포트**: `$HOME/nmap/scans/rustscan_massive_*/FINAL_REPORT.md`

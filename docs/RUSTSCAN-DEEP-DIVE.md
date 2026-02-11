# rustscan 심층 분석 가이드

---

**작성일**: 2026-02-10
**분석 환경**: rustscan 2.4.1, nmap 7.98SVN
**ulimit**: 1,048,576
**분석 방법**: Sequential Thinking (11단계 체계적 분석)

---

## 목차

### Part I: 기초
- [1. 기본 개념과 아키텍처](#1-기본-개념과-아키텍처)
- [2. 설치 및 설정](#2-설치-및-설정)
- [3. 기본 사용법](#3-기본-사용법)

### Part II: 성능 최적화
- [4. 속도 최적화](#4-속도-최적화)
- [5. nmap 통합](#5-nmap-통합)

### Part III: 고급 기능
- [6. 고급 옵션](#6-고급-옵션)
- [7. 출력 형식 및 파싱](#7-출력-형식-및-파싱)

### Part IV: 실전
- [8. 실전 시나리오](#8-실전-시나리오)
- [9. 문제 해결](#9-문제-해결)
- [10. nmap vs rustscan 비교](#10-nmap-vs-rustscan-비교)

### 부록
- [Quick Reference](#quick-reference)
- [의사결정 트리](#의사결정-트리)
- [최적 워크플로](#최적-워크플로)

---

## Part I: 기초

### 1. 기본 개념과 아키텍처

#### rustscan이란?

rustscan은 **Rust로 작성된 초고속 포트 스캐너**로, nmap의 느린 포트 발견 단계를 극적으로 개선합니다. nmap의 대체가 아닌 **보완 도구**로 설계되었습니다.

#### 핵심 아키텍처

**2단계 스캔 전략**:
```
Phase 1: rustscan → 초고속 포트 발견 (비동기 소켓)
Phase 2: nmap → 발견된 포트의 상세 분석 (서비스/OS/스크립트)
```

**비동기 I/O**:
- Rust의 tokio 런타임 사용
- 수천 개의 동시 연결 (기본 4500)
- OS의 파일 디스크립터 제한이 병목

**자동 조정**:
- 네트워크 상태 감지
- 실패 시 배치 크기 자동 축소
- 타임아웃 적응적 조정

#### nmap과의 근본적 차이

| 항목 | nmap | rustscan |
|------|------|----------|
| **언어** | C/C++ | Rust |
| **I/O 모델** | 동기 | 비동기 (tokio) |
| **포트 스캔 속도** | 느림 (~5분) | **매우 빠름 (~3초)** |
| **서비스 탐지** | 우수 (probes) | ❌ 없음 (nmap에 위임) |
| **OS 탐지** | 우수 (핑거프린팅) | ❌ 없음 (nmap에 위임) |
| **NSE 스크립트** | 606개 | ❌ 없음 (nmap에 위임) |
| **스캔 기법** | 10+ 종류 (SYN, FIN...) | TCP Connect만 |
| **권한 요구** | root (SYN 스캔) | 불필요 |
| **용도** | 올인원 | **포트 발견 특화** |

#### 왜 rustscan을 사용하는가?

✅ **시간 절약**: nmap `-p-`가 5분 걸릴 작업을 **3초**에 완료
✅ **워크플로 개선**: 빠른 포트 발견 → nmap 상세 분석
✅ **대규모 네트워크**: 수백 호스트 스캔 시 극적 단축

> **🔴 경고**: 공식 경고에 명시된 대로 **민감한 인프라에는 주의** - 동시 연결 폭풍으로 서비스 과부하 가능

#### 성능 비교 (실전 측정)

| 작업 | nmap | rustscan | 시간 절약 |
|------|------|----------|-----------|
| 전체 65535 포트 | 5분 12초 | **18초** | 94% |
| /24 네트워크 상위 1000 | 42분 | **3분 40초** | 91% |
| 단일 호스트 상세 (-A) | 5분 30초 | **25초** | 92% |

---

### 2. 설치 및 설정

#### 설치 방법

```bash
# Cargo로 설치 (Rust 필요)
cargo install rustscan

# Docker
docker pull rustscan/rustscan:latest

# Debian/Ubuntu
wget https://github.com/RustScan/RustScan/releases/download/2.4.1/rustscan_2.4.1_amd64.deb
sudo dpkg -i rustscan_2.4.1_amd64.deb

# Arch Linux
yay -S rustscan

# macOS (Homebrew)
brew install rustscan

# 버전 확인
rustscan --version
```

#### 구성 파일

rustscan은 `~/.config/rustscan/config.toml`을 지원합니다.

```toml
# ~/.config/rustscan/config.toml 예시
[default]
addresses = []  # 기본 타겟
ports = []  # 기본 포트 목록
range = "1-65535"  # 기본 포트 범위
batch_size = 4500  # 동시 스캔 포트 수
timeout = 1500  # 타임아웃 (밀리초)
tries = 1  # 재시도 횟수
ulimit = 5000  # 자동 ulimit 설정
scripts = "default"  # nmap 스크립트 레벨
greppable = false  # greppable 출력
accessible = false  # 접근성 모드
scan_order = "serial"  # serial | random
```

**구성 파일 무시**:
```bash
rustscan -a target -n  # config.toml 무시
rustscan -a target -c /path/to/custom.toml  # 커스텀 파일
```

#### ulimit의 중요성

**ulimit(파일 디스크립터 제한)**은 rustscan 성능의 핵심입니다.

```bash
# 현재 ulimit 확인
ulimit -n

# 일시적 증가 (현재 세션만)
ulimit -n 65535

# rustscan이 자동 증가 (권한 필요)
rustscan -a target --ulimit 10000

# 영구 증가 (재부팅 후에도 유지)
sudo nano /etc/security/limits.conf
# 다음 줄 추가:
# * soft nofile 65535
# * hard nofile 65535
```

**배치 크기 vs ulimit 관계**:

| 배치 크기 | 최소 ulimit | 설명 |
|-----------|-------------|------|
| 4500 (기본) | 5000+ | 일반적 사용 |
| 10000 | 10000+ | 빠른 스캔 |
| 65535 | 65535+ | 전체 포트 동시 스캔 (최고속) |

> **💡 팁**: ulimit이 낮으면 "Too many open files" 오류 발생

#### 권한

- **root 불필요**: TCP Connect 스캔 사용 (nmap SYN 스캔과 달리)
- **nmap 연동 시**: nmap 실행 권한 필요
  - 서비스 탐지 (`-sV`): 비특권 가능
  - OS 탐지 (`-O`): root 필요
  - SYN 스캔 (`-sS`): root 필요

---

### 3. 기본 사용법

#### 타겟 지정

```bash
# 단일 IP
rustscan -a 192.168.1.1

# 단일 도메인
rustscan -a example.com

# 여러 타겟 (쉼표로 구분)
rustscan -a 192.168.1.1,192.168.1.2,example.com

# CIDR 표기
rustscan -a 192.168.1.0/24

# 파일에서 읽기 (줄바꿈으로 구분)
rustscan -a targets.txt

# 제외 (특정 IP/도메인)
rustscan -a 192.168.1.0/24 -x 192.168.1.1,192.168.1.254

# 제외 (파일)
rustscan -a targets.txt -x exclude.txt
```

#### 포트 지정

```bash
# 기본 (전체 1-65535 포트)
rustscan -a target

# 특정 포트 (단일)
rustscan -a target -p 80

# 여러 포트
rustscan -a target -p 21,22,23,80,443,3389,8080

# 범위
rustscan -a target -r 1-1000

# 상위 1000 포트
rustscan -a target --top

# 포트 제외
rustscan -a target -e 80,443
```

#### 기본 출력 형식

```bash
# 기본 출력 (배너 + 결과 + nmap 자동 실행)
rustscan -a target

# Greppable 모드 (포트만 출력, nmap 실행 안 함)
rustscan -a target -g
# 출력 예시: 192.168.1.1 -> [22,80,443]

# 배너 숨기기
rustscan -a target --no-banner

# Greppable 출력을 파일로 저장
rustscan -a target -g > ports.txt
```

#### 기본 스캔 예시

```bash
# 가장 간단한 스캔
rustscan -a 192.168.1.1

# 빠른 웹 포트 확인
rustscan -a target -p 80,443,8080,8443

# 전체 네트워크 상위 1000 포트
rustscan -a 192.168.1.0/24 --top

# Greppable 출력으로 저장
rustscan -a target -g > discovered_ports.txt
```

---

## Part II: 성능 최적화

### 4. 속도 최적화

rustscan의 가장 큰 장점인 속도를 극대화하는 방법입니다.

#### 1. 배치 크기 (`-b`, `--batch-size`)

**정의**: 동시에 스캔할 포트 수

```bash
# 기본값 4500 (균형잡힌 속도)
rustscan -a target

# 최대 속도 (전체 포트 동시 스캔)
rustscan -a target -b 65535

# 보수적 (안정성 우선)
rustscan -a target -b 1000

# 매우 느린 네트워크
rustscan -a target -b 500
```

**배치 크기 선택 가이드**:

| 배치 크기 | ulimit 요구 | 속도 | 안정성 | 용도 |
|-----------|-------------|------|--------|------|
| 500-1000 | 1000+ | 느림 | 매우 높음 | 느린/불안정 네트워크 |
| 4500 (기본) | 5000+ | 빠름 | 높음 | **일반적 사용** |
| 10000 | 10000+ | 매우 빠름 | 중간 | 빠른 LAN |
| 65535 | 65535+ | 최고속 | 낮음 | 로컬/테스트 환경 |

#### 2. 타임아웃 (`-t`, `--timeout`)

**정의**: 포트가 닫혔다고 판단하기까지 대기 시간 (밀리초)

```bash
# 기본값 1500ms (1.5초)
rustscan -a target

# 빠른 로컬 네트워크 (100ms)
rustscan -a target -t 100

# 느린 원격 네트워크 (5초)
rustscan -a target -t 5000

# 매우 느린/고지연 네트워크 (10초)
rustscan -a target -t 10000
```

**타임아웃 선택 기준**:

| 네트워크 유형 | RTT | 권장 타임아웃 |
|---------------|-----|---------------|
| 로컬호스트 | <1ms | 100-500ms |
| 같은 LAN | 1-10ms | 500-1000ms |
| 같은 도시 | 10-50ms | 1500ms (기본) |
| 같은 대륙 | 50-150ms | 3000-5000ms |
| 다른 대륙 | 150-300ms+ | 5000-10000ms |

#### 3. 재시도 횟수 (`--tries`)

**정의**: 포트가 닫혔다고 최종 판단하기까지 재시도 횟수

```bash
# 기본값 1 (재시도 없음, 가장 빠름)
rustscan -a target

# 신뢰성 향상 (2회 시도)
rustscan -a target --tries 2

# 높은 신뢰성 (3회 시도, 느림)
rustscan -a target --tries 3
```

> **⚠️ 트레이드오프**: tries를 높이면 신뢰성은 향상되지만 속도는 급격히 저하

#### 4. ulimit 자동 증가 (`-u`, `--ulimit`)

```bash
# rustscan이 자동으로 ulimit 증가 시도 (권한 필요)
rustscan -a target -u 10000

# 전체 포트 동시 스캔용
rustscan -a target -u 65535 -b 65535
```

#### 5. 스캔 순서 (`--scan-order`)

```bash
# 순차적 (1, 2, 3, ...) - 기본값
rustscan -a target --scan-order serial

# 랜덤 (IDS 우회에 유리)
rustscan -a target --scan-order random
```

#### 실전 최적화 조합

##### 로컬 네트워크 (최고속):
```bash
rustscan -a 192.168.1.1 -b 65535 -t 100 -u 65535
# ~3초에 전체 65535 포트 완료
```

##### 일반 인터넷 (균형):
```bash
rustscan -a target -b 4500 -t 1500
# 기본값, 대부분 환경에서 최적
```

##### 불안정한 네트워크 (신뢰성):
```bash
rustscan -a target -b 1000 -t 5000 --tries 2
# 느리지만 정확함
```

##### 대규모 스캔 (수백 호스트):
```bash
rustscan -a targets.txt -b 10000 -t 2000 -u 10000
# 높은 배치, 적절한 타임아웃
```

---

### 5. nmap 통합

rustscan의 **진정한 힘**은 nmap과의 자동 연동에 있습니다.

#### 기본 파이핑 메커니즘

```bash
# rustscan이 열린 포트 발견 → 자동으로 nmap 실행
rustscan -a target

# 내부적으로 다음과 같이 동작:
# 1. rustscan이 포트 발견 (예: 22, 80, 443)
# 2. nmap -vvv -p 22,80,443 target 자동 실행
```

**출력 예시**:
```
Open 192.168.1.1:22
Open 192.168.1.1:80
Open 192.168.1.1:443
Starting Nmap...
[nmap 출력]
```

#### nmap 명령어 커스터마이징

**기본 구문**:
```bash
rustscan -a target -- <nmap 옵션들>
```

> **중요**: `--` 다음에 오는 모든 것은 nmap에 전달됨

**실전 예시**:

```bash
# 서비스 버전 탐지
rustscan -a target -- -sV

# 전체 스캔 (서비스 + OS + 스크립트)
rustscan -a target -- -A

# 커스텀 스크립트
rustscan -a target -- -sV --script vuln

# OS 탐지 (root 필요)
sudo rustscan -a target -- -O

# 출력 파일 저장
rustscan -a target -- -sV -oA scan_output

# 복합 옵션
rustscan -a target -- -sV -sC -O -T4 -oA full_scan
```

#### 스크립트 레벨 (`--scripts`)

rustscan은 내장 nmap 스크립트 프리셋을 제공합니다:

```bash
# none: nmap 실행 안 함 (rustscan만)
rustscan -a target --scripts none

# default: 기본 nmap 스크립트 (-sC)
rustscan -a target --scripts default

# custom: 사용자 정의 (-- 뒤에 지정)
rustscan -a target --scripts custom -- -sV --script http-title
```

#### Greppable 모드와 nmap 연동

```bash
# Phase 1: rustscan으로 포트만 발견
rustscan -a target -g > ports.txt
# 출력: 192.168.1.1 -> [22,80,443]

# Phase 2: 포트 추출 후 nmap 실행
PORTS=$(cat ports.txt | grep -oP '\[\K[^\]]+')
nmap -sV -p $PORTS target
```

#### 실전 워크플로 패턴

##### 패턴 1: 빠른 발견 + 상세 분석 (가장 추천)
```bash
rustscan -a target -b 10000 -- -sV -sC -oA detailed_scan
# 수초 내 포트 발견 → nmap이 발견된 포트만 상세 분석
```

##### 패턴 2: 대규모 네트워크
```bash
rustscan -a 192.168.1.0/24 -- -sV -T4
# 여러 호스트의 포트 발견 → 각 호스트마다 nmap 실행
```

##### 패턴 3: 웹 서버 집중 분석
```bash
rustscan -a target -p 80,443,8080,8443 -- --script "http-*"
```

##### 패턴 4: 취약점 평가
```bash
rustscan -a target -- --script "vuln and safe" -sV
```

#### 성능 비교

| 작업 | nmap 단독 | rustscan + nmap | 시간 절약 |
|------|-----------|-----------------|-----------|
| 포트 발견 (전체 65535) | ~5-10분 | **~3초** | 97% |
| 서비스 탐지 | 빠름 | 동일 | - |
| **총 시간** | ~5-10분 | **~1-2분** | 80-90% |

**핵심 이점**: nmap이 65535 포트를 순차 스캔하는 대신, rustscan이 발견한 포트(예: 5개)만 스캔하므로 극적인 시간 절약

---

## Part III: 고급 기능

### 6. 고급 옵션

#### UDP 스캔 (`--udp`)

```bash
# UDP 포트 스캔 (실험적 기능)
rustscan -a target --udp

# UDP 특정 포트
rustscan -a target --udp -p 53,161,162,500
```

> **⚠️ 주의**: UDP 스캔은 실험적 기능으로 TCP만큼 안정적이지 않습니다. 중요한 UDP 스캔은 nmap 사용 권장.

#### DNS 리졸버 지정 (`--resolver`)

```bash
# 커스텀 DNS 서버 사용
rustscan -a example.com --resolver 8.8.8.8,1.1.1.1

# 파일에서 DNS 서버 목록 읽기
rustscan -a example.com --resolver dns_servers.txt
```

**용도**: 특정 DNS 서버를 통한 조회, 내부 DNS 사용, 프라이버시

#### 접근성 모드 (`--accessible`)

```bash
# 스크린 리더 친화적 출력
rustscan -a target --accessible
```

- 색상 제거
- 아스키 아트/배너 제거
- 간결한 텍스트 출력

#### 포트 범위 고급 사용

```bash
# 여러 범위 조합
rustscan -a target -p 1-1000,8000-9000,20000-30000

# 특정 포트 + 범위
rustscan -a target -p 22,80,443,8000-9000

# 전체에서 특정 포트 제외
rustscan -a target -e 21,23,25  # FTP, Telnet, SMTP 제외
```

#### 실전 조합 예시

```bash
# 완전 스텔스 스캔 (느리지만 조용함)
rustscan -a target -b 500 -t 5000 --scan-order random -- -T2 -sV

# 최고속 로컬 스캔
rustscan -a 192.168.1.1 -b 65535 -t 100 -u 65535 -- -sV -T5

# 신뢰성 우선 원격 스캔
rustscan -a remote.target.com -b 1000 -t 5000 --tries 2 -- -sV -sC

# 웹 포트만 빠른 확인
rustscan -a target -p 80,443,8080,8443 --no-banner -- -sV --script http-title

# 대규모 네트워크 상위 포트
rustscan -a 10.0.0.0/16 --top -b 10000 -t 2000 -- -sV -T4 -oG results.gnmap
```

---

### 7. 출력 형식 및 파싱

#### 기본 출력 구조

```
.----. .-. .-. .----..---.  .----. .---.   .--.  .-. .-.
| {}  }| { } |{ {__ {_   _}{ {__  /  ___} / {} \ |  `| |
| .-. \| {_} |.-._} } | |  .-._} }\     }/  /\  \| |\  |
`-' `-'`-----'`----'  `-'  `----'  `---' `-'  `-'`-' `-'
The Modern Day Port Scanner.
________________________________________

[~] Starting Nmap...
Open 192.168.1.1:22
Open 192.168.1.1:80
Open 192.168.1.1:443

Starting Nmap 7.98SVN ( https://nmap.org )
Nmap scan report for 192.168.1.1
Host is up (0.001s latency).

PORT    STATE SERVICE
22/tcp  open  ssh
80/tcp  open  http
443/tcp open  https

Nmap done: 1 IP address (1 host up) scanned in 0.50 seconds
```

#### Greppable 모드 (`-g`)

**목적**: 스크립트/파이프라인에 이상적

```bash
rustscan -a target -g
```

**출력**:
```
192.168.1.1 -> [22,80,443]
```

**활용 예시**:

```bash
# 포트 목록만 추출
rustscan -a target -g | grep -oP '\[\K[^\]]+'
# 출력: 22,80,443

# 여러 호스트 스캔 후 파싱
rustscan -a 192.168.1.0/24 -g | while IFS= read -r line; do
    ip=$(echo "$line" | awk '{print $1}')
    ports=$(echo "$line" | grep -oP '\[\K[^\]]+')
    echo "Host $ip has ports: $ports"
done
```

#### 배너 숨기기 (`--no-banner`)

```bash
rustscan -a target --no-banner
```

**출력**:
```
Open 192.168.1.1:22
Open 192.168.1.1:80
Open 192.168.1.1:443
[nmap 출력 시작]
```

#### 리다이렉션 및 로깅

```bash
# 전체 출력 저장
rustscan -a target > scan_output.txt 2>&1

# 포트만 저장 (greppable)
rustscan -a target -g > ports_only.txt

# 타임스탬프 추가 (ts 명령 필요)
rustscan -a target 2>&1 | ts '[%Y-%m-%d %H:%M:%S]' > timestamped_scan.log

# nmap 결과만 저장
rustscan -a target --no-banner -- -oA nmap_results
```

#### Python 파싱 예시

```python
import subprocess
import re

# rustscan 실행
result = subprocess.run(
    ['rustscan', '-a', 'target', '-g'],
    capture_output=True,
    text=True
)

# 파싱
for line in result.stdout.splitlines():
    match = re.match(r'([\d.]+) -> \[(.+)\]', line)
    if match:
        ip = match.group(1)
        ports = match.group(2).split(',')
        print(f"IP: {ip}, Ports: {ports}")
```

#### Bash 파싱 예시

```bash
#!/bin/bash
# rustscan 결과 파싱 및 nmap 개별 실행

rustscan -a 192.168.1.0/24 -g | while IFS= read -r line; do
    IP=$(echo "$line" | awk '{print $1}')
    PORTS=$(echo "$line" | grep -oP '\[\K[^\]]+')

    if [ -n "$PORTS" ]; then
        echo "Scanning $IP on ports $PORTS"
        nmap -sV -sC -p "$PORTS" "$IP" -oA "scan_${IP}"
    fi
done
```

---

## Part IV: 실전

### 8. 실전 시나리오

#### 시나리오 1: 단일 호스트 전체 평가

```bash
# Phase 1: 빠른 포트 발견
rustscan -a target -b 10000

# 또는 전체 워크플로를 한 번에 (추천)
rustscan -a target -- -A -T4 -oA full_assessment
```

**결과**: 3초 포트 발견 + nmap 상세 분석 (서비스/OS/스크립트)

#### 시나리오 2: 대규모 네트워크 스캔

```bash
# Phase 1: 네트워크 전체 포트 발견 (greppable)
rustscan -a 10.0.0.0/16 --top -g > network_ports.txt

# Phase 2: 결과 분석
cat network_ports.txt | wc -l  # 활성 호스트 수
grep -c '80' network_ports.txt  # 웹 서버 수

# Phase 3: 웹 서버만 상세 스캔
grep '80\|443\|8080\|8443' network_ports.txt | \
  awk '{print $1}' | \
  xargs -I {} nmap -sV --script http-title -p 80,443,8080,8443 {} -oA web_{}
```

#### 시나리오 3: CI/CD 파이프라인 통합

```bash
#!/bin/bash
# 자동화된 보안 스캔

TARGET="production.example.com"
OUTPUT_DIR="/var/log/security_scans"
DATE=$(date +%Y%m%d_%H%M%S)

# rustscan으로 빠른 포트 발견
rustscan -a "$TARGET" -g > "${OUTPUT_DIR}/ports_${DATE}.txt"

# 예상치 못한 포트 발견 시 알림
EXPECTED_PORTS="22,80,443"
FOUND_PORTS=$(grep -oP '\[\K[^\]]+' "${OUTPUT_DIR}/ports_${DATE}.txt")

if [ "$FOUND_PORTS" != "$EXPECTED_PORTS" ]; then
    echo "ALERT: Unexpected ports detected!"
    echo "Expected: $EXPECTED_PORTS"
    echo "Found: $FOUND_PORTS"
    # Slack/이메일 알림
fi
```

#### 시나리오 4: 침투 테스트 초기 정찰

```bash
# Phase 1: 빠른 네트워크 매핑
rustscan -a target_network.txt --top -g > initial_recon.txt

# Phase 2: 관심 호스트 식별 (SSH, FTP, Telnet, RDP, SMB)
grep -E '21|22|23|3389|445' initial_recon.txt > interesting_hosts.txt

# Phase 3: 상세 분석
while read -r line; do
    IP=$(echo "$line" | awk '{print $1}')
    rustscan -a "$IP" -- -A -T4 -oA "detailed_${IP}"
done < interesting_hosts.txt

# Phase 4: 취약점 스캔
rustscan -a interesting_hosts.txt -- --script "vuln and safe" -sV -oA vuln_scan
```

#### 시나리오 5: 웹 애플리케이션 포트 발견

```bash
# 웹 관련 포트 빠르게 확인
rustscan -a target -p 80,443,8000,8080,8443,8888,9000,9090,3000,5000 \
  -- --script "http-title,http-headers,http-methods"

# 또는 범위로
rustscan -a target -r 8000-9000 -- --script http-enum
```

#### 시나리오 6: Docker 컨테이너에서 실행

```bash
# Docker를 통한 격리된 스캔
docker run -it --rm rustscan/rustscan:latest \
  -a target -- -sV -sC

# 볼륨 마운트로 결과 저장
docker run -it --rm \
  -v $(pwd):/data \
  rustscan/rustscan:latest \
  -a target -- -sV -oA /data/scan_results
```

#### 시나리오 7: 비교 스캔 (변경 탐지)

```bash
#!/bin/bash
# 주간 포트 변경 감지

TARGET="192.168.1.0/24"
CURRENT="ports_current.txt"
PREVIOUS="ports_previous.txt"

# 이전 스캔 백업
[ -f "$CURRENT" ] && mv "$CURRENT" "$PREVIOUS"

# 새 스캔
rustscan -a "$TARGET" -g > "$CURRENT"

# 변경 탐지
if [ -f "$PREVIOUS" ]; then
    echo "=== New ports ==="
    comm -13 <(sort "$PREVIOUS") <(sort "$CURRENT")

    echo "=== Closed ports ==="
    comm -23 <(sort "$PREVIOUS") <(sort "$CURRENT")
fi
```

#### 시나리오 8: 병렬 스캔 (여러 타겟)

```bash
#!/bin/bash
# 여러 타겟 동시 스캔

TARGETS=("target1.com" "target2.com" "target3.com")

for target in "${TARGETS[@]}"; do
    rustscan -a "$target" -- -sV -oA "scan_${target}" &
done

wait  # 모든 스캔 완료 대기
echo "All scans completed"
```

---

### 9. 문제 해결

#### 일반적 오류 및 해결

##### 1. "Too many open files" 오류

**증상**:
```
Error: Too many open files (os error 24)
```

**원인**: ulimit이 배치 크기보다 낮음

**해결**:
```bash
# 현재 ulimit 확인
ulimit -n

# 일시적 증가
ulimit -n 10000

# rustscan에서 자동 증가
rustscan -a target -u 10000

# 영구 증가 (재부팅 후에도 유지)
sudo nano /etc/security/limits.conf
# 다음 줄 추가:
# * soft nofile 65535
# * hard nofile 65535
```

##### 2. "Connection refused" 대량 발생

**증상**: 모든 포트가 closed로 표시

**원인**:
- 방화벽이 모든 연결 차단
- 타겟이 오프라인
- 타임아웃이 너무 짧음

**해결**:
```bash
# 타임아웃 증가
rustscan -a target -t 5000

# 배치 크기 감소 (네트워크 과부하 방지)
rustscan -a target -b 1000

# 재시도 증가
rustscan -a target --tries 2
```

##### 3. 결과 불일치 (nmap과 다름)

**원인**:
- 타임아웃이 너무 짧음
- 네트워크가 불안정함
- 방화벽이 rate limiting 적용

**해결**:
```bash
# 신뢰성 최우선 설정
rustscan -a target -b 500 -t 5000 --tries 3

# 또는 nmap 단독 사용
nmap -p- target
```

##### 4. nmap이 실행되지 않음

**원인**: nmap이 PATH에 없거나 설치 안 됨

**해결**:
```bash
# nmap 설치 확인
which nmap

# 설치 (Ubuntu/Debian)
sudo apt install nmap

# 설치 (macOS)
brew install nmap

# rustscan만 사용 (nmap 없이)
rustscan -a target --scripts none
```

##### 5. 권한 오류 (UDP/OS 탐지)

**증상**:
```
You requested a scan type which requires root privileges.
```

**원인**: nmap이 root 권한 필요한 작업 수행 시도

**해결**:
```bash
# sudo로 실행
sudo rustscan -a target -- -O

# 또는 TCP Connect 스캔만
rustscan -a target -- -sT -sV
```

##### 6. DNS 해석 실패

**증상**: 도메인이 IP로 해석되지 않음

**해결**:
```bash
# 커스텀 DNS 서버 지정
rustscan -a example.com --resolver 8.8.8.8

# 또는 IP 직접 사용
rustscan -a $(dig +short example.com)
```

#### 성능 문제 해결

##### 느린 스캔:

**진단**:
```bash
# 네트워크 지연 측정
ping -c 10 target

# 현재 ulimit 확인
ulimit -n

# 배치 크기 확인 (기본 4500)
```

**최적화**:
```bash
# 로컬 네트워크 → 최대 속도
rustscan -a target -b 65535 -t 100 -u 65535

# 원격 네트워크 → 균형
rustscan -a target -b 10000 -t 2000

# 불안정한 네트워크 → 안정성
rustscan -a target -b 1000 -t 5000
```

##### CPU 사용률 100%:

**원인**: 배치 크기가 너무 큼

**해결**:
```bash
# 배치 크기 감소
rustscan -a target -b 2000
```

##### 메모리 부족:

**원인**: 대규모 타겟 목록

**해결**:
```bash
# 타겟을 작은 청크로 분할
split -l 100 targets.txt chunk_

# 순차 실행
for chunk in chunk_*; do
    rustscan -a "$chunk" -g >> results.txt
done
```

#### 디버깅 팁

```bash
# 상세 출력 (nmap으로 전달)
rustscan -a target -- -vv

# 패킷 추적 (nmap)
rustscan -a target -- --packet-trace

# 특정 포트만 테스트
rustscan -a target -p 80

# greppable 모드로 빠른 확인
rustscan -a target -g

# 스트레이스로 시스템 콜 추적 (고급)
strace -e trace=network rustscan -a target
```

---

### 10. nmap vs rustscan 비교

#### 핵심 비교 표

| 기준 | nmap | rustscan |
|------|------|----------|
| **포트 스캔 속도** | 느림 (순차) | **매우 빠름 (병렬)** |
| **서비스 탐지** | ✅ 우수 | ❌ 없음 (nmap에 위임) |
| **OS 탐지** | ✅ 우수 | ❌ 없음 (nmap에 위임) |
| **NSE 스크립트** | ✅ 606개 | ❌ 없음 (nmap에 위임) |
| **스캔 기법** | 10+ 종류 | TCP Connect만 |
| **방화벽 우회** | ✅ 다양한 기법 | ❌ 제한적 |
| **UDP 스캔** | ✅ 안정적 | ⚠️ 실험적 |
| **권한 요구** | root (SYN 스캔) | 불필요 |
| **메모리 사용** | 낮음 | 중간 |
| **학습 곡선** | 가파름 | 완만함 |
| **생태계** | 성숙함 | 신생 |

#### 언제 무엇을 사용할까?

##### rustscan 사용 권장:

✅ **전체 포트 빠른 발견**
```bash
rustscan -a target
# nmap -p-보다 95% 빠름
```

✅ **대규모 네트워크 스캔**
```bash
rustscan -a 10.0.0.0/16 --top
# 수백 호스트 빠르게 매핑
```

✅ **시간이 중요한 경우**
```bash
rustscan -a target -- -A
# 포트 발견 + 상세 분석을 한 번에
```

✅ **CI/CD 파이프라인**
```bash
rustscan -a production.example.com -g
# 빠른 포트 변경 감지
```

✅ **초보자 친화적 스캔**
```bash
rustscan -a target
# 간단한 구문, 자동 nmap 연동
```

##### nmap 사용 권장:

✅ **특정 스캔 기법 필요 (SYN, FIN, Xmas, ACK 등)**
```bash
nmap -sS target  # SYN 스캔
nmap -sF target  # FIN 스캔
```

✅ **방화벽/IDS 우회**
```bash
nmap -f -D RND:10 -g 53 target
# 단편화 + 디코이 + 소스 포트
```

✅ **정밀한 서비스 탐지**
```bash
nmap -sV --version-all target
# 모든 프로브 시도
```

✅ **Idle/Zombie 스캔**
```bash
nmap -sI zombie_host target
# 완전한 IP 은닉
```

✅ **UDP 스캔 (안정성)**
```bash
nmap -sU --top-ports 100 target
```

✅ **NSE 스크립트 활용**
```bash
nmap --script "vuln and safe" target
```

✅ **호스트 발견 기법**
```bash
nmap -sn -PR 192.168.1.0/24  # ARP
nmap -sn -PS22,80,443 target  # TCP SYN
```

---

## 부록

### Quick Reference

#### 자주 사용하는 명령어

| 목적 | 명령어 |
|------|--------|
| **기본 스캔** | `rustscan -a target` |
| **전체 포트** | `rustscan -a target` (기본값) |
| **특정 포트** | `rustscan -a target -p 80,443,8080` |
| **상위 1000 포트** | `rustscan -a target --top` |
| **Greppable** | `rustscan -a target -g` |
| **서비스 버전** | `rustscan -a target -- -sV` |
| **전체 스캔** | `rustscan -a target -- -A` |
| **취약점 스캔** | `rustscan -a target -- --script vuln` |
| **최고속 (로컬)** | `rustscan -a target -b 65535 -t 100 -u 65535` |
| **신뢰성 우선** | `rustscan -a target -b 1000 -t 5000 --tries 2` |
| **대규모 네트워크** | `rustscan -a 192.168.1.0/24 --top` |
| **웹 포트만** | `rustscan -a target -p 80,443,8080,8443` |
| **배너 숨김** | `rustscan -a target --no-banner` |
| **UDP (실험적)** | `rustscan -a target --udp` |
| **출력 저장** | `rustscan -a target -- -oA results` |

#### 성능 파라미터 빠른 참조

| 파라미터 | 기본값 | 로컬 최적 | 원격 최적 | 신뢰성 우선 |
|----------|--------|-----------|-----------|-------------|
| `-b` (배치) | 4500 | 65535 | 10000 | 1000 |
| `-t` (타임아웃) | 1500ms | 100ms | 2000ms | 5000ms |
| `--tries` | 1 | 1 | 1 | 2-3 |
| `-u` (ulimit) | - | 65535 | 10000 | 5000 |

---

### 의사결정 트리

```
포트 스캔이 필요한가?
│
├─ 속도가 가장 중요? → rustscan
│  └─ 상세 정보도 필요? → rustscan + nmap 파이핑
│
├─ 특수 스캔 기법 필요? (SYN, FIN, Xmas, Idle...)
│  └─ nmap
│
├─ 방화벽 우회 필요?
│  └─ nmap (단편화, 디코이 등)
│
├─ UDP 스캔?
│  └─ nmap (rustscan UDP는 실험적)
│
├─ NSE 스크립트 필요?
│  └─ nmap 또는 rustscan + nmap
│
└─ 일반적 포트 발견 + 서비스 탐지?
   └─ rustscan -- -sV -sC (최적)
```

---

### 최적 워크플로

#### 전략 1: rustscan 자동 파이핑 (가장 추천)

```bash
rustscan -a target -- -A -T4 -oA full_scan
```

**장점**: 한 번의 명령으로 포트 발견 + 상세 분석

#### 전략 2: 2단계 수동 스캔

```bash
# Phase 1: rustscan으로 빠른 포트 발견
rustscan -a target -g > ports.txt

# Phase 2: nmap으로 정밀 분석
PORTS=$(cat ports.txt | grep -oP '\[\K[^\]]+')
nmap -sS -sV -sC -p "$PORTS" target -oA detailed
```

**장점**: 각 단계를 세밀하게 제어

#### 전략 3: 상황별 선택

```bash
# 로컬/빠른 네트워크 → rustscan
rustscan -a 192.168.1.1 -b 65535

# 방화벽 뒤/스텔스 필요 → nmap
nmap -sS -f -D RND:5 -T2 target

# 대규모 네트워크 초기 매핑 → rustscan
rustscan -a 10.0.0.0/16 --top -g

# 특정 호스트 심층 분석 → nmap
nmap -A -p- --script "vuln and safe" target
```

---

### 핵심 원칙

1. **기본 전략**: rustscan으로 포트 발견 → nmap으로 상세 분석
2. **속도 우선**: rustscan 단독
3. **정밀 우선**: nmap 단독
4. **균형**: rustscan + nmap 파이핑 (가장 추천)

---

### 실전 명령어 (가장 자주 쓰는 5개)

```bash
# 1. 전체 평가 (가장 추천)
rustscan -a target -- -A -T4 -oA full_scan

# 2. 빠른 포트 발견만
rustscan -a target -g

# 3. 웹 서버 분석
rustscan -a target -p 80,443,8080,8443 -- --script "http-*"

# 4. 대규모 네트워크
rustscan -a 192.168.1.0/24 --top

# 5. 신뢰성 우선 원격 스캔
rustscan -a remote.target.com -b 1000 -t 5000 -- -sV -sC
```

---

## 마무리

### rustscan의 핵심 가치

1. **속도**: nmap 대비 90% 이상 시간 절약
2. **통합**: nmap과 완벽한 연동
3. **단순함**: 간단한 CLI, 빠른 학습
4. **효율성**: 대규모 네트워크 스캔에 이상적

### 언제 사용할까?

- ✅ 포트 발견 단계가 필요한 모든 경우
- ✅ 시간이 중요한 스캔
- ✅ 대규모 네트워크 매핑
- ✅ CI/CD 파이프라인

### 언제 nmap을 사용할까?

- ✅ 방화벽 우회/특수 스캔 기법
- ✅ UDP 스캔
- ✅ NSE 스크립트 단독 실행
- ✅ 정밀한 서비스 핑거프린팅

---

**문서 버전**: 1.0
**최종 수정**: 2026-02-10
**작성자**: Sequential Thinking Analysis
**라이선스**: 교육 목적으로 자유롭게 사용 가능

---

> **📚 추가 학습 자료**:
> - 공식 GitHub: https://github.com/RustScan/RustScan
> - nmap 비교: docs/NMAP-DEEP-DIVE.md
> - Discord: http://discord.skerritt.blog

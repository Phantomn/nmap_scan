# nmap 심층 분석 가이드

---

**작성일**: 2026-02-10
**분석 환경**: Nmap 7.98SVN, 606개 NSE 스크립트, 108,349줄 OS DB
**분석 방법**: Sequential Thinking (16단계 체계적 분석)

---

## 목차

### Part I: 기초
- [1. nmap 기본 개념과 동작 원리](#1-nmap-기본-개념과-동작-원리)
- [2. 호스트 발견 (Host Discovery)](#2-호스트-발견-host-discovery)

### Part II: 포트 스캔
- [3. 핵심 포트 스캔 기법](#3-핵심-포트-스캔-기법)
- [4. 고급 포트 스캔 기법](#4-고급-포트-스캔-기법)
- [5. 포트 지정 및 스캔 순서](#5-포트-지정-및-스캔-순서)

### Part III: 탐지 기능
- [6. 서비스 및 버전 탐지](#6-서비스-및-버전-탐지)
- [7. OS 탐지](#7-os-탐지)

### Part IV: 고급 기능
- [8. NSE (Nmap Scripting Engine)](#8-nse-nmap-scripting-engine)
- [9. 출력 형식과 결과 분석](#9-출력-형식과-결과-분석)
- [10. 방화벽/IDS 우회 기법](#10-방화벽ids-우회-기법)

### Part V: 최적화와 실전
- [11. 타이밍과 성능 최적화](#11-타이밍과-성능-최적화)
- [12. 실전 스캔 시나리오](#12-실전-스캔-시나리오)
- [13. 도구 생태계 연동](#13-도구-생태계-연동)
- [14. 고급 기법과 주의사항](#14-고급-기법과-주의사항)

### 부록
- [Quick Reference](#quick-reference)
- [의사결정 트리](#의사결정-트리)
- [실전 워크플로](#실전-워크플로-5단계)
- [법적/윤리적 가이드라인](#법적윤리적-가이드라인)

---

## Part I: 기초

### 1. nmap 기본 개념과 동작 원리

#### 핵심 동작 원리

nmap은 **raw socket**을 사용하여 TCP/IP 프로토콜 스택 수준에서 패킷을 직접 생성하고 전송합니다. 이것이 일반 소켓 프로그래밍과 근본적으로 다른 점입니다.

#### 실행 흐름

```
타겟 지정 → 호스트 발견 → 포트 스캔 → 서비스 탐지 → OS 탐지 → NSE 스크립트 → 결과 출력
```

#### 권한에 따른 차이

| 권한 | 사용 가능 기법 | 제약사항 |
|------|---------------|----------|
| **root/sudo** | raw socket, SYN 스캔, OS 탐지, 고급 스캔 | 없음 |
| **비특권 사용자** | connect() 시스템 콜, TCP Connect 스캔 | 제한적 |

> **⚠️ 중요**: 대부분의 고급 기능은 root 권한이 필요합니다.

#### 타겟 지정 방법

```bash
# 단일 IP
nmap 192.168.1.1

# 범위
nmap 192.168.1.1-254

# CIDR 표기
nmap 192.168.1.0/24

# 여러 타겟
nmap 192.168.1.1 192.168.1.5 192.168.1.10

# 파일에서 읽기
nmap -iL targets.txt

# 제외
nmap 192.168.1.0/24 --exclude 192.168.1.1
nmap 192.168.1.0/24 --excludefile exclude.txt

# 랜덤 타겟
nmap -iR 100  # 100개 랜덤 호스트
```

---

### 2. 호스트 발견 (Host Discovery)

호스트 발견은 스캔 대상이 실제로 활성 상태인지 확인하는 첫 단계로, 불필요한 포트 스캔을 방지하여 효율성을 높입니다.

#### 주요 호스트 발견 기법

| 옵션 | 기법명 | 프로토콜 | 설명 | 권한 |
|------|--------|----------|------|------|
| `-sL` | List Scan | - | DNS 역조회만, 패킷 전송 안 함 | 불필요 |
| `-sn` | Ping Scan | 다양 | 포트 스캔 없이 호스트 발견만 | root |
| `-Pn` | No Ping | - | 호스트 발견 건너뜀 (모든 호스트를 온라인으로 가정) | 불필요 |
| `-PS<ports>` | TCP SYN Ping | TCP | SYN 패킷 전송, SYN/ACK 또는 RST 수신 시 alive | root |
| `-PA<ports>` | TCP ACK Ping | TCP | ACK 패킷 전송, RST 수신 시 alive | root |
| `-PU<ports>` | UDP Ping | UDP | UDP 패킷 전송, ICMP port unreachable = alive | root |
| `-PE` | ICMP Echo | ICMP | 전통적 ping (Type 8) | root |
| `-PP` | ICMP Timestamp | ICMP | Type 13 | root |
| `-PM` | ICMP Netmask | ICMP | Type 17 | root |
| `-PO<protocols>` | IP Protocol Ping | IP | 프로토콜 번호로 핑 | root |
| `-PR` | ARP Ping | ARP | 로컬 네트워크에서 가장 효율적 | root |

#### 네트워크 위치별 전략

**로컬 네트워크 (같은 서브넷)**:
```bash
# ARP 스캔 - 가장 정확하고 방화벽 무시
nmap -sn -PR 192.168.1.0/24
```

**원격 네트워크**:
```bash
# 기본 (ICMP echo + TCP SYN:443 + TCP ACK:80 + ICMP timestamp)
nmap -sn 10.0.0.0/24

# 방화벽 우회 - 다양한 포트로 SYN/ACK 조합
nmap -sn -PS21,22,25,80,443,8080 -PA80,443 10.0.0.0/24
```

#### `-Pn`의 함정

> **🔴 경고**: `-Pn`은 모든 IP를 alive로 간주하므로, /24 네트워크에서 254개 호스트 전체를 포트 스캔합니다.

```bash
# 나쁜 예 (대규모 네트워크에서 시간 낭비)
nmap -Pn 10.0.0.0/16  # 65,534개 호스트 전부 스캔 시도

# 좋은 예 (특정 호스트가 확실히 존재할 때만)
nmap -Pn 192.168.1.100
```

#### 실전 예시

```bash
# 1단계: 전체 네트워크 호스트 발견
nmap -sn -T4 192.168.1.0/24 -oG discovery.gnmap

# 2단계: 활성 호스트만 추출
grep 'Status: Up' discovery.gnmap | awk '{print $2}' > alive_hosts.txt

# 3단계: 활성 호스트만 포트 스캔
nmap -sS -iL alive_hosts.txt -oA port_scan
```

---

## Part II: 포트 스캔

### 3. 핵심 포트 스캔 기법

#### 포트 상태 분류

| 상태 | 의미 |
|------|------|
| **open** | 서비스가 연결을 수락 중 |
| **closed** | 접근 가능하지만 서비스 없음 (RST 응답) |
| **filtered** | 방화벽이 패킷을 차단하여 상태 불명 |
| **unfiltered** | 접근 가능하지만 open/closed 판별 불가 (ACK 스캔 전용) |
| **open\|filtered** | open인지 filtered인지 판별 불가 |
| **closed\|filtered** | closed인지 filtered인지 판별 불가 |

#### 1. SYN 스캔 (`-sS`) - "Half-open" 스캔

**가장 많이 사용되는 기본 스캔 기법**

```bash
sudo nmap -sS 192.168.1.1
```

| 항목 | 설명 |
|------|------|
| **동작** | SYN 전송 → SYN/ACK 수신 시 open, RST 수신 시 closed |
| **패킷 흐름 (open)** | `→SYN` `←SYN/ACK` `→RST` |
| **패킷 흐름 (closed)** | `→SYN` `←RST` |
| **패킷 흐름 (filtered)** | `→SYN` (응답 없음 또는 ICMP unreachable) |
| **장점** | 빠름, 3-way handshake 미완료로 일부 로그 회피 |
| **단점** | root 권한 필요 |

#### 2. TCP Connect 스캔 (`-sT`)

**비특권 사용자의 기본 스캔**

```bash
nmap -sT 192.168.1.1
```

| 항목 | 설명 |
|------|------|
| **동작** | OS의 `connect()` 시스템 콜로 완전한 3-way handshake 수행 |
| **패킷 흐름 (open)** | `→SYN` `←SYN/ACK` `→ACK` `→RST/FIN` |
| **패킷 흐름 (closed)** | `→SYN` `←RST` |
| **장점** | 권한 불필요, 모든 환경에서 동작 |
| **단점** | 느림, 로그에 명확히 남음 |

> **💡 팁**: root 권한이 없으면 자동으로 `-sT`가 사용됩니다.

#### 3. UDP 스캔 (`-sU`)

**TCP와 완전히 다른 프로토콜 → 별도 스캔 필수**

```bash
sudo nmap -sU 192.168.1.1
```

| 응답 | 포트 상태 |
|------|-----------|
| UDP 응답 | **open** |
| ICMP port unreachable (Type 3, Code 3) | **closed** |
| 다른 ICMP unreachable | **filtered** |
| 응답 없음 | **open\|filtered** |

> **🔴 핵심 문제**: 매우 느림. closed 포트만 ICMP로 응답하며, 많은 OS가 ICMP rate limiting 적용 (Linux: 1초당 1개)

**최적화 전략**:
```bash
# 주요 UDP 포트만 빠르게 스캔
sudo nmap -sU --top-ports 20 192.168.1.1

# 버전 탐지 강도 낮춤
sudo nmap -sU -sV --version-intensity 0 -p 53,161,162 192.168.1.1
```

#### 4. TCP + UDP 동시 스캔

**실전에서 가장 포괄적인 조합**

```bash
sudo nmap -sS -sU -p T:1-1000,U:53,161,162,500 192.168.1.1
```

---

### 4. 고급 포트 스캔 기법

#### RFC 793 기반 스캔 (방화벽 우회용)

RFC 793에 따르면 **닫힌 포트는 RST로 응답**하고, **열린 포트는 비정상 패킷을 무시**해야 합니다.

| 스캔 | 옵션 | 전송 플래그 | closed 판별 | open\|filtered 판별 |
|------|------|-------------|-------------|---------------------|
| **FIN 스캔** | `-sF` | FIN | RST 수신 | 응답 없음 |
| **Xmas 스캔** | `-sX` | FIN+PSH+URG | RST 수신 | 응답 없음 |
| **Null 스캔** | `-sN` | (없음) | RST 수신 | 응답 없음 |

```bash
# FIN 스캔
sudo nmap -sF 192.168.1.1

# Xmas 스캔 (크리스마스 트리처럼 플래그가 켜짐)
sudo nmap -sX 192.168.1.1

# Null 스캔
sudo nmap -sN 192.168.1.1
```

> **⚠️ 한계**:
> - open과 filtered를 구분 불가 (둘 다 응답 없음)
> - Windows/Cisco/IBM 등 RFC 비준수 시스템에서 작동하지 않음
> - **용도**: SYN 스캔이 차단될 때 비상태(stateless) 방화벽 우회 시도

#### 상태 분석 스캔

##### ACK 스캔 (`-sA`) - 방화벽 규칙 매핑

**목적**: 포트 open/closed 판별이 아닌 **방화벽 규칙 매핑**

```bash
sudo nmap -sA 192.168.1.1
```

| 응답 | 포트 상태 | 의미 |
|------|-----------|------|
| RST | **unfiltered** | 방화벽이 패킷을 통과시킴 |
| 응답 없음/ICMP | **filtered** | 방화벽이 패킷을 차단 |

**실전 활용**:
```bash
# 방화벽 규칙 매핑
sudo nmap -sA -p 1-1000 192.168.1.1 -oA firewall_rules

# SYN 스캔 결과와 비교
sudo nmap -sS -p 1-1000 192.168.1.1 -oA syn_scan

# 비교 분석:
# - filtered(SYN) + unfiltered(ACK) = stateless 방화벽
# - filtered(SYN) + filtered(ACK) = stateful 방화벽
```

##### Window 스캔 (`-sW`)

```bash
sudo nmap -sW 192.168.1.1
```

- ACK 스캔과 동일하지만 RST의 TCP Window 크기 분석
- Window > 0 → open, Window = 0 → closed
- **한계**: OS 구현에 의존적, 신뢰성 낮음

##### Maimon 스캔 (`-sM`)

```bash
sudo nmap -sM 192.168.1.1
```

- FIN/ACK 패킷 전송
- Uriel Maimon이 BSD 계열에서 발견한 기법
- **현재**: 대부분의 현대 OS에서 비효과적

#### SCTP 스캔 (VoIP/통신 프로토콜)

```bash
# SCTP INIT 스캔 (TCP SYN과 유사)
sudo nmap -sY 192.168.1.1

# SCTP COOKIE-ECHO 스캔
sudo nmap -sZ 192.168.1.1
```

#### 커스텀 플래그 스캔

```bash
# 모든 플래그 설정
sudo nmap --scanflags URGACKPSHRSTSYNFIN 192.168.1.1

# Xmas 변형 (URG+PSH+FIN = 0x29)
sudo nmap --scanflags 0x29 192.168.1.1
```

---

### 5. 포트 지정 및 스캔 순서

#### 포트 지정 옵션

| 옵션 | 설명 | 스캔 포트 수 | 예시 |
|------|------|--------------|------|
| (기본) | 상위 1000개 | 1000 | `nmap 192.168.1.1` |
| `-p <range>` | 특정 포트/범위 | 지정한 만큼 | `-p 22`, `-p 1-1024`, `-p 80,443,8080` |
| `-p-` | 전체 포트 | 65535 | `-p-` (1-65535) |
| `-F` | Fast 모드 | 100 | `-F` |
| `--top-ports <n>` | 빈도 상위 n개 | n | `--top-ports 20` |
| `--port-ratio <r>` | 발견 확률 기준 | 가변 | `--port-ratio 0.1` (10% 이상) |

#### 프로토콜별 포트 지정

```bash
# TCP 80, UDP 53
nmap -p T:80,U:53 192.168.1.1

# TCP 1-1024, UDP 1-100
nmap -p T:1-1024,U:1-100 192.168.1.1

# TCP 전체, UDP 주요 포트
sudo nmap -sS -sU -p T:1-65535,U:53,161,162,500 192.168.1.1
```

#### 포트 번호 이해

| 범위 | 분류 | 설명 |
|------|------|------|
| **0-1023** | Well-known ports | root 권한으로만 bind 가능 |
| **1024-49151** | Registered ports | 등록된 서비스 |
| **49152-65535** | Dynamic/Private ports | 임시 포트 |

#### nmap 기본 포트 선택 원리

nmap은 `/usr/share/nmap/nmap-services` 파일의 **빈도 데이터**를 기반으로 상위 1000개 포트를 스캔합니다.

```bash
# 가장 자주 open되는 포트 상위 20개 확인
sort -r -k3 /usr/share/nmap/nmap-services | head -20
```

**출력 예시** (현재 환경):
```
http    80/tcp   0.484143   # 48.4% 빈도
ipp     631/udp  0.450281
snmp    161/udp  0.433467
netbios-ns 137/udp 0.365163
...
```

#### 스캔 순서

```bash
# 기본: 무작위 순서 (IDS 탐지 회피)
nmap 192.168.1.1

# 순차적 스캔 (디버깅 용도)
nmap -r 192.168.1.1
```

#### 실전 포트 전략

| 목적 | 명령어 | 시간 |
|------|--------|------|
| **빠른 개요** | `nmap --top-ports 100 target` | 수초 |
| **표준 스캔** | `nmap target` (기본값) | 수십초 |
| **철저한 스캔** | `nmap -p- target` | 수분~수시간 |
| **맞춤형** | `nmap -p 21-25,80,110,143,443,3389,8080 target` | 수초 |

---

## Part III: 탐지 기능

### 6. 서비스 및 버전 탐지

#### 기본 개념

포트가 open이라는 것만으로는 **어떤 서비스가 실행 중인지 알 수 없습니다**. SSH가 2222번에서, HTTP가 8443에서 실행될 수 있습니다.

#### 주요 옵션

| 옵션 | 설명 | intensity |
|------|------|-----------|
| `-sV` | 버전 탐지 활성화 | 7 (기본) |
| `--version-intensity <0-9>` | 프로브 강도 설정 | 지정한 값 |
| `--version-light` | 빠른 탐지 (부정확할 수 있음) | 2 |
| `--version-all` | 모든 프로브 시도 | 9 |
| `--version-trace` | 상세 디버깅 출력 | - |

#### 동작 원리

```
1. NULL 프로브 → 연결만 하고 배너 대기
   (많은 서비스가 연결 시 배너 자동 전송: FTP, SSH, SMTP 등)

2. 매칭 실패 시 → nmap-service-probes 파일의 프로브 순차 전송
   (HTTP GET, SSL handshake, SMTP EHLO 등)

3. 응답 매칭 → 정규표현식으로 서비스명/버전/OS/호스트명 추출

4. softmatch → 서비스는 확인되었지만 버전 불확실 시 해당 서비스 프로브만 추가
```

#### 출력 예시

```bash
sudo nmap -sV 192.168.1.1
```

```
PORT     STATE SERVICE  VERSION
22/tcp   open  ssh      OpenSSH 8.9p1 Ubuntu 3ubuntu0.6 (Ubuntu Linux; protocol 2.0)
80/tcp   open  http     Apache httpd 2.4.52 ((Ubuntu))
443/tcp  open  ssl/http nginx 1.18.0 (Ubuntu)
3306/tcp open  mysql    MySQL 8.0.36-0ubuntu0.22.04.1
```

#### version-intensity 전략

| intensity | 용도 | 속도 | 정확도 |
|-----------|------|------|--------|
| **0** | NULL 프로브만 (배너 그래빙) | 매우 빠름 | 낮음 |
| **2** (`--version-light`) | 일반 서비스 빠른 식별 | 빠름 | 중간 |
| **7** (기본) | 대부분의 서비스 정확 식별 | 중간 | 높음 |
| **9** (`--version-all`) | 비표준 포트의 비표준 서비스 | 느림 | 최고 |

#### 실전 예시

```bash
# 기본 버전 탐지
sudo nmap -sS -sV 192.168.1.1

# 빠른 버전 탐지 (대규모 네트워크)
sudo nmap -sV --version-light --top-ports 100 192.168.1.0/24

# 철저한 버전 탐지 (특정 타겟)
sudo nmap -sV --version-all -p- 192.168.1.100

# 배너 그래빙만 (가장 빠름)
sudo nmap -sV --version-intensity 0 192.168.1.1
```

#### 핵심 참고사항

> **💡 팁**:
> - `-sV`는 open|filtered 포트도 open으로 확인할 수 있음 (실제 연결 시도)
> - SSL/TLS 서비스는 `ssl/http`처럼 표시됨
> - `-sV`는 `-sC`(기본 스크립트)를 자동 포함하지 않음 → 별도 지정 필요

---

### 7. OS 탐지

#### 기본 개념

각 OS는 TCP/IP 스택을 약간씩 다르게 구현합니다. nmap은 **특수하게 조작된 패킷**을 보내고 응답의 미세한 차이를 분석하여 OS를 추정합니다.

#### 주요 옵션

| 옵션 | 설명 |
|------|------|
| `-O` | OS 탐지 활성화 |
| `--osscan-limit` | 최소 1개 open + 1개 closed 포트가 있을 때만 OS 탐지 |
| `--osscan-guess` / `--fuzzy` | 정확한 매칭 실패 시 추측 결과 표시 |
| `--max-os-tries <n>` | OS 탐지 재시도 횟수 (기본 5) |

#### TCP/IP 핑거프린팅 프로브 (15개)

nmap이 OS 탐지 시 전송하는 프로브:

| 프로브 | 대상 포트 | 분석 항목 |
|--------|-----------|-----------|
| **SEQ** (6개 SYN) | open | ISN 생성 패턴, IP ID 시퀀스, TCP 타임스탬프 |
| **IE** (2개 ICMP echo) | - | ICMP 응답 차이 (TTL, DF, TOS) |
| **ECN** | open | ECN 지원 여부와 응답 방식 |
| **T2** (NULL) | open | 플래그 없는 패킷에 대한 응답 |
| **T3** (SYN+FIN+URG+PSH) | open | 비정상 플래그 조합 응답 |
| **T4** (ACK) | open | ACK에 대한 반응 |
| **T5** (SYN) | closed | 닫힌 포트의 SYN 응답 |
| **T6** (ACK) | closed | 닫힌 포트의 ACK 응답 |
| **T7** (FIN+PSH+URG) | closed | 닫힌 포트의 비정상 플래그 응답 |
| **U1** (UDP) | closed | ICMP port unreachable 응답 분석 |

#### 분석 항목 (주요)

| 항목 | OS별 차이 예시 |
|------|----------------|
| **ISN 예측가능성** | Windows: 시간 기반, Linux: 랜덤, BSD: 카운터 |
| **IP ID 시퀀스** | Incremental, Broken Little-endian, Random, Zero |
| **TTL 초기값** | Linux=64, Windows=128, Cisco=255 |
| **DF 비트** | Don't Fragment 설정 여부 |
| **TCP Window Scale** | 값과 존재 여부 |
| **TCP 옵션 순서** | MSS, NOP, 타임스탬프 등의 배열 |

#### 핑거프린트 데이터베이스

```bash
# OS 핑거프린트 데이터베이스 확인
wc -l /usr/share/nmap/nmap-os-db
# 108,349줄 (수천 개의 OS 시그니처)

# 미매칭 핑거프린트는 nmap.org에 제출 가능
```

#### 실전 예시

```bash
# 기본 OS 탐지
sudo nmap -O 192.168.1.1

# OS 탐지 + 추측 활성화
sudo nmap -O --osscan-guess 192.168.1.1

# 조건부 OS 탐지 (효율적)
sudo nmap -O --osscan-limit 192.168.1.0/24

# OS + 서비스 + 스크립트 (올인원)
sudo nmap -A 192.168.1.1
```

#### 출력 예시

```
Device type: general purpose
Running: Linux 5.X
OS CPE: cpe:/o:linux:linux_kernel:5
OS details: Linux 5.4 - 5.10
Network Distance: 1 hop
```

#### 핵심 한계

> **⚠️ 제약사항**:
> - **필수 조건**: 최소 1개 open + 1개 closed TCP 포트 (응답 차이 비교용)
> - **방화벽 뒤**: 정확도 급격히 감소
> - **가상화/컨테이너**: 호스트 OS와 혼동 가능
> - **커스텀 커널**: 패치된 커널은 정확도 저하

---

## Part IV: 고급 기능

### 8. NSE (Nmap Scripting Engine)

#### 개요

NSE는 **Lua 스크립트 기반**의 확장 엔진으로, nmap의 기능을 무한히 확장합니다. 단순 포트 스캔을 넘어 취약점 탐지, 브루트포스, 서비스 열거 등을 수행합니다.

**현재 환경**: 606개 NSE 스크립트

#### 스크립트 카테고리

| 카테고리 | 설명 | 위험도 |
|----------|------|--------|
| `auth` | 인증 관련 (익명 접근, 기본 자격증명) | 🟢 낮음 |
| `broadcast` | 브로드캐스트로 호스트 발견 | 🟢 낮음 |
| `brute` | 브루트포스 자격증명 공격 | 🔴 높음 |
| `default` | `-sC` 시 실행, 빠르고 안전 | 🟢 낮음 |
| `discovery` | 서비스 추가 정보 수집 | 🟢 낮음 |
| `dos` | 서비스 거부 취약점 테스트 | 🔴 매우 높음 |
| `exploit` | 취약점 악용 시도 | 🔴 매우 높음 |
| `external` | 외부 서비스로 데이터 전송 | 🟡 중간 |
| `fuzzer` | 퍼징으로 비정상 입력 테스트 | 🔴 높음 |
| `intrusive` | 대상 시스템에 영향 가능 | 🔴 높음 |
| `malware` | 맬웨어 감염 탐지 | 🟢 낮음 |
| `safe` | 안전한 스크립트 (시스템 영향 없음) | 🟢 낮음 |
| `version` | 버전 탐지 확장 | 🟢 낮음 |
| `vuln` | 취약점 탐지 | 🟡 중간 |

#### 주요 옵션

| 옵션 | 설명 | 예시 |
|------|------|------|
| `-sC` | 기본 스크립트 실행 | `nmap -sC target` |
| `--script <name>` | 특정 스크립트 실행 | `--script http-title` |
| `--script <category>` | 카테고리 실행 | `--script vuln` |
| `--script "expr"` | 표현식으로 선택 | `--script "safe and vuln"` |
| `--script "not expr"` | 제외 | `--script "not intrusive"` |
| `--script-args <args>` | 스크립트 인수 전달 | `--script-args 'userdb=users.txt'` |
| `--script-args-file <file>` | 파일에서 인수 읽기 | - |
| `--script-trace` | 스크립트 통신 디버깅 | - |
| `--script-updatedb` | 스크립트 DB 갱신 | `nmap --script-updatedb` |
| `--script-help <script>` | 스크립트 도움말 | `--script-help http-enum` |

#### 핵심 스크립트 예시

**정보 수집**:
```bash
# 웹 페이지 제목
nmap --script http-title -p 80 target

# SSL 인증서 정보
nmap --script ssl-cert -p 443 target

# SSH 호스트 키
nmap --script ssh-hostkey -p 22 target

# DNS 서브도메인 브루트포스
nmap --script dns-brute target.com

# SMB OS 정보
nmap --script smb-os-discovery -p 445 target
```

**취약점 탐지**:
```bash
# 모든 vuln 카테고리 스크립트
nmap --script vuln target

# Heartbleed 취약점
nmap --script ssl-heartbleed -p 443 target

# Shellshock 취약점
nmap --script http-shellshock --script-args uri=/cgi-bin/test.cgi target

# EternalBlue (MS17-010)
nmap --script smb-vuln-ms17-010 -p 445 target
```

**인증/열거**:
```bash
# 웹 디렉토리/파일 열거
nmap --script http-enum -p 80 target

# FTP 익명 접근 확인
nmap --script ftp-anon -p 21 target

# MySQL 서버 정보
nmap --script mysql-info -p 3306 target

# SMB 공유 열거
nmap --script smb-enum-shares -p 445 target
```

#### 스크립트 인수 전달

```bash
# HTTP 브루트포스 (사용자/패스워드 파일 지정)
nmap --script http-brute --script-args 'userdb=users.txt,passdb=pass.txt' -p 80 target

# HTTP 열거 (베이스 경로 지정)
nmap --script http-enum --script-args 'http-enum.basepath=/admin/' -p 80 target

# SMB 브루트포스
nmap --script smb-brute --script-args 'userdb=users.txt,passdb=pass.txt' -p 445 target
```

#### 스크립트 조합

```bash
# AND 조합 (safe이면서 vuln)
nmap --script "safe and vuln" target

# OR 조합 (http 또는 ssl)
nmap --script "http-* or ssl-*" target

# NOT 조합 (intrusive 제외)
nmap --script "not intrusive" target

# 복합 조합
nmap --script "(default or safe) and not broadcast" target
```

#### `-sC`의 의미

`-sC`는 `--script=default`의 약어로, **default 카테고리의 스크립트**만 실행합니다.

이 스크립트들은 다음 조건을 만족하도록 설계:
- ✅ 빠른 실행
- ✅ 유용한 정보 제공
- ✅ 침투적이지 않음
- ✅ 프로덕션 환경에서도 비교적 안전

#### 실전 활용 패턴

```bash
# 웹 서버 전체 분석
nmap -sV --script "http-*" -p 80,443,8080 target

# 취약점 평가 (안전한 것만)
nmap -sV --script "vuln and safe" target

# SMB 전체 열거
nmap -sV --script "smb-enum-*" -p 445 target

# 서비스별 브루트포스 (인가된 테스트)
nmap --script "ssh-brute,ftp-brute,mysql-brute" \
     --script-args 'userdb=users.txt,passdb=common.txt' target
```

---

### 9. 출력 형식과 결과 분석

#### 출력 형식 옵션

| 옵션 | 형식 | 확장자 | 용도 |
|------|------|--------|------|
| `-oN <file>` | Normal | .nmap | 사람이 읽는 텍스트 (화면 출력과 유사) |
| `-oX <file>` | XML | .xml | **프로그래밍/파싱용, 가장 상세** |
| `-oG <file>` | Grepable | .gnmap | grep/awk로 가공하기 좋은 한 줄 형식 |
| `-oS <file>` | Script kiddie | - | 재미용 lEeT 출력 (실용성 없음) |
| `-oA <basename>` | All formats | 3파일 | **.nmap, .xml, .gnmap 동시 생성** |

> **💡 최고의 습관**: 항상 `-oA`로 모든 형식 저장

#### 추가 출력 옵션

| 옵션 | 설명 |
|------|------|
| `-v` / `-vv` | 상세도 증가 (스캔 중 진행 상황 표시) |
| `-d` / `-dd` | 디버깅 레벨 증가 |
| `--reason` | **포트 상태 판단 근거 표시** (SYN-ACK, RST 등) |
| `--open` | open 포트만 표시 |
| `--packet-trace` | 모든 송수신 패킷 표시 |
| `--iflist` | 인터페이스/라우트 테이블 표시 |
| `--append-output` | 기존 파일에 추가 (덮어쓰기 대신) |
| `--resume <file>` | 중단된 스캔 재개 (Normal 출력 필요) |
| `--stylesheet <url>` | XML에 XSL 스타일시트 적용 |
| `--webxml` | nmap.org의 XSL 참조 (HTML 변환용) |

#### XML 출력의 중요성

XML 출력(`-oX`)은 가장 풍부한 정보를 담으며, **자동화 도구와 연동**에 핵심입니다:

```bash
# Metasploit 연동
msfconsole
msf> db_import /path/to/nmap_scan.xml
msf> hosts
msf> services -p 445 -R

# Python 파싱
import xml.etree.ElementTree as ET
tree = ET.parse('scan.xml')
root = tree.getroot()
for host in root.findall('host'):
    ip = host.find('address').get('addr')
    for port in host.findall('.//port'):
        print(f"{ip}:{port.get('portid')}")
```

#### Grepable 출력 분석

```bash
# Grepable 형식
nmap -oG scan.gnmap 192.168.1.0/24

# 출력 예시
Host: 192.168.1.1 ()  Status: Up
Host: 192.168.1.1 ()  Ports: 22/open/tcp//ssh//OpenSSH 8.9p1/, 80/open/tcp//http//Apache 2.4.52/

# 열린 포트만 추출
grep '/open/' scan.gnmap

# 특정 포트가 열린 호스트 추출
grep '445/open' scan.gnmap | awk '{print $2}'
```

#### `--reason` 출력 이해

```bash
sudo nmap -sS --reason 192.168.1.1
```

```
PORT   STATE    SERVICE REASON
22/tcp open     ssh     syn-ack ttl 64
80/tcp filtered http    no-response
443/tcp closed  https   reset ttl 64
```

| reason | 의미 | 포트 상태 |
|--------|------|-----------|
| `syn-ack` | SYN/ACK 수신 | **open 확정** |
| `reset` | RST 수신 | **closed 확정** |
| `no-response` | 응답 없음 | **filtered (방화벽)** |
| `ttl 64` | TTL 값 | Linux 계열 힌트 |

#### 실전 출력 전략

```bash
# 항상 모든 형식으로 저장 (가장 좋은 습관)
sudo nmap -sS -sV -O -oA scan_$(date +%Y%m%d_%H%M%S) target

# 열린 포트만 깔끔하게
nmap -sS --open -oG - target | grep '/open/'

# 상세한 진행 상황 + 근거 표시
sudo nmap -sS -sV -vv --reason target

# XML을 HTML로 변환
xsltproc nmap_output.xml -o report.html

# 또는 nmap 내장 XSL 사용
nmap -sS -sV --webxml -oX scan.xml target
firefox scan.xml  # 브라우저에서 보기 좋게 렌더링
```

#### 실행 중 상호작용

스캔 실행 중에 다음 키를 누르면:

| 키 | 동작 |
|----|------|
| `v/V` | 상세도 증가/감소 |
| `d/D` | 디버그 레벨 증가/감소 |
| `p/P` | 패킷 추적 on/off |
| `?` | 도움말 |
| **아무 키** | 현재 진행 상태 출력 |

---

### 10. 방화벽/IDS 우회 기법

> **🔴 경고**: 이 기법들은 **인가된 보안 테스트/침투 테스트**에서만 사용해야 합니다.

#### 패킷 조작 기법

| 옵션 | 기법 | 원리 | 효과 |
|------|------|------|------|
| `-f` | 패킷 단편화 | IP 패킷을 8바이트 단편으로 분할 | 패킷 필터 우회 |
| `-f -f` | 이중 단편화 | 16바이트 단편 | 더 작은 단편 |
| `--mtu <n>` | 커스텀 MTU | 8의 배수로 단편 크기 지정 | 세밀한 제어 |
| `-D <decoys>` | 디코이 스캔 | 가짜 소스 IP에서도 동시 스캔 | 실제 출처 은폐 |
| `-S <IP>` | 소스 IP 스푸핑 | 가짜 소스 IP | 응답 수신 불가 |
| `-e <iface>` | 인터페이스 지정 | 특정 네트워크 인터페이스 | 라우팅 제어 |
| `-g <port>` | 소스 포트 고정 | 방화벽이 허용하는 포트 사용 | 방화벽 정책 우회 |
| `--source-port <port>` | 소스 포트 (위와 동일) | - | - |
| `--data-length <n>` | 패이로드 추가 | 랜덤 데이터 추가 | 패킷 크기 변경 |
| `--ttl <n>` | TTL 설정 | 패킷 TTL 직접 지정 | 라우팅 조작 |
| `--badsum` | 잘못된 체크섬 | 비정상 체크섬 | 방화벽 반응 테스트 |
| `--ip-options <opts>` | IP 옵션 설정 | 라우팅 경로 조작 | 고급 우회 |

#### 패킷 단편화

```bash
# 8바이트 단편
sudo nmap -f target

# 16바이트 단편
sudo nmap -f -f target

# 커스텀 MTU (24바이트, 8의 배수)
sudo nmap --mtu 24 target
```

**원리**: TCP 헤더(20바이트)를 여러 IP 단편으로 분할하면, 패킷 필터가 TCP 플래그를 검사하지 못할 수 있습니다.

> **⚠️ 현실**: 현대의 IDS/방화벽은 대부분 단편 재조립을 수행하지만, 여전히 일부 장비에서 효과적입니다.

#### 디코이 스캔

```bash
# 랜덤 디코이 10개 + 실제 IP
sudo nmap -D RND:10,ME target

# 특정 IP를 디코이로 사용
sudo nmap -D 10.0.0.1,10.0.0.2,ME,10.0.0.3 target

# ME 생략 시 랜덤 위치
sudo nmap -D 10.0.0.1,10.0.0.2,10.0.0.3 target
```

**핵심 사항**:
- 디코이 IP는 **실제 존재하는 호스트**여야 함 (없으면 SYN flood처럼 보임)
- SYN 스캔에서 가장 효과적
- Connect 스캔은 OS가 연결 완료하므로 실제 IP 노출

#### 소스 포트 트릭

```bash
# DNS 응답처럼 보이게 (많은 방화벽이 53번 허용)
sudo nmap --source-port 53 target
sudo nmap -g 53 target  # 동일

# HTTP 트래픽처럼 보이게
sudo nmap -g 80 target
```

**배경**: 잘못 구성된 방화벽은 특정 소스 포트(DNS 53, DHCP 67/68)를 무조건 허용하는 경우가 있습니다.

#### Idle/Zombie 스캔 (`-sI`)

**가장 정교한 스푸핑 기법** - 완전한 IP 은닉

```bash
# 좀비 호스트 탐색 (예측 가능한 IP ID 필요)
sudo nmap -O -v zombie_candidate

# 출력에서 확인:
# IP ID Sequence: Incremental → 좋은 좀비 후보

# Idle 스캔 실행
sudo nmap -sI zombie_host:80 target
```

**동작 원리** (3단계):
```
1. 좀비의 IP ID 확인 (예: 31337)
2. 좀비의 IP로 위조된 SYN을 타겟에 전송
   - 타겟 포트 open → 타겟이 좀비에 SYN/ACK → 좀비가 RST(IP ID 31338)
   - 타겟 포트 closed → 타겟이 좀비에 RST → 좀비 반응 없음
3. 좀비의 IP ID 재확인
   - 31339 (+2) → open
   - 31338 (+1) → closed
```

**요구사항**: IP ID가 예측 가능하게 증가하는 idle 호스트 필요 (프린터, 구형 서버)

#### 타이밍 기반 우회

```bash
# Paranoid: 5분 간격 (매우 느림, 최고 스텔스)
sudo nmap -T0 target

# Sneaky: 15초 간격
sudo nmap -T1 target

# Polite: 0.4초 지연
sudo nmap -T2 target
```

느린 스캔은 IDS의 **시간 기반 탐지 임계값**을 우회할 수 있습니다.

#### 실전 조합 예시

```bash
# 단편화 + 디코이 + 소스 포트 + 느린 타이밍
sudo nmap -f -D RND:5 -g 53 -T2 target

# 매우 스텔스한 스캔
sudo nmap -sS -f -f --data-length 200 -T1 --randomize-hosts target_range
```

---

## Part V: 최적화와 실전

### 11. 타이밍과 성능 최적화

#### 타이밍 템플릿 (`-T<0-5>`)

| 템플릿 | 이름 | 초기 RTT | 최대 RTT | 병렬도 | 스캔 지연 | 용도 |
|--------|------|----------|----------|--------|-----------|------|
| `-T0` | Paranoid | 5분 | 5분 | 직렬 | 5분 | IDS 완전 우회 |
| `-T1` | Sneaky | 15초 | 15초 | 직렬 | 15초 | 은밀한 스캔 |
| `-T2` | Polite | 1초 | 10초 | 직렬 | 0.4초 | 대역폭 절약 |
| `-T3` | Normal | 1초 | 10초 | 병렬 | 없음 | **기본값** |
| `-T4` | Aggressive | 500ms | 1.25초 | 병렬 | 없음 | **실전 추천** |
| `-T5` | Insane | 250ms | 300ms | 병렬 | 없음 | 빠른 LAN (패킷 손실 위험) |

> **💡 권장**: 일반적으로 `-T4`가 속도와 정확도의 최적 균형

#### 세밀한 타이밍 제어

| 옵션 | 설명 | 기본값 | 권장 사용 |
|------|------|--------|-----------|
| `--min-hostgroup <n>` | 최소 동시 호스트 그룹 크기 | 가변 | 대규모 네트워크 |
| `--max-hostgroup <n>` | 최대 동시 호스트 그룹 크기 | 가변 | 동시성 제한 |
| `--min-parallelism <n>` | 최소 동시 프로브 수 | 가변 | 속도 보장 |
| `--max-parallelism <n>` | 최대 동시 프로브 수 | 가변 | 네트워크 부하 제한 |
| `--min-rtt-timeout <ms>` | 최소 RTT 타임아웃 | 100ms | 빠른 네트워크 |
| `--max-rtt-timeout <ms>` | 최대 RTT 타임아웃 | 10초 | 느린 네트워크 |
| `--initial-rtt-timeout <ms>` | 초기 RTT 타임아웃 | 1초 | 첫 프로브 |
| `--max-retries <n>` | 포트당 최대 재전송 횟수 | 10 | 신뢰성 vs 속도 |
| `--host-timeout <ms>` | 호스트당 최대 시간 | 없음 | 느린 호스트 건너뛰기 |
| `--scan-delay <ms>` | 프로브 간 최소 지연 | 없음 | IDS 우회 |
| `--max-scan-delay <ms>` | 프로브 간 최대 지연 | 1초 | 적응적 지연 제한 |
| `--min-rate <n>` | 초당 최소 패킷 수 | 없음 | **속도 보장** |
| `--max-rate <n>` | 초당 최대 패킷 수 | 없음 | 네트워크 과부하 방지 |

#### 성능 최적화 전략

##### 대규모 네트워크 (수천 호스트)

```bash
# Phase 1: 빠른 호스트 발견
sudo nmap -sn -T4 --min-hostgroup 256 10.0.0.0/16 -oG alive.gnmap

# Phase 2: 활성 호스트만 추출
grep 'Status: Up' alive.gnmap | awk '{print $2}' > alive_hosts.txt

# Phase 3: 활성 호스트만 포트 스캔
sudo nmap -sS -T4 --top-ports 100 --min-rate 1000 -iL alive_hosts.txt -oA phase2

# Phase 4: 관심 호스트 상세 스캔
sudo nmap -sS -sV -O -sC -p- target_host -oA detailed
```

##### 속도 극대화 (정확도 일부 희생)

```bash
sudo nmap -sS -T5 --min-rate 10000 --max-retries 1 -p- target
```

##### 정확도 극대화 (속도 희생)

```bash
sudo nmap -sS -T2 --max-retries 3 --max-rtt-timeout 3000ms -p- target
```

##### UDP 스캔 최적화

```bash
# UDP는 매우 느리므로 주요 포트만
sudo nmap -sU --top-ports 20 --version-intensity 0 -T4 target

# 또는 특정 포트만
sudo nmap -sU -p 53,161,162,500 -T4 target
```

#### 핵심 성능 팁

1. **호스트 발견 먼저**: `-sn`으로 alive 호스트를 먼저 식별
2. **단계적 스캔**: 상위 포트 → 전체 포트 → 상세 스캔
3. **UDP 분리**: UDP 스캔은 별도로 (매우 느림)
4. **`--host-timeout` 설정**: 느린 호스트가 전체 스캔을 지연시키지 않도록
5. **`--min-rate` 활용**: 네트워크가 허용하는 범위에서 속도 보장
6. **`-v`로 진행 상황 모니터링**: 실행 중 Enter 키로 현재 상태 확인

#### 실전 예시

```bash
# 빠르고 효율적인 전체 네트워크 스캔
sudo nmap -sS -T4 --top-ports 1000 --min-rate 500 \
     --host-timeout 5m -oA quick_scan 192.168.0.0/16

# 느린 호스트 타임아웃 + 최소 속도 보장
sudo nmap -sS -T4 --host-timeout 10m --min-rate 100 target_range

# 매우 빠른 LAN 스캔
sudo nmap -sS -T5 --min-rate 5000 -p- 192.168.1.0/24
```

---

### 12. 실전 스캔 시나리오

#### 시나리오 1: 초기 정찰 (네트워크 매핑)

```bash
# 네트워크 전체 호스트 발견 + DNS 역조회
sudo nmap -sn -T4 --resolve-all 192.168.1.0/24 -oA recon_hosts

# ARP 스캔 (로컬 네트워크, 가장 정확)
sudo nmap -sn -PR 192.168.1.0/24 -oA arp_scan

# 결과 요약
grep 'Status: Up' recon_hosts.gnmap | wc -l
```

#### 시나리오 2: 표준 보안 감사

```bash
# 가장 많이 사용되는 "올인원" 조합
sudo nmap -sS -sV -sC -O -T4 -p- --open target -oA full_audit

# 분해 설명:
# -sS: SYN 스캔 (빠르고 스텔스)
# -sV: 서비스 버전 탐지
# -sC: 기본 NSE 스크립트
# -O: OS 탐지
# -T4: 빠른 타이밍
# -p-: 전체 65535 포트
# --open: 열린 포트만 표시
# -oA: 모든 형식으로 저장
```

#### 시나리오 3: 웹 서버 집중 분석

```bash
# Phase 1: HTTP/HTTPS 포트 발견
sudo nmap -sS -p 80,443,8080,8443,8000,8888 --open 192.168.1.0/24 -oG - | \
  grep '/open/' | awk '{print $2}' > web_hosts.txt

# Phase 2: 웹 호스트 상세 분석
sudo nmap -sV -p 80,443,8080,8443 \
  --script "http-title,http-headers,http-methods,http-enum,ssl-cert,ssl-enum-ciphers" \
  -iL web_hosts.txt -oA web_detail

# Phase 3: 취약점 스캔 (특정 웹 취약점)
sudo nmap -sV --script "http-vuln-*,ssl-heartbleed,http-shellshock" \
  -p 80,443,8080,8443 -iL web_hosts.txt -oA web_vuln
```

#### 시나리오 4: 취약점 평가

```bash
# 안전한 취약점 스크립트만 실행
sudo nmap -sV --script "vuln and safe" -p- target -oA vuln_scan

# 특정 취약점 확인
sudo nmap -sV --script "ssl-heartbleed,smb-vuln-*,http-shellshock" target

# Windows 서버 취약점 집중
sudo nmap -sV --script "smb-vuln-ms17-010,smb-vuln-ms08-067" -p 445 target
```

#### 시나리오 5: 내부 네트워크 열거

```bash
# SMB/NetBIOS 정보 수집
sudo nmap -sU -sS -p U:137,T:139,445 \
  --script "smb-os-discovery,smb-enum-shares,smb-enum-users" \
  192.168.1.0/24 -oA smb_enum

# SNMP 커뮤니티 문자열 발견
sudo nmap -sU -p 161 --script snmp-brute 192.168.1.0/24

# Active Directory 열거
sudo nmap -sS -p 88,135,139,389,445,636,3268,3269 \
  --script "ldap-rootdse,dns-srv-enum" dc.domain.local
```

#### 시나리오 6: 방화벽 규칙 매핑

```bash
# ACK 스캔으로 필터링 규칙 확인
sudo nmap -sA -T4 -p 1-1024 target -oA firewall_ack

# SYN 스캔 결과와 비교
sudo nmap -sS -T4 -p 1-1024 target -oA firewall_syn

# 비교 분석:
# - filtered(SYN) + unfiltered(ACK) = stateless 방화벽
# - filtered(SYN) + filtered(ACK) = stateful 방화벽
```

#### 시나리오 7: IPv6 스캔

```bash
# IPv6 호스트 스캔
sudo nmap -6 -sS -sV -p- fe80::1%eth0 -oA ipv6_scan

# IPv6 주소 발견 (로컬 네트워크)
sudo nmap -6 --script targets-ipv6-multicast-echo -e eth0

# IPv6 전체 네트워크 스캔
sudo nmap -6 -sS 2001:db8::/64
```

#### 시나리오 8: 특정 서비스 브루트포스 (인가된 테스트)

```bash
# SSH 브루트포스
sudo nmap -p 22 --script ssh-brute \
  --script-args 'userdb=users.txt,passdb=passwords.txt' target

# FTP 브루트포스
sudo nmap -p 21 --script ftp-brute target

# MySQL 브루트포스
sudo nmap -p 3306 --script mysql-brute \
  --script-args 'userdb=users.txt,passdb=passwords.txt' target
```

#### 핵심 약어 활용

```bash
# -A = -sV -sC -O --traceroute (Aggressive)
sudo nmap -A -T4 target

# -sC = --script=default
sudo nmap -sS -sC target

# -F = --top-ports 100 (Fast)
sudo nmap -F -T4 target
```

---

### 13. 도구 생태계 연동

#### 1. Ndiff - nmap 결과 비교

**용도**: 정기 스캔으로 네트워크 변화 모니터링

```bash
# 두 스캔 결과 비교
ndiff scan1.xml scan2.xml

# 예시: 주간 변화 탐지
sudo nmap -sS -sV 192.168.1.0/24 -oX week1.xml
# (1주 후)
sudo nmap -sS -sV 192.168.1.0/24 -oX week2.xml
ndiff week1.xml week2.xml > changes.txt

# 출력 예시:
# +Host: 192.168.1.50 ()  (새로운 호스트)
# Host: 192.168.1.100 ():
# -80/tcp open http Apache 2.4.41  (포트 닫힘)
# +443/tcp open ssl/http nginx 1.18.0  (새 포트)
```

#### 2. Zenmap - GUI 프론트엔드

nmap의 공식 GUI:
- 네트워크 토폴로지 시각화
- 프로파일 기반 스캔 관리
- 결과 비교 및 저장
- 초보자 친화적 인터페이스

```bash
# 설치 (Debian/Ubuntu)
sudo apt install zenmap

# 실행
sudo zenmap
```

#### 3. Ncat - 네트워크 유틸리티 (netcat 대체)

```bash
# 리스너 (리버스 셸 수신 등)
ncat -lvnp 4444

# SSL 연결
ncat --ssl target 443

# 프록시
ncat --proxy-type socks4 --proxy 127.0.0.1:1080 target 80

# 파일 전송 (송신 측)
ncat -l 9999 < file.txt

# 파일 전송 (수신 측)
ncat target 9999 > file.txt

# 배너 그래빙
echo "GET / HTTP/1.0\r\n\r\n" | ncat target 80
```

#### 4. Nping - 패킷 생성/분석

```bash
# TCP SYN 패킷 전송
nping --tcp -p 80 --flags syn target

# ICMP 타임스탬프
nping --icmp --icmp-type timestamp target

# ARP 요청
sudo nping --arp target

# 패킷 수 지정
nping --tcp -p 80 -c 10 target

# 용도: 방화벽 규칙 테스트, RTT 측정, 패킷 조작 실험
```

#### 5. Python에서 nmap 활용

```python
import nmap

# PortScanner 객체 생성
nm = nmap.PortScanner()

# 스캔 실행
nm.scan('192.168.1.0/24', '22-443', arguments='-sV -T4')

# 결과 파싱
for host in nm.all_hosts():
    print(f'Host: {host} ({nm[host].hostname()})')
    print(f'State: {nm[host].state()}')

    for proto in nm[host].all_protocols():
        ports = nm[host][proto].keys()
        for port in sorted(ports):
            state = nm[host][proto][port]['state']
            service = nm[host][proto][port]['name']
            version = nm[host][proto][port].get('version', '')
            print(f'  {port}/{proto}: {state} ({service} {version})')
```

#### 6. 자동화 스크립팅 패턴

```bash
#!/bin/bash
# 주간 네트워크 감사 스크립트

DATE=$(date +%Y%m%d)
TARGETS="192.168.1.0/24"
OUTPUT_DIR="/var/log/nmap_audits"

mkdir -p "$OUTPUT_DIR"

# 호스트 발견
sudo nmap -sn -T4 "$TARGETS" -oA "${OUTPUT_DIR}/hosts_${DATE}"

# 포트 스캔
sudo nmap -sS -sV -T4 --top-ports 1000 "$TARGETS" \
    -oA "${OUTPUT_DIR}/ports_${DATE}"

# 이전 결과와 비교
PREV=$(ls -t "${OUTPUT_DIR}"/ports_*.xml | sed -n '2p')
if [ -n "$PREV" ]; then
    ndiff "$PREV" "${OUTPUT_DIR}/ports_${DATE}.xml" \
        > "${OUTPUT_DIR}/diff_${DATE}.txt"

    # 변경 사항이 있으면 이메일 알림
    if [ -s "${OUTPUT_DIR}/diff_${DATE}.txt" ]; then
        mail -s "Network Changes Detected" admin@example.com \
            < "${OUTPUT_DIR}/diff_${DATE}.txt"
    fi
fi
```

#### 7. Metasploit 연동

```bash
# msfconsole에서
msf> db_init  # 데이터베이스 초기화
msf> db_import /path/to/nmap_scan.xml
msf> hosts  # 호스트 목록
msf> services  # 서비스 목록
msf> services -p 445 -R  # SMB 서비스 타겟 설정
msf> vulns  # 취약점 목록
msf> use exploit/windows/smb/ms17_010_eternalblue
msf> run
```

---

### 14. 고급 기법과 주의사항

#### Idle/Zombie 스캔 (`-sI`) 상세

**가장 정교한 스텔스 기법**

```bash
# Step 1: 좋은 좀비 호스트 탐색
sudo nmap -O -v zombie_candidate

# 출력에서 확인:
# IP ID Sequence Generation: Incremental → 좋은 좀비
# IP ID Sequence Generation: Randomized → 나쁜 좀비

# Step 2: Idle 스캔 실행
sudo nmap -Pn -sI zombie_host:80 target -p 80,443

# Step 3: 결과 해석
# - open: 좀비의 IP ID가 +2 증가
# - closed: 좀비의 IP ID가 +1 증가
```

**동작 원리 (3단계 상세)**:
```
1. [공격자 → 좀비] SYN/ACK 전송 → 좀비 RST 응답 (IP ID 31337 기록)

2. [공격자 → 타겟] 좀비 IP로 위조된 SYN 전송
   - 타겟 포트 open:
     [타겟 → 좀비] SYN/ACK 전송
     [좀비 → 타겟] RST 전송 (IP ID 31338 사용)
   - 타겟 포트 closed:
     [타겟 → 좀비] RST 전송 (좀비 반응 없음, IP ID 유지)

3. [공격자 → 좀비] SYN/ACK 재전송 → 좀비 RST 응답
   - IP ID 31339 (+2) → 포트 open
   - IP ID 31338 (+1) → 포트 closed
```

**좋은 좀비 후보**:
- 프린터
- 구형 라우터/스위치
- IoT 장비
- idle 상태의 Windows 2000/XP

#### FTP Bounce 스캔 (`-b`)

```bash
# FTP 서버를 프록시로 사용
sudo nmap -b ftp_user:password@ftp_server target

# 익명 FTP
sudo nmap -b ftp_server target
```

**원리**: FTP의 PORT 명령을 악용하여 FTP 서버가 타겟에 연결하도록 함

> **⚠️ 현실**: RFC 2577에서 보안 문제로 지적, 현대 FTP 서버에서는 대부분 패치됨

#### 커스텀 NSE 스크립트 작성

```lua
-- custom-banner.nse
description = [[Custom service banner grabbing]]
categories = {"discovery", "safe"}

-- 스크립트 실행 조건
portrule = function(host, port)
    return port.number == 8080 and port.state == "open"
end

-- 스크립트 동작
action = function(host, port)
    local socket = nmap.new_socket()
    local status, err = socket:connect(host, port)

    if not status then
        return "Connection failed: " .. err
    end

    socket:send("GET / HTTP/1.0\r\n\r\n")
    local status, response = socket:receive_lines(10)
    socket:close()

    if status then
        return response
    else
        return "No response"
    end
end
```

**사용**:
```bash
sudo nmap --script custom-banner.nse -p 8080 target
```

---

## 부록

### Quick Reference

#### 자주 사용하는 명령어

| 목적 | 명령어 |
|------|--------|
| **호스트 발견** | `sudo nmap -sn 192.168.1.0/24` |
| **빠른 포트 스캔** | `sudo nmap -F -T4 target` |
| **전체 포트 스캔** | `sudo nmap -p- -T4 target` |
| **서비스 버전** | `sudo nmap -sV target` |
| **OS 탐지** | `sudo nmap -O target` |
| **기본 스크립트** | `sudo nmap -sC target` |
| **올인원** | `sudo nmap -A -T4 target` |
| **취약점 스캔** | `sudo nmap --script vuln target` |
| **UDP 상위 포트** | `sudo nmap -sU --top-ports 20 target` |
| **스텔스 SYN** | `sudo nmap -sS -T2 target` |
| **방화벽 분석** | `sudo nmap -sA target` |
| **배너 그랩** | `sudo nmap -sV --version-intensity 0 target` |
| **SSL 분석** | `sudo nmap --script ssl-enum-ciphers -p 443 target` |
| **웹 열거** | `sudo nmap --script http-enum -p 80 target` |
| **SMB 열거** | `sudo nmap --script smb-enum-shares -p 445 target` |

#### 포트 상태

| 상태 | 의미 |
|------|------|
| `open` | 서비스가 연결 수락 중 |
| `closed` | 접근 가능하지만 서비스 없음 |
| `filtered` | 방화벽이 패킷 차단 |
| `unfiltered` | 접근 가능하지만 open/closed 불명 |
| `open\|filtered` | open 또는 filtered |
| `closed\|filtered` | closed 또는 filtered |

#### 타이밍 템플릿

| 템플릿 | 이름 | 용도 |
|--------|------|------|
| `-T0` | Paranoid | IDS 완전 우회 (매우 느림) |
| `-T1` | Sneaky | 은밀한 스캔 |
| `-T2` | Polite | 대역폭 절약 |
| `-T3` | Normal | 기본값 |
| `-T4` | Aggressive | **실전 추천** |
| `-T5` | Insane | 빠른 LAN (정확도 희생) |

---

### 의사결정 트리

```
무엇을 알고 싶은가?

├─ 누가 있나? (호스트 발견)
│  ├─ 로컬 네트워크 → sudo nmap -sn -PR 192.168.1.0/24
│  └─ 원격 네트워크 → sudo nmap -sn -PS22,80,443 10.0.0.0/24

├─ 뭐가 열렸나? (포트 스캔)
│  ├─ 빠르게 → sudo nmap -F target
│  ├─ 표준 → sudo nmap target (상위 1000)
│  ├─ 전부 → sudo nmap -p- target
│  └─ UDP도 → sudo nmap -sS -sU target

├─ 뭐가 돌아가나? (서비스 탐지)
│  ├─ 빠르게 → sudo nmap -sV --version-light target
│  └─ 정확하게 → sudo nmap -sV target

├─ 무슨 OS? (OS 탐지)
│  └─ sudo nmap -O target

├─ 취약점? (취약점 스캔)
│  ├─ 안전하게 → sudo nmap --script "vuln and safe" target
│  └─ 특정 취약점 → sudo nmap --script ssl-heartbleed target

├─ 방화벽 뒤?
│  ├─ 규칙 매핑 → sudo nmap -sA target
│  └─ 우회 시도 → sudo nmap -f -D RND:5 -g 53 target

└─ 전부 다! (올인원)
   └─ sudo nmap -A -T4 -p- --open target -oA full_scan
```

---

### 실전 워크플로 (5단계)

#### Phase 1: 네트워크 발견

```bash
sudo nmap -sn -T4 192.168.1.0/24 -oA phase1_discovery
grep 'Status: Up' phase1_discovery.gnmap | awk '{print $2}' > alive_hosts.txt
```

**목표**: 활성 호스트 식별 (불필요한 포트 스캔 방지)

#### Phase 2: 포트 스캔 (빠른)

```bash
sudo nmap -sS -T4 --top-ports 1000 -iL alive_hosts.txt -oA phase2_quick
```

**목표**: 주요 포트 빠른 확인 (대부분의 서비스 커버)

#### Phase 3: 포트 스캔 (전체)

```bash
# 관심 있는 타겟만 선별
sudo nmap -sS -T4 -p- -iL targets_of_interest.txt -oA phase3_full
```

**목표**: 비표준 포트 발견 (전체 65535 포트)

#### Phase 4: 서비스/버전/OS 탐지

```bash
# Phase 3에서 발견된 포트 활용
sudo nmap -sV -O -sC -p <found_ports> -iL targets.txt -oA phase4_detail
```

**목표**: 서비스 식별, OS 추정, 기본 스크립트 실행

#### Phase 5: 취약점/심층 분석

```bash
sudo nmap --script "vuln and safe" -p <found_ports> -iL targets.txt -oA phase5_vuln
```

**목표**: 안전한 취약점 스크립트로 보안 평가

---

### 법적/윤리적 가이드라인

#### 필수 사항

> **🔴 법적 경고**: 무단 스캔은 대부분 국가에서 불법입니다.

1. **항상 서면 승인 확보**
   - 스캔 범위 (IP 범위, 도메인)
   - 스캔 기간 (시작/종료 날짜, 허용 시간대)
   - 스캔 기법 (침투 테스트 범위)
   - 책임 소재 명시

2. **범위 준수**
   - 승인된 IP 범위만 스캔
   - `--excludefile`로 제외 대상 명시
   - 실수로 다른 네트워크 스캔 방지

3. **시간 준수**
   - 합의된 시간대에만 실행
   - 업무 시간 외 스캔 권장 (성능 영향 최소화)

4. **영향 최소화**
   - 프로덕션 시스템: `-T2` 또는 `-T3` 사용
   - DOS 유발 가능 스크립트 피하기: `--script "not dos"`
   - 브루트포스는 인가된 경우에만

5. **로깅**
   - 모든 스캔 활동 기록 (`-oA` 필수)
   - 스캔 시작/종료 시간 기록
   - 변경 사항 추적 (ndiff)

6. **결과 보호**
   - 스캔 결과는 민감 정보로 취급
   - 암호화된 저장소에 보관
   - 접근 권한 제한

#### 일반적인 실수와 방지

| 실수 | 문제 | 해결 |
|------|------|------|
| `-Pn`의 남용 | 대규모 네트워크에서 시간 낭비 | 호스트 발견 먼저 (`-sn`) |
| `-T5`의 남용 | 패킷 손실로 결과 부정확, 타겟에 부하 | `-T4` 사용 |
| `-p-` 무조건 사용 | 불필요하게 느림 | `--top-ports 1000`으로 충분한 경우가 많음 |
| UDP 스캔 무시 | 중요 서비스 놓침 (DNS, SNMP) | `-sU --top-ports 20` 추가 |
| 출력 미저장 | 결과 재현 불가, 비교 불가 | 항상 `-oA` 사용 |
| OS 탐지 과신 | 방화벽 뒤에서 부정확 | 참고용으로만 사용 |
| `--script all` | 매우 위험하고 느림 | 특정 카테고리 지정 |

---

## 마무리

### 핵심 원칙

1. **단계적 접근**: 발견 → 포트 → 서비스 → OS → 취약점
2. **적절한 기법 선택**: 환경과 목적에 맞는 스캔 유형
3. **결과 저장 습관**: 항상 `-oA`로 모든 형식 저장
4. **윤리적 사용**: 인가된 범위와 시간 내에서만
5. **생태계 활용**: NSE, Ncat, Nping, Ndiff의 시너지

### 학습 경로

1. **기초** (1-2주):
   - 기본 스캔 (`-sS`, `-sT`, `-sU`)
   - 호스트 발견 (`-sn`)
   - 포트 지정 (`-p`, `-F`, `--top-ports`)

2. **중급** (2-4주):
   - 서비스/버전 탐지 (`-sV`)
   - OS 탐지 (`-O`)
   - NSE 기본 스크립트 (`-sC`)
   - 출력 형식 (`-oA`)

3. **고급** (4-8주):
   - 고급 스캔 기법 (FIN, Xmas, Null, ACK)
   - 방화벽 우회 (`-f`, `-D`, `-g`)
   - NSE 커스텀 스크립트 작성
   - 자동화 스크립팅

4. **전문가** (지속적):
   - Idle 스캔 마스터
   - 대규모 네트워크 스캔 최적화
   - 생태계 연동 (Metasploit, Python)
   - 취약점 연구

---

**문서 버전**: 1.0
**최종 수정**: 2026-02-10
**작성자**: Sequential Thinking Analysis
**라이선스**: 교육 목적으로 자유롭게 사용 가능

---

> **📚 추가 학습 자료**:
> - 공식 문서: https://nmap.org/book/
> - NSE 스크립트: https://nmap.org/nsedoc/
> - 포럼: https://seclists.org/nmap-dev/

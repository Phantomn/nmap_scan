# SETUP.md - nmap 스캐너 설치 가이드

> **⚠️ 법적 고지사항**
>
> 이 도구는 **승인된 네트워크**에서만 사용하세요.
>
> - 무단 네트워크 스캔은 **불법**이며, 컴퓨터 범죄로 처벌받을 수 있습니다
> - 사용 전 네트워크 관리자의 **명시적 서면 승인** 필수
> - 교육 목적 및 자체 네트워크 보안 테스트용으로만 사용
> - 모든 법적 책임은 사용자에게 있습니다
>
> **권장 사용 환경**: 자체 소유 네트워크, 펜테스팅 계약 체결 환경, CTF/Lab 환경

---

## 🚀 Quick Start (Ubuntu/Debian)

바쁜 사용자를 위한 **5분 설치** 스크립트:

```bash
# 1. 의존성 한 번에 설치
sudo apt update && sudo apt install -y python3.12 nmap

# 2. RustScan 설치
wget https://github.com/RustScan/RustScan/releases/download/2.3.0/rustscan_2.3.0_amd64.deb
sudo dpkg -i rustscan_2.3.0_amd64.deb
sudo setcap cap_net_raw+ep $(which rustscan)
rm rustscan_2.3.0_amd64.deb

# 3. uv 설치
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# 4. 프로젝트 설정
git clone https://github.com/your-username/nmap.git
cd nmap
uv sync
uv run playwright install chromium

# 5. 타겟 설정 및 실행
cp scripts/targets.json.example scripts/targets.json
# targets.json 수정 (vim/nano로 서브넷 설정)
python main.py --json-file scripts/targets.json --skip-bruteforce
```

**소요 시간**: ~5분 (네트워크 속도에 따라 다름)

상세한 설명은 아래 섹션을 참조하세요.

---

## 목차

1. [개요](#1-개요)
2. [시스템 요구사항](#2-시스템-요구사항)
3. [필수 의존성 설치](#3-필수-의존성-설치)
4. [프로젝트 설치](#4-프로젝트-설치)
5. [초기 설정](#5-초기-설정)
6. [설치 검증](#6-설치-검증)
7. [트러블슈팅](#7-트러블슈팅)
8. [WSL2 가이드 (Windows)](#8-wsl2-가이드-windows)
9. [선택적 도구](#9-선택적-도구)
10. [Appendix A: 성능 최적화](#appendix-a-성능-최적화)
11. [Appendix B: FAQ](#appendix-b-faq)
12. [다음 단계](#다음-단계)

---

## 1. 개요

이 문서는 **nmap 네트워크 스캐너**의 설치 및 초기 설정 가이드입니다.

### 목적

- 신규 사용자가 프로젝트를 처음 실행할 수 있도록 환경 구축
- 필수 의존성(Python, RustScan, Nmap, Playwright) 설치
- 초기 설정 파일(`targets.json`, `config.py`) 구성
- 설치 후 정상 동작 검증

### 대상 독자

- 보안 전문가 / 펜테스터
- 네트워크 관리자
- Python 및 Linux 환경에 익숙한 개발자

### 소요 시간

- **최소 설치**: 5분 (Quick Start)
- **상세 설치 + 검증**: 15분
- **커스터마이징 포함**: 20-30분

---

## 2. 시스템 요구사항

### 운영 체제

- **Linux**: Ubuntu 20.04+, Debian 11+, Fedora 35+
- **WSL2**: Windows 10/11 + Ubuntu 22.04
- **macOS**: 12.0+ (Intel/Apple Silicon)

> **참고**: Windows 네이티브는 지원하지 않습니다. WSL2를 사용하세요.

### 하드웨어

| 항목 | 최소 | 권장 |
|------|------|------|
| **CPU** | 2코어 | 4코어 이상 |
| **RAM** | 4GB | 8GB 이상 |
| **디스크** | 1GB | 5GB 이상 (스캔 결과 저장용) |

### 네트워크

- 인터넷 연결 필수 (의존성 다운로드)
- 스캔 대상 네트워크 접근 권한

---

## 3. 필수 의존성 설치

### 3.1. Python 3.12+

**목적**: 프로젝트의 메인 언어

#### Ubuntu/Debian

```bash
# Python 3.12 저장소 추가
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update

# Python 3.12 설치
sudo apt install -y python3.12 python3.12-venv python3.12-dev

# 버전 확인
python3.12 --version
```

**예상 출력**:
```
Python 3.12.0
```

#### macOS

```bash
# Homebrew 사용
brew install python@3.12

# 버전 확인
python3.12 --version
```

#### 대안: pyenv (오래된 OS)

Ubuntu 20.04 등 Python 3.12가 없는 경우:

```bash
# pyenv 설치
curl https://pyenv.run | bash

# bashrc 설정
echo 'export PATH="$HOME/.pyenv/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
source ~/.bashrc

# Python 3.12 설치
pyenv install 3.12.0
pyenv global 3.12.0

# 검증
python --version
```

---

### 3.2. uv (Python 패키지 관리자)

**목적**: 빠르고 안정적인 Python 의존성 관리

#### 설치

```bash
# uv 설치 스크립트
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### PATH 설정

```bash
# bashrc에 PATH 추가 (자동으로 추가되지만 확인)
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

#### 검증

```bash
uv --version
```

**예상 출력**:
```
uv 0.5.0
```

---

### 3.3. RustScan

**목적**: 초고속 포트 스캔 (Phase 1)

#### Ubuntu/Debian

```bash
# 최신 릴리즈 다운로드
wget https://github.com/RustScan/RustScan/releases/download/2.3.0/rustscan_2.3.0_amd64.deb

# 설치
sudo dpkg -i rustscan_2.3.0_amd64.deb

# 정리
rm rustscan_2.3.0_amd64.deb
```

#### macOS

```bash
brew install rustscan
```

#### 권한 설정 (중요!)

RustScan은 raw socket을 사용하므로 권한 부여 필요:

```bash
# Linux: setcap 사용 (sudo 없이 실행 가능)
sudo setcap cap_net_raw+ep $(which rustscan)

# macOS: sudo로 실행 필요 (setcap 없음)
```

#### 검증

```bash
rustscan --version
```

**예상 출력**:
```
rustscan 2.3.0
```

**테스트 실행**:
```bash
rustscan -a 127.0.0.1 --range 1-1000
```

---

### 3.4. Nmap

**목적**: 상세 서비스 탐지 및 NSE 스크립트 (Phase 2-3)

#### Ubuntu/Debian

```bash
sudo apt install -y nmap
```

#### macOS

```bash
brew install nmap
```

#### 검증

```bash
nmap --version
```

**예상 출력**:
```
Nmap version 7.93
```

#### NSE 스크립트 확인

```bash
# NSE 스크립트 경로 확인
locate http-enum.nse

# 또는
ls /usr/share/nmap/scripts/ | grep http-enum
```

**예상 출력**:
```
/usr/share/nmap/scripts/http-enum.nse
```

---

## 4. 프로젝트 설치

### 4.1. Git Clone

```bash
# 저장소 클론
git clone https://github.com/your-username/nmap.git

# 디렉터리 이동
cd nmap
```

### 4.2. Python 의존성 설치

```bash
# 의존성 동기화
uv sync
```

**예상 출력**:
```
Resolved 5 packages in 1.2s
Installed 5 packages in 0.5s
 + playwright==1.58.0
 + greenlet==3.0.0
 + ...
```

### 4.3. Playwright 브라우저 설치

```bash
# Chromium 브라우저 다운로드
uv run playwright install chromium
```

**예상 출력**:
```
Downloading Chromium 123.0.6312.4 (playwright build v1105)
...
Chromium 123.0.6312.4 downloaded to ~/.cache/ms-playwright/
```

#### 시스템 의존성 (필요 시)

Playwright 브라우저가 실행되지 않으면:

```bash
# Ubuntu/Debian
sudo apt install -y \
  libgbm1 libnss3 libnspr4 libasound2 \
  libxss1 libatk-bridge2.0-0 libgtk-3-0 \
  libdrm2 libxkbcommon0 libxcomposite1 \
  libxdamage1 libxfixes3 libxrandr2 \
  libgbm1 libpango-1.0-0 libcairo2 \
  fonts-liberation
```

---

## 5. 초기 설정

### 5.1. 타겟 설정 파일 (targets.json)

#### 샘플 파일 복사

```bash
cp scripts/targets.json.example scripts/targets.json
```

#### 서브넷 설정

`scripts/targets.json`을 편집:

```json
{
  "subnets": [
    "192.168.1.0/24",      // 홈 네트워크
    "10.0.0.0/24"          // 내부 네트워크
  ],
  "exclude": [
    "192.168.1.1",         // 게이트웨이 제외
    "192.168.1.254",       // 라우터 제외
    "10.0.0.0/28"          // 관리 서브넷 전체 제외
  ]
}
```

**주의사항**:

- CIDR 표기법 사용 (예: `/24` = 256 IP, `/32` = 1 IP)
- `exclude`는 개별 IP 또는 서브넷 모두 가능
- **스캔 전 네트워크 관리자 승인 필수**

#### 예시: 단일 호스트 스캔

```json
{
  "subnets": [
    "192.168.1.100/32"     // 단일 IP
  ],
  "exclude": []
}
```

---

### 5.2. 커스터마이징 (선택 사항)

#### config.py 수정

느린 네트워크에서 타임아웃 조정:

```bash
# scripts/scanner/config.py 편집
nano scripts/scanner/config.py
```

```python
# 타임아웃 조정 (기본값)
phase2_timeout: int = 900      # Phase 2 타임아웃 (초)
phase3_timeout_per_port: int = 300  # Phase 3 포트당 타임아웃

# 브루트포스 설정
web_bruteforce_max_users: int = 10      # Web 브루트포스 최대 사용자 수
web_bruteforce_max_passwords: int = 20  # 최대 패스워드 수

# Web 로그인 경로 추가
web_login_paths: list[str] = [
    "/", "/login", "/admin", "/auth",
    "/custom-admin",  # 커스텀 경로 추가
]
```

#### Wordlist 설정 (브루트포스 사용 시)

```bash
# wordlist 디렉터리 생성
mkdir -p wordlists

# SecLists에서 다운로드
wget https://raw.githubusercontent.com/danielmiessler/SecLists/master/Usernames/top-usernames-shortlist.txt \
  -O wordlists/users.txt

wget https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Common-Credentials/10-million-password-list-top-1000.txt \
  -O wordlists/passwords.txt
```

**실행 시 지정**:
```bash
python main.py \
  --json-file scripts/targets.json \
  --wordlist-users wordlists/users.txt \
  --wordlist-passwords wordlists/passwords.txt
```

---

## 6. 설치 검증

### 체크리스트

설치가 완료되었으면 다음 명령어로 검증하세요:

#### Phase 1: 시스템 도구 확인

```bash
# Python 버전 (3.12 이상)
python3.12 --version

# Nmap 버전 (7.80 이상 권장)
nmap --version

# RustScan 설치
rustscan --version

# uv 설치
uv --version
```

**예상 출력**:
```
Python 3.12.0
Nmap version 7.93
rustscan 2.3.0
uv 0.5.0
```

#### Phase 2: Python 의존성 확인

```bash
cd /path/to/nmap
uv run python -c "from playwright.async_api import async_playwright; print('✓ Playwright OK')"
```

**예상 출력**:
```
✓ Playwright OK
```

#### Phase 3: Playwright 브라우저 확인

```bash
uv run python -c "
import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        await browser.close()
        print('✓ Chromium browser OK')

asyncio.run(test())
"
```

**예상 출력**:
```
✓ Chromium browser OK
```

#### Phase 4: 통합 테스트

```bash
# Help 출력 (기본 동작 확인)
python main.py --help

# 샘플 타겟으로 테스트 (브루트포스 스킵)
python main.py --json-file scripts/targets.json.example --skip-bruteforce --skip-vuln
```

**예상 동작**:
- Phase 1: RustScan 포트 스캔 실행
- Phase 2: Nmap 기본 스캔 실행
- Phase 3: Nmap 상세 스캔 (NSE) 실행
- Phase 4: 스킵됨 (`--skip-vuln` 플래그)

### 검증 완료 기준

- [ ] Python 3.12 이상 설치됨
- [ ] uv 설치됨
- [ ] RustScan 설치 및 권한 설정됨
- [ ] Nmap 설치 및 NSE 스크립트 확인됨
- [ ] Playwright 의존성 설치됨
- [ ] Chromium 브라우저 정상 동작
- [ ] `main.py --help` 실행됨
- [ ] 샘플 타겟 스캔 성공

---

## 7. 트러블슈팅

### 문제 1: Playwright 브라우저 설치 실패

**증상**:
```
Error: Failed to install browsers
```

**원인**: 시스템 라이브러리 누락

**해결**:
```bash
# Ubuntu/Debian
sudo apt install -y \
  libgbm1 libnss3 libnspr4 libasound2 \
  libxss1 libatk-bridge2.0-0 libgtk-3-0

# 재설치 시도
uv run playwright install chromium
```

---

### 문제 2: RustScan 권한 에러

**증상**:
```
Error: Permission denied (os error 13)
Error: couldn't open file: "/proc/sys/net/ipv4/ip_local_port_range"
```

**원인**: Raw socket 권한 없음

**해결**:
```bash
# Linux: setcap 사용
sudo setcap cap_net_raw+ep $(which rustscan)

# 또는 sudo로 실행
sudo rustscan -a <target>
```

---

### 문제 3: Python 3.12 없음 (Ubuntu 20.04)

**증상**:
```
python3.12: command not found
```

**해결**: pyenv 사용

```bash
# pyenv 설치
curl https://pyenv.run | bash

# bashrc 설정
echo 'export PATH="$HOME/.pyenv/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
source ~/.bashrc

# Python 3.12 설치
pyenv install 3.12.0
pyenv global 3.12.0

# 검증
python --version
```

---

### 문제 4: Nmap NSE 스크립트 없음

**증상**:
```
NSE script not found: http-enum
```

**해결**:
```bash
# NSE 스크립트 패키지 설치
sudo apt install nmap-common

# 스크립트 경로 확인
locate *.nse | head -10
```

---

### 문제 5: uv: command not found

**증상**:
```bash
uv: command not found
```

**원인**: PATH 설정 누락

**해결**:
```bash
# bashrc에 PATH 추가
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# 검증
uv --version
```

---

## 8. WSL2 가이드 (Windows)

Windows 사용자는 **WSL2**를 사용하세요.

### WSL2 설치

```powershell
# PowerShell (관리자 권한)
wsl --install -d Ubuntu-22.04
```

재부팅 후 Ubuntu 실행.

### WSL2 내부 설정

WSL2 Ubuntu 터미널에서:

```bash
# Ubuntu 가이드와 동일하게 설치
sudo apt update && sudo apt install -y python3.12 nmap
# ... (3. 필수 의존성 설치 참조)
```

### 추가 고려사항

#### 1. Windows 방화벽

WSL2에서 실행되는 스캔이 방화벽에 차단될 수 있음:

```powershell
# PowerShell (관리자 권한, 선택 사항)
New-NetFirewallRule -DisplayName "WSL2 Nmap" -Direction Outbound -Action Allow
```

#### 2. 네트워크 브리지

- WSL2는 기본적으로 NAT 모드
- 호스트 네트워크 스캔: 문제없음
- 외부 네트워크 스캔: 성능 저하 가능

#### 3. 파일 시스템 성능

```bash
# ❌ 느림: Windows 파일 시스템
cd /mnt/c/Users/username/nmap

# ✅ 빠름: WSL2 파일 시스템
cd ~/nmap
```

**권장**: Git clone도 WSL2 내부(`~/`)에서 수행

#### 검증

```bash
# WSL2 내부에서
ip addr show eth0  # IP 확인
ping 8.8.8.8       # 외부 연결 확인
```

---

## 9. 선택적 도구

### Hydra (Phase 4 브루트포스용)

**목적**: FTP/SSH/Telnet 브루트포스

#### 설치

```bash
# Ubuntu/Debian
sudo apt install hydra

# macOS
brew install hydra
```

#### 검증

```bash
hydra -h
```

#### 사용 여부

- `--skip-bruteforce` 플래그로 스킵 가능
- 설치하지 않아도 Phase 1-3는 정상 동작
- 필요 시에만 설치

**대안**: Medusa
```bash
sudo apt install medusa
```

---

## Appendix A: 성능 최적화

### 대규모 네트워크 스캔 팁

#### 1. 타임아웃 조정

```python
# scripts/scanner/config.py 수정
phase2_timeout: int = 1800  # 느린 네트워크용
```

#### 2. Resume 기능 활용

```bash
# 스캔 중단 시 재개
python main.py --resume
```

#### 3. Phase별 선택 실행

```bash
# Phase 4만 스킵
python main.py --json-file scripts/targets.json --skip-vuln --skip-bruteforce
```

### 리소스 관리

#### 디스크 공간

```bash
# 오래된 스캔 결과 삭제
rm -rf scans/rustscan_massive_2024*
```

#### 메모리 사용

- 대규모 스캔 시 **4GB+ RAM** 권장
- Playwright 브라우저가 메모리 많이 사용

#### 네트워크 대역폭

- RustScan은 매우 빠름 (초당 수만 패킷)
- 네트워크 포화 주의

---

## Appendix B: FAQ

### Q1: Python 3.12가 없는 오래된 OS에서 사용하려면?

**A**: pyenv 사용 권장

```bash
curl https://pyenv.run | bash
pyenv install 3.12.0
pyenv local 3.12.0
```

---

### Q2: RustScan이 너무 빠르게 스캔해서 방화벽에 차단되면?

**A**: RustScan의 `--ulimit` 옵션을 조정해야 하지만, 현재 코드에 하드코딩되어 있습니다. `scripts/phases/phase1.py`를 수정하여 `--ulimit` 값을 낮추세요.

---

### Q3: Web 브루트포스 없이 사용하려면?

**A**: `--skip-bruteforce` 플래그 사용

```bash
python main.py --json-file scripts/targets.json --skip-bruteforce
```

---

### Q4: Playwright 없이 사용 가능한가?

**A**: 불가능. Phase 4 Web 공격 기능이 핵심이므로 Playwright는 필수 의존성입니다.

---

### Q5: sudo 없이 실행하려면?

**A**: RustScan/Nmap은 raw socket 필요 → `sudo` 또는 `setcap` 필수

```bash
# setcap 사용 (Linux)
sudo setcap cap_net_raw+ep $(which rustscan)
sudo setcap cap_net_raw+ep $(which nmap)
```

---

### Q6: Windows에서 네이티브 실행 가능?

**A**: 불가능. WSL2 필수 (Bash 스크립트, Unix 도구 의존).

---

## 다음 단계

설치가 완료되었다면:

1. **README.md** 참조 - 프로젝트 개요 및 사용법
2. **실제 스캔 실행** - `targets.json` 수정 후 실행
3. **고급 설정** - `config.py` 커스터마이징
4. **문서 참조**:
   - `docs/SCANNER_ARCHITECTURE.md` - 아키텍처 상세
   - `docs/NMAP-DEEP-DIVE.md` - Nmap 가이드
   - `docs/RUSTSCAN-DEEP-DIVE.md` - RustScan 가이드

---

**설치 완료!** 🎉

문제가 발생하면 [Issues](https://github.com/your-username/nmap/issues)에 제보해주세요.

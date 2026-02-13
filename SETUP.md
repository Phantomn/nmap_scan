# 설치 가이드

네트워크 스캐너의 모든 의존성을 설치하는 가이드입니다.

## ⚠️ 법적 고지사항

**이 도구는 승인된 네트워크에서만 사용하세요.**

- 무단 네트워크 스캔은 **불법**이며, 컴퓨터 범죄로 처벌받을 수 있습니다
- 사용 전 네트워크 관리자의 **명시적 서면 승인** 필수
- 교육 목적 및 자체 네트워크 보안 테스트용으로만 사용
- 모든 법적 책임은 사용자에게 있습니다

---

## 빠른 시작 (자동 설치)

**가장 쉬운 방법**: 자동 설치 스크립트 사용

```bash
# 1. 의존성 확인 및 자동 설치
./check_deps.sh --install

# 2. 타겟 설정
cp targets.json.example targets.json
nano targets.json

# 3. 실행
python main.py
```

---

## 목차

- [빠른 시작 (자동 설치)](#빠른-시작-자동-설치)
- [시스템 요구사항](#시스템-요구사항)
- [플랫폼별 설치](#플랫폼별-설치)
  - [Ubuntu/Debian](#ubuntudebian)
  - [CentOS/RHEL](#centosrhel)
  - [macOS](#macos)
  - [WSL (Windows)](#wsl-windows)
- [Python 의존성](#python-의존성)
- [설정 및 검증](#설정-및-검증)
- [문제 해결](#문제-해결)

---

## 시스템 요구사항

### 필수 도구

| 도구 | 최소 버전 | 용도 |
|------|----------|------|
| **Python** | 3.10+ | 메인 실행 환경 |
| **RustScan** | 2.0+ | 빠른 포트 스캔 |
| **Nmap** | 7.80+ | 호스트 발견 및 서비스 탐지 |

### 선택 도구

| 도구 | 용도 |
|------|------|
| **uv** | Python 패키지 관리 (권장) |
| **git** | 소스 코드 관리 |

---

## 플랫폼별 설치

### Ubuntu/Debian

```bash
# 1. 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# 2. Python 3.10+ 설치
sudo apt install -y python3 python3-pip python3-venv

# 3. Nmap 설치
sudo apt install -y nmap

# 4. RustScan 설치 (Option 1: 바이너리)
wget https://github.com/RustScan/RustScan/releases/download/2.1.1/rustscan_2.1.1_amd64.deb
sudo dpkg -i rustscan_2.1.1_amd64.deb
rm rustscan_2.1.1_amd64.deb

# 4. RustScan 설치 (Option 2: Cargo)
# curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
# cargo install rustscan

# 5. uv 설치 (권장)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 6. 버전 확인
python3 --version    # Python 3.10.0 이상
nmap --version       # Nmap 7.80 이상
rustscan --version   # 2.0.0 이상
```

---

### CentOS/RHEL

```bash
# 1. 시스템 업데이트
sudo yum update -y

# 2. Python 3.10+ 설치 (EPEL 저장소 필요)
sudo yum install -y epel-release
sudo yum install -y python3 python3-pip

# 3. Nmap 설치
sudo yum install -y nmap

# 4. RustScan 설치 (Cargo 권장)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env
cargo install rustscan

# 5. uv 설치
curl -LsSf https://astral.sh/uv/install.sh | sh

# 6. 버전 확인
python3 --version
nmap --version
rustscan --version
```

---

### macOS

```bash
# 1. Homebrew 설치 (없으면)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Python 3.10+ 설치
brew install python@3.10

# 3. Nmap 설치
brew install nmap

# 4. RustScan 설치
brew install rustscan

# 5. uv 설치
curl -LsSf https://astral.sh/uv/install.sh | sh

# 6. 버전 확인
python3 --version
nmap --version
rustscan --version
```

---

### WSL (Windows)

**WSL2 Ubuntu 권장**

```bash
# 1. WSL2 설치 (PowerShell 관리자 권한)
# wsl --install

# 2. Ubuntu 실행 후 아래 명령 실행
sudo apt update && sudo apt upgrade -y

# 3. Python 3.10+ 설치
sudo apt install -y python3 python3-pip python3-venv

# 4. Nmap 설치
sudo apt install -y nmap

# 5. RustScan 설치
wget https://github.com/RustScan/RustScan/releases/download/2.1.1/rustscan_2.1.1_amd64.deb
sudo dpkg -i rustscan_2.1.1_amd64.deb
rm rustscan_2.1.1_amd64.deb

# 6. uv 설치
curl -LsSf https://astral.sh/uv/install.sh | sh

# 7. ulimit 설정 (중요!)
echo "* soft nofile 65535" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65535" | sudo tee -a /etc/security/limits.conf
# WSL 재시작 필요

# 8. 버전 확인
python3 --version
nmap --version
rustscan --version
ulimit -n  # 65535 이상이어야 함
```

**WSL 주의사항**:
- RustScan이 네트워크 드라이버 문제로 불안정할 수 있음
- `batch_size=10000`, `timeout=2000ms`, `parallel_limit=5`로 최적화 (이미 적용됨)
- ulimit 설정 필수 (파일 디스크립터 제한, 55000 이상 권장)

---

## Python 의존성

### Option 1: uv 사용 (권장)

```bash
# 1. 프로젝트 클론
git clone https://github.com/your-repo/nmap.git
cd nmap

# 2. 의존성 설치
uv sync

# 3. 실행 테스트
uv run python main.py --help
```

### Option 2: pip + venv

```bash
# 1. 프로젝트 클론
git clone https://github.com/your-repo/nmap.git
cd nmap

# 2. 가상환경 생성
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. 의존성 설치
pip install --upgrade pip
pip install -r requirements.txt

# 4. 실행 테스트
python main.py --help
```

### requirements.txt 생성 (없을 경우)

```bash
# pyproject.toml에서 requirements.txt 생성
uv pip compile pyproject.toml -o requirements.txt
```

---

## 설정 및 검증

### 1. sudo 권한 설정 (선택사항)

스캔 중 비밀번호 입력을 피하려면 NOPASSWD 설정:

```bash
# sudoers 파일 편집
sudo visudo

# 아래 라인 추가 (your-username을 실제 사용자명으로 변경)
your-username ALL=(ALL) NOPASSWD: /usr/bin/nmap
```

**주의**: 보안상 프로덕션 환경에서는 권장하지 않습니다.

### 2. 타겟 설정

```bash
# targets.json 생성
cp targets.json.example targets.json

# 편집
nano targets.json
```

**예제**:
```json
{
  "subnets": [
    "192.168.1.0/24",
    "10.0.0.0/24"
  ],
  "exclude": [
    "192.168.1.1",
    "10.0.0.1"
  ]
}
```

### 3. 실행 테스트

```bash
# 기본 실행
python main.py

# 또는
uv run python main.py
```

**예상 출력**:
```
[✓] 타겟 로드: 2개 서브넷
sudo 비밀번호: ********
[i] 스캔 디렉토리: /home/user/nmap/scans/rustscan_massive_20260212_123456
[✓] 설정 검증 완료
================================================================================
대규모 스캔 시작
================================================================================
```

### 4. 버전 확인 스크립트

```bash
#!/bin/bash
echo "=== 의존성 버전 확인 ==="
echo "Python: $(python3 --version 2>&1)"
echo "Nmap: $(nmap --version 2>&1 | head -2 | tail -1)"
echo "RustScan: $(rustscan --version 2>&1)"
echo "uv: $(uv --version 2>&1)"
echo ""
echo "=== ulimit 확인 (WSL 중요) ==="
echo "nofile: $(ulimit -n)"
```

저장: `check_deps.sh` → `chmod +x check_deps.sh` → `./check_deps.sh`

---

## 문제 해결

### 문제 1: RustScan 설치 실패

**증상**: `rustscan: command not found`

**해결**:
```bash
# Cargo로 재설치
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env
cargo install rustscan

# PATH 추가 (필요시)
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

---

### 문제 2: sudo 비밀번호 반복 요청

**증상**: nmap 실행 시마다 비밀번호 요청

**해결**:
```bash
# Option 1: NOPASSWD 설정 (위 참조)

# Option 2: 환경변수 사용 (비추천)
export SUDO_PASSWORD="your-password"
python main.py

# Option 3: sudo 캐시 타임아웃 연장
sudo visudo
# Defaults timestamp_timeout=60  # 60분으로 연장
```

---

### 문제 3: WSL에서 RustScan 불안정

**증상**: "Too many open files" 또는 무응답

**해결**:
```bash
# 1. ulimit 확인
ulimit -n  # 1024 이하면 문제

# 2. ulimit 영구 설정
echo "* soft nofile 65535" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65535" | sudo tee -a /etc/security/limits.conf

# 3. WSL 재시작 (PowerShell)
wsl --shutdown

# 4. 재확인
ulimit -n  # 65535여야 함
```

---

### 문제 4: Python 버전 낮음

**증상**: `Python 3.9 이하`

**해결**:
```bash
# Ubuntu: deadsnakes PPA
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3.10-dev

# python3.10을 기본으로 설정
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1
```

---

## 다음 단계

설치가 완료되었으면:

1. **README.md** 읽기 - 사용법 및 주의사항
2. **targets.json 설정** - 스캔할 네트워크 정의
3. **테스트 스캔 실행** - 작은 네트워크로 테스트
4. **결과 확인** - `scans/` 디렉터리

---

## 추가 리소스

- [Nmap 공식 문서](https://nmap.org/book/man.html)
- [RustScan GitHub](https://github.com/RustScan/RustScan)
- [uv 문서](https://github.com/astral-sh/uv)

---

## 라이선스

MIT License - 자세한 내용은 LICENSE 파일 참조

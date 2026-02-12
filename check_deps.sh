#!/bin/bash
# 의존성 확인 및 자동 설치 스크립트

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

MISSING_TOOLS=()
INSTALL_MODE=false

# 사용법 출력
usage() {
    cat << EOF
사용법: $0 [옵션]

옵션:
  --install, -i    누락된 의존성 자동 설치
  --help, -h       도움말 출력

예제:
  $0               # 의존성만 확인
  $0 --install     # 의존성 확인 및 자동 설치
EOF
}

# 인자 파싱
while [[ $# -gt 0 ]]; do
    case $1 in
        --install|-i)
            INSTALL_MODE=true
            shift
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo "알 수 없는 옵션: $1"
            usage
            exit 1
            ;;
    esac
done

echo "=========================================="
echo "  네트워크 스캐너 의존성 확인"
echo "=========================================="
echo ""

# OS 감지
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            OS=$ID
            if grep -qi microsoft /proc/version; then
                OS="wsl"
            fi
        else
            OS="unknown"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    else
        OS="unknown"
    fi
    echo -e "${BLUE}감지된 OS: $OS${NC}"
    echo ""
}

# 함수: 버전 확인
check_tool() {
    local name=$1
    local cmd=$2
    local min_version=$3

    if command -v ${cmd%% *} &> /dev/null; then
        version=$(eval "$cmd" 2>&1 || true)
        echo -e "${GREEN}✓${NC} $name: $version"
        return 0
    else
        echo -e "${RED}✗${NC} $name: 설치되지 않음 (최소 버전: $min_version)"
        MISSING_TOOLS+=("$name")
        return 1
    fi
}

# OS 감지
detect_os

# 의존성 확인
echo "=== 필수 도구 확인 ==="
check_tool "Python" "python3 --version" "3.10+" || true
check_tool "Nmap" "nmap --version | head -2 | tail -1" "7.80+" || true
check_tool "fping" "fping --version" "최신" || true
check_tool "RustScan" "rustscan --version" "2.0+" || true

echo ""
echo "=== 선택 도구 확인 ==="
if command -v uv &> /dev/null; then
    check_tool "uv" "uv --version" "최신" || true
else
    echo -e "${YELLOW}○${NC} uv: 설치되지 않음 (선택사항, 하지만 권장)"
fi

if command -v git &> /dev/null; then
    check_tool "git" "git --version" "최신" || true
else
    echo -e "${YELLOW}○${NC} git: 설치되지 않음 (선택사항)"
fi

echo ""
echo "=== 시스템 설정 확인 ==="

# ulimit 확인
nofile=$(ulimit -n)
if [ "$nofile" -ge 65535 ]; then
    echo -e "${GREEN}✓${NC} ulimit -n: $nofile (충분함)"
elif [ "$nofile" -ge 5000 ]; then
    echo -e "${YELLOW}○${NC} ulimit -n: $nofile (권장: 65535 이상)"
else
    echo -e "${RED}✗${NC} ulimit -n: $nofile (너무 낮음, 최소 5000 필요)"
fi

# sudo 권한 확인
if sudo -n true 2>/dev/null; then
    echo -e "${GREEN}✓${NC} sudo: NOPASSWD 설정됨 (비밀번호 불필요)"
else
    echo -e "${YELLOW}○${NC} sudo: 비밀번호 필요 (NOPASSWD 설정 권장)"
fi

echo ""
echo "=== Python 환경 확인 ==="

# 가상환경 확인
if [ -n "$VIRTUAL_ENV" ]; then
    echo -e "${GREEN}✓${NC} 가상환경: 활성화됨 ($VIRTUAL_ENV)"
else
    echo -e "${YELLOW}○${NC} 가상환경: 비활성화 (권장: uv sync 또는 python -m venv .venv)"
fi

# Python 패키지
echo -e "${GREEN}✓${NC} Python 의존성: 표준 라이브러리만 사용 (외부 패키지 불필요)"

echo ""
echo "=========================================="

# 누락된 도구가 있는지 확인
if [ ${#MISSING_TOOLS[@]} -eq 0 ]; then
    echo -e "${GREEN}✓ 모든 필수 도구 설치 완료!${NC}"
    echo ""
    echo "다음 단계:"
    echo "  1. cp targets.json.example targets.json"
    echo "  2. nano targets.json  # 스캔할 네트워크 설정"
    echo "  3. python main.py"
    exit 0
fi

# 설치 모드
if [ "$INSTALL_MODE" = true ]; then
    echo -e "${YELLOW}누락된 도구: ${MISSING_TOOLS[*]}${NC}"
    echo ""

    # 사용자 확인
    read -p "누락된 도구를 자동으로 설치하시겠습니까? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "설치가 취소되었습니다."
        exit 1
    fi

    echo ""
    echo "=========================================="
    echo "  자동 설치 시작"
    echo "=========================================="
    echo ""

    # OS별 설치 명령
    case $OS in
        ubuntu|debian|wsl)
            echo "Ubuntu/Debian 패키지 설치 중..."

            # 시스템 업데이트
            sudo apt update

            # 누락된 도구별 설치
            for tool in "${MISSING_TOOLS[@]}"; do
                case $tool in
                    Python)
                        echo "Python 3.10+ 설치 중..."
                        sudo apt install -y python3 python3-pip python3-venv
                        ;;
                    Nmap)
                        echo "Nmap 설치 중..."
                        sudo apt install -y nmap
                        ;;
                    fping)
                        echo "fping 설치 중..."
                        sudo apt install -y fping
                        # fping에 CAP_NET_RAW 권한 부여
                        sudo setcap cap_net_raw+ep $(which fping) 2>/dev/null || true
                        ;;
                    RustScan)
                        echo "RustScan 설치 중..."
                        # 최신 릴리스 URL 가져오기
                        RUSTSCAN_VERSION=$(curl -s https://api.github.com/repos/RustScan/RustScan/releases/latest | grep '"tag_name"' | sed -E 's/.*"([^"]+)".*/\1/')
                        RUSTSCAN_URL="https://github.com/RustScan/RustScan/releases/download/${RUSTSCAN_VERSION}/rustscan_${RUSTSCAN_VERSION#v}_amd64.deb"

                        echo "다운로드: $RUSTSCAN_URL"
                        wget -q "$RUSTSCAN_URL" -O /tmp/rustscan.deb
                        sudo dpkg -i /tmp/rustscan.deb
                        rm /tmp/rustscan.deb
                        ;;
                esac
            done

            # WSL인 경우 ulimit 설정
            if [ "$OS" = "wsl" ]; then
                echo ""
                echo "WSL ulimit 설정 중..."
                if ! grep -q "nofile 65535" /etc/security/limits.conf; then
                    echo "* soft nofile 65535" | sudo tee -a /etc/security/limits.conf
                    echo "* hard nofile 65535" | sudo tee -a /etc/security/limits.conf
                    echo -e "${YELLOW}⚠ WSL을 재시작해야 ulimit 설정이 적용됩니다.${NC}"
                    echo "  PowerShell에서: wsl --shutdown"
                fi
            fi
            ;;

        centos|rhel|fedora)
            echo "CentOS/RHEL/Fedora 패키지 설치 중..."

            # EPEL 저장소 추가
            sudo yum install -y epel-release || sudo dnf install -y epel-release

            # 누락된 도구별 설치
            for tool in "${MISSING_TOOLS[@]}"; do
                case $tool in
                    Python)
                        echo "Python 3.10+ 설치 중..."
                        sudo yum install -y python3 python3-pip || sudo dnf install -y python3 python3-pip
                        ;;
                    Nmap)
                        echo "Nmap 설치 중..."
                        sudo yum install -y nmap || sudo dnf install -y nmap
                        ;;
                    fping)
                        echo "fping 설치 중..."
                        sudo yum install -y fping || sudo dnf install -y fping
                        sudo setcap cap_net_raw+ep $(which fping) 2>/dev/null || true
                        ;;
                    RustScan)
                        echo "RustScan 설치 중 (Cargo 사용)..."
                        if ! command -v cargo &> /dev/null; then
                            echo "Rust 설치 중..."
                            curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
                            source $HOME/.cargo/env
                        fi
                        cargo install rustscan
                        ;;
                esac
            done
            ;;

        macos)
            echo "macOS 패키지 설치 중..."

            # Homebrew 확인
            if ! command -v brew &> /dev/null; then
                echo "Homebrew 설치 중..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            fi

            # 누락된 도구별 설치
            for tool in "${MISSING_TOOLS[@]}"; do
                case $tool in
                    Python)
                        echo "Python 3.10+ 설치 중..."
                        brew install python@3.10
                        ;;
                    Nmap)
                        echo "Nmap 설치 중..."
                        brew install nmap
                        ;;
                    fping)
                        echo "fping 설치 중..."
                        brew install fping
                        ;;
                    RustScan)
                        echo "RustScan 설치 중..."
                        brew install rustscan
                        ;;
                esac
            done
            ;;

        *)
            echo -e "${RED}지원하지 않는 OS: $OS${NC}"
            echo "SETUP.md를 참조하여 수동으로 설치하세요."
            exit 1
            ;;
    esac

    # uv 설치 (선택사항)
    if ! command -v uv &> /dev/null; then
        echo ""
        read -p "uv (Python 패키지 관리자)를 설치하시겠습니까? (권장) (Y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            echo "uv 설치 중..."
            curl -LsSf https://astral.sh/uv/install.sh | sh
            export PATH="$HOME/.cargo/bin:$PATH"
        fi
    fi

    echo ""
    echo "=========================================="
    echo "  설치 완료"
    echo "=========================================="
    echo ""

    # 재검증
    echo "의존성 재확인 중..."
    echo ""

    # 재귀 호출 (설치 모드 없이)
    exec "$0"

else
    # 설치 모드가 아닐 때
    echo -e "${RED}✗ 일부 필수 도구가 설치되지 않았습니다.${NC}"
    echo -e "${YELLOW}누락된 도구: ${MISSING_TOOLS[*]}${NC}"
    echo ""
    echo "설치 방법:"
    echo "  1. 자동 설치: $0 --install"
    echo "  2. 수동 설치: SETUP.md 참조"
    exit 1
fi

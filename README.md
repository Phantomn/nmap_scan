# 네트워크 스캐너

RustScan + Nmap을 조합한 **2-phase 네트워크 스캐너**.

## 특징

- **🚀 빠른 포트 스캔**: RustScan으로 초고속 포트 발견
- **🔍 상세 분석**: Nmap으로 OS/버전/스크립트 스캔
- **📊 간결한 출력**: nmap 형식 결과만 생성 (중간 파일 없음)
- **⚡ WSL 최적화**: 안정적인 파라미터 사용

## 2-Phase 구조

```
Phase 1: Health Check
  └─ fping + nmap -sn → alive_hosts.txt, dead_hosts.txt

Phase 2: Detailed Scan
  └─ rustscan → nmap -A → scan_*.nmap (각 IP별)
```

## 사용법

### 1. 설치

```bash
# 의존성 설치
uv sync

# 또는 pip로 설치
pip install -r requirements.txt
```

### 2. 타겟 설정

`targets.json` 생성 (루트 디렉토리):

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

**참고**: `targets.json.example`을 복사하여 수정하세요.

### 3. 실행

```bash
# 기본 실행 (targets.json 사용)
python main.py

# 또는 명시적으로 파일 지정
python main.py --json-file targets.json

# 또는 스크립트 직접 호출
uv run scripts/rustscan_massive.py --json-file targets.json
```

## 프로젝트 구조

```
.
├── main.py                      # 진입점 (간단한 래퍼)
├── targets.json.example         # 타겟 설정 예제
├── scripts/
│   ├── rustscan_massive.py      # 메인 로직
│   ├── phases/                  # 2단계 구현
│   │   ├── phase1.py            # Health Check
│   │   └── phase2.py            # Detailed Scan
│   ├── scanner/                 # 스캐너 엔진
│   │   ├── config.py            # 설정 (6개 필드)
│   │   ├── logger.py            # 로깅
│   │   └── scanner.py           # 오케스트레이터
│   └── utils/                   # 유틸리티
│       ├── subprocess_runner.py # 비동기 subprocess 실행
│       ├── json_loader.py       # targets.json 로더
│       └── rtt_optimizer.py     # RTT 기반 파라미터 최적화
└── scans/                       # 스캔 결과 (gitignore)
```

## 출력 결과

```
scans/rustscan_massive_YYYYMMDD_HHMMSS/
├── alive_hosts.txt       # 살아있는 IP 목록
├── dead_hosts.txt        # 죽은 IP 목록
└── scan_*.nmap           # 각 IP별 nmap 상세 스캔 결과
```

**출력 파일 특징**:
- **nmap 형식**: 표준 nmap 출력 (`-oN`)
- **중간 파일 없음**: XML, JSON, 포트 맵 등 제거
- **단순함**: 3종류 파일만 생성

## 설정

`scripts/scanner/config.py`의 `Config` 클래스:

```python
@dataclass
class Config:
    script_dir: Path       # 스크립트 디렉토리
    scan_dir: Path         # 스캔 결과 디렉토리
    json_file: Path        # targets.json 경로
    subnets: list[str]     # 스캔할 서브넷 목록
    exclude_ips: list[str] # 제외할 IP 목록
    sudo_password: str     # sudo 비밀번호
```

**RustScan 파라미터** (WSL 최적화):
- `batch_size`: 1000 (보수적)
- `timeout`: 3000ms
- `parallel_limit`: 2 (동시 실행 제한)
- `ulimit`: 5000

**Nmap 파라미터**:
- `-T3`: 보수적 타이밍
- `-A`: OS/버전/스크립트 스캔
- `-v`: 상세 출력

## 요구사항

- **Python**: 3.10+
- **RustScan**: 2.0+
- **Nmap**: 7.80+
- **fping**: 최신 버전
- **uv**: Python 패키지 관리 (권장)

## ⚠️ 법적 고지사항

**이 도구는 승인된 네트워크에서만 사용하세요.**

- 무단 네트워크 스캔은 **불법**이며, 컴퓨터 범죄로 처벌받을 수 있습니다
- 사용 전 네트워크 관리자의 **명시적 서면 승인** 필수
- 교육 목적 및 자체 네트워크 보안 테스트용으로만 사용
- 모든 법적 책임은 사용자에게 있습니다

## 보안 주의사항

1. **sudo 비밀번호**: 환경변수 `SUDO_PASSWORD` 또는 프롬프트 입력
2. **targets.json**: `.gitignore`에 포함됨 (민감 정보 유출 방지)
3. **스캔 권한**: 네트워크 스캔은 권한이 있는 네트워크에서만 수행

## 라이선스

MIT

## 기여

Pull Request 환영합니다!

## 변경 이력

### v2.0.0 (2026-02-12)
- **리팩토링**: 4-phase → 2-phase 구조로 단순화
- **제거**: Phase 3-4, checkpoint, 브루트포스, Playwright, 리포트 생성
- **개선**: nmap pass-through 활용, 절대 경로 사용, 에러 핸들링 강화
- **최적화**: 코드 라인 수 81% 감소 (~800줄 → ~150줄)

### v1.0.0
- 초기 릴리스 (4-phase 구조)

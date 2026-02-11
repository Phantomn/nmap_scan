# nmap 네트워크 스캐너

RustScan + Nmap을 조합한 4단계 파이프라인 네트워크 스캐너.

## 특징

- **🚀 빠른 포트 스캔**: RustScan으로 초고속 포트 발견
- **🔍 상세 분석**: Nmap NSE 스크립트로 서비스 탐지
- **🔐 보안 테스트**: FTP/SSH/Telnet/Web 브루트포스 + Playwright 스크린샷
- **📊 체크포인트**: 중단 시 재개 가능 (Resume 기능)

## 4단계 파이프라인

```
Phase 1: RustScan    → 포트 발견 (1-65535)
Phase 2: Nmap 기본   → 서비스 버전 탐지
Phase 3: Nmap 상세   → NSE 스크립트 실행
Phase 4: 공격        → 브루트포스 + Web 스캔
```

## 사용법

### 1. 설치

```bash
# 의존성 설치
uv sync

# Playwright 브라우저 설치
uv run playwright install chromium
```

### 2. 타겟 설정

`scripts/targets.json` 생성:

```json
{
  "subnets": [
    "192.168.1.0/24"
  ],
  "exclude": [
    "192.168.1.1"
  ]
}
```

### 3. 실행

```bash
# 기본 실행
python main.py --json-file scripts/targets.json

# 취약점 스캔 스킵
python main.py --json-file scripts/targets.json --skip-vuln

# 브루트포스 스킵
python main.py --json-file scripts/targets.json --skip-bruteforce

# 중단된 스캔 재개
python main.py --resume
```

## 프로젝트 구조

```
.
├── main.py                      # 진입점
├── scripts/
│   ├── rustscan_massive.py      # 메인 로직
│   ├── phases/                  # 4단계 구현
│   │   ├── phase1.py            # RustScan
│   │   ├── phase2.py            # Nmap 기본
│   │   ├── phase3.py            # Nmap 상세
│   │   └── phase4.py            # 브루트포스 + Web
│   ├── scanner/                 # 스캐너 엔진
│   │   ├── config.py            # 설정
│   │   ├── logger.py            # 로깅
│   │   ├── scanner.py           # 오케스트레이터
│   │   └── checkpoint.py        # Resume 기능
│   └── utils/                   # 유틸리티
│       ├── web_bruteforce.py    # Playwright Web 공격
│       ├── nse_script_selector.py  # NSE 스크립트 선택
│       └── xml_to_markdown.py   # 결과 리포트 생성
├── docs/                        # 문서
│   ├── SCANNER_ARCHITECTURE.md  # 아키텍처
│   ├── NMAP-DEEP-DIVE.md        # Nmap 가이드
│   └── RUSTSCAN-DEEP-DIVE.md    # RustScan 가이드
└── scans/                       # 스캔 결과 (gitignore)
```

## 설정

`scripts/scanner/config.py`에서 커스터마이징 가능:

- **타임아웃**: `phase2_timeout`, `phase3_timeout_per_port`
- **브루트포스**: `bruteforce_max_attempts`, `web_bruteforce_max_users`
- **Web 경로**: `web_login_paths` (로그인 페이지 탐색)
- **NSE 스크립트**: `nse_script_selector.py`에서 포트별 선택

## 출력 결과

```
scans/rustscan_massive_YYYYMMDD_HHMMSS/
├── checkpoint.json               # Resume 체크포인트
├── phase1_rustscan_*.txt         # RustScan 결과
├── phase2_basic_*.{xml,gnmap}    # Nmap 기본 스캔
├── phase3_detail_*.xml           # Nmap 상세 스캔
├── phase4_bruteforce_*.txt       # 브루트포스 결과
├── phase4_web_bruteforce_*.json  # Web 공격 결과
└── screenshots/                  # Playwright 스크린샷
```

## 요구사항

- Python 3.10+
- RustScan 2.0+
- Nmap 7.80+
- uv (Python 패키지 관리)

## 라이선스

MIT

## 기여

Pull Request 환영합니다!

## 참고

- [RustScan 문서](docs/RUSTSCAN-DEEP-DIVE.md)
- [Nmap 문서](docs/NMAP-DEEP-DIVE.md)
- [아키텍처 상세](docs/SCANNER_ARCHITECTURE.md)

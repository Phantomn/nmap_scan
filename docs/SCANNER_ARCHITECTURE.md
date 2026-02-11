# Scanner 아키텍처 설계 (Python 버전)

## 개요
Bash 스크립트 `rustscan_massive_4phase.sh`를 Python으로 재작성하여 유지보수성, 확장성, 테스트 가능성을 향상시킵니다.

## 목표
- **코드 품질**: 타입 안전, 에러 핸들링, 테스트 가능성
- **성능 유지**: 비동기 I/O로 병렬 실행 최적화
- **기능 동등성**: 기존 Bash 스크립트의 모든 기능 지원
- **확장성**: 새로운 Phase 추가 용이

---

## 프로젝트 구조

```
scripts/
├── rustscan_massive.py          # CLI 진입점 (main)
├── scanner/
│   ├── __init__.py
│   ├── config.py                # Config 데이터 클래스 ✅
│   ├── logger.py                # ColorLogger, ProgressTracker ✅
│   ├── checkpoint.py            # Resume 기능 (체크포인트 관리)
│   └── scanner.py               # Scanner 메인 클래스
├── phases/
│   ├── __init__.py
│   ├── base.py                  # PhaseBase 추상 클래스
│   ├── host_discovery.py        # Phase 1: HostDiscovery
│   ├── port_scanner.py          # Phase 2: PortScanner
│   ├── service_detector.py      # Phase 3: ServiceDetector
│   └── vulnerability_scanner.py # Phase 4: VulnerabilityScannerWithBruteforce
├── utils/
│   ├── __init__.py
│   ├── subprocess_runner.py     # async 명령어 실행 ✅
│   ├── json_loader.py           # targets.json 로더 ✅
│   └── rtt_optimizer.py         # RTT 기반 Rustscan 파라미터 최적화
└── wordlists/
    ├── usernames.txt            # 기본 사용자 이름
    └── passwords.txt            # 기본 비밀번호
```

---

## 핵심 클래스 설계

### 1. `Scanner` 메인 클래스

```python
# scanner/scanner.py
from pathlib import Path
from typing import Optional
from scanner.config import Config
from scanner.logger import ColorLogger
from scanner.checkpoint import CheckpointManager
from phases.host_discovery import HostDiscovery
from phases.port_scanner import PortScanner
from phases.service_detector import ServiceDetector
from phases.vulnerability_scanner import VulnerabilityScannerWithBruteforce


class Scanner:
    """4단계 스캔 오케스트레이터"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = ColorLogger
        self.checkpoint = CheckpointManager(config.scan_dir)

        # Phase 인스턴스 생성
        self.phases = [
            HostDiscovery(config, self.logger),
            PortScanner(config, self.logger),
            ServiceDetector(config, self.logger),
        ]

        if not config.skip_vuln:
            self.phases.append(
                VulnerabilityScannerWithBruteforce(config, self.logger)
            )

    async def run(self) -> None:
        """스캔 실행 (서브넷별 순차, Phase별 순차)"""
        self.logger.header("대규모 스캔 시작")
        self.logger.info(f"대상: {len(self.config.subnets)}개 서브넷")
        self.logger.info(f"스캔 디렉토리: {self.config.scan_dir}")

        for i, subnet in enumerate(self.config.subnets, start=1):
            subnet_label = subnet.replace(".", "_").replace("/", "_")

            # Resume: 이미 완료된 서브넷 스킵
            if self.checkpoint.is_subnet_completed(subnet_label):
                self.logger.warning(f"서브넷 {subnet} 이미 완료 - 스킵")
                continue

            self.logger.separator()
            self.logger.info(f"[{i}/{len(self.config.subnets)}] 서브넷 처리: {subnet}")

            # Phase 1-4 순차 실행
            context = {"subnet": subnet, "label": subnet_label}

            for phase in self.phases:
                # Resume: 이미 완료된 Phase 스킵
                if self.checkpoint.is_phase_completed(subnet_label, phase.name):
                    self.logger.warning(f"{phase.name} 이미 완료 - 스킵")
                    context = self.checkpoint.load_phase_context(subnet_label, phase.name)
                    continue

                # Phase 실행
                self.logger.phase(phase.name, f"시작 - {phase.description}")
                context = await phase.execute(context)

                # 체크포인트 저장
                self.checkpoint.save_phase_completion(
                    subnet_label, phase.name, context
                )

            # 서브넷 완료 마킹
            self.checkpoint.save_subnet_completion(subnet_label)

        self.logger.success("모든 스캔 완료")
```

**핵심 특징**:
- ✅ Phase 순차 실행 (서브넷별)
- ✅ Resume 기능 (체크포인트 기반)
- ✅ Context 기반 데이터 전달 (Phase 간)
- ✅ 에러 핸들링 (Phase별 독립)

---

### 2. `PhaseBase` 추상 클래스

```python
# phases/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict
from scanner.config import Config
from scanner.logger import ColorLogger


class PhaseBase(ABC):
    """모든 Phase의 추상 기반 클래스"""

    def __init__(self, config: Config, logger: type[ColorLogger]):
        self.config = config
        self.logger = logger
        self.name = self.__class__.__name__
        self.description = ""

    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Phase 실행 메서드 (서브클래스에서 구현)

        Args:
            context: 이전 Phase의 결과 (dict)
                - subnet: 현재 서브넷
                - label: 서브넷 라벨
                - alive_hosts: Phase 1 결과 (list[str])
                - port_map: Phase 2 결과 (dict[str, list[int]])
                - ...

        Returns:
            업데이트된 context (다음 Phase로 전달)
        """
        pass
```

**Context 전달 예시**:
```python
# Phase 1 → Phase 2
context = {
    "subnet": "172.20.1.0/24",
    "label": "172_20_1_0_24",
    "alive_hosts": ["172.20.1.10", "172.20.1.20", ...],
    "avg_rtt": 45.3
}

# Phase 2 → Phase 3
context = {
    ...,  # Phase 1 결과 유지
    "port_map": {
        "172.20.1.10": [22, 80, 443],
        "172.20.1.20": [3306, 8080]
    },
    "total_ports": 347
}
```

---

### 3. `CheckpointManager` (Resume 기능)

```python
# scanner/checkpoint.py
import json
from pathlib import Path
from typing import Any, Dict, Optional


class CheckpointManager:
    """체크포인트 관리 (Resume 기능)"""

    def __init__(self, scan_dir: Path):
        self.scan_dir = Path(scan_dir)
        self.checkpoint_dir = self.scan_dir / ".checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def is_subnet_completed(self, subnet_label: str) -> bool:
        """서브넷 완료 여부 확인"""
        marker = self.checkpoint_dir / f".subnet_{subnet_label}_complete"
        return marker.exists()

    def save_subnet_completion(self, subnet_label: str) -> None:
        """서브넷 완료 마킹"""
        marker = self.checkpoint_dir / f".subnet_{subnet_label}_complete"
        marker.touch()

    def is_phase_completed(self, subnet_label: str, phase_name: str) -> bool:
        """Phase 완료 여부 확인"""
        checkpoint_file = self._get_checkpoint_file(subnet_label, phase_name)
        return checkpoint_file.exists()

    def save_phase_completion(
        self, subnet_label: str, phase_name: str, context: Dict[str, Any]
    ) -> None:
        """Phase 완료 저장 (context 포함)"""
        checkpoint_file = self._get_checkpoint_file(subnet_label, phase_name)
        with open(checkpoint_file, "w") as f:
            json.dump(context, f, indent=2)

    def load_phase_context(
        self, subnet_label: str, phase_name: str
    ) -> Dict[str, Any]:
        """저장된 Phase context 로드"""
        checkpoint_file = self._get_checkpoint_file(subnet_label, phase_name)
        if not checkpoint_file.exists():
            return {}

        with open(checkpoint_file) as f:
            return json.load(f)

    def _get_checkpoint_file(self, subnet_label: str, phase_name: str) -> Path:
        """체크포인트 파일 경로 생성"""
        return self.checkpoint_dir / f"{subnet_label}_{phase_name}.json"
```

**Resume 동작 방식**:
1. `--resume` 플래그로 실행 시 최신 스캔 디렉토리 사용
2. `.checkpoints/` 디렉토리에서 완료된 서브넷/Phase 확인
3. 완료된 작업은 스킵, 미완료 작업부터 재개
4. Context는 JSON으로 저장/로드

---

## CLI 인터페이스 설계

### `rustscan_massive.py` (진입점)

```python
#!/usr/bin/env python3
"""대규모 네트워크 스캔 도구 (4단계 파이프라인)"""
import argparse
import asyncio
import getpass
import sys
from datetime import datetime
from pathlib import Path

from scanner.config import Config
from scanner.logger import ColorLogger
from scanner.scanner import Scanner
from utils.json_loader import load_targets


def parse_args() -> argparse.Namespace:
    """CLI 인자 파싱"""
    parser = argparse.ArgumentParser(
        description="대규모 네트워크 스캔 (rustscan + nmap 4단계)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 기본 스캔
  %(prog)s

  # 취약점 스캔 건너뛰기
  %(prog)s --skip-vuln

  # 브루트포스 건너뛰기
  %(prog)s --skip-bruteforce

  # 이전 스캔 재개
  %(prog)s --resume

  # 커스텀 워드리스트
  %(prog)s --wordlist-users custom_users.txt --wordlist-passwords custom_pass.txt
        """,
    )

    parser.add_argument(
        "--skip-vuln",
        action="store_true",
        help="Phase 4 (취약점 스캔) 건너뛰기",
    )
    parser.add_argument(
        "--skip-bruteforce",
        action="store_true",
        help="브루트포스 공격 건너뛰기",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="최신 스캔 디렉토리에서 재개",
    )
    parser.add_argument(
        "--wordlist-users",
        type=Path,
        help="사용자 이름 워드리스트 경로",
    )
    parser.add_argument(
        "--wordlist-passwords",
        type=Path,
        help="비밀번호 워드리스트 경로",
    )
    parser.add_argument(
        "--bruteforce-timeout",
        type=int,
        default=300,
        help="브루트포스 타임아웃 (초, 기본값: 300)",
    )
    parser.add_argument(
        "--bruteforce-threads",
        type=int,
        default=5,
        help="브루트포스 병렬 스레드 (기본값: 5)",
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=Path(__file__).parent / "targets.json",
        help="타겟 JSON 파일 경로 (기본값: ./targets.json)",
    )

    return parser.parse_args()


def get_scan_directory(resume: bool) -> Path:
    """스캔 디렉토리 결정"""
    scans_root = Path.home() / "nmap" / "scans"

    if resume:
        # 최신 rustscan_massive_* 디렉토리 찾기
        existing = sorted(
            scans_root.glob("rustscan_massive_*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if existing:
            return existing[0]
        else:
            ColorLogger.warning("기존 스캔 디렉토리 없음 - 새로 생성")

    # 새 디렉토리 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    scan_dir = scans_root / f"rustscan_massive_{timestamp}"
    scan_dir.mkdir(parents=True, exist_ok=True)
    return scan_dir


async def main() -> int:
    """메인 진입점"""
    args = parse_args()

    # 타겟 로드
    try:
        targets = load_targets(args.json)
    except Exception as e:
        ColorLogger.error(f"타겟 로드 실패: {e}")
        return 1

    # sudo 비밀번호 입력
    sudo_password = getpass.getpass("sudo 비밀번호: ")

    # Config 생성
    script_dir = Path(__file__).parent
    scan_dir = get_scan_directory(args.resume)

    config = Config(
        script_dir=script_dir,
        scan_dir=scan_dir,
        json_file=args.json,
        subnets=targets.subnets,
        exclude_ips=targets.exclude,
        skip_vuln=args.skip_vuln,
        skip_bruteforce=args.skip_bruteforce,
        resume=args.resume,
        sudo_password=sudo_password,
        wordlist_users=args.wordlist_users,
        wordlist_passwords=args.wordlist_passwords,
        bruteforce_timeout=args.bruteforce_timeout,
        bruteforce_threads=args.bruteforce_threads,
    )

    # 검증
    try:
        config.validate()
    except Exception as e:
        ColorLogger.error(f"설정 검증 실패: {e}")
        return 1

    # Scanner 실행
    scanner = Scanner(config)
    try:
        await scanner.run()
        ColorLogger.success("스캔 성공적으로 완료")
        return 0
    except KeyboardInterrupt:
        ColorLogger.warning("사용자에 의해 중단됨")
        return 130
    except Exception as e:
        ColorLogger.error(f"스캔 실패: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
```

**CLI 특징**:
- ✅ argparse 기반 명확한 인자 처리
- ✅ Resume 기능 (`--resume`)
- ✅ Skip 옵션 (`--skip-vuln`, `--skip-bruteforce`)
- ✅ 커스텀 워드리스트 지원
- ✅ 타임아웃/스레드 설정 가능

---

## Phase별 구현 개요

### Phase 1: HostDiscovery

**책임**:
- fping + nmap -sn 병렬 실행 (Health Check)
- 활성 호스트 목록 생성
- RTT 프로파일링 (샘플링)
- Phase 1 XML 생성 (포트 22,80,443)

**출력**:
- `alive_hosts_{label}.txt`
- `avg_rtt_{label}.txt`
- `phase1_{label}.xml`

**Context 업데이트**:
```python
{
    "alive_hosts": ["172.20.1.10", ...],
    "alive_count": 42,
    "avg_rtt": 45.3
}
```

---

### Phase 2: PortScanner

**책임**:
- RTT 기반 Rustscan 파라미터 최적화
- 전체 포트 스캔 (Main Scan)
- SAP 포트 재검증
- 포트 맵 생성 (IP:포트 리스트)

**출력**:
- `phase2_all_ports_{label}.txt`
- `phase2_port_map_{label}.txt`

**Context 업데이트**:
```python
{
    "port_map": {
        "172.20.1.10": [22, 80, 443],
        "172.20.1.20": [3306, 8080]
    },
    "total_ports": 347
}
```

---

### Phase 3: ServiceDetector

**책임**:
- nmap -sV -sC 서비스 버전 탐지
- OS 탐지 (조건: 포트 2개 이상)
- 타이밍 최적화 (호스트 수 기반)

**출력**:
- `phase3_detail_{ip}.xml` (서비스 스캔)
- `phase3_os_{ip}.xml` (OS 탐지)

**Context 업데이트**:
```python
{
    "service_scanned_count": 42,
    "os_scanned_count": 35
}
```

---

### Phase 4: VulnerabilityScannerWithBruteforce

**책임**:
- Critical 호스트 필터링 (SSH, RDP, HTTP, DB, SAP)
- 포트별 NSE 스크립트 선택
- 취약점 스캔 실행
- 브루트포스 공격 (선택적)

**출력**:
- `phase4_vuln_{ip}.xml` (취약점 스캔)
- `phase4_bruteforce_{ip}.txt` (브루트포스 결과)

**Context 업데이트**:
```python
{
    "critical_hosts_count": 25,
    "vulnerabilities_found": 12,
    "bruteforce_success": 3
}
```

---

## 데이터 흐름 다이어그램

```
[targets.json]
     ↓
[load_targets]
     ↓
[Config 생성 + 검증]
     ↓
[Scanner.run()]
     ↓
┌─────────────────────────────────────────┐
│  서브넷 루프 (순차)                       │
│  ┌───────────────────────────────────┐  │
│  │ Phase 1: HostDiscovery            │  │
│  │  - fping + nmap -sn 병렬          │  │
│  │  - RTT 프로파일링                  │  │
│  │  Output: alive_hosts, avg_rtt     │  │
│  └───────────────────────────────────┘  │
│            ↓ context                    │
│  ┌───────────────────────────────────┐  │
│  │ Phase 2: PortScanner              │  │
│  │  - Rustscan 병렬 (RTT 최적화)     │  │
│  │  - SAP 포트 재검증                 │  │
│  │  Output: port_map                 │  │
│  └───────────────────────────────────┘  │
│            ↓ context                    │
│  ┌───────────────────────────────────┐  │
│  │ Phase 3: ServiceDetector          │  │
│  │  - nmap -sV -sC 병렬              │  │
│  │  - OS 탐지 병렬                    │  │
│  │  Output: service XMLs             │  │
│  └───────────────────────────────────┘  │
│            ↓ context                    │
│  ┌───────────────────────────────────┐  │
│  │ Phase 4: VulnerabilityScannerWith │  │
│  │          Bruteforce               │  │
│  │  - Critical 호스트 필터링          │  │
│  │  - NSE 스캔 병렬                   │  │
│  │  - 브루트포스 병렬 (선택)          │  │
│  │  Output: vuln XMLs, bruteforce    │  │
│  └───────────────────────────────────┘  │
│            ↓                            │
│  [체크포인트 저장]                       │
└─────────────────────────────────────────┘
     ↓
[리포트 생성] (선택적)
     ↓
[완료]
```

---

## 통합 체크리스트

### Task #2-6 완료 후 확인 사항

- [ ] `phases/host_discovery.py` 구현 완료
- [ ] `phases/port_scanner.py` 구현 완료
- [ ] `phases/service_detector.py` 구현 완료
- [ ] `phases/vulnerability_scanner.py` 구현 완료
- [ ] `utils/rtt_optimizer.py` 구현 완료
- [ ] `wordlists/usernames.txt`, `wordlists/passwords.txt` 준비 완료

### Task #7 통합 작업

1. **scanner/checkpoint.py 구현**
   - CheckpointManager 클래스
   - JSON 기반 context 저장/로드

2. **scanner/scanner.py 구현**
   - Scanner 메인 클래스
   - Phase 오케스트레이션
   - Resume 로직

3. **rustscan_massive.py 구현**
   - CLI 진입점
   - argparse 설정
   - main() async 함수

4. **통합 테스트**
   - 단일 서브넷 전체 파이프라인 테스트
   - Resume 기능 테스트
   - 에러 핸들링 테스트

---

## 에러 핸들링 전략

### Phase별 에러 처리

```python
# scanner/scanner.py
async def run(self) -> None:
    for subnet in self.config.subnets:
        try:
            context = {"subnet": subnet, "label": label}

            for phase in self.phases:
                try:
                    context = await phase.execute(context)
                except PhaseError as e:
                    self.logger.error(f"{phase.name} 실패: {e}")
                    # Phase 실패 시 다음 서브넷으로 진행
                    break
                except Exception as e:
                    self.logger.error(f"{phase.name} 예외: {e}")
                    raise
        except KeyboardInterrupt:
            self.logger.warning("사용자 중단 - 체크포인트 저장")
            raise
        except Exception as e:
            self.logger.error(f"서브넷 {subnet} 처리 실패: {e}")
            # 다음 서브넷 계속 진행
            continue
```

### 복구 가능한 에러 vs 치명적 에러

**복구 가능**:
- 활성 호스트 0개 → 경고 후 다음 서브넷
- 포트 스캔 실패 → Phase 스킵
- 브루트포스 타임아웃 → 결과 기록 후 계속

**치명적**:
- targets.json 파싱 실패 → 즉시 종료
- sudo 권한 없음 → 즉시 종료
- 스캔 디렉토리 생성 실패 → 즉시 종료

---

## 성능 최적화 전략

### 1. 비동기 I/O (asyncio)
- 모든 subprocess 호출은 async
- 병렬 실행 제한 (Semaphore)

### 2. RTT 기반 파라미터 최적화
- Phase 1에서 평균 RTT 측정
- Phase 2에서 Rustscan 파라미터 자동 조정

### 3. 진행률 표시
- ProgressTracker 사용
- 주기적 상태 업데이트 (5개 단위)

### 4. 리소스 관리
- ulimit 자동 증가
- 파일 디스크립터 관리
- 임시 파일 정리

---

## 차이점: Bash vs Python

| 항목 | Bash | Python |
|------|------|--------|
| **타입 안전** | ❌ 없음 | ✅ 타입 힌트 |
| **에러 핸들링** | `set -e` | try-except |
| **비동기** | 백그라운드 (`&`) | asyncio |
| **데이터 구조** | 텍스트 파일 | 딕셔너리, 리스트 |
| **Resume** | 마커 파일 | JSON context |
| **테스트** | 어려움 | 유닛 테스트 가능 |
| **유지보수** | 복잡 (500줄+) | 모듈화, 명확 |

---

## 다음 단계 (Task #7)

1. **checkpoint.py 구현** (약 100줄)
2. **scanner.py 구현** (약 150줄)
3. **rustscan_massive.py 구현** (약 120줄)
4. **통합 테스트** (단일 서브넷)
5. **문서화** (README 업데이트)

---

## 참고 자료

- 기존 Bash 스크립트: `scripts/rustscan_massive_4phase.sh`
- Phase 구현 예시: `phases/host_discovery.py` (Task #2)
- 공통 모듈: `scanner/config.py`, `scanner/logger.py`, `utils/`

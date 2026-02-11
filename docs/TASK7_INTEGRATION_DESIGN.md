# Task #7: CLI + Scanner 통합 상세 설계

## 목표
Phase 1-4 모듈을 통합하여 완전한 스캔 파이프라인을 구축하고, 사용자 친화적인 CLI 제공.

---

## 구현 파일 목록

1. **scanner/checkpoint.py** (~100줄)
   - Resume 기능 구현
   - 서브넷별/Phase별 체크포인트 관리

2. **scanner/scanner.py** (~300줄)
   - Scanner 메인 클래스
   - Phase 오케스트레이션
   - 결과 집계 및 리포트 생성

3. **rustscan_massive.py** (~200줄)
   - CLI 진입점
   - argparse 인자 처리
   - Config 생성 및 검증

---

## 1. rustscan_massive.py 상세 설계

### CLI 인자 구조

```python
#!/usr/bin/env python3
"""대규모 네트워크 스캔 도구 (4단계 파이프라인)"""
import argparse
import asyncio
import getpass
import os
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
  # 기본 스캔 (targets.json 사용)
  %(prog)s

  # 취약점 스캔 건너뛰기
  %(prog)s --skip-vuln

  # 브루트포스 건너뛰기
  %(prog)s --skip-bruteforce

  # 이전 스캔 재개
  %(prog)s --resume

  # 커스텀 워드리스트
  %(prog)s --wordlist-users custom_users.txt --wordlist-passwords custom_pass.txt

  # sudo 비밀번호 환경변수로 전달 (자동화)
  export SUDO_PASSWORD="your_password"
  %(prog)s --skip-vuln
        """,
    )

    # 필수 인자
    parser.add_argument(
        "--json-file",
        type=Path,
        default=Path(__file__).parent / "targets.json",
        help="타겟 JSON 파일 경로 (기본값: ./targets.json)",
    )

    # 스킵 옵션
    parser.add_argument(
        "--skip-vuln",
        action="store_true",
        help="Phase 4 (취약점 스캔) 건너뛰기",
    )
    parser.add_argument(
        "--skip-bruteforce",
        action="store_true",
        help="브루트포스 공격 건너뛰기 (Phase 4 내)",
    )

    # Resume 옵션
    parser.add_argument(
        "--resume",
        action="store_true",
        help="최신 스캔 디렉토리에서 재개 (체크포인트 기반)",
    )

    # 스캔 디렉토리
    parser.add_argument(
        "--scan-dir",
        type=Path,
        help="스캔 결과 저장 디렉토리 (기본값: scans/rustscan_massive_YYYYMMDD_HHMMSS)",
    )

    # 브루트포스 설정
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

    # SAP 포트 (고급 옵션)
    parser.add_argument(
        "--sap-ports",
        type=str,
        default="3200,3300,3600,8000,8001,50000,50013,50014",
        help="SAP 포트 리스트 (기본값: 3200,3300,...)",
    )

    return parser.parse_args()


def get_scan_directory(args: argparse.Namespace) -> Path:
    """스캔 디렉토리 결정"""
    scans_root = Path.home() / "nmap" / "scans"

    # --scan-dir 명시적 지정
    if args.scan_dir:
        scan_dir = args.scan_dir
        scan_dir.mkdir(parents=True, exist_ok=True)
        return scan_dir

    # --resume 플래그
    if args.resume:
        existing = sorted(
            scans_root.glob("rustscan_massive_*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if existing:
            ColorLogger.info(f"Resume: {existing[0]}")
            return existing[0]
        else:
            ColorLogger.warning("기존 스캔 디렉토리 없음 - 새로 생성")

    # 새 디렉토리 생성 (타임스탬프)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    scan_dir = scans_root / f"rustscan_massive_{timestamp}"
    scan_dir.mkdir(parents=True, exist_ok=True)
    return scan_dir


def get_sudo_password() -> str:
    """sudo 비밀번호 획득 (환경변수 우선, 없으면 프롬프트)"""
    # 환경변수 SUDO_PASSWORD 체크
    sudo_password = os.getenv("SUDO_PASSWORD")
    if sudo_password:
        ColorLogger.info("sudo 비밀번호: 환경변수에서 로드")
        return sudo_password

    # 대화형 프롬프트
    return getpass.getpass("sudo 비밀번호: ")


async def main() -> int:
    """메인 진입점"""
    args = parse_args()

    # 타겟 로드
    try:
        targets = load_targets(args.json_file)
        ColorLogger.success(f"타겟 로드: {len(targets.subnets)}개 서브넷")
    except Exception as e:
        ColorLogger.error(f"타겟 로드 실패: {e}")
        return 1

    # sudo 비밀번호
    try:
        sudo_password = get_sudo_password()
    except KeyboardInterrupt:
        ColorLogger.warning("\n사용자 취소")
        return 130

    # 스캔 디렉토리
    scan_dir = get_scan_directory(args)

    # Config 생성
    script_dir = Path(__file__).parent
    config = Config(
        script_dir=script_dir,
        scan_dir=scan_dir,
        json_file=args.json_file,
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
        sap_ports=args.sap_ports,
    )

    # 검증
    try:
        config.validate()
        ColorLogger.success("설정 검증 완료")
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
        ColorLogger.warning("\n사용자에 의해 중단됨 (Ctrl+C)")
        ColorLogger.info("체크포인트 저장됨 - --resume으로 재개 가능")
        return 130
    except Exception as e:
        ColorLogger.error(f"스캔 실패: {e}")
        import traceback
        ColorLogger.debug(traceback.format_exc())
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        ColorLogger.warning("\n강제 종료")
        sys.exit(130)
```

**핵심 특징**:
- ✅ 환경변수 `SUDO_PASSWORD` 지원 (자동화 용이)
- ✅ Resume 디렉토리 자동 탐지
- ✅ 상세한 에러 메시지 및 트레이스백
- ✅ Ctrl+C 처리 (체크포인트 보존)

---

## 2. scanner/scanner.py 상세 설계

### Scanner 클래스 전체 구조

```python
# scanner/scanner.py
"""Scanner 메인 오케스트레이터"""
import asyncio
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from scanner.config import Config
from scanner.logger import ColorLogger, ProgressTracker
from scanner.checkpoint import CheckpointManager
from phases.host_discovery import HostDiscovery
from phases.port_scanner import PortScanner
from phases.service_detector import ServiceDetector
from phases.vulnerability_scanner import VulnerabilityScannerWithBruteforce


class ScanStatistics:
    """스캔 통계 추적"""

    def __init__(self):
        self.total_subnets = 0
        self.completed_subnets = 0
        self.total_hosts_discovered = 0
        self.total_ports_discovered = 0
        self.total_services_detected = 0
        self.total_vulnerabilities_found = 0
        self.total_bruteforce_success = 0
        self.start_time = time.time()

    def elapsed_time(self) -> str:
        """경과 시간 (MM:SS 형식)"""
        elapsed = int(time.time() - self.start_time)
        minutes, seconds = divmod(elapsed, 60)
        return f"{minutes}m{seconds:02d}s"

    def summary(self) -> str:
        """최종 요약 문자열"""
        return f"""
╔════════════════════════════════════════════════╗
║          스캔 완료 - 최종 요약                  ║
╠════════════════════════════════════════════════╣
║ 서브넷:          {self.completed_subnets}/{self.total_subnets}개 완료
║ 활성 호스트:     {self.total_hosts_discovered}개
║ 발견 포트:       {self.total_ports_discovered}개
║ 서비스 탐지:     {self.total_services_detected}개
║ 취약점 발견:     {self.total_vulnerabilities_found}개
║ 브루트포스 성공: {self.total_bruteforce_success}개
║ 총 실행 시간:    {self.elapsed_time()}
╚════════════════════════════════════════════════╝
        """


class Scanner:
    """4단계 스캔 오케스트레이터"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = ColorLogger
        self.checkpoint = CheckpointManager(config.scan_dir)
        self.stats = ScanStatistics()
        self.stats.total_subnets = len(config.subnets)

    async def run(self) -> None:
        """스캔 실행 (서브넷별 순차, Phase별 순차)"""
        self.logger.header("대규모 스캔 시작")
        self.logger.info(f"대상: {len(self.config.subnets)}개 서브넷")
        self.logger.info(f"스캔 디렉토리: {self.config.scan_dir}")

        if self.config.skip_vuln:
            self.logger.warning("Phase 4 (취약점 스캔) 건너뜀")
        if self.config.skip_bruteforce:
            self.logger.warning("브루트포스 공격 건너뜀")

        # 서브넷별 루프
        for i, subnet in enumerate(self.config.subnets, start=1):
            try:
                await self._run_subnet(i, subnet)
                self.stats.completed_subnets += 1
            except KeyboardInterrupt:
                self.logger.warning("사용자 중단 - 체크포인트 저장 중...")
                raise
            except Exception as e:
                self.logger.error(f"서브넷 {subnet} 처리 실패: {e}")
                # 다음 서브넷 계속 진행
                continue

        # 최종 집계
        await self._aggregate_results()
        await self._generate_final_report()

        # 요약 출력
        print(self.stats.summary())

    async def _run_subnet(self, index: int, subnet: str) -> None:
        """서브넷별 Phase 1-4 실행"""
        subnet_label = self._get_subnet_label(subnet)

        # Resume: 이미 완료된 서브넷 스킵
        if self.checkpoint.is_subnet_completed(subnet_label):
            self.logger.warning(f"서브넷 {subnet} 이미 완료 - 스킵")
            # 통계 업데이트 (체크포인트에서 로드)
            self._update_stats_from_checkpoint(subnet_label)
            return

        self.logger.separator()
        self.logger.info(f"[{index}/{len(self.config.subnets)}] 서브넷 처리: {subnet}")

        # Context 초기화
        context: Dict[str, Any] = {
            "subnet": subnet,
            "label": subnet_label,
        }

        # Phase 1: HostDiscovery
        context = await self._run_phase(
            "Phase1_HostDiscovery",
            subnet_label,
            lambda: HostDiscovery(self.config).execute(context),
        )
        if not context.get("alive_hosts"):
            self.logger.warning(f"서브넷 {subnet} - 활성 호스트 없음, 스킵")
            self.checkpoint.save_subnet_completion(subnet_label)
            return

        self.stats.total_hosts_discovered += len(context.get("alive_hosts", []))

        # Phase 2: PortScanner
        context = await self._run_phase(
            "Phase2_PortScanner",
            subnet_label,
            lambda: PortScanner(self.config).execute(context),
        )
        if not context.get("port_map"):
            self.logger.warning(f"서브넷 {subnet} - 포트 없음, Phase 3-4 스킵")
            self.checkpoint.save_subnet_completion(subnet_label)
            return

        self.stats.total_ports_discovered += context.get("total_ports", 0)

        # Phase 3: ServiceDetector
        context = await self._run_phase(
            "Phase3_ServiceDetector",
            subnet_label,
            lambda: ServiceDetector(self.config).execute(context),
        )
        self.stats.total_services_detected += context.get("service_scanned_count", 0)

        # Phase 4: VulnerabilityScannerWithBruteforce (선택적)
        if not self.config.skip_vuln:
            context = await self._run_phase(
                "Phase4_VulnerabilityScannerWithBruteforce",
                subnet_label,
                lambda: VulnerabilityScannerWithBruteforce(self.config).execute(context),
            )
            self.stats.total_vulnerabilities_found += context.get("vulnerabilities_found", 0)
            self.stats.total_bruteforce_success += context.get("bruteforce_success", 0)

        # 서브넷 완료 마킹
        self.checkpoint.save_subnet_completion(subnet_label, context)

    async def _run_phase(
        self,
        phase_name: str,
        subnet_label: str,
        phase_func,
    ) -> Dict[str, Any]:
        """Phase 실행 (체크포인트 + 에러 핸들링)"""
        # Resume: 이미 완료된 Phase 스킵
        if self.checkpoint.is_phase_completed(subnet_label, phase_name):
            self.logger.info(f"{phase_name} 이미 완료 - 체크포인트에서 로드")
            return self.checkpoint.load_phase_context(subnet_label, phase_name)

        # Phase 실행
        self.logger.phase(phase_name, f"시작")
        start_time = time.time()

        try:
            context = await phase_func()
            elapsed = time.time() - start_time
            self.logger.success(f"{phase_name} 완료 ({int(elapsed)}초)")

            # 체크포인트 저장
            self.checkpoint.save_phase_completion(subnet_label, phase_name, context)
            return context

        except Exception as e:
            self.logger.error(f"{phase_name} 실패: {e}")
            raise

    def _get_subnet_label(self, subnet: str) -> str:
        """서브넷 라벨 생성 (파일명 안전)"""
        return subnet.replace(".", "_").replace("/", "_")

    def _update_stats_from_checkpoint(self, subnet_label: str) -> None:
        """체크포인트에서 통계 복원"""
        final_context = self.checkpoint.load_subnet_context(subnet_label)
        if final_context:
            self.stats.total_hosts_discovered += len(final_context.get("alive_hosts", []))
            self.stats.total_ports_discovered += final_context.get("total_ports", 0)
            self.stats.total_services_detected += final_context.get("service_scanned_count", 0)
            self.stats.total_vulnerabilities_found += final_context.get("vulnerabilities_found", 0)
            self.stats.total_bruteforce_success += final_context.get("bruteforce_success", 0)

    async def _aggregate_results(self) -> None:
        """결과 집계 (모든 서브넷의 XML 파일 수집)"""
        self.logger.header("결과 집계")

        # Phase별 XML 파일 수집
        xml_files = {
            "phase1": list(self.config.scan_dir.glob("phase1_*.xml")),
            "phase3": list(self.config.scan_dir.glob("phase3_detail_*.xml")),
            "phase3_os": list(self.config.scan_dir.glob("phase3_os_*.xml")),
            "phase4": list(self.config.scan_dir.glob("phase4_vuln_*.xml")),
        }

        for phase, files in xml_files.items():
            self.logger.info(f"{phase}: {len(files)}개 XML 파일")

    async def _generate_final_report(self) -> None:
        """최종 리포트 생성 (xml_to_markdown.py 호출)"""
        self.logger.header("최종 리포트 생성")

        # xml_to_markdown.py 실행
        xml_script = self.config.script_dir / "xml_to_markdown.py"
        if not xml_script.exists():
            self.logger.warning("xml_to_markdown.py 없음 - 리포트 생성 스킵")
            return

        # 모든 XML 파일을 인자로 전달
        xml_files = list(self.config.scan_dir.glob("*.xml"))
        if not xml_files:
            self.logger.warning("XML 파일 없음 - 리포트 생성 스킵")
            return

        self.logger.info(f"리포트 생성 중... ({len(xml_files)}개 XML 파일)")

        # subprocess로 xml_to_markdown.py 실행
        from utils.subprocess_runner import run_command

        cmd = ["python3", str(xml_script)] + [str(f) for f in xml_files]
        result = await run_command(cmd, timeout=300)

        if result.success:
            self.logger.success("리포트 생성 완료")
        else:
            self.logger.error(f"리포트 생성 실패: {result.stderr}")
```

**핵심 특징**:
- ✅ ScanStatistics 클래스로 통계 추적
- ✅ Resume 시 체크포인트에서 통계 복원
- ✅ Phase별 독립적 에러 핸들링
- ✅ 최종 요약 박스 출력 (Bash 스크립트와 동일)
- ✅ xml_to_markdown.py 자동 호출

---

## 3. scanner/checkpoint.py 상세 설계

```python
# scanner/checkpoint.py
"""Resume 기능을 위한 체크포인트 관리"""
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

    def save_subnet_completion(
        self, subnet_label: str, final_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """서브넷 완료 마킹 (최종 context 저장)"""
        marker = self.checkpoint_dir / f".subnet_{subnet_label}_complete"

        if final_context:
            # 최종 context를 JSON으로 저장
            with open(marker, "w") as f:
                json.dump(final_context, f, indent=2, default=str)
        else:
            marker.touch()

    def load_subnet_context(self, subnet_label: str) -> Dict[str, Any]:
        """서브넷 최종 context 로드"""
        marker = self.checkpoint_dir / f".subnet_{subnet_label}_complete"
        if not marker.exists() or marker.stat().st_size == 0:
            return {}

        try:
            with open(marker) as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}

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
            json.dump(context, f, indent=2, default=str)

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

    def cleanup_old_checkpoints(self) -> None:
        """완료된 체크포인트 정리 (선택적)"""
        # 서브넷 완료 시 개별 Phase 체크포인트 삭제
        for marker in self.checkpoint_dir.glob(".subnet_*_complete"):
            subnet_label = marker.name.replace(".subnet_", "").replace("_complete", "")
            for phase_file in self.checkpoint_dir.glob(f"{subnet_label}_Phase*.json"):
                phase_file.unlink()
```

**핵심 특징**:
- ✅ JSON 기반 context 저장 (복잡한 데이터 구조 지원)
- ✅ 서브넷별 최종 context 저장 (통계 복원용)
- ✅ Phase별 개별 체크포인트
- ✅ 정리 기능 (디스크 공간 절약)

---

## 4. Phase 인터페이스 정의

### Context 전달 스키마

```python
# phases/base.py (이미 Task #2-6에서 구현됨)
from abc import ABC, abstractmethod
from typing import Any, Dict


class PhaseBase(ABC):
    """모든 Phase의 추상 기반 클래스"""

    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Phase 실행 메서드

        Args:
            context: 이전 Phase의 결과
                - subnet (str): 현재 서브넷 (예: "172.20.1.0/24")
                - label (str): 서브넷 라벨 (예: "172_20_1_0_24")
                - (Phase 1 추가) alive_hosts (list[str]): 활성 호스트 목록
                - (Phase 1 추가) avg_rtt (float): 평균 RTT (ms)
                - (Phase 2 추가) port_map (dict[str, list[int]]): IP별 포트 맵
                - (Phase 2 추가) total_ports (int): 총 포트 수
                - (Phase 3 추가) service_scanned_count (int): 서비스 스캔된 호스트 수
                - (Phase 4 추가) vulnerabilities_found (int): 발견된 취약점 수
                - (Phase 4 추가) bruteforce_success (int): 브루트포스 성공 수

        Returns:
            업데이트된 context (다음 Phase로 전달)
        """
        pass
```

### Context 전달 예시 (전체 파이프라인)

```python
# 초기 context (Scanner에서 생성)
context = {
    "subnet": "172.20.1.0/24",
    "label": "172_20_1_0_24"
}

# Phase 1 실행 후
context = {
    "subnet": "172.20.1.0/24",
    "label": "172_20_1_0_24",
    "alive_hosts": ["172.20.1.10", "172.20.1.20", "172.20.1.30"],
    "alive_count": 3,
    "avg_rtt": 45.3
}

# Phase 2 실행 후
context = {
    ...,  # Phase 1 결과 유지
    "port_map": {
        "172.20.1.10": [22, 80, 443],
        "172.20.1.20": [3306, 8080],
        "172.20.1.30": [22, 3389]
    },
    "total_ports": 7
}

# Phase 3 실행 후
context = {
    ...,  # Phase 1-2 결과 유지
    "service_scanned_count": 3,
    "os_scanned_count": 2
}

# Phase 4 실행 후 (최종)
context = {
    ...,  # Phase 1-3 결과 유지
    "critical_hosts_count": 2,
    "vulnerabilities_found": 5,
    "bruteforce_success": 1
}
```

---

## 5. 에러 시나리오 정의

### 시나리오 1: Phase 1에서 활성 호스트 0개
```python
# Scanner._run_subnet()
context = await self._run_phase("Phase1_HostDiscovery", ...)
if not context.get("alive_hosts"):
    self.logger.warning(f"서브넷 {subnet} - 활성 호스트 없음, 스킵")
    self.checkpoint.save_subnet_completion(subnet_label)
    return  # Phase 2-4 실행 안 함
```

### 시나리오 2: Phase 2에서 포트 0개
```python
context = await self._run_phase("Phase2_PortScanner", ...)
if not context.get("port_map"):
    self.logger.warning(f"서브넷 {subnet} - 포트 없음, Phase 3-4 스킵")
    self.checkpoint.save_subnet_completion(subnet_label)
    return
```

### 시나리오 3: Phase 실행 중 예외 발생
```python
try:
    context = await phase_func()
except Exception as e:
    self.logger.error(f"{phase_name} 실패: {e}")
    raise  # Scanner._run_subnet()으로 전파
```

### 시나리오 4: 서브넷 전체 실패
```python
# Scanner.run()
try:
    await self._run_subnet(i, subnet)
    self.stats.completed_subnets += 1
except Exception as e:
    self.logger.error(f"서브넷 {subnet} 처리 실패: {e}")
    continue  # 다음 서브넷 계속 진행
```

### 시나리오 5: 사용자 중단 (Ctrl+C)
```python
except KeyboardInterrupt:
    self.logger.warning("사용자 중단 - 체크포인트 저장 중...")
    raise  # main()에서 처리
```

### 시나리오 6: sudo 비밀번호 오류
```python
# Phase 내부에서 sudo 명령어 실패 시
result = await run_command(["sudo", ...], sudo_password=config.sudo_password)
if not result.success:
    if "password" in result.stderr.lower():
        raise ValueError("sudo 비밀번호 오류 - 다시 확인하세요")
    else:
        raise RuntimeError(f"명령어 실패: {result.stderr}")
```

---

## 6. 최종 요약 출력 형식

```
╔════════════════════════════════════════════════╗
║          스캔 완료 - 최종 요약                  ║
╠════════════════════════════════════════════════╣
║ 서브넷:          3/3개 완료
║ 활성 호스트:     42개
║ 발견 포트:       347개
║ 서비스 탐지:     42개
║ 취약점 발견:     12개
║ 브루트포스 성공: 3개
║ 총 실행 시간:    15m42s
╚════════════════════════════════════════════════╝

리포트 파일:
  - scans/rustscan_massive_20260211_103045/report.md

다음 단계:
  1. 리포트 검토: cat scans/.../report.md
  2. XML 파일 확인: ls -lh scans/.../*.xml
  3. 브루트포스 결과: grep "SUCCESS" scans/.../phase4_bruteforce_*.txt
```

---

## 7. 통합 체크리스트

### 사전 조건 (Task #2-6 완료)
- [ ] `phases/host_discovery.py` 구현 완료
- [ ] `phases/port_scanner.py` 구현 완료
- [ ] `phases/service_detector.py` 구현 완료
- [ ] `phases/vulnerability_scanner.py` 구현 완료
- [ ] `utils/rtt_optimizer.py` 구현 완료
- [ ] `wordlists/usernames.txt`, `wordlists/passwords.txt` 준비 완료

### Task #7 구현 순서
1. **scanner/checkpoint.py** 구현 및 테스트
2. **scanner/scanner.py** 구현 (ScanStatistics + Scanner)
3. **rustscan_massive.py** 구현 (CLI)
4. **통합 테스트** (단일 서브넷)
5. **Resume 기능 테스트**
6. **에러 시나리오 테스트**
7. **문서 업데이트** (README.md)

### 통합 테스트 시나리오
1. **정상 실행**: 모든 Phase 정상 완료
2. **Resume 테스트**: 중간에 중단 후 --resume으로 재개
3. **활성 호스트 0개**: Phase 1 결과 없을 때 graceful skip
4. **포트 0개**: Phase 2 결과 없을 때 graceful skip
5. **Skip 옵션**: --skip-vuln, --skip-bruteforce 동작 확인
6. **다중 서브넷**: 3개 서브넷 순차 처리 확인
7. **Ctrl+C 중단**: 체크포인트 보존 확인

---

## 8. 구현 예상 시간

| 파일 | 예상 시간 | 복잡도 |
|------|----------|--------|
| checkpoint.py | 30분 | 낮음 (JSON I/O) |
| scanner.py | 60분 | 중간 (오케스트레이션) |
| rustscan_massive.py | 40분 | 중간 (argparse + 검증) |
| 통합 테스트 | 30분 | 높음 (다양한 시나리오) |
| **총계** | **160분 (2.5시간)** | |

---

## 9. 구현 후 검증 체크리스트

- [ ] `python3 rustscan_massive.py --help` 출력 확인
- [ ] `python3 rustscan_massive.py` 정상 실행 (단일 서브넷)
- [ ] `python3 rustscan_massive.py --resume` Resume 동작 확인
- [ ] Ctrl+C 중단 후 --resume 재개 성공
- [ ] --skip-vuln 플래그 동작 확인
- [ ] 최종 요약 박스 출력 확인
- [ ] xml_to_markdown.py 자동 호출 확인
- [ ] 에러 메시지 가독성 확인

---

## 10. 다음 단계 (Task #8)

Task #7 완료 후 Task #8 (전체 통합 테스트 및 검증) 진행:
1. 실제 네트워크 환경에서 테스트
2. 성능 벤치마크 (Bash vs Python)
3. 메모리 사용량 모니터링
4. 대규모 서브넷 테스트 (10+ 서브넷)
5. 문서화 완성 (README.md, USAGE.md)

---

## 참고 자료

- 기존 Bash 스크립트: `scripts/rustscan_massive_4phase.sh`
- 공통 모듈: `scanner/config.py`, `scanner/logger.py`, `utils/`
- Phase 구현: `phases/host_discovery.py`, `phases/port_scanner.py`, ...
- 아키텍처 개요: `docs/SCANNER_ARCHITECTURE.md`

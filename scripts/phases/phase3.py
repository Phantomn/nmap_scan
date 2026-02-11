"""Phase 3: 서비스 버전 + OS 탐지"""
import asyncio
from pathlib import Path
from typing import Optional

from scanner.config import Config
from scanner.logger import ColorLogger, ProgressTracker
from utils.subprocess_runner import run_command


class ServiceDetector:
    """서비스 버전 및 OS 탐지를 수행하는 클래스"""

    def __init__(self, config: Config, subnet_label: str):
        self.config = config
        self.subnet_label = subnet_label
        self.scan_dir = config.scan_dir

        # 입력 파일
        self.alive_hosts_file = self.scan_dir / f"alive_hosts_{subnet_label}.txt"
        self.port_map_file = self.scan_dir / f"phase2_port_map_{subnet_label}.txt"

        # 출력 파일
        self.os_candidates_file = self.scan_dir / f"phase3_os_candidates_{subnet_label}.txt"

        # 병렬 실행 제한
        self.parallel_detail = 15  # 서비스 스캔
        self.parallel_os = 10  # OS 스캔

    async def run(self) -> None:
        """Phase 3 메인 실행 함수"""
        ColorLogger.phase("Phase 3", f"서비스 버전 + OS 탐지 (서브넷: {self.subnet_label})")

        # 활성 호스트 체크
        if not self._check_prerequisites():
            return

        # 포트 맵 로드
        port_map = self._load_port_map()
        if not port_map:
            ColorLogger.warning(f"⏭ Phase 3 건너뜀: 포트 맵 없음 ({self.subnet_label})")
            return

        host_count = len(port_map)
        ColorLogger.info(f"대상 호스트: {host_count}개")

        # 동적 타이밍 결정
        nmap_timing = self._get_nmap_timing(host_count)
        ColorLogger.info(f"nmap 타이밍: {nmap_timing}")

        # 1. 서비스 스캔
        ColorLogger.info(f"서비스 스캔 시작 ({host_count}개 호스트)")
        await self._service_scan(port_map, nmap_timing)

        # 2. OS 스캔
        await self._os_scan()

        ColorLogger.success(f"Phase 3 완료: {host_count}개 호스트 처리")

    def _check_prerequisites(self) -> bool:
        """사전 조건 체크 (활성 호스트 존재 여부)"""
        if not self.alive_hosts_file.exists() or self.alive_hosts_file.stat().st_size == 0:
            ColorLogger.warning(f"⏭ Phase 3 건너뜀: 활성 호스트 없음 ({self.subnet_label})")
            return False
        return True

    def _load_port_map(self) -> dict[str, list[int]]:
        """
        phase2_port_map 파일 로드

        형식: IP:포트1,포트2,포트3
        예: 192.168.1.1:22,80,443

        Returns:
            {IP: [포트 리스트]}
        """
        if not self.port_map_file.exists():
            return {}

        port_map = {}
        with open(self.port_map_file) as f:
            for line in f:
                line = line.strip()
                if not line or ":" not in line:
                    continue

                ip, ports_str = line.split(":", 1)
                ports = [int(p) for p in ports_str.split(",") if p.strip().isdigit()]

                if ports:
                    port_map[ip] = ports

        return port_map

    def _get_nmap_timing(self, host_count: int) -> str:
        """
        호스트 수에 따라 nmap 타이밍 결정

        - < 50개: -T5 (매우 빠름)
        - < 200개: -T4 (빠름)
        - >= 200개: -T3 (보통)
        """
        if host_count < 50:
            return "-T5"
        elif host_count < 200:
            return "-T4"
        else:
            return "-T3"

    def _get_version_intensity(self, port_count: int) -> str:
        """
        포트 수에 따라 버전 탐지 강도 결정

        - <= 5개: --version-all (최대 강도)
        - <= 20개: --version-intensity 7 (높음)
        - > 20개: --version-intensity 5 (보통)
        """
        if port_count <= 5:
            return "--version-all"
        elif port_count <= 20:
            return "--version-intensity 7"
        else:
            return "--version-intensity 5"

    async def _service_scan(self, port_map: dict[str, list[int]], nmap_timing: str) -> None:
        """
        서비스 버전 스캔 (nmap -sS -sV -sC)

        병렬 실행: 최대 15개 동시
        """
        semaphore = asyncio.Semaphore(self.parallel_detail)
        tasks = []

        for ip, ports in port_map.items():
            task = self._service_scan_single(ip, ports, nmap_timing, semaphore)
            tasks.append(task)

        # 진행률 추적
        tracker = ProgressTracker(len(tasks), prefix="서비스 스캔: ")
        completed = 0

        for coro in asyncio.as_completed(tasks):
            await coro
            completed += 1
            if completed % 5 == 0 or completed == len(tasks):
                tracker.update(5 if completed % 5 == 0 else completed % 5)

        if completed % 5 != 0:
            tracker.complete()

    async def _service_scan_single(
        self,
        ip: str,
        ports: list[int],
        nmap_timing: str,
        semaphore: asyncio.Semaphore,
    ) -> None:
        """단일 호스트 서비스 스캔"""
        async with semaphore:
            ip_safe = ip.replace(".", "_").replace("/", "_")
            ports_str = ",".join(str(p) for p in ports)
            port_count = len(ports)

            version_intensity = self._get_version_intensity(port_count)

            cmd = [
                "sudo",
                "-S",
                "nmap",
                "-sS",
                "-sV",
                "-sC",
                version_intensity,
                nmap_timing,
                "-p",
                ports_str,
                ip,
                "-oA",
                str(self.scan_dir / f"phase3_detail_{ip_safe}"),
                "--host-timeout",
                "10m",
                "--reason",
                "-v",
            ]

            try:
                await run_command(
                    cmd,
                    timeout=600,  # 10분 타임아웃
                    sudo_password=f"{self.config.sudo_password}\n",
                )
            except Exception as e:
                ColorLogger.error(f"서비스 스캔 실패 ({ip}): {e}")

    async def _os_scan(self) -> None:
        """
        OS 탐지 (nmap -O --osscan-guess)

        대상: 2개 이상 포트를 가진 호스트만
        병렬 실행: 최대 10개 동시
        """
        # OS 후보 추출 (2개 이상 포트 보유 호스트)
        self._extract_os_candidates()

        if not self.os_candidates_file.exists() or self.os_candidates_file.stat().st_size == 0:
            ColorLogger.info("OS 탐지 대상 없음 (2개 이상 포트 보유 호스트 없음)")
            return

        # OS 후보 로드
        with open(self.os_candidates_file) as f:
            os_hosts = [line.strip() for line in f if line.strip()]

        if not os_hosts:
            ColorLogger.info("OS 탐지 대상 없음")
            return

        ColorLogger.info(f"OS 탐지 시작 ({len(os_hosts)}개 호스트)")

        semaphore = asyncio.Semaphore(self.parallel_os)
        tasks = []

        for host in os_hosts:
            task = self._os_scan_single(host, semaphore)
            tasks.append(task)

        # 진행률 추적
        tracker = ProgressTracker(len(tasks), prefix="OS 탐지: ")
        completed = 0

        for coro in asyncio.as_completed(tasks):
            await coro
            completed += 1
            if completed % 5 == 0 or completed == len(tasks):
                tracker.update(5 if completed % 5 == 0 else completed % 5)

        if completed % 5 != 0:
            tracker.complete()

    def _extract_os_candidates(self) -> None:
        """
        phase2_port_map에서 2개 이상 포트를 가진 호스트 추출

        출력: phase3_os_candidates_{label}.txt
        """
        if not self.port_map_file.exists():
            self.os_candidates_file.touch()
            return

        os_candidates = []

        with open(self.port_map_file) as f:
            for line in f:
                line = line.strip()
                if not line or ":" not in line:
                    continue

                ip, ports_str = line.split(":", 1)
                port_count = len(ports_str.split(","))

                # 2개 이상 포트 보유 시 OS 탐지 후보
                if port_count >= 2:
                    os_candidates.append(ip)

        with open(self.os_candidates_file, "w") as f:
            f.write("\n".join(os_candidates))

    async def _os_scan_single(self, host: str, semaphore: asyncio.Semaphore) -> None:
        """단일 호스트 OS 스캔"""
        async with semaphore:
            host_safe = host.replace(".", "_").replace("/", "_")

            cmd = [
                "sudo",
                "-S",
                "nmap",
                "-O",
                "--osscan-guess",
                "-T4",
                host,
                "-oA",
                str(self.scan_dir / f"phase3_os_{host_safe}"),
            ]

            try:
                await run_command(
                    cmd,
                    timeout=300,  # 5분 타임아웃
                    sudo_password=f"{self.config.sudo_password}\n",
                )
            except Exception as e:
                ColorLogger.error(f"OS 스캔 실패 ({host}): {e}")


async def run_phase3(config: Config, subnet: str, subnet_label: str) -> None:
    """
    Phase 3 실행 함수 (외부 호출용)

    Args:
        config: 스캔 설정
        subnet: 서브넷 (예: 192.168.1.0/24)
        subnet_label: 서브넷 라벨 (파일명용)
    """
    detector = ServiceDetector(config, subnet_label)
    await detector.run()

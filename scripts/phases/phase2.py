"""Phase 2: 전체 포트 스캔 (rustscan 병렬 실행)"""
import asyncio
import resource
from pathlib import Path
from typing import Optional

from scanner.config import Config
from scanner.logger import ColorLogger, ProgressTracker
from utils.subprocess_runner import run_command
from utils.rtt_optimizer import optimize_rustscan_params


class PortScanner:
    """rustscan 기반 전체 포트 스캐너"""

    def __init__(self, config: Config, scan_dir: Path):
        self.config = config
        self.scan_dir = scan_dir
        self.logger = ColorLogger

    async def scan(self, subnet: str, label: str) -> Optional[Path]:
        """
        Phase 2 실행: 전체 포트 스캔

        Args:
            subnet: 스캔할 서브넷 (CIDR)
            label: 서브넷 레이블 (파일명용)

        Returns:
            포트 맵 파일 경로 (phase2_port_map_{label}.txt)
            활성 호스트가 없으면 None 반환
        """
        self.logger.header(f"Phase 2: 전체 포트 스캔 - {subnet}")

        # 사전 조건 확인
        alive_hosts_file = self.scan_dir / f"alive_hosts_{label}.txt"
        if not alive_hosts_file.exists() or alive_hosts_file.stat().st_size == 0:
            self.logger.warning(f"⏭ Phase 2 건너뜀: 활성 호스트 없음 ({subnet})")
            return None

        avg_rtt_file = self.scan_dir / f"avg_rtt_{label}.txt"
        if not avg_rtt_file.exists():
            self.logger.error(f"avg_rtt_{label}.txt 파일을 찾을 수 없음")
            raise FileNotFoundError(f"avg_rtt_{label}.txt")

        # RTT 기반 파라미터 최적화
        avg_rtt = float(avg_rtt_file.read_text().strip())
        params = optimize_rustscan_params(avg_rtt)

        self.logger.info(
            f"RTT {avg_rtt:.1f}ms → Batch={params.batch_size}, "
            f"Timeout={params.timeout}ms, 병렬={params.parallel_limit}"
        )

        # ulimit 검증 및 증가
        self._verify_and_increase_ulimit(params.required_ulimit)

        # 활성 호스트 목록 로드
        alive_hosts = alive_hosts_file.read_text().strip().split("\n")
        self.logger.info(f"Main 스캔 시작 ({len(alive_hosts)}개 호스트)")

        # Main 스캔 (전체 포트)
        main_results = await self._run_main_scan(alive_hosts, label, params)

        # SAP 스캔 (특정 포트)
        sap_results = await self._run_sap_scan(alive_hosts, label, params)

        # 결과 통합
        port_map_file = self._merge_results(main_results + sap_results, label)

        total_ports = sum(len(line.split(":")[1].split(",")) for line in port_map_file.read_text().strip().split("\n") if ":" in line)
        self.logger.success(f"Phase 2 완료: {total_ports}개 포트 발견")

        return port_map_file

    async def _run_main_scan(
        self, hosts: list[str], label: str, params
    ) -> list[Path]:
        """Main 스캔 실행 (전체 포트)"""
        results = []
        progress = ProgressTracker(len(hosts), "Main 스캔")

        semaphore = asyncio.Semaphore(params.parallel_limit)

        async def scan_host(host: str) -> Optional[Path]:
            async with semaphore:
                host_safe = host.replace(".", "_").replace("/", "_")
                output_file = self.scan_dir / f"phase2_rustscan_{host_safe}.txt"

                cmd = [
                    "rustscan",
                    "-a", host,
                    "-b", str(params.batch_size),
                    "-t", str(params.timeout),
                    "--tries", "1",
                    "--no-banner",
                    "-g",
                ]

                try:
                    result = await run_command(cmd, timeout=600)
                    if result.success and result.stdout.strip():
                        output_file.write_text(result.stdout)
                        progress.update()
                        return output_file
                except Exception as e:
                    self.logger.debug(f"Main 스캔 실패 ({host}): {e}")

                progress.update()
                return None

        tasks = [scan_host(host) for host in hosts]
        scan_results = await asyncio.gather(*tasks)

        return [r for r in scan_results if r is not None]

    async def _run_sap_scan(
        self, hosts: list[str], label: str, params
    ) -> list[Path]:
        """SAP 스캔 실행 (특정 포트)"""
        results = []
        progress = ProgressTracker(len(hosts), "SAP 스캔")

        semaphore = asyncio.Semaphore(params.parallel_limit)

        async def scan_host(host: str) -> Optional[Path]:
            async with semaphore:
                host_safe = host.replace(".", "_").replace("/", "_")
                output_file = self.scan_dir / f"phase2_sap_{host_safe}.txt"

                cmd = [
                    "rustscan",
                    "-a", host,
                    "-p", self.config.sap_ports,
                    "-b", "2000",
                    "-t", "1000",
                    "--tries", "1",
                    "--no-banner",
                    "-g",
                ]

                try:
                    result = await run_command(cmd, timeout=300)
                    if result.success and result.stdout.strip():
                        output_file.write_text(result.stdout)
                        progress.update()
                        return output_file
                except Exception as e:
                    self.logger.debug(f"SAP 스캔 실패 ({host}): {e}")

                progress.update()
                return None

        tasks = [scan_host(host) for host in hosts]
        scan_results = await asyncio.gather(*tasks)

        return [r for r in scan_results if r is not None]

    def _merge_results(self, result_files: list[Path], label: str) -> Path:
        """
        rustscan 결과 통합 및 포트 맵 생성

        Args:
            result_files: rustscan 출력 파일 리스트
            label: 서브넷 레이블

        Returns:
            phase2_port_map_{label}.txt 파일 경로 (형식: IP:PORT1,PORT2,...)
        """
        self.logger.info("결과 통합 중...")

        # 1. 모든 결과 파일에서 IP:PORT 추출
        all_ports_file = self.scan_dir / f"phase2_all_ports_{label}.txt"
        ip_ports: dict[str, set[str]] = {}

        for file in result_files:
            if not file.exists():
                continue

            content = file.read_text()
            # rustscan 출력 형식: "192.168.1.1 -> [22,80,443]"
            for line in content.split("\n"):
                if "->" not in line:
                    continue

                try:
                    # IP 추출
                    ip_part = line.split("->")[0].strip()
                    # 포트 추출 (대괄호 제거)
                    ports_part = line.split("->")[1].strip().strip("[]")

                    if not ports_part:
                        continue

                    # 포트 리스트 파싱
                    ports = [p.strip() for p in ports_part.split(",") if p.strip()]

                    if ip_part not in ip_ports:
                        ip_ports[ip_part] = set()
                    ip_ports[ip_part].update(ports)

                except (IndexError, ValueError):
                    continue

        # 2. IP:PORT 형식으로 저장 (중복 제거)
        with all_ports_file.open("w") as f:
            for ip in sorted(ip_ports.keys()):
                for port in sorted(ip_ports[ip], key=lambda x: int(x) if x.isdigit() else 0):
                    f.write(f"{ip}:{port}\n")

        # 3. 포트 맵 생성 (IP:PORT1,PORT2,... 형식)
        port_map_file = self.scan_dir / f"phase2_port_map_{label}.txt"
        with port_map_file.open("w") as f:
            for ip in sorted(ip_ports.keys()):
                ports_str = ",".join(sorted(ip_ports[ip], key=lambda x: int(x) if x.isdigit() else 0))
                f.write(f"{ip}:{ports_str}\n")

        return port_map_file

    def _verify_and_increase_ulimit(self, required_ulimit: int) -> None:
        """
        ulimit 검증 및 자동 증가

        Args:
            required_ulimit: 필요한 최소 ulimit 값

        Raises:
            RuntimeError: ulimit 증가 실패 시
        """
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)

        if soft >= required_ulimit:
            self.logger.debug(f"ulimit 충분: {soft} >= {required_ulimit}")
            return

        # soft limit 증가 시도
        try:
            new_soft = min(required_ulimit, hard)
            resource.setrlimit(resource.RLIMIT_NOFILE, (new_soft, hard))
            self.logger.info(f"ulimit 증가: {soft} → {new_soft}")
        except (ValueError, OSError) as e:
            self.logger.error(
                f"ulimit 증가 실패: sudo를 사용하거나 /etc/security/limits.conf 수정 필요\n"
                f"현재: {soft}, 필요: {required_ulimit}, 에러: {e}"
            )
            raise RuntimeError(f"ulimit 증가 실패 ({soft} < {required_ulimit})") from e

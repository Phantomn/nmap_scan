"""Phase 2: 전체 포트 스캔 (rustscan 병렬 실행)"""
import asyncio
import resource
from pathlib import Path
from typing import Optional

from scanner.config import Config
from scanner.logger import ColorLogger, ProgressTracker
from utils.subprocess_runner import run_command
from utils.rtt_optimizer import get_safe_rustscan_params


class PortScanner:
    """rustscan 기반 전체 포트 스캐너 (rustscan 포트 발견 + nmap -sV -sC 분석)"""

    def __init__(self, config: Config, scan_dir: Path):
        self.config = config
        self.scan_dir = scan_dir
        self.logger = ColorLogger

    async def scan(
        self, subnet: str, label: str
    ) -> None:
        """
        Phase 2 실행: 전체 포트 스캔

        Args:
            subnet: 스캔할 서브넷 (CIDR)
            label: 서브넷 레이블 (파일명용)

        Returns:
            None (각 호스트별 scan_{host}.nmap 파일 생성)
        """
        self.logger.header(f"Phase 2: 전체 포트 스캔 - {subnet}")

        # 사전 조건 확인
        alive_hosts_file = self.scan_dir / f"alive_hosts_{label}.txt"
        if not alive_hosts_file.exists() or alive_hosts_file.stat().st_size == 0:
            self.logger.warning(f"⏭ Phase 2 건너뜀: 활성 호스트 없음 ({subnet})")
            return None

        # 안전 모드 파라미터 사용
        params = get_safe_rustscan_params()
        self.logger.info(f"안전 모드: Batch={params.batch_size}, Timeout={params.timeout}ms, 병렬={params.parallel_limit}")

        # ulimit 검증 및 증가
        self._verify_and_increase_ulimit(params.required_ulimit)

        # 활성 호스트 목록 로드
        alive_hosts = alive_hosts_file.read_text().strip().split("\n")
        self.logger.info(f"Main 스캔 시작 ({len(alive_hosts)}개 호스트)")

        # Main 스캔 (전체 포트)
        await self._run_main_scan(alive_hosts, label, params)

        self.logger.success(f"Phase 2 완료: rustscan+nmap 스캔 완료 ({len(alive_hosts)}개 호스트)")

        return None

    async def _run_main_scan(
        self, hosts: list[str], label: str, params
    ) -> None:
        """Main 스캔 실행 (전체 포트, nmap -sV -sC pass-through)"""
        progress = ProgressTracker(len(hosts), "rustscan+nmap 스캔")

        semaphore = asyncio.Semaphore(params.parallel_limit)

        async def scan_host(host: str) -> None:
            async with semaphore:
                host_safe = host.replace(".", "_").replace("/", "_")

                cmd = [
                    "rustscan",
                    "-a", host,
                    "-b", str(params.batch_size),
                    "-t", str(params.timeout),
                    "--ulimit", str(params.required_ulimit),
                    "--",                                      # nmap pass-through
                    "-Pn",                                     # 호스트 발견 스킵 (Phase 1 완료)
                    "-T4",                                     # T3→T4 (Phase 1 검증 완료)
                    "-sV", "-sC",                              # -A → -sV -sC (OS/traceroute 제거)
                    "-n",                                      # DNS 비활성화
                    "--max-retries", "2",                      # 재시도 최소화
                    "--host-timeout", "240s",                  # 개별 호스트 4분 제한
                    "-v",                                      # 상세 출력
                    "-oN", str(self.scan_dir / f"scan_{host_safe}.nmap")
                ]

                try:
                    await run_command(cmd, timeout=600)
                    progress.update()
                except Exception as e:
                    self.logger.debug(f"스캔 실패 ({host}): {e}")
                    progress.update()

        tasks = [scan_host(host) for host in hosts]
        await asyncio.gather(*tasks)


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

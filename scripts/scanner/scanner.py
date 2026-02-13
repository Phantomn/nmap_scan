"""Scanner 메인 오케스트레이터"""
import asyncio
import time
from pathlib import Path
from typing import List, Set

from scanner.config import Config
from scanner.logger import ColorLogger
from phases.phase1 import HostDiscovery
from phases.phase2 import PortScanner


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
        self.total_web_bruteforce_success = 0
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
║ 서브넷:              {self.completed_subnets}/{self.total_subnets}개 완료
║ 활성 호스트:         {self.total_hosts_discovered}개
║ 발견 포트:           {self.total_ports_discovered}개
║ 서비스 탐지:         {self.total_services_detected}개
║ 취약점 발견:         {self.total_vulnerabilities_found}개
║ 브루트포스 성공:     {self.total_bruteforce_success}개
║ Web 브루트포스 성공: {self.total_web_bruteforce_success}개
║ 총 실행 시간:        {self.elapsed_time()}
╚════════════════════════════════════════════════╝
        """


class Scanner:
    """4단계 스캔 오케스트레이터"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = ColorLogger
        self.stats = ScanStatistics()
        self.stats.total_subnets = len(config.subnets)

    async def run(self) -> None:
        """스캔 실행 (서브넷별 순차, Phase별 순차)"""
        self.logger.header("대규모 스캔 시작")
        self.logger.info(f"대상: {len(self.config.subnets)}개 서브넷")
        self.logger.info(f"스캔 디렉토리: {self.config.scan_dir}")

        # 서브넷별 루프
        for i, subnet in enumerate(self.config.subnets, start=1):
            try:
                await self._run_subnet(i, subnet)
                self.stats.completed_subnets += 1
            except KeyboardInterrupt:
                self.logger.warning("사용자 중단...")
                raise
            except Exception as e:
                self.logger.error(f"서브넷 {subnet} 처리 실패: {e}")
                # 다음 서브넷 계속 진행
                continue

        # 요약 출력
        print(self.stats.summary())

    async def _run_subnet(self, index: int, subnet: str) -> None:
        """서브넷별 Phase 1-2 실행"""
        subnet_label = self._get_subnet_label(subnet)

        self.logger.separator()
        self.logger.info(f"[{index}/{len(self.config.subnets)}] 서브넷 처리: {subnet}")

        # Phase 1: HostDiscovery
        phase1 = HostDiscovery(self.config, subnet, subnet_label)

        try:
            alive_hosts = await phase1.health_check_hybrid()

            if not alive_hosts:
                self.logger.warning(f"서브넷 {subnet} - 활성 호스트 없음, 스킵")
                return

            self.stats.total_hosts_discovered += len(alive_hosts)
            self.logger.success(f"Phase 1 완료: {len(alive_hosts)}개 호스트 발견")

            # RTT 프로파일링
            avg_rtt = await phase1.profile_rtt(alive_hosts)
            self.logger.info(f"평균 RTT: {avg_rtt:.1f}ms")

        except Exception as e:
            self.logger.error(f"Phase 1 실패: {e}")
            raise

        # Phase 2: PortScanner (rustscan + nmap)
        phase2 = PortScanner(self.config, self.config.scan_dir)

        try:
            await phase2.scan(subnet, subnet_label, avg_rtt=avg_rtt)
        except Exception as e:
            self.logger.error(f"Phase 2 실패: {e}")
            raise

    def _get_subnet_label(self, subnet: str) -> str:
        """서브넷 라벨 생성 (파일명 안전)"""
        return subnet.replace(".", "_").replace("/", "_")

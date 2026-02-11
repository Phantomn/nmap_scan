"""Scanner 메인 오케스트레이터"""
import asyncio
import time
from pathlib import Path
from typing import List, Set

from scanner.config import Config
from scanner.logger import ColorLogger
from scanner.checkpoint import CheckpointManager
from phases.phase1 import HostDiscovery
from phases.phase2 import PortScanner
from phases.phase3 import ServiceDetector
from phases.phase4 import VulnerabilityScannerWithBruteforce


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

        # Resume: 체크포인트 확인 (구 형식)
        if self.checkpoint.exists():
            checkpoint_data = self.checkpoint.load()
            if checkpoint_data and checkpoint_data.phase >= 4:
                self.logger.warning(f"서브넷 {subnet} 이미 완료 - 스킵")
                return

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

            # 체크포인트 저장
            self.checkpoint.update_phase(2)

        except Exception as e:
            self.logger.error(f"Phase 1 실패: {e}")
            raise

        # Phase 2: PortScanner
        phase2 = PortScanner(self.config, self.config.scan_dir)

        try:
            port_map_file = await phase2.scan(subnet, subnet_label)

            if not port_map_file or not port_map_file.exists():
                self.logger.warning(f"서브넷 {subnet} - 포트 없음, Phase 3-4 스킵")
                return

            # 포트 맵 파일에서 포트 수 계산
            port_map_content = port_map_file.read_text().strip()
            if port_map_content:
                total_ports = sum(
                    len(line.split(":")[1].split(","))
                    for line in port_map_content.split("\n")
                    if ":" in line
                )
                self.stats.total_ports_discovered += total_ports
                host_count = len(port_map_content.split("\n"))
                self.logger.success(f"Phase 2 완료: {host_count}개 호스트, {total_ports}개 포트")

                # 체크포인트 저장
                self.checkpoint.update_phase(3)
            else:
                self.logger.warning(f"서브넷 {subnet} - 포트 없음, Phase 3-4 스킵")
                return

        except Exception as e:
            self.logger.error(f"Phase 2 실패: {e}")
            raise

        # Phase 3: ServiceDetector
        phase3 = ServiceDetector(self.config, subnet_label)

        try:
            await phase3.run()
            # Phase 3는 XML 파일 수로 통계 계산
            xml_count = len(list(self.config.scan_dir.glob(f"phase3_detail_*.xml")))
            self.stats.total_services_detected += xml_count
            self.logger.success(f"Phase 3 완료: {xml_count}개 호스트 서비스 탐지")

            # 체크포인트 저장
            if not self.config.skip_vuln:
                self.checkpoint.update_phase(4)

        except Exception as e:
            self.logger.error(f"Phase 3 실패: {e}")
            raise

        # Phase 4: VulnerabilityScannerWithBruteforce (선택적)
        if not self.config.skip_vuln:
            phase4 = VulnerabilityScannerWithBruteforce(self.config, self.config.scan_dir)

            try:
                result = await phase4.run(subnet, subnet_label)
                vuln_count = result.get("vulnerabilities_found", 0)
                bruteforce_success = result.get("bruteforce_success", 0)
                web_bruteforce_success = result.get("web_bruteforce_success", 0)
                self.stats.total_vulnerabilities_found += vuln_count
                self.stats.total_bruteforce_success += bruteforce_success
                self.stats.total_web_bruteforce_success += web_bruteforce_success
                self.logger.success(
                    f"Phase 4 완료: 취약점 {vuln_count}개, "
                    f"브루트포스 성공 {bruteforce_success}개, "
                    f"Web 브루트포스 성공 {web_bruteforce_success}개"
                )

                # 체크포인트 정리 (완료)
                self.checkpoint.clear()

            except Exception as e:
                self.logger.error(f"Phase 4 실패: {e}")
                raise
        else:
            # skip_vuln=True일 경우 Phase 3 완료 후 체크포인트 정리
            self.checkpoint.clear()

    def _get_subnet_label(self, subnet: str) -> str:
        """서브넷 라벨 생성 (파일명 안전)"""
        return subnet.replace(".", "_").replace("/", "_")

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
        xml_script = self.config.script_dir / "utils" / "xml_to_markdown.py"
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

        # 출력 파일 경로
        output_file = self.config.scan_dir / "FINAL_REPORT.md"

        cmd = [
            "python3",
            str(xml_script),
            "--scan-dir", str(self.config.scan_dir),
            "--output", str(output_file)
        ]

        try:
            result = await run_command(cmd, timeout=300)

            if result.success:
                self.logger.success(f"리포트 생성 완료: {output_file}")
            else:
                self.logger.error(f"리포트 생성 실패: {result.stderr}")
        except Exception as e:
            self.logger.error(f"리포트 생성 예외: {e}")

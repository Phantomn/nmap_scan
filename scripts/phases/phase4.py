"""Phase 4: 취약점 스캔 + 브루트포스"""
import asyncio
import json
from pathlib import Path
from typing import Optional

from scanner.config import Config
from scanner.logger import ColorLogger, ProgressTracker
from utils.nse_script_selector import select_nse_scripts, should_run_bruteforce
from utils.subprocess_runner import run_command


class VulnerabilityScannerWithBruteforce:
    """취약점 스캔 + 브루트포스 Phase"""

    def __init__(self, config: Config, scan_dir: Path):
        self.config = config
        self.logger = ColorLogger
        self.scan_dir = scan_dir

    async def run(self, subnet: str, label: str) -> dict:
        """
        Phase 4 실행: Critical 호스트 대상 취약점 스캔 + 브루트포스

        Args:
            subnet: 서브넷 CIDR
            label: 서브넷 라벨 (파일명용)

        Returns:
            실행 결과 딕셔너리
        """
        self.logger.phase_header(4, "취약점 스캔 (Critical Hosts)", subnet)

        # alive_hosts 파일 체크
        alive_hosts_file = self.scan_dir / f"alive_hosts_{label}.txt"
        if not alive_hosts_file.exists() or alive_hosts_file.stat().st_size == 0:
            self.logger.warn(f"⏭ Phase 4 건너뜀: 활성 호스트 없음 ({subnet})")
            return {"skipped": True, "reason": "no_alive_hosts"}

        # phase2_port_map 파일 체크
        port_map_file = self.scan_dir / f"phase2_port_map_{label}.txt"
        if not port_map_file.exists() or port_map_file.stat().st_size == 0:
            self.logger.warn(f"⏭ Phase 4 건너뜀: 포트 맵 없음 ({subnet})")
            return {"skipped": True, "reason": "no_port_map"}

        # Critical 호스트 추출
        critical_hosts = await self._extract_critical_hosts(port_map_file, label)

        if not critical_hosts:
            self.logger.info("Critical 호스트 없음")
            return {"critical_hosts": 0, "scans_completed": 0}

        self.logger.info(f"NSE 스캔 시작 ({len(critical_hosts)}개 호스트)")

        # NSE 스캔 병렬 실행 (최대 5개)
        nse_results = await self._run_nse_scans(critical_hosts, label)

        # 브루트포스 실행 (옵션)
        bruteforce_results = {}
        if not self.config.skip_bruteforce:
            bruteforce_results = await self._run_bruteforce_scans(critical_hosts, label)

        # 결과 파싱 (취약점 및 브루트포스 성공 케이스)
        parsed_results = await self.parse_results(label)

        return {
            "critical_hosts": len(critical_hosts),
            "nse_scans": nse_results,
            "bruteforce_scans": bruteforce_results,
            # scanner.py 호환 키
            "vulnerabilities_found": len(parsed_results.get("vulnerabilities", [])),
            "bruteforce_success": len(parsed_results.get("bruteforce_success", [])),
        }

    async def _extract_critical_hosts(
        self, port_map_file: Path, label: str
    ) -> dict[str, str]:
        """
        Critical 포트를 가진 호스트 추출

        Critical 포트:
        - 22, 3389, 5900 (RDP, SSH, VNC)
        - 80, 443, 8080, 8443 (HTTP/HTTPS)
        - 3306, 5432, 1433, 27017 (DB)
        - 3200, 3300, 8000, 50000 (SAP)

        Returns:
            {IP: "포트목록"} 딕셔너리
        """
        critical_ports = {
            "22", "3389", "5900",  # 원격 접속
            "80", "443", "8080", "8443",  # 웹
            "3306", "5432", "1433", "27017",  # DB
            "3200", "3300", "8000", "50000",  # SAP
            "21", "23",  # FTP, Telnet (브루트포스 대상)
        }

        critical_hosts = {}

        with open(port_map_file) as f:
            for line in f:
                line = line.strip()
                if not line or ":" not in line:
                    continue

                ip, ports_str = line.split(":", 1)
                ports = set(p.strip() for p in ports_str.split(","))

                # Critical 포트가 하나라도 있으면 추가
                if ports & critical_ports:
                    critical_hosts[ip] = ports_str

        # Critical 호스트 목록 저장
        critical_file = self.scan_dir / f"phase4_critical_hosts_{label}.txt"
        with open(critical_file, "w") as f:
            for ip in sorted(critical_hosts.keys()):
                f.write(f"{ip}\n")

        return critical_hosts

    async def _run_nse_scans(
        self, critical_hosts: dict[str, str], label: str
    ) -> dict:
        """
        NSE 스크립트 병렬 실행

        Args:
            critical_hosts: {IP: "포트목록"}
            label: 서브넷 라벨

        Returns:
            실행 결과 통계
        """
        semaphore = asyncio.Semaphore(5)  # 최대 5개 병렬
        tracker = ProgressTracker(len(critical_hosts), "NSE 스캔")

        # NSE 선택 로그 파일
        nse_log_file = self.scan_dir / f"phase4_nse_selection_{label}.log"
        nse_log_lines = []

        async def scan_host(ip: str, ports: str):
            async with semaphore:
                ip_safe = ip.replace(".", "_").replace("/", "_")

                # NSE 스크립트 선택
                nse_scripts = select_nse_scripts(ports)

                # 로그 기록
                nse_log_lines.append(f"[{ip}] Ports: {ports}")
                nse_log_lines.append(f"[{ip}] Scripts: {nse_scripts}")
                nse_log_lines.append("")

                # nmap NSE 스캔
                cmd = [
                    "nmap",
                    "--script", nse_scripts,
                    "-sV",
                    "-p", ports,
                    ip,
                    "-oA", str(self.scan_dir / f"phase4_vuln_{ip_safe}"),
                    "--host-timeout", "10m",
                ]

                result = await run_command(
                    cmd,
                    timeout=600,  # 10분
                    sudo_password=self.config.sudo_password,
                )

                tracker.increment()
                if tracker.should_log():
                    self.logger.progress(tracker.format())

                return result.success

        tasks = [scan_host(ip, ports) for ip, ports in critical_hosts.items()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # NSE 로그 저장
        with open(nse_log_file, "w") as f:
            f.write("\n".join(nse_log_lines))

        success_count = sum(1 for r in results if r is True)
        return {
            "total": len(critical_hosts),
            "success": success_count,
            "failed": len(critical_hosts) - success_count,
        }

    async def _run_bruteforce_scans(
        self, critical_hosts: dict[str, str], label: str
    ) -> dict:
        """
        브루트포스 스캔 실행 (FTP, SSH, Telnet)

        Args:
            critical_hosts: {IP: "포트목록"}
            label: 서브넷 라벨

        Returns:
            실행 결과 통계
        """
        # 워드리스트 검증
        if not self.config.wordlist_users.exists():
            self.logger.warn(f"사용자 워드리스트 없음: {self.config.wordlist_users}")
            return {"skipped": True, "reason": "no_wordlist"}

        if not self.config.wordlist_passwords.exists():
            self.logger.warn(f"비밀번호 워드리스트 없음: {self.config.wordlist_passwords}")
            return {"skipped": True, "reason": "no_wordlist"}

        # 브루트포스 대상 필터링
        bruteforce_targets = {}
        for ip, ports in critical_hosts.items():
            services = []
            if should_run_bruteforce(ports, "ftp"):
                services.append("ftp")
            if should_run_bruteforce(ports, "ssh"):
                services.append("ssh")
            if should_run_bruteforce(ports, "telnet"):
                services.append("telnet")

            if services:
                bruteforce_targets[ip] = services

        if not bruteforce_targets:
            self.logger.info("브루트포스 대상 없음 (FTP/SSH/Telnet)")
            return {"targets": 0, "scans_completed": 0}

        self.logger.info(
            f"브루트포스 시작 ({len(bruteforce_targets)}개 호스트, "
            f"서비스: FTP/SSH/Telnet)"
        )

        semaphore = asyncio.Semaphore(3)  # 최대 3개 병렬 (부하 고려)
        tracker = ProgressTracker(len(bruteforce_targets), "브루트포스")

        async def bruteforce_host(ip: str, services: list[str]):
            async with semaphore:
                ip_safe = ip.replace(".", "_").replace("/", "_")
                results = []

                for service in services:
                    script_map = {
                        "ftp": "ftp-brute",
                        "ssh": "ssh-brute",
                        "telnet": "telnet-brute",
                    }
                    script_name = script_map[service]

                    # nmap 브루트포스 스크립트
                    cmd = [
                        "nmap",
                        "--script", script_name,
                        "--script-args",
                        f"userdb={self.config.wordlist_users},"
                        f"passdb={self.config.wordlist_passwords},"
                        f"brute.threads={self.config.bruteforce_threads}",
                        "-p", self._get_service_port(service),
                        ip,
                        "-oA", str(self.scan_dir / f"phase4_bruteforce_{service}_{ip_safe}"),
                        "--host-timeout", f"{self.config.bruteforce_timeout}s",
                    ]

                    result = await run_command(
                        cmd,
                        timeout=self.config.bruteforce_timeout,
                        sudo_password=self.config.sudo_password,
                    )

                    results.append({
                        "service": service,
                        "success": result.success,
                    })

                tracker.increment()
                if tracker.should_log():
                    self.logger.progress(tracker.format())

                return results

        tasks = [
            bruteforce_host(ip, services)
            for ip, services in bruteforce_targets.items()
        ]
        all_results = await asyncio.gather(*tasks, return_exceptions=True)

        # 통계 집계
        total_scans = sum(
            len(r) for r in all_results if isinstance(r, list)
        )
        success_scans = sum(
            sum(1 for scan in r if scan["success"])
            for r in all_results
            if isinstance(r, list)
        )

        return {
            "targets": len(bruteforce_targets),
            "total_scans": total_scans,
            "success": success_scans,
            "failed": total_scans - success_scans,
        }

    def _get_service_port(self, service: str) -> str:
        """서비스별 기본 포트 반환"""
        port_map = {
            "ftp": "21",
            "ssh": "22",
            "telnet": "23",
        }
        return port_map.get(service, "")

    async def parse_results(self, label: str) -> dict:
        """
        Phase 4 결과 파싱 및 JSON 생성

        Args:
            label: 서브넷 라벨

        Returns:
            파싱된 결과 딕셔너리
        """
        results = {
            "vulnerabilities": [],
            "cves": [],
            "bruteforce_success": [],
        }

        # 취약점 정보 파싱
        vuln_files = list(self.scan_dir.glob(f"phase4_vuln_*.nmap"))
        for vuln_file in vuln_files:
            with open(vuln_file) as f:
                content = f.read()

                # VULNERABLE 키워드 추출
                for line in content.splitlines():
                    if "VULNERABLE" in line:
                        results["vulnerabilities"].append(line.strip())

                # CVE 추출
                import re
                cves = re.findall(r"CVE-\d{4}-\d+", content)
                results["cves"].extend(cves)

        # 브루트포스 성공 케이스 파싱
        bruteforce_files = list(self.scan_dir.glob(f"phase4_bruteforce_*.nmap"))
        for bf_file in bruteforce_files:
            with open(bf_file) as f:
                content = f.read()

                # 성공 케이스 파싱 (예: Valid credentials)
                if "Valid credentials" in content or "login:" in content:
                    ip = bf_file.stem.split("_")[-1].replace("_", ".")
                    service = bf_file.stem.split("_")[2]
                    results["bruteforce_success"].append({
                        "ip": ip,
                        "service": service,
                        "file": str(bf_file),
                    })

        # 중복 제거
        results["cves"] = list(set(results["cves"]))

        # JSON 저장
        json_file = self.scan_dir / f"phase4_results_{label}.json"
        with open(json_file, "w") as f:
            json.dump(results, f, indent=2)

        self.logger.info(
            f"Phase 4 결과: 취약점 {len(results['vulnerabilities'])}개, "
            f"CVE {len(results['cves'])}개, "
            f"브루트포스 성공 {len(results['bruteforce_success'])}개"
        )

        return results

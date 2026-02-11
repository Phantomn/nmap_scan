"""스캔 결과 집계 및 리포트 생성 모듈"""
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class HostResult:
    """호스트별 스캔 결과"""

    ip: str
    hostname: Optional[str] = None
    open_ports: list[int] = field(default_factory=list)
    services: dict[int, dict] = field(default_factory=dict)  # port -> service info
    vulnerabilities: list[dict] = field(default_factory=list)
    bruteforce_results: list[dict] = field(default_factory=list)

    def add_port(self, port: int) -> None:
        """오픈 포트 추가"""
        if port not in self.open_ports:
            self.open_ports.append(port)
            self.open_ports.sort()

    def add_service(self, port: int, service_info: dict) -> None:
        """서비스 정보 추가"""
        self.services[port] = service_info
        self.add_port(port)

    def add_vulnerability(self, vuln_info: dict) -> None:
        """취약점 정보 추가"""
        self.vulnerabilities.append(vuln_info)

    def add_bruteforce_result(self, result: dict) -> None:
        """브루트포스 결과 추가"""
        self.bruteforce_results.append(result)


@dataclass
class ScanSummary:
    """전체 스캔 요약"""

    total_hosts_scanned: int = 0
    total_hosts_up: int = 0
    total_open_ports: int = 0
    total_services: int = 0
    total_vulnerabilities: int = 0
    total_bruteforce_attempts: int = 0
    total_bruteforce_success: int = 0
    phase_durations: dict[str, float] = field(default_factory=dict)  # phase -> duration
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    total_duration: float = 0.0


class ReportGenerator:
    """스캔 결과 리포트 생성기"""

    def __init__(self, scan_dir: Path):
        """
        Args:
            scan_dir: 스캔 결과 디렉토리
        """
        self.scan_dir = Path(scan_dir)
        self.hosts: dict[str, HostResult] = {}
        self.summary = ScanSummary()

    def add_host_discovery(self, ip: str, hostname: Optional[str] = None) -> None:
        """호스트 발견 결과 추가

        Args:
            ip: IP 주소
            hostname: 호스트명 (선택)
        """
        if ip not in self.hosts:
            self.hosts[ip] = HostResult(ip=ip, hostname=hostname)
            self.summary.total_hosts_up += 1
        elif hostname:
            self.hosts[ip].hostname = hostname

    def add_port_scan(self, ip: str, ports: list[int]) -> None:
        """포트 스캔 결과 추가

        Args:
            ip: IP 주소
            ports: 오픈 포트 목록
        """
        if ip not in self.hosts:
            self.hosts[ip] = HostResult(ip=ip)

        for port in ports:
            self.hosts[ip].add_port(port)
            self.summary.total_open_ports += 1

    def add_service_detection(self, ip: str, port: int, service_info: dict) -> None:
        """서비스 탐지 결과 추가

        Args:
            ip: IP 주소
            port: 포트 번호
            service_info: 서비스 정보
        """
        if ip not in self.hosts:
            self.hosts[ip] = HostResult(ip=ip)

        self.hosts[ip].add_service(port, service_info)
        self.summary.total_services += 1

    def add_vulnerability(self, ip: str, vuln_info: dict) -> None:
        """취약점 스캔 결과 추가

        Args:
            ip: IP 주소
            vuln_info: 취약점 정보
        """
        if ip not in self.hosts:
            self.hosts[ip] = HostResult(ip=ip)

        self.hosts[ip].add_vulnerability(vuln_info)
        self.summary.total_vulnerabilities += 1

    def add_bruteforce_result(self, ip: str, port: int, service: str, result: dict) -> None:
        """브루트포스 결과 추가

        Args:
            ip: IP 주소
            port: 포트 번호
            service: 서비스 이름
            result: 브루트포스 결과 (username, password, success)
        """
        if ip not in self.hosts:
            self.hosts[ip] = HostResult(ip=ip)

        bruteforce_entry = {
            "port": port,
            "service": service,
            **result,
        }
        self.hosts[ip].add_bruteforce_result(bruteforce_entry)
        self.summary.total_bruteforce_attempts += 1

        if result.get("success", False):
            self.summary.total_bruteforce_success += 1

    def load_phase1_results(self) -> None:
        """Phase 1 (Host Discovery) 결과 로드"""
        phase1_file = self.scan_dir / "phase1" / "discovered_hosts.json"
        if not phase1_file.exists():
            return

        with open(phase1_file, encoding="utf-8") as f:
            data = json.load(f)
            for host_info in data.get("hosts", []):
                ip = host_info.get("ip")
                hostname = host_info.get("hostname")
                if ip:
                    self.add_host_discovery(ip, hostname)

    def load_phase2_results(self) -> None:
        """Phase 2 (Port Scan) 결과 로드"""
        phase2_dir = self.scan_dir / "phase2"
        if not phase2_dir.exists():
            return

        for json_file in phase2_dir.glob("*.json"):
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)
                ip = data.get("ip")
                open_ports = data.get("open_ports", [])
                if ip and open_ports:
                    self.add_port_scan(ip, open_ports)

    def load_phase3_results(self) -> None:
        """Phase 3 (Service Detection) 결과 로드"""
        phase3_dir = self.scan_dir / "phase3"
        if not phase3_dir.exists():
            return

        for json_file in phase3_dir.glob("*.json"):
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)
                ip = data.get("ip")
                services = data.get("services", {})
                if ip:
                    for port_str, service_info in services.items():
                        try:
                            port = int(port_str)
                            self.add_service_detection(ip, port, service_info)
                        except (ValueError, TypeError):
                            continue

    def load_phase4_results(self) -> None:
        """Phase 4 (Vulnerability + Bruteforce) 결과 로드"""
        phase4_dir = self.scan_dir / "phase4"
        if not phase4_dir.exists():
            return

        # 취약점 스캔 결과
        vuln_dir = phase4_dir / "vulnerabilities"
        if vuln_dir.exists():
            for json_file in vuln_dir.glob("*.json"):
                with open(json_file, encoding="utf-8") as f:
                    data = json.load(f)
                    ip = data.get("ip")
                    vulns = data.get("vulnerabilities", [])
                    if ip:
                        for vuln in vulns:
                            self.add_vulnerability(ip, vuln)

        # 브루트포스 결과
        bruteforce_dir = phase4_dir / "bruteforce"
        if bruteforce_dir.exists():
            for json_file in bruteforce_dir.glob("*.json"):
                with open(json_file, encoding="utf-8") as f:
                    data = json.load(f)
                    ip = data.get("ip")
                    results = data.get("results", [])
                    if ip:
                        for result in results:
                            port = result.get("port")
                            service = result.get("service", "unknown")
                            if port:
                                self.add_bruteforce_result(ip, port, service, result)

    def load_all_results(self) -> None:
        """모든 페이즈 결과 로드"""
        self.load_phase1_results()
        self.load_phase2_results()
        self.load_phase3_results()
        self.load_phase4_results()

    def generate_summary(self) -> dict:
        """요약 정보 생성

        Returns:
            요약 정보 딕셔너리
        """
        return asdict(self.summary)

    def generate_full_report(self) -> dict:
        """전체 리포트 생성

        Returns:
            전체 리포트 딕셔너리
        """
        return {
            "summary": self.generate_summary(),
            "hosts": {ip: asdict(host) for ip, host in self.hosts.items()},
        }

    def save_summary(self) -> None:
        """요약 정보를 summary.json으로 저장"""
        summary_file = self.scan_dir / "summary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(self.generate_summary(), f, indent=2, ensure_ascii=False)

    def save_full_report(self) -> None:
        """전체 리포트를 full_report.json으로 저장"""
        report_file = self.scan_dir / "full_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(self.generate_full_report(), f, indent=2, ensure_ascii=False)

    def save_all(self) -> None:
        """모든 리포트 저장"""
        self.save_summary()
        self.save_full_report()

"""Phase 1: Host Discovery 모듈

rustscan + nmap -sn으로 활성 호스트 발견 및 RTT 프로파일링
"""
import asyncio
import ipaddress
from pathlib import Path
from typing import Set
import sys
import re

# 부모 디렉토리를 import path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from scanner.config import Config
from scanner.logger import ColorLogger
from utils.subprocess_runner import run_command, CommandResult


def expand_subnets(subnets: list[str]) -> set[str]:
    """CIDR을 개별 IP로 확장"""
    all_ips = set()
    for subnet in subnets:
        network = ipaddress.ip_network(subnet, strict=False)
        all_ips.update(str(ip) for ip in network.hosts())
    return all_ips


class HostDiscovery:
    """활성 호스트 발견 및 RTT 측정 클래스"""

    def __init__(self, config: Config, subnet: str, label: str):
        """
        Args:
            config: 스캐너 설정
            subnet: 스캔할 서브넷 (예: 192.168.1.0/24)
            label: 서브넷 식별 레이블 (파일명에 사용)
        """
        self.config = config
        self.subnet = subnet
        self.label = label
        self.scan_dir = config.scan_dir
        self.logger = ColorLogger

    async def health_check_hybrid(self) -> Set[str]:
        """
        rustscan + nmap -sn으로 활성 호스트 발견

        Returns:
            활성 호스트 IP 집합
        """
        self.logger.phase("Phase 1", f"[{self.label}] Starting rustscan host discovery...")

        # rustscan 실행
        try:
            alive_hosts = await self._run_rustscan_ping()
        except Exception as e:
            self.logger.warning(f"rustscan 실패: {e}")
            alive_hosts = set()

        # exclude IP 필터링
        alive_hosts = self._filter_exclude_ips(alive_hosts)

        # ✅ alive_hosts가 없으면 파일 생성하지 않고 early return
        if not alive_hosts:
            self.logger.warning(
                f"[{self.label}] No alive hosts found - skipping file creation"
            )
            return set()

        # 결과 저장
        output_file = self.scan_dir / f"alive_hosts_{self.label}.txt"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w") as f:
            for ip in sorted(alive_hosts, key=ipaddress.IPv4Address):
                f.write(f"{ip}\n")

        # dead_hosts 생성
        all_ips = expand_subnets([self.subnet])
        exclude_set = set(self.config.exclude_ips)
        alive_set = set(alive_hosts)
        dead_ips = (all_ips - exclude_set) - alive_set

        dead_file = self.scan_dir / f"dead_hosts_{self.label}.txt"
        with open(dead_file, "w") as f:
            f.write("\n".join(sorted(dead_ips, key=ipaddress.IPv4Address)))

        self.logger.success(
            f"[{self.label}] Found {len(alive_hosts)} alive hosts → {output_file}"
        )
        return alive_hosts

    async def _run_rustscan_ping(self) -> Set[str]:
        """rustscan + nmap -sn으로 활성 호스트 발견"""
        cmd = [
            "rustscan",
            "-a", self.subnet,
            "--",
            "-sn",                      # Ping scan (no port scan)
            "-T4",                      # Aggressive timing (네트워크 친화적)
            "--min-parallelism", "30",  # 최소 30개 동시 스캔
            "--max-retries", "3",       # 재시도 3회로 제한
            "--max-rate", "500",        # 초당 500 패킷 제한 (네트워크 보호)
            "-oG", "-"                  # Grepable output to stdout
        ]
        self.logger.info(
            f"[{self.label}] Running rustscan + nmap ping scan "
            f"(T4, parallel=30, max-rate=500): {' '.join(cmd)}"
        )

        try:
            result = await run_command(cmd, timeout=300)
            hosts = set()
            # nmap -oG 출력에서 "Host: IP (hostname) Status: Up" 파싱
            for line in result.stdout.splitlines():
                if "Status: Up" in line:
                    match = re.search(r"Host:\s+(\d+\.\d+\.\d+\.\d+)", line)
                    if match:
                        hosts.add(match.group(1))

            self.logger.success(f"[{self.label}] rustscan found {len(hosts)} hosts")
            return hosts
        except asyncio.TimeoutError:
            self.logger.warning(f"[{self.label}] rustscan ping scan timeout (300s)")
            return set()
        except Exception as e:
            self.logger.warning(f"[{self.label}] rustscan ping scan failed: {e}")
            return set()

    def _filter_exclude_ips(self, hosts: Set[str]) -> Set[str]:
        """exclude IP 필터링"""
        if not self.config.exclude_ips:
            return hosts

        exclude_set = set(self.config.exclude_ips)
        filtered = hosts - exclude_set
        excluded_count = len(hosts) - len(filtered)

        if excluded_count > 0:
            self.logger.info(f"[{self.label}] Excluded {excluded_count} IPs")

        return filtered

    async def profile_rtt(self, alive_hosts: Set[str]) -> float:
        """
        샘플 호스트 RTT 측정

        Args:
            alive_hosts: 활성 호스트 집합

        Returns:
            평균 RTT (ms)
        """
        if not alive_hosts:
            self.logger.warning(f"[{self.label}] No hosts to profile RTT, using default 50.0 ms")
            return 50.0

        # 최대 10개 샘플
        sample_hosts = sorted(alive_hosts)[:10]

        self.logger.info(
            f"[{self.label}] Profiling RTT for {len(sample_hosts)} sample hosts..."
        )

        # 병렬로 RTT 측정
        tasks = [self._measure_rtt(host) for host in sample_hosts]
        rtt_results = await asyncio.gather(*tasks)

        # None이 아닌 값만 필터링
        rtt_values = [rtt for rtt in rtt_results if rtt is not None]

        if not rtt_values:
            self.logger.warning(
                f"[{self.label}] Failed to measure RTT, using default 50.0 ms"
            )
            return 50.0

        avg_rtt = sum(rtt_values) / len(rtt_values)

        # 결과 저장
        output_file = self.scan_dir / f"avg_rtt_{self.label}.txt"
        with open(output_file, "w") as f:
            f.write(f"{avg_rtt:.2f}\n")

        self.logger.success(
            f"[{self.label}] Average RTT: {avg_rtt:.2f} ms (sampled {len(rtt_values)}/{len(sample_hosts)} hosts)"
        )
        return avg_rtt

    async def _measure_rtt(self, host: str) -> float:
        """단일 호스트 RTT 측정"""
        cmd = ["ping", "-c", "3", "-W", "2", host]

        try:
            result = await run_command(cmd, timeout=10)

            # ping 출력에서 avg RTT 파싱
            # 예: rtt min/avg/max/mdev = 1.234/2.345/3.456/0.123 ms
            for line in result.stdout.splitlines():
                if "rtt min/avg/max" in line or "round-trip" in line:
                    match = re.search(r"=\s*[\d.]+/([\d.]+)/", line)
                    if match:
                        return float(match.group(1))

            return None
        except Exception:
            return None

    @staticmethod
    def _is_valid_ip(ip: str) -> bool:
        """간단한 IP 주소 검증"""
        parts = ip.split(".")
        if len(parts) != 4:
            return False
        try:
            return all(0 <= int(part) <= 255 for part in parts)
        except ValueError:
            return False


async def main():
    """테스트 코드"""
    # 테스트용 Config 생성
    script_dir = Path(__file__).parent.parent
    scan_dir = Path("/tmp/test_phase1_scan")
    json_file = script_dir / "targets.json"

    config = Config(
        script_dir=script_dir,
        scan_dir=scan_dir,
        json_file=json_file,
        subnets=["192.168.1.0/24"],
        exclude_ips=[],
        sudo_password="",
    )

    # 스캔 디렉토리 생성
    scan_dir.mkdir(parents=True, exist_ok=True)

    # Phase 1 실행
    phase1 = HostDiscovery(config, "192.168.1.0/24", "test")

    logger = ColorLogger()
    logger.header("Phase 1: Host Discovery Test")

    # 활성 호스트 발견
    alive_hosts = await phase1.health_check_hybrid()
    logger.info(f"Discovered {len(alive_hosts)} alive hosts")

    # RTT 프로파일링
    if alive_hosts:
        avg_rtt = await phase1.profile_rtt(alive_hosts)
        logger.info(f"Average RTT: {avg_rtt:.2f} ms")
    else:
        logger.warning("No alive hosts found - skipping RTT profiling")

    logger.separator()
    logger.success("Phase 1 test completed!")
    logger.info(f"Results saved to: {scan_dir}")


if __name__ == "__main__":
    asyncio.run(main())

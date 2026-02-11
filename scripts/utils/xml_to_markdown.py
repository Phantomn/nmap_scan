#!/usr/bin/env python3
"""
nmap XML → Markdown 리포트 변환 스크립트 (통합)

Phase 1-4 XML 파일 파싱 → 구조화된 Markdown 리포트 생성
- 프로토콜별 자동 분류 (HTTP, SSH, DB, SAP 등)
- 취약점 우선순위 정렬 (Critical/High/Medium)
- NSE 스크립트 완전 활용 (계층 구조 유지)

Usage:
    python3 xml_to_markdown.py --scan-dir <dir> --output <file.md> [--verbose]
"""

from __future__ import annotations

import argparse
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class NmapXMLParser:
    """nmap XML 파싱 및 데이터 구조 생성"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.hosts: List[Dict[str, Any]] = []

    def parse_file(self, xml_path: Path) -> List[Dict[str, Any]]:
        """단일 XML 파일 파싱"""
        if self.verbose:
            print(f"[DEBUG] Parsing {xml_path.name}...")

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
        except ET.ParseError as e:
            print(f"[WARNING] XML 파싱 실패 ({xml_path.name}): {e}")
            return []

        hosts = []
        for host_elem in root.findall("host"):
            host_data = self._parse_host(host_elem)
            if host_data:
                hosts.append(host_data)

        if self.verbose:
            print(f"[DEBUG]   → {len(hosts)} hosts parsed")

        return hosts

    def _parse_host(self, host_elem: ET.Element) -> Optional[Dict[str, Any]]:
        """호스트 정보 파싱"""
        # 상태 확인
        status_elem = host_elem.find("status")
        if status_elem is None or status_elem.get("state") != "up":
            return None

        # IP 주소
        ip_elem = host_elem.find('address[@addrtype="ipv4"]')
        if ip_elem is None:
            return None

        ip = ip_elem.get("addr")

        # 호스트명
        hostname = self._extract_hostname(host_elem)

        # 포트 정보
        ports = []
        ports_elem = host_elem.find("ports")
        if ports_elem is not None:
            for port_elem in ports_elem.findall("port"):
                port_data = self._parse_port(port_elem)
                if port_data:
                    ports.append(port_data)

        # 포트가 없는 호스트는 제외
        if not ports:
            return None

        # OS 정보
        os_info = self._extract_os(host_elem)

        # 프로토콜 태깅
        tags = self._classify_protocols(ports)

        return {
            "ip": ip,
            "hostname": hostname,
            "status": "up",
            "ports": ports,
            "os": os_info,
            "tags": tags,
        }

    def _extract_hostname(self, host_elem: ET.Element) -> Optional[str]:
        """호스트명 추출"""
        hostnames_elem = host_elem.find("hostnames")
        if hostnames_elem is not None:
            hostname_elem = hostnames_elem.find('hostname[@type="PTR"]')
            if hostname_elem is None:
                hostname_elem = hostnames_elem.find("hostname")
            if hostname_elem is not None:
                return hostname_elem.get("name")
        return None

    def _extract_os(self, host_elem: ET.Element) -> Optional[Dict[str, Any]]:
        """OS 정보 추출"""
        os_elem = host_elem.find("os/osmatch")
        if os_elem is not None:
            return {
                "name": os_elem.get("name"),
                "accuracy": int(os_elem.get("accuracy", 0)),
            }
        return None

    def _parse_port(self, port_elem: ET.Element) -> Optional[Dict[str, Any]]:
        """포트 정보 파싱"""
        state_elem = port_elem.find("state")
        if state_elem is None or state_elem.get("state") != "open":
            return None

        port_data = {
            "portid": int(port_elem.get("portid")),
            "protocol": port_elem.get("protocol"),
            "state": "open",
            "scripts": [],
        }

        # 서비스 정보
        service_elem = port_elem.find("service")
        if service_elem is not None:
            port_data["service"] = {
                "name": service_elem.get("name", "unknown"),
                "product": service_elem.get("product"),
                "version": service_elem.get("version"),
                "extrainfo": service_elem.get("extrainfo"),
            }

        # NSE 스크립트 (MVP: output만, elements는 Phase 2)
        for script_elem in port_elem.findall("script"):
            script_data = {
                "id": script_elem.get("id"),
                "output": script_elem.get("output", ""),
            }
            port_data["scripts"].append(script_data)

        return port_data

    def _classify_protocols(self, ports: List[Dict[str, Any]]) -> List[str]:
        """포트 기반 프로토콜 자동 분류"""
        tags: Set[str] = set()

        for port in ports:
            portid = port["portid"]
            service_name = port.get("service", {}).get("name", "")

            # 포트 번호 기반
            if portid in [80, 8080, 8000]:
                tags.add("http")
            elif portid in [443, 8443]:
                tags.add("https")
            elif portid == 22:
                tags.add("ssh")
            elif portid == 3306:
                tags.add("mysql")
            elif portid == 5432:
                tags.add("postgresql")
            elif portid == 1433:
                tags.add("mssql")
            elif portid == 27017:
                tags.add("mongodb")
            elif portid in [3200, 3300, 8000, 50000]:
                tags.add("sap")
            elif portid == 445:
                tags.add("smb")
            elif portid == 3389:
                tags.add("rdp")
            elif portid == 5900:
                tags.add("vnc")

            # 서비스 이름 기반 (보강)
            if "http" in service_name.lower():
                tags.add("web")
            if "sql" in service_name.lower() or "database" in service_name.lower():
                tags.add("database")

        return sorted(list(tags))

    def merge_hosts(self, all_hosts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """중복 호스트 병합 (Phase 3 + Phase 4 결과 통합)"""
        unique_hosts: Dict[str, Dict[str, Any]] = {}

        for host in all_hosts:
            ip = host["ip"]
            if ip in unique_hosts:
                # 기존 호스트에 포트 추가 (중복 제거)
                existing_ports = {p["portid"]: p for p in unique_hosts[ip]["ports"]}
                for port in host["ports"]:
                    portid = port["portid"]
                    if portid in existing_ports:
                        # 스크립트 병합
                        existing_scripts = {
                            s["id"]: s for s in existing_ports[portid]["scripts"]
                        }
                        for script in port["scripts"]:
                            script_id = script["id"]
                            if script_id not in existing_scripts:
                                existing_ports[portid]["scripts"].append(script)
                    else:
                        existing_ports[portid] = port

                unique_hosts[ip]["ports"] = list(existing_ports.values())

                # 태그 병합
                unique_hosts[ip]["tags"] = sorted(
                    list(set(unique_hosts[ip]["tags"] + host["tags"]))
                )
            else:
                unique_hosts[ip] = host

        return list(unique_hosts.values())


class StatisticsCalculator:
    """프로토콜별 통계 및 취약점 집계"""

    def __init__(self, hosts: List[Dict[str, Any]]):
        self.hosts = hosts

    def calculate(self) -> Dict[str, Any]:
        """통합 통계 계산"""
        return {
            "statistics": self._basic_stats(),
            "by_protocol": self._protocol_stats(),
            "vulnerabilities": self._vulnerability_stats(),
        }

    def _basic_stats(self) -> Dict[str, Any]:
        """기본 통계"""
        total_ports = sum(len(h["ports"]) for h in self.hosts)
        return {
            "total_hosts": len(self.hosts),
            "alive_hosts": len(self.hosts),
            "total_open_ports": total_ports,
        }

    def _protocol_stats(self) -> Dict[str, Dict[str, Any]]:
        """프로토콜별 통계"""
        protocol_map: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"host_count": 0, "port_count": 0, "hosts": []}
        )

        for host in self.hosts:
            for tag in host["tags"]:
                if host["ip"] not in protocol_map[tag]["hosts"]:
                    protocol_map[tag]["hosts"].append(host["ip"])
                    protocol_map[tag]["host_count"] += 1

            for port in host["ports"]:
                portid = port["portid"]
                # HTTP
                if portid in [80, 8080, 8000]:
                    protocol_map["http"]["port_count"] += 1
                # HTTPS
                elif portid in [443, 8443]:
                    protocol_map["https"]["port_count"] += 1
                    # SSL 인증서 카운트
                    ssl_scripts = [s for s in port["scripts"] if "ssl" in s["id"]]
                    if ssl_scripts:
                        protocol_map["https"]["ssl_cert_count"] = protocol_map[
                            "https"
                        ].get("ssl_cert_count", 0) + 1
                # SSH
                elif portid == 22:
                    protocol_map["ssh"]["port_count"] += 1
                # DB
                elif portid in [3306, 5432, 1433, 27017]:
                    protocol_map["database"]["port_count"] += 1

        # hosts 리스트 제거 (통계만 유지)
        for proto in protocol_map:
            del protocol_map[proto]["hosts"]

        return dict(protocol_map)

    def _vulnerability_stats(self) -> Dict[str, Any]:
        """취약점 통계"""
        cve_set: Set[str] = set()
        by_severity: Dict[str, int] = defaultdict(int)
        vulnerable_hosts: Set[str] = set()

        for host in self.hosts:
            host_vulnerable = False
            for port in host["ports"]:
                for script in port["scripts"]:
                    output = script.get("output", "")
                    script_id = script["id"]

                    # CVE 추출
                    cves = re.findall(r"CVE-\d{4}-\d+", output)
                    cve_set.update(cves)

                    # 취약점 발견 시
                    if cves or "VULNERABLE" in output.upper():
                        host_vulnerable = True

                        # 심각도 분류 (NSE script ID 기반)
                        if any(
                            keyword in script_id
                            for keyword in ["heartbleed", "shellshock", "ms17-010"]
                        ):
                            by_severity["critical"] += 1
                        elif "vuln" in script_id or "exploit" in script_id:
                            by_severity["high"] += 1
                        else:
                            by_severity["medium"] += 1

            if host_vulnerable:
                vulnerable_hosts.add(host["ip"])

        return {
            "total_vulnerable_hosts": len(vulnerable_hosts),
            "cve_list": sorted(list(cve_set)),
            "by_severity": dict(by_severity),
        }


class MarkdownGenerator:
    """Markdown 리포트 생성"""

    def __init__(self, hosts: List[Dict[str, Any]], summary: Dict[str, Any], scan_dir: Path):
        self.hosts = hosts
        self.summary = summary
        self.scan_dir = scan_dir

    def generate(self) -> str:
        """Markdown 생성"""
        sections = [
            self._header(),
            self._scan_summary(),  # 새로 추가: summary.json 기반
            self._excluded_hosts(),  # 새로 추가: Exclude IP
            self._undetected_hosts(),  # 새로 추가: Undetected IP
            self._executive_summary(),
            self._risk_summary(),
            self._protocol_analysis(),
            self._vulnerability_details(),
            self._recommendations(),
            self._appendix(),
        ]

        return "\n\n".join(sections)

    def _header(self) -> str:
        """헤더"""
        stats = self.summary["statistics"]
        return f"""# 대규모 네트워크 스캔 보고서

**스캔 시간**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**활성 호스트**: {stats['alive_hosts']}개

---"""

    def _scan_summary(self) -> str:
        """스캔 요약 (summary.json 기반)"""
        import json
        summary_path = self.scan_dir / "reports" / "summary.json"

        if not summary_path.exists():
            return "## 스캔 요약\n\n*summary.json 파일이 없습니다*\n\n---"

        with open(summary_path) as f:
            summary_data = json.load(f)

        stats = summary_data['statistics']
        lines = ["## 스캔 요약\n"]
        lines.append(f"- **Scan ID**: `{summary_data['scan_id']}`")
        lines.append(f"- **Timestamp**: {summary_data['timestamp']}")
        lines.append(f"- **활성 호스트**: {stats['alive_hosts']}개")
        lines.append(f"- **제외된 호스트**: {stats['excluded_hosts']}개")
        lines.append(f"- **탐지되지 않은 호스트**: {stats['undetected_hosts']}개")
        lines.append(f"- **열린 포트**: {stats['open_ports']}개")
        lines.append(f"- **취약점**: {stats['vulnerabilities']}개")
        lines.append(f"- **CVE**: {stats['cve_count']}개")
        lines.append("\n---")

        return "\n".join(lines)

    def _excluded_hosts(self) -> str:
        """제외된 호스트 목록"""
        excluded_path = self.scan_dir / "reports" / "excluded_hosts.txt"

        if not excluded_path.exists():
            return "## 제외된 호스트\n\n*excluded_hosts.txt 파일이 없습니다*\n\n---"

        with open(excluded_path) as f:
            exclude_list = [line.strip() for line in f if line.strip()]

        lines = ["## 제외된 호스트\n"]

        if not exclude_list:
            lines.append("*제외된 호스트가 없습니다*")
        else:
            for item in exclude_list:
                lines.append(f"- `{item}`")
            lines.append(f"\n**총 {len(exclude_list)}개 항목**")

        lines.append("\n---")
        return "\n".join(lines)

    def _undetected_hosts(self) -> str:
        """탐지되지 않은 호스트 목록 (샘플)"""
        undetected_path = self.scan_dir / "reports" / "undetected_hosts.txt"

        if not undetected_path.exists():
            return "## 탐지되지 않은 호스트\n\n*undetected_hosts.txt 파일이 없습니다*\n\n---"

        with open(undetected_path) as f:
            undetected = [line.strip() for line in f if line.strip()]

        lines = ["## 탐지되지 않은 호스트\n"]

        if not undetected:
            lines.append("*모든 호스트가 탐지되었습니다*")
        else:
            if len(undetected) > 50:
                lines.append(f"처음 50개 호스트 표시 (총 {len(undetected)}개):\n")
                for ip in undetected[:50]:
                    lines.append(f"- `{ip}`")
                lines.append(f"\n**전체 목록**: `reports/undetected_hosts.txt`")
            else:
                for ip in undetected:
                    lines.append(f"- `{ip}`")
                lines.append(f"\n**총 {len(undetected)}개**")

        lines.append("\n---")
        return "\n".join(lines)

    def _executive_summary(self) -> str:
        """실행 요약"""
        stats = self.summary["statistics"]
        return f"""## 실행 요약

- **활성 호스트**: {stats['alive_hosts']}개
- **열린 포트**: {stats['total_open_ports']}개
- **발견된 CVE**: {len(self.summary['vulnerabilities']['cve_list'])}개
- **취약 호스트**: {self.summary['vulnerabilities']['total_vulnerable_hosts']}개

---"""

    def _risk_summary(self) -> str:
        """위험도 요약"""
        vuln = self.summary["vulnerabilities"]
        by_severity = vuln["by_severity"]

        lines = ["## 위험도 요약\n"]

        if by_severity.get("critical", 0) > 0:
            lines.append(f"### 🔴 Critical ({by_severity['critical']}건)\n")
            lines.append(self._critical_findings())

        if by_severity.get("high", 0) > 0:
            lines.append(f"### 🟡 High ({by_severity['high']}건)\n")
            lines.append(self._high_findings())

        if by_severity.get("medium", 0) > 0:
            lines.append(f"### 🟢 Medium ({by_severity['medium']}건)\n")

        if not by_severity:
            lines.append("✅ **취약점 미발견**\n")

        lines.append("---")
        return "\n".join(lines)

    def _critical_findings(self) -> str:
        """Critical 취약점 상세"""
        critical_hosts = []
        for host in self.hosts:
            for port in host["ports"]:
                for script in port["scripts"]:
                    script_id = script["id"]
                    if any(
                        keyword in script_id
                        for keyword in ["heartbleed", "shellshock", "ms17-010"]
                    ):
                        output = script.get("output", "")[:200]  # 200자 제한
                        critical_hosts.append(
                            f"- **{host['ip']}:{port['portid']}** - `{script_id}`\n  {output}..."
                        )

        if critical_hosts:
            return "\n".join(critical_hosts[:5])  # Top 5
        return "_(상세 정보 없음)_\n"

    def _high_findings(self) -> str:
        """High 취약점 상세"""
        high_hosts = []
        for host in self.hosts:
            for port in host["ports"]:
                for script in port["scripts"]:
                    script_id = script["id"]
                    output = script.get("output", "")
                    if "vuln" in script_id and "VULNERABLE" in output.upper():
                        cves = re.findall(r"CVE-\d{4}-\d+", output)
                        cve_str = ", ".join(cves[:3]) if cves else "No CVE"
                        high_hosts.append(
                            f"- **{host['ip']}:{port['portid']}** - {cve_str}"
                        )

        if high_hosts:
            return "\n".join(high_hosts[:10])  # Top 10
        return "_(상세 정보 없음)_\n"

    def _protocol_analysis(self) -> str:
        """프로토콜별 분석"""
        by_protocol = self.summary["by_protocol"]

        lines = ["## 프로토콜별 분석\n"]

        # HTTP
        if "http" in by_protocol:
            http = by_protocol["http"]
            lines.append(f"### HTTP ({http['host_count']}개 호스트)\n")
            lines.append(f"- 총 포트: {http['port_count']}개\n")

        # HTTPS
        if "https" in by_protocol:
            https = by_protocol["https"]
            lines.append(f"### HTTPS ({https['host_count']}개 호스트)\n")
            lines.append(f"- 총 포트: {https['port_count']}개")
            if "ssl_cert_count" in https:
                lines.append(f"- SSL 인증서: {https['ssl_cert_count']}개\n")
            else:
                lines.append("\n")

        # SSH
        if "ssh" in by_protocol:
            ssh = by_protocol["ssh"]
            lines.append(f"### SSH ({ssh['host_count']}개 호스트)\n")
            lines.append(f"- 총 포트: {ssh['port_count']}개\n")

        # Database
        if "database" in by_protocol:
            db = by_protocol["database"]
            lines.append(f"### Database ({db['host_count']}개 호스트)\n")
            lines.append(f"- 총 포트: {db['port_count']}개\n")

        # SAP
        if "sap" in by_protocol:
            sap = by_protocol["sap"]
            lines.append(f"### SAP ({sap['host_count']}개 호스트)\n")

        lines.append("---")
        return "\n".join(lines)

    def _vulnerability_details(self) -> str:
        """취약점 상세"""
        cve_list = self.summary["vulnerabilities"]["cve_list"]

        lines = ["## 취약점 상세\n"]

        if cve_list:
            lines.append("### CVE 목록 (Top 10)\n")
            for i, cve in enumerate(cve_list[:10], 1):
                lines.append(f"{i}. {cve}")
        else:
            lines.append("✅ **CVE 미발견**")

        lines.append("\n---")
        return "\n".join(lines)

    def _recommendations(self) -> str:
        """권장 조치사항"""
        vuln = self.summary["vulnerabilities"]
        by_severity = vuln["by_severity"]

        lines = ["## 권장 조치사항\n"]

        # 즉시 조치 (Critical)
        if by_severity.get("critical", 0) > 0:
            lines.append("### 🚨 즉시 조치 필요\n")
            lines.append("- Critical 취약점 패치 적용")
            lines.append("- 영향받는 호스트 격리 검토\n")

        # 단기 조치 (High)
        if by_severity.get("high", 0) > 0:
            lines.append("### ⚠️ 단기 조치 (1주일 이내)\n")
            lines.append("- High 취약점 패치 계획 수립")
            lines.append("- 우선순위 기반 순차 적용\n")

        # 장기 조치 (Medium)
        if by_severity.get("medium", 0) > 0:
            lines.append("### 📋 장기 조치 (1개월 이내)\n")
            lines.append("- Medium 취약점 모니터링")
            lines.append("- 정기 패치 사이클에 포함\n")

        # 일반 권장사항
        lines.append("### 일반 권장사항\n")
        lines.append("- 정기적 취약점 스캔 (월 1회 이상)")
        lines.append("- 불필요한 서비스 포트 차단")
        lines.append("- 방화벽 정책 재검토")

        lines.append("\n---")
        return "\n".join(lines)

    def _appendix(self) -> str:
        """부록"""
        return f"""## 부록

### 스캔 파라미터

- **Phase 1**: 호스트 발견 (`-sn`, `-PS`, `-T4`)
- **Phase 2**: 전체 포트 스캔 (`rustscan` → `nmap -p-`)
- **Phase 3**: 서비스 버전 탐지 (`-sV -sC`)
- **Phase 4**: 취약점 스캔 (프로토콜별 NSE)

### 파일 목록

- `phase1_*.xml`: 호스트 발견 결과
- `phase3_detail_*.xml`: 서비스 상세 정보
- `phase4_vuln_*.xml`: 취약점 스캔 결과
- `FINAL_REPORT.md`: 본 리포트

---

*생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"""


def main() -> int:
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="nmap XML → Markdown 리포트 변환 (통합)"
    )
    parser.add_argument("--scan-dir", required=True, help="스캔 디렉토리 경로")
    parser.add_argument("--output", required=True, help="출력 Markdown 파일 경로")
    parser.add_argument("--verbose", action="store_true", help="상세 로그 출력")

    args = parser.parse_args()

    scan_dir = Path(args.scan_dir)
    if not scan_dir.exists():
        print(f"ERROR: 디렉토리 없음 - {scan_dir}")
        return 1

    # XML 파일 수집 (raw/ 디렉토리 우선, 없으면 fallback)
    raw_dir = scan_dir / "raw"
    if raw_dir.exists():
        xml_files = []
        xml_files.extend(raw_dir.glob("phase1_*.xml"))
        xml_files.extend(raw_dir.glob("phase3_detail_*.xml"))
        xml_files.extend(raw_dir.glob("phase4_vuln_*.xml"))
    else:
        # Fallback: 구 버전 호환
        xml_files = []
        xml_files.extend(scan_dir.glob("phase1_*.xml"))
        xml_files.extend(scan_dir.glob("phase3_detail_*.xml"))
        xml_files.extend(scan_dir.glob("phase4_vuln_*.xml"))

    if not xml_files:
        print(f"ERROR: XML 파일 없음 - {scan_dir}")
        return 1

    if args.verbose:
        print(f"[INFO] XML 파일 {len(xml_files)}개 발견")

    # 파싱
    parser_obj = NmapXMLParser(verbose=args.verbose)
    all_hosts: List[Dict[str, Any]] = []

    for xml_file in xml_files:
        hosts = parser_obj.parse_file(xml_file)
        all_hosts.extend(hosts)

    # 중복 병합
    if args.verbose:
        print(f"[INFO] 총 {len(all_hosts)}개 호스트 파싱됨")
    unique_hosts = parser_obj.merge_hosts(all_hosts)
    if args.verbose:
        print(f"[INFO] 중복 제거 후 {len(unique_hosts)}개 호스트")

    # 통계 계산
    calc = StatisticsCalculator(unique_hosts)
    summary = calc.calculate()

    # Markdown 생성
    md_gen = MarkdownGenerator(unique_hosts, summary, scan_dir)
    markdown = md_gen.generate()

    # 저장
    output_path = Path(args.output)
    output_path.write_text(markdown, encoding="utf-8")

    # 결과 출력
    print(f"✅ SUCCESS: Markdown 리포트 생성 완료")
    print(f"  파일: {output_path}")
    print(f"  활성 호스트: {summary['statistics']['alive_hosts']}개")
    print(f"  열린 포트: {summary['statistics']['total_open_ports']}개")
    print(f"  발견된 CVE: {len(summary['vulnerabilities']['cve_list'])}개")

    return 0


if __name__ == "__main__":
    exit(main())

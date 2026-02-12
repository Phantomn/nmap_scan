#!/usr/bin/env python3
"""네트워크 스캐너 진입점

RustScan + Nmap을 조합한 2-phase 네트워크 스캐너.

## 구조
- Phase 1: Health Check (fping + nmap -sn)
  → alive_hosts.txt, dead_hosts.txt 생성

- Phase 2: Detailed Scan (rustscan → nmap -A)
  → scan_*.nmap 생성 (각 IP별 상세 스캔 결과)

## 사용법
    # targets.json에 스캔할 IP/CIDR 정의
    {
      "subnets": ["172.20.1.0/24", "100.103.28.0/24"],
      "exclude": ["172.20.1.1", "172.20.2.0/28"]
    }

    # 실행
    python main.py --json-file targets.json

    # 또는 루트에 targets.json이 있으면
    python main.py

## 출력
    scans/rustscan_massive_YYYYMMDD_HHMMSS/
    ├── alive_hosts.txt       # 살아있는 IP 목록
    ├── dead_hosts.txt        # 죽은 IP 목록
    └── scan_*.nmap           # 각 IP별 nmap 상세 스캔
"""
import asyncio
import sys
from pathlib import Path

# scripts 디렉터리를 sys.path에 추가
script_dir = Path(__file__).parent / "scripts"
sys.path.insert(0, str(script_dir))


if __name__ == "__main__":
    # rustscan_massive 실행
    from rustscan_massive import main

    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n강제 종료")
        sys.exit(130)

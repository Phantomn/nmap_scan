#!/usr/bin/env python3
"""네트워크 스캐너 진입점 (scripts/rustscan_massive.py 래퍼)

RustScan + Nmap 2-phase 네트워크 스캐너.

Phase 1: nmap -sn (T4) → alive/dead hosts
Phase 2: rustscan → nmap -sV -sC (T4) → scan_*.nmap

Usage:
    python main.py
    python main.py --json-file targets.json
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

#!/usr/bin/env python3
"""nmap 스캐너 진입점

RustScan + Nmap을 조합한 네트워크 스캐너.
4단계 파이프라인 구조:
- Phase 1: RustScan 포트 발견
- Phase 2: Nmap 기본 스캔
- Phase 3: Nmap 상세 스캔 (NSE)
- Phase 4: 브루트포스 + Web 공격

사용법:
    python main.py --target 192.168.1.0/24
    python main.py --target 10.0.0.1/32 --aggressive
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

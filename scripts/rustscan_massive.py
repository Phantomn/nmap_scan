#!/usr/bin/env python3
"""대규모 네트워크 스캔 도구 (4단계 파이프라인)"""
import argparse
import asyncio
import getpass
import os
import sys
from datetime import datetime
from pathlib import Path

# 부모 디렉토리를 import path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from scanner.config import Config
from scanner.logger import ColorLogger
from scanner.scanner import Scanner
from utils.json_loader import load_targets


def parse_args() -> argparse.Namespace:
    """CLI 인자 파싱"""
    parser = argparse.ArgumentParser(
        description="네트워크 스캐너: Alive/Dead IP 구분 + rustscan + nmap 통합",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 기본 스캔 (targets.json 사용)
  %(prog)s

  # 커스텀 타겟 파일
  %(prog)s --json-file custom_targets.json

  # sudo 비밀번호 환경변수로 전달 (자동화)
  export SUDO_PASSWORD="your_password"
  %(prog)s
        """,
    )

    # 필수 인자
    parser.add_argument(
        "--json-file",
        type=Path,
        default=Path(__file__).parent / "targets.json",
        help="타겟 JSON 파일 경로 (기본값: ./targets.json)",
    )


    return parser.parse_args()


def get_scan_directory() -> Path:
    """타임스탬프 기반 스캔 디렉토리 생성"""
    scans_root = Path.(__file__).parent / "scans"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    scan_dir = scans_root / f"rustscan_massive_{timestamp}"
    scan_dir.mkdir(parents=True, exist_ok=True)
    return scan_dir


def get_sudo_password() -> str:
    """sudo 비밀번호 획득 (환경변수 우선, 없으면 프롬프트)"""
    # 환경변수 SUDO_PASSWORD 체크
    sudo_password = os.getenv("SUDO_PASSWORD")
    if sudo_password:
        ColorLogger.info("sudo 비밀번호: 환경변수에서 로드")
        return sudo_password

    # 대화형 프롬프트
    return getpass.getpass("sudo 비밀번호: ")


async def main() -> int:
    """메인 진입점"""
    args = parse_args()

    # 타겟 로드
    try:
        targets = load_targets(args.json_file)
        ColorLogger.success(f"타겟 로드: {len(targets.subnets)}개 서브넷")
    except Exception as e:
        ColorLogger.error(f"타겟 로드 실패: {e}")
        return 1

    # sudo 비밀번호
    try:
        sudo_password = get_sudo_password()
    except KeyboardInterrupt:
        ColorLogger.warning("\n사용자 취소")
        return 130

    # 스캔 디렉토리
    scan_dir = get_scan_directory()
    ColorLogger.info(f"스캔 디렉토리: {scan_dir}")

    # Config 생성
    script_dir = Path(__file__).parent
    config = Config(
        script_dir=script_dir,
        scan_dir=scan_dir,
        json_file=args.json_file,
        subnets=targets.subnets,
        exclude_ips=targets.exclude,
        sudo_password=sudo_password,
    )

    # 검증
    try:
        config.validate()
        ColorLogger.success("설정 검증 완료")
    except Exception as e:
        ColorLogger.error(f"설정 검증 실패: {e}")
        return 1

    # Scanner 실행
    scanner = Scanner(config)
    try:
        await scanner.run()
        ColorLogger.success("스캔 성공적으로 완료")
        return 0
    except KeyboardInterrupt:
        ColorLogger.warning("\n사용자에 의해 중단됨 (Ctrl+C)")
        return 130
    except Exception as e:
        ColorLogger.error(f"스캔 실패: {e}")
        import traceback
        ColorLogger.debug(traceback.format_exc())
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        ColorLogger.warning("\n강제 종료")
        sys.exit(130)

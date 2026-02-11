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
        description="대규모 네트워크 스캔 (rustscan + nmap 4단계)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 기본 스캔 (targets.json 사용)
  %(prog)s

  # 취약점 스캔 건너뛰기
  %(prog)s --skip-vuln

  # 브루트포스 건너뛰기
  %(prog)s --skip-bruteforce

  # 이전 스캔 재개
  %(prog)s --resume

  # 커스텀 워드리스트
  %(prog)s --wordlist-users custom_users.txt --wordlist-passwords custom_pass.txt

  # sudo 비밀번호 환경변수로 전달 (자동화)
  export SUDO_PASSWORD="your_password"
  %(prog)s --skip-vuln
        """,
    )

    # 필수 인자
    parser.add_argument(
        "--json-file",
        type=Path,
        default=Path(__file__).parent / "targets.json",
        help="타겟 JSON 파일 경로 (기본값: ./targets.json)",
    )

    # 스킵 옵션
    parser.add_argument(
        "--skip-vuln",
        action="store_true",
        help="Phase 4 (취약점 스캔) 건너뛰기",
    )
    parser.add_argument(
        "--skip-bruteforce",
        action="store_true",
        help="브루트포스 공격 건너뛰기 (Phase 4 내)",
    )

    # Resume 옵션
    parser.add_argument(
        "--resume",
        action="store_true",
        help="최신 스캔 디렉토리에서 재개 (체크포인트 기반)",
    )

    # 스캔 디렉토리
    parser.add_argument(
        "--scan-dir",
        type=Path,
        help="스캔 결과 저장 디렉토리 (기본값: scans/rustscan_massive_YYYYMMDD_HHMMSS)",
    )

    # 브루트포스 설정
    parser.add_argument(
        "--wordlist-users",
        type=Path,
        help="사용자 이름 워드리스트 경로",
    )
    parser.add_argument(
        "--wordlist-passwords",
        type=Path,
        help="비밀번호 워드리스트 경로",
    )
    parser.add_argument(
        "--bruteforce-timeout",
        type=int,
        default=300,
        help="브루트포스 타임아웃 (초, 기본값: 300)",
    )
    parser.add_argument(
        "--bruteforce-threads",
        type=int,
        default=5,
        help="브루트포스 병렬 스레드 (기본값: 5)",
    )

    # SAP 포트 (고급 옵션)
    parser.add_argument(
        "--sap-ports",
        type=str,
        default="3200,3300,3600,8000,8001,50000,50013,50014",
        help="SAP 포트 리스트 (기본값: 3200,3300,...)",
    )

    return parser.parse_args()


def get_scan_directory(args: argparse.Namespace) -> Path:
    """스캔 디렉토리 결정"""
    scans_root = Path.home() / "nmap" / "scans"

    # --scan-dir 명시적 지정
    if args.scan_dir:
        scan_dir = args.scan_dir
        scan_dir.mkdir(parents=True, exist_ok=True)
        return scan_dir

    # --resume 플래그
    if args.resume:
        existing = sorted(
            scans_root.glob("rustscan_massive_*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if existing:
            ColorLogger.info(f"Resume: {existing[0]}")
            return existing[0]
        else:
            ColorLogger.warning("기존 스캔 디렉토리 없음 - 새로 생성")

    # 새 디렉토리 생성 (타임스탬프)
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
    scan_dir = get_scan_directory(args)
    ColorLogger.info(f"스캔 디렉토리: {scan_dir}")

    # Config 생성
    script_dir = Path(__file__).parent
    config = Config(
        script_dir=script_dir,
        scan_dir=scan_dir,
        json_file=args.json_file,
        subnets=targets.subnets,
        exclude_ips=targets.exclude,
        skip_vuln=args.skip_vuln,
        skip_bruteforce=args.skip_bruteforce,
        resume=args.resume,
        sudo_password=sudo_password,
        wordlist_users=args.wordlist_users,
        wordlist_passwords=args.wordlist_passwords,
        bruteforce_timeout=args.bruteforce_timeout,
        bruteforce_threads=args.bruteforce_threads,
        sap_ports=args.sap_ports,
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
        ColorLogger.info("체크포인트 저장됨 - --resume으로 재개 가능")
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

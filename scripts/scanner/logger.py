"""색상 로깅 및 진행률 표시 모듈"""
import sys
from typing import Optional


class ColorLogger:
    """ANSI 색상 코드를 사용한 로거"""

    # ANSI 색상 코드
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    # 로그 레벨별 아이콘
    ICON_INFO = "[i]"
    ICON_SUCCESS = "[✓]"
    ICON_ERROR = "[✗]"
    ICON_WARNING = "[!]"
    ICON_DEBUG = "[*]"

    @staticmethod
    def info(msg: str) -> None:
        """정보 메시지 출력 (파란색)"""
        print(f"{ColorLogger.BLUE}{ColorLogger.ICON_INFO}{ColorLogger.RESET} {msg}")

    @staticmethod
    def success(msg: str) -> None:
        """성공 메시지 출력 (녹색)"""
        print(f"{ColorLogger.GREEN}{ColorLogger.ICON_SUCCESS}{ColorLogger.RESET} {msg}")

    @staticmethod
    def error(msg: str) -> None:
        """에러 메시지 출력 (빨간색)"""
        print(f"{ColorLogger.RED}{ColorLogger.ICON_ERROR}{ColorLogger.RESET} {msg}", file=sys.stderr)

    @staticmethod
    def warning(msg: str) -> None:
        """경고 메시지 출력 (노란색)"""
        print(f"{ColorLogger.YELLOW}{ColorLogger.ICON_WARNING}{ColorLogger.RESET} {msg}")

    @staticmethod
    def debug(msg: str) -> None:
        """디버그 메시지 출력 (회색)"""
        print(f"{ColorLogger.WHITE}{ColorLogger.ICON_DEBUG}{ColorLogger.RESET} {msg}")

    @staticmethod
    def phase(phase_name: str, msg: str) -> None:
        """단계별 메시지 출력 (마젠타 강조)"""
        print(f"{ColorLogger.BOLD}{ColorLogger.MAGENTA}[{phase_name}]{ColorLogger.RESET} {msg}")

    @staticmethod
    def progress(current: int, total: int, prefix: str = "") -> None:
        """진행률 표시 (한 줄로 업데이트)"""
        percent = (current / total) * 100 if total > 0 else 0
        bar_length = 40
        filled_length = int(bar_length * current // total) if total > 0 else 0

        bar = "█" * filled_length + "░" * (bar_length - filled_length)
        progress_msg = f"\r{prefix}[{bar}] {current}/{total} ({percent:.1f}%)"

        sys.stdout.write(progress_msg)
        sys.stdout.flush()

        if current >= total:
            sys.stdout.write("\n")

    @staticmethod
    def separator(char: str = "=", length: int = 80) -> None:
        """구분선 출력"""
        print(char * length)

    @staticmethod
    def header(title: str) -> None:
        """헤더 출력 (굵은 파란색)"""
        ColorLogger.separator()
        print(f"{ColorLogger.BOLD}{ColorLogger.CYAN}{title}{ColorLogger.RESET}")
        ColorLogger.separator()

    @staticmethod
    def phase_header(phase_num: int, description: str, subnet: str = "") -> None:
        """Phase 헤더 출력 (단계 번호 + 설명 + 서브넷)"""
        print()
        print(f"{ColorLogger.BOLD}{ColorLogger.BLUE}{'=' * 80}{ColorLogger.RESET}")
        header_text = f"Phase {phase_num}: {description}"
        if subnet:
            header_text += f" ({subnet})"
        print(f"{ColorLogger.BOLD}{ColorLogger.BLUE}{header_text}{ColorLogger.RESET}")
        print(f"{ColorLogger.BOLD}{ColorLogger.BLUE}{'=' * 80}{ColorLogger.RESET}")
        print()


class ProgressTracker:
    """진행률 추적 클래스"""

    def __init__(self, total: int, prefix: str = "Progress"):
        self.total = total
        self.current = 0
        self.prefix = prefix

    def update(self, increment: int = 1) -> None:
        """진행 상태 업데이트"""
        self.current += increment
        ColorLogger.progress(self.current, self.total, self.prefix)

    def reset(self) -> None:
        """진행 상태 초기화"""
        self.current = 0

    def complete(self) -> None:
        """진행 완료 처리"""
        self.current = self.total
        ColorLogger.progress(self.current, self.total, self.prefix)

    def increment(self, step: int = 1) -> None:
        """진행 상태 증가 (update의 별칭)"""
        self.update(step)

    def should_log(self) -> bool:
        """로깅 필요 여부 판단 (10% 단위)"""
        if self.total == 0:
            return False
        # 10% 단위로만 로깅 (1%, 11%, 21%, ...)
        prev_percent = ((self.current - 1) / self.total) * 100
        curr_percent = (self.current / self.total) * 100
        return int(prev_percent / 10) != int(curr_percent / 10)

    def format(self) -> str:
        """진행률 문자열 반환"""
        percent = (self.current / self.total) * 100 if self.total > 0 else 0
        return f"{self.prefix}: {self.current}/{self.total} ({percent:.1f}%)"

"""스캐너 설정 관리 모듈"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    """스캔 설정을 관리하는 데이터 클래스"""

    # 경로
    script_dir: Path
    scan_dir: Path
    json_file: Path

    # 타겟
    subnets: list[str]
    exclude_ips: list[str] = field(default_factory=list)

    # 플래그
    skip_vuln: bool = False
    skip_bruteforce: bool = False
    skip_web_bruteforce: bool = False
    resume: bool = False

    # sudo
    sudo_password: str = ""

    # 브루트포스 설정
    wordlist_users: Optional[Path] = None
    wordlist_passwords: Optional[Path] = None
    bruteforce_timeout: int = 300
    bruteforce_threads: int = 5

    # Web 브루트포스 설정
    web_bruteforce_timeout: int = 60
    web_bruteforce_page_timeout: int = 15000
    web_bruteforce_max_users: int = 10
    web_bruteforce_max_passwords: int = 20
    web_bruteforce_attempt_delay: float = 1.5
    web_login_paths: list[str] = field(default_factory=lambda: [
        "/", "/login", "/admin", "/auth", "/signin",
        "/wp-login.php", "/user/login", "/account/login",
    ])

    # SAP 포트
    sap_ports: str = "3200,3300,3600,8000,8001,50000,50013,50014"

    def __post_init__(self):
        """초기화 후 기본값 설정"""
        if self.wordlist_users is None:
            self.wordlist_users = self.script_dir / "wordlists" / "usernames.txt"
        if self.wordlist_passwords is None:
            self.wordlist_passwords = self.script_dir / "wordlists" / "passwords.txt"

        # Path 타입 보장
        self.script_dir = Path(self.script_dir)
        self.scan_dir = Path(self.scan_dir)
        self.json_file = Path(self.json_file)
        if self.wordlist_users:
            self.wordlist_users = Path(self.wordlist_users)
        if self.wordlist_passwords:
            self.wordlist_passwords = Path(self.wordlist_passwords)

    def validate(self) -> None:
        """설정 검증"""
        if not self.json_file.exists():
            raise FileNotFoundError(f"타겟 파일을 찾을 수 없음: {self.json_file}")

        if not self.subnets:
            raise ValueError("최소 하나 이상의 서브넷이 필요합니다")

        if not self.skip_bruteforce:
            if not self.wordlist_users or not self.wordlist_users.exists():
                raise FileNotFoundError(f"사용자 이름 워드리스트를 찾을 수 없음: {self.wordlist_users}")
            if not self.wordlist_passwords or not self.wordlist_passwords.exists():
                raise FileNotFoundError(f"비밀번호 워드리스트를 찾을 수 없음: {self.wordlist_passwords}")

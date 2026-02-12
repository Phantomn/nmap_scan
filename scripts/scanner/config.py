"""스캐너 설정 관리 모듈"""
from dataclasses import dataclass, field
from pathlib import Path


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

    # sudo
    sudo_password: str = ""

    def __post_init__(self):
        """초기화 후 기본값 설정"""
        # Path 타입 보장
        self.script_dir = Path(self.script_dir)
        self.scan_dir = Path(self.scan_dir)
        self.json_file = Path(self.json_file)

    def validate(self) -> None:
        """설정 검증"""
        if not self.json_file.exists():
            raise FileNotFoundError(f"타겟 파일을 찾을 수 없음: {self.json_file}")

        if not self.subnets:
            raise ValueError("최소 하나 이상의 서브넷이 필요합니다")

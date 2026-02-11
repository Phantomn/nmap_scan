"""체크포인트 관리 모듈

스캔 진행 상태를 저장하고 복원하여 중단된 스캔을 재개할 수 있도록 지원합니다.
"""
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional


@dataclass
class CheckpointData:
    """체크포인트 데이터"""

    phase: int  # 현재 페이즈 (1-4)
    completed_phases: list[int]  # 완료된 페이즈 목록
    current_host: Optional[str] = None  # 현재 처리 중인 호스트
    processed_hosts: list[str] = None  # 처리 완료된 호스트 목록
    total_hosts: int = 0  # 전체 호스트 수

    def __post_init__(self):
        if self.processed_hosts is None:
            self.processed_hosts = []


class CheckpointManager:
    """체크포인트 관리자"""

    def __init__(self, scan_dir: Path):
        """
        Args:
            scan_dir: 스캔 결과 디렉토리
        """
        self.scan_dir = Path(scan_dir)
        self.checkpoint_file = self.scan_dir / "checkpoint.json"

    def save(self, data: CheckpointData) -> None:
        """체크포인트 저장

        Args:
            data: 저장할 체크포인트 데이터
        """
        self.scan_dir.mkdir(parents=True, exist_ok=True)
        with open(self.checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(asdict(data), f, indent=2, ensure_ascii=False)

    def load(self) -> Optional[CheckpointData]:
        """체크포인트 로드

        Returns:
            CheckpointData 또는 None (파일이 없는 경우)
        """
        if not self.checkpoint_file.exists():
            return None

        with open(self.checkpoint_file, encoding="utf-8") as f:
            data_dict = json.load(f)
            return CheckpointData(**data_dict)

    def exists(self) -> bool:
        """체크포인트 존재 여부 확인

        Returns:
            체크포인트 파일이 존재하면 True
        """
        return self.checkpoint_file.exists()

    def clear(self) -> None:
        """체크포인트 삭제"""
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()

    def update_phase(self, phase: int) -> None:
        """페이즈 업데이트

        Args:
            phase: 새로운 페이즈 번호
        """
        data = self.load()
        if data is None:
            data = CheckpointData(phase=phase, completed_phases=[])
        else:
            # 이전 페이즈를 완료 목록에 추가
            if data.phase not in data.completed_phases:
                data.completed_phases.append(data.phase)
            data.phase = phase
            data.current_host = None

        self.save(data)

    def update_host(self, host: str, total_hosts: int) -> None:
        """현재 처리 중인 호스트 업데이트

        Args:
            host: 현재 호스트
            total_hosts: 전체 호스트 수
        """
        data = self.load()
        if data is None:
            data = CheckpointData(phase=1, completed_phases=[])

        data.current_host = host
        data.total_hosts = total_hosts
        self.save(data)

    def mark_host_completed(self, host: str) -> None:
        """호스트 처리 완료 표시

        Args:
            host: 완료된 호스트
        """
        data = self.load()
        if data is None:
            return

        if host not in data.processed_hosts:
            data.processed_hosts.append(host)
        data.current_host = None
        self.save(data)

    def get_remaining_hosts(self, all_hosts: list[str]) -> list[str]:
        """미처리 호스트 목록 반환

        Args:
            all_hosts: 전체 호스트 목록

        Returns:
            처리되지 않은 호스트 목록
        """
        data = self.load()
        if data is None:
            return all_hosts

        return [host for host in all_hosts if host not in data.processed_hosts]

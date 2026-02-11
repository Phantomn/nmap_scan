"""타겟 JSON 파일 로드 및 검증 모듈"""
import json
from pathlib import Path
from typing import Any


class TargetsData:
    """타겟 데이터 클래스"""

    def __init__(self, subnets: list[str], exclude: list[str]):
        self.subnets = subnets
        self.exclude = exclude

    def __repr__(self) -> str:
        return f"TargetsData(subnets={len(self.subnets)}, exclude={len(self.exclude)})"


def load_targets(json_file: Path) -> TargetsData:
    """
    targets.json 로드 및 검증

    Args:
        json_file: JSON 파일 경로

    Returns:
        TargetsData 객체

    Raises:
        FileNotFoundError: 파일이 존재하지 않는 경우
        ValueError: JSON 스키마가 올바르지 않은 경우
        json.JSONDecodeError: JSON 파싱 실패 시
    """
    if not json_file.exists():
        raise FileNotFoundError(f"타겟 파일을 찾을 수 없음: {json_file}")

    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 파싱 실패: {e}") from e

    # 스키마 검증
    if not isinstance(data, dict):
        raise ValueError("JSON 루트는 객체여야 합니다")

    if "subnets" not in data:
        raise ValueError("'subnets' 키가 필요합니다")

    if not isinstance(data["subnets"], list):
        raise ValueError("'subnets'는 배열이어야 합니다")

    if not data["subnets"]:
        raise ValueError("최소 하나 이상의 서브넷이 필요합니다")

    # exclude는 선택적
    exclude = data.get("exclude", [])
    if not isinstance(exclude, list):
        raise ValueError("'exclude'는 배열이어야 합니다")

    return TargetsData(subnets=data["subnets"], exclude=exclude)


def save_targets(json_file: Path, targets: TargetsData) -> None:
    """
    타겟 데이터를 JSON 파일로 저장

    Args:
        json_file: 저장할 파일 경로
        targets: TargetsData 객체
    """
    data = {"subnets": targets.subnets, "exclude": targets.exclude}

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

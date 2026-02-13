"""RTT 기반 rustscan 파라미터 최적화 모듈"""
from dataclasses import dataclass


@dataclass
class RustscanParams:
    """rustscan 실행 파라미터"""

    batch_size: int
    timeout: int  # milliseconds
    parallel_limit: int

    @property
    def required_ulimit(self) -> int:
        """필요한 ulimit 값 계산"""
        return self.parallel_limit * self.batch_size + 5000


def get_safe_rustscan_params() -> RustscanParams:
    """
    안전한 rustscan 파라미터 반환 (고정값)

    Returns:
        RustscanParams: 밸런스 고정 파라미터 (batch_size=10000, timeout=5000, parallel_limit=5, required_ulimit=55000)

    Examples:
        >>> get_safe_rustscan_params()
        RustscanParams(batch_size=10000, timeout=5000, parallel_limit=5)
    """
    return RustscanParams(batch_size=10000, timeout=5000, parallel_limit=5)

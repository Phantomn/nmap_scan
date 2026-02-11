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


def optimize_rustscan_params(avg_rtt: float) -> RustscanParams:
    """
    평균 RTT 기반 rustscan 파라미터 최적화

    Args:
        avg_rtt: 평균 RTT (밀리초)

    Returns:
        RustscanParams: 최적화된 파라미터 (batch_size, timeout, parallel_limit)

    Examples:
        >>> optimize_rustscan_params(5.0)
        RustscanParams(batch_size=65535, timeout=500, parallel_limit=15)

        >>> optimize_rustscan_params(30.0)
        RustscanParams(batch_size=10000, timeout=1500, parallel_limit=12)

        >>> optimize_rustscan_params(100.0)
        RustscanParams(batch_size=8000, timeout=2000, parallel_limit=10)

        >>> optimize_rustscan_params(200.0)
        RustscanParams(batch_size=5000, timeout=5000, parallel_limit=8)
    """
    if avg_rtt < 10:
        # 저지연 네트워크 (LAN)
        return RustscanParams(batch_size=65535, timeout=500, parallel_limit=15)
    elif avg_rtt < 50:
        # 중간 지연 네트워크 (로컬 DC)
        return RustscanParams(batch_size=10000, timeout=1500, parallel_limit=12)
    elif avg_rtt < 150:
        # 일반 WAN 네트워크
        return RustscanParams(batch_size=8000, timeout=2000, parallel_limit=10)
    else:
        # 고지연 네트워크 (원격/해외)
        return RustscanParams(batch_size=5000, timeout=5000, parallel_limit=8)

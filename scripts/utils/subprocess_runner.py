"""비동기 subprocess 실행 래퍼 모듈"""
import asyncio
from pathlib import Path
from typing import Optional


class CommandResult:
    """명령어 실행 결과"""

    def __init__(self, returncode: int, stdout: str, stderr: str):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

    @property
    def success(self) -> bool:
        """명령어가 성공적으로 실행되었는지 확인"""
        return self.returncode == 0

    def __repr__(self) -> str:
        return f"CommandResult(returncode={self.returncode}, success={self.success})"


async def run_command(
    cmd: list[str],
    timeout: Optional[int] = None,
    sudo_password: Optional[str] = None,
    check: bool = False,
    cwd: Optional[Path] = None,
) -> CommandResult:
    """
    비동기로 명령어 실행

    Args:
        cmd: 실행할 명령어 리스트
        timeout: 타임아웃 (초 단위, None이면 무제한)
        sudo_password: sudo 비밀번호 (필요한 경우)
        check: True인 경우 returncode가 0이 아니면 예외 발생
        cwd: 작업 디렉토리 (지정하지 않으면 현재 디렉토리)

    Returns:
        CommandResult 객체 (returncode, stdout, stderr 포함)

    Raises:
        asyncio.TimeoutError: 타임아웃 발생 시
        RuntimeError: check=True이고 명령어 실행 실패 시
    """
    # sudo 명령에 -S 플래그 추가 (stdin에서 비밀번호 읽기)
    if sudo_password and cmd and cmd[0] == "sudo":
        # sudo 다음에 -S가 없으면 추가
        if "-S" not in cmd:
            cmd = [cmd[0], "-S"] + cmd[1:]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        stdin=asyncio.subprocess.PIPE if sudo_password else None,
        cwd=str(cwd) if cwd else None,
    )

    try:
        stdout_data, stderr_data = await asyncio.wait_for(
            proc.communicate(input=sudo_password.encode() if sudo_password else None),
            timeout=timeout,
        )

        result = CommandResult(
            returncode=proc.returncode or 0,
            stdout=stdout_data.decode(errors="replace"),
            stderr=stderr_data.decode(errors="replace"),
        )

        if check and not result.success:
            raise RuntimeError(
                f"명령어 실행 실패 (exit code {result.returncode}): {' '.join(cmd)}\n"
                f"stderr: {result.stderr}"
            )

        return result

    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise


async def run_command_with_retry(
    cmd: list[str],
    max_retries: int = 3,
    retry_delay: int = 2,
    timeout: Optional[int] = None,
    sudo_password: Optional[str] = None,
) -> CommandResult:
    """
    재시도 로직이 포함된 명령어 실행

    Args:
        cmd: 실행할 명령어 리스트
        max_retries: 최대 재시도 횟수
        retry_delay: 재시도 간 대기 시간 (초)
        timeout: 타임아웃 (초 단위)
        sudo_password: sudo 비밀번호

    Returns:
        CommandResult 객체

    Raises:
        RuntimeError: 모든 재시도 실패 시
    """
    last_exception = None

    for attempt in range(max_retries):
        try:
            result = await run_command(cmd, timeout=timeout, sudo_password=sudo_password)
            if result.success:
                return result
        except Exception as e:
            last_exception = e

        if attempt < max_retries - 1:
            await asyncio.sleep(retry_delay)

    raise RuntimeError(
        f"명령어 실행 실패 ({max_retries}회 시도): {' '.join(cmd)}"
    ) from last_exception

"""Playwright 기반 Web 브루트포스 모듈"""
import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, Browser, Page, Playwright


@dataclass
class WebBruteforceResult:
    """Web 브루트포스 실행 결과"""

    ip: str
    port: int
    service: str  # "http" | "https"
    status: str  # "success" | "failed" | "no_form" | "captcha" | "timeout" | "error"
    url: str = ""
    credentials: list[dict] = field(default_factory=list)
    screenshots: list[str] = field(default_factory=list)
    error: str = ""


class WebBruteforcer:
    """Playwright 기반 Web 브루트포스 엔진"""

    # 로그인 성공 키워드
    SUCCESS_KEYWORDS = [
        "logout",
        "dashboard",
        "welcome",
        "profile",
        "signout",
        "sign out",
        "logged in",
        "account",
    ]

    # 로그인 실패 키워드 (false positive 방지)
    FAILURE_KEYWORDS = [
        "invalid",
        "incorrect",
        "failed",
        "wrong",
        "error",
        "denied",
        "login",
    ]

    def __init__(self, config, scan_dir: Path):
        """
        Args:
            config: Config 객체 (web_bruteforce_* 설정 필요)
            scan_dir: 스크린샷 저장 디렉터리
        """
        self.config = config
        self.scan_dir = scan_dir
        self.screenshot_dir = scan_dir / "screenshots"
        self.screenshot_dir.mkdir(exist_ok=True)

        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None

    async def start_browser(self) -> None:
        """Chromium 브라우저 시작 (1회)"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)

    async def close_browser(self) -> None:
        """브라우저 종료"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def bruteforce(
        self,
        ip: str,
        port: int,
        service: str,
        usernames: list[str],
        passwords: list[str],
        discovered_paths: list[str] | None = None,
    ) -> WebBruteforceResult:
        """
        단일 호스트 Web 브루트포스 실행

        Args:
            ip: 대상 IP
            port: 대상 포트
            service: "http" 또는 "https"
            usernames: 사용자명 리스트
            passwords: 비밀번호 리스트
            discovered_paths: Phase 3에서 탐지된 경로 리스트 (우선 시도)

        Returns:
            WebBruteforceResult
        """
        result = WebBruteforceResult(ip=ip, port=port, service=service, status="failed")

        try:
            # 1. 로그인 페이지 탐색 (탐지된 경로 우선 → fallback)
            login_url, form_info = await self._discover_login_page(
                ip, port, service, discovered_paths
            )
            if not login_url:
                result.status = "no_form"
                return result

            result.url = login_url

            # 2. CAPTCHA 확인
            if await self._detect_captcha(login_url):
                result.status = "captcha"
                return result

            # 3. 폼 발견 스크린샷
            screenshot_path = await self._take_screenshot(
                login_url, f"{ip.replace('.', '_')}_{port}_form_detected"
            )
            if screenshot_path:
                result.screenshots.append(str(screenshot_path))

            # 4. 크레덴셜 시도 (상위 N x M 조합)
            max_users = self.config.web_bruteforce_max_users
            max_passwords = self.config.web_bruteforce_max_passwords

            for username in usernames[:max_users]:
                for password in passwords[:max_passwords]:
                    success = await self._try_credential(
                        login_url, form_info, username, password
                    )

                    if success:
                        result.status = "success"
                        result.credentials.append(
                            {"username": username, "password": password}
                        )

                        # 성공 스크린샷
                        screenshot_path = await self._take_screenshot(
                            login_url, f"{ip.replace('.', '_')}_{port}_success"
                        )
                        if screenshot_path:
                            result.screenshots.append(str(screenshot_path))

                        return result

                    # 시도 간 지연
                    await asyncio.sleep(self.config.web_bruteforce_attempt_delay)

        except asyncio.TimeoutError:
            result.status = "timeout"
        except Exception as e:
            result.status = "error"
            result.error = str(e)

        return result

    async def _discover_login_page(
        self,
        ip: str,
        port: int,
        service: str,
        discovered_paths: list[str] | None = None,
    ) -> tuple[str | None, dict]:
        """
        로그인 폼 탐색 (탐지된 경로 우선, fallback 지원)

        Args:
            discovered_paths: Phase 3에서 탐지된 경로 (있으면 우선 시도)

        Returns:
            (login_url, form_info) 튜플 (폼 없으면 (None, {}))
        """
        base_url = f"{service}://{ip}:{port}"

        # 1단계: Phase 3에서 탐지된 경로 우선 시도
        if discovered_paths:
            for path in discovered_paths:
                url = base_url + path
                try:
                    page = await self.browser.new_page()
                    await page.goto(
                        url, timeout=self.config.web_bruteforce_page_timeout
                    )

                    form_info = await self._detect_login_form(page)
                    if form_info:
                        await page.close()
                        return url, form_info

                    await page.close()
                except Exception:
                    continue

        # 2단계: Fallback - config 경로 시도 (탐지 실패 시만)
        for path in self.config.web_login_paths:
            url = base_url + path
            try:
                page = await self.browser.new_page()
                await page.goto(url, timeout=self.config.web_bruteforce_page_timeout)

                form_info = await self._detect_login_form(page)
                if form_info:
                    await page.close()
                    return url, form_info

                await page.close()
            except Exception:
                continue

        return None, {}

    async def _detect_login_form(self, page: Page) -> dict:
        """
        로그인 폼 필드 매핑

        Returns:
            {"username": selector, "password": selector, "submit": selector}
            (필수: username, password)
        """
        # username 필드 탐지
        username_selectors = [
            'input[name*="user"]',
            'input[name*="login"]',
            'input[name*="email"]',
            'input[id*="user"]',
            'input[id*="login"]',
            'input[type="text"]',
        ]

        # password 필드 탐지
        password_selectors = [
            'input[type="password"]',
            'input[name*="pass"]',
            'input[id*="pass"]',
        ]

        # submit 버튼 탐지
        submit_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("login")',
            'button:has-text("sign in")',
        ]

        form_info = {}

        for selector in username_selectors:
            if await page.query_selector(selector):
                form_info["username"] = selector
                break

        for selector in password_selectors:
            if await page.query_selector(selector):
                form_info["password"] = selector
                break

        for selector in submit_selectors:
            if await page.query_selector(selector):
                form_info["submit"] = selector
                break

        # username, password 필수
        if "username" in form_info and "password" in form_info:
            return form_info

        return {}

    async def _detect_captcha(self, url: str) -> bool:
        """
        CAPTCHA 탐지

        Returns:
            CAPTCHA 존재 여부
        """
        try:
            page = await self.browser.new_page()
            await page.goto(url, timeout=self.config.web_bruteforce_page_timeout)

            captcha_keywords = ["captcha", "recaptcha", "hcaptcha", "challenge"]
            content = await page.content()

            await page.close()
            return any(keyword in content.lower() for keyword in captcha_keywords)
        except Exception:
            return False

    async def _try_credential(
        self, url: str, form_info: dict, username: str, password: str
    ) -> bool:
        """
        단일 크레덴셜 시도

        Returns:
            로그인 성공 여부
        """
        try:
            page = await self.browser.new_page()
            await page.goto(url, timeout=self.config.web_bruteforce_page_timeout)

            # 폼 입력
            await page.fill(form_info["username"], username)
            await page.fill(form_info["password"], password)

            # 제출
            if "submit" in form_info:
                await page.click(form_info["submit"])
            else:
                await page.press(form_info["password"], "Enter")

            # 로그인 성공 확인 (최대 5초 대기)
            await page.wait_for_load_state("networkidle", timeout=5000)

            success = await self._check_login_success(page, url)
            await page.close()

            return success
        except Exception:
            return False

    async def _check_login_success(self, page: Page, original_url: str) -> bool:
        """
        로그인 성공 여부 확인 (다중 기준)

        Returns:
            로그인 성공 여부
        """
        # 1. URL 변경 확인
        current_url = page.url
        if current_url != original_url and "/login" not in current_url.lower():
            return True

        # 2. 성공 키워드 확인
        content = await page.content()
        content_lower = content.lower()

        if any(keyword in content_lower for keyword in self.SUCCESS_KEYWORDS):
            return True

        # 3. 실패 키워드 확인 (false positive 방지)
        if any(keyword in content_lower for keyword in self.FAILURE_KEYWORDS):
            return False

        # 4. 로그인 폼 소멸 확인
        username_field = await page.query_selector('input[type="text"]')
        password_field = await page.query_selector('input[type="password"]')

        if not username_field and not password_field:
            return True

        return False

    async def _take_screenshot(self, url: str, filename: str) -> Path | None:
        """
        스크린샷 촬영

        Args:
            url: 대상 URL
            filename: 파일명 (확장자 제외)

        Returns:
            스크린샷 경로 (실패 시 None)
        """
        try:
            page = await self.browser.new_page()
            await page.goto(url, timeout=self.config.web_bruteforce_page_timeout)

            screenshot_path = self.screenshot_dir / f"{filename}.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)

            await page.close()
            return screenshot_path
        except Exception:
            return None

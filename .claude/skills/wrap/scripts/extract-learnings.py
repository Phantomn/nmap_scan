#!/usr/bin/env python3
"""
extract-learnings.py - 세션 로그에서 학습 내용 자동 추출
"""
import json
import re
import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


class LearningExtractor:
    """세션 로그 분석 및 학습 내용 추출"""

    def __init__(self, log_file: Path):
        self.log_file = log_file
        self.learnings = []
        self.mistakes = []
        self.patterns = []

    def extract_from_log(self) -> Dict[str, Any]:
        """로그 파일에서 학습 내용 추출"""
        with open(self.log_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    self._analyze_entry(entry)
                except json.JSONDecodeError:
                    continue

        return {
            "timestamp": datetime.now().isoformat(),
            "session_file": str(self.log_file),
            "learnings": self.learnings,
            "mistakes": self.mistakes,
            "patterns": self.patterns,
            "summary": self._generate_summary()
        }

    def _analyze_entry(self, entry: Dict[str, Any]):
        """개별 로그 항목 분석"""
        content = str(entry)

        # 에러 패턴 감지
        if self._is_error(content):
            self.mistakes.append(self._extract_mistake(entry))

        # 해결 패턴 감지
        if self._is_solution(content):
            self.learnings.append(self._extract_learning(entry))

        # 반복 패턴 감지
        pattern = self._detect_pattern(content)
        if pattern:
            self.patterns.append(pattern)

    def _is_error(self, content: str) -> bool:
        """에러 관련 내용 확인"""
        error_keywords = ['error', 'failed', 'exception', 'traceback', '❌']
        return any(keyword in content.lower() for keyword in error_keywords)

    def _is_solution(self, content: str) -> bool:
        """해결책 관련 내용 확인"""
        solution_keywords = ['fixed', 'solved', 'resolved', 'success', '✅']
        return any(keyword in content.lower() for keyword in solution_keywords)

    def _extract_mistake(self, entry: Dict[str, Any]) -> Dict[str, str]:
        """실수 내용 추출"""
        return {
            "type": "mistake",
            "description": self._clean_text(str(entry)[:200]),
            "timestamp": entry.get("timestamp", "")
        }

    def _extract_learning(self, entry: Dict[str, Any]) -> Dict[str, str]:
        """학습 내용 추출"""
        return {
            "type": "learning",
            "description": self._clean_text(str(entry)[:200]),
            "timestamp": entry.get("timestamp", "")
        }

    def _detect_pattern(self, content: str) -> Dict[str, str] | None:
        """반복 패턴 감지"""
        # 특정 도구나 명령어 반복 사용 패턴
        tool_pattern = re.search(r'(ruff|mypy|eslint|tsc|clippy)\s+\w+', content)
        if tool_pattern:
            return {
                "type": "tool_usage",
                "pattern": tool_pattern.group(0)
            }
        return None

    def _clean_text(self, text: str) -> str:
        """텍스트 정리"""
        # ANSI 색상 코드 제거
        text = re.sub(r'\x1b\[[0-9;]*m', '', text)
        # 여러 줄바꿈을 하나로
        text = re.sub(r'\n+', ' ', text)
        # 여러 공백을 하나로
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _generate_summary(self) -> str:
        """요약 생성"""
        return f"""
세션 분석 요약:
- 학습 내용: {len(self.learnings)}개
- 실수/오류: {len(self.mistakes)}개
- 반복 패턴: {len(self.patterns)}개
"""


def main():
    if len(sys.argv) < 2:
        print("사용법: extract-learnings.py <session_log.jsonl>")
        sys.exit(1)

    log_file = Path(sys.argv[1])
    if not log_file.exists():
        print(f"❌ 파일 미발견: {log_file}")
        sys.exit(1)

    extractor = LearningExtractor(log_file)
    result = extractor.extract_from_log()

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

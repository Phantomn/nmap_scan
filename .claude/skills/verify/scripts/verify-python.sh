#!/usr/bin/env bash
# verify-python.sh - Python 프로젝트 검증 스크립트
set -euo pipefail

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 결과 추적
ERRORS=0
WARNINGS=0

echo "🐍 Python 프로젝트 검증 시작..."

# 환경 감지
detect_environment() {
    if [[ -f "pyproject.toml" ]]; then
        echo "✅ pyproject.toml 감지"
        return 0
    elif [[ -f "setup.py" ]] || [[ -f "setup.cfg" ]]; then
        echo "✅ setup.py/setup.cfg 감지"
        return 0
    elif [[ -f "requirements.txt" ]]; then
        echo "✅ requirements.txt 감지"
        return 0
    else
        echo -e "${YELLOW}⚠️  Python 프로젝트 설정 파일 미발견${NC}"
        WARNINGS=$((WARNINGS + 1))
        return 1
    fi
}

# Ruff 린트 검사
run_ruff() {
    if ! command -v ruff &> /dev/null; then
        echo -e "${YELLOW}⚠️  ruff 미설치 (pip install ruff)${NC}"
        WARNINGS=$((WARNINGS + 1))
        return 1
    fi

    echo ""
    echo "📋 Ruff 린트 검사 중..."
    if ruff check . --output-format=concise; then
        echo -e "${GREEN}✅ Ruff 린트 통과${NC}"
        return 0
    else
        echo -e "${RED}❌ Ruff 린트 실패${NC}"
        echo "💡 자동 수정: ruff check . --fix"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

# MyPy 타입 검사
run_mypy() {
    if ! command -v mypy &> /dev/null; then
        echo -e "${YELLOW}⚠️  mypy 미설치 (pip install mypy)${NC}"
        WARNINGS=$((WARNINGS + 1))
        return 1
    fi

    echo ""
    echo "🔍 MyPy 타입 검사 중..."
    if mypy . --no-error-summary 2>&1 | head -20; then
        echo -e "${GREEN}✅ MyPy 타입 검사 통과${NC}"
        return 0
    else
        echo -e "${RED}❌ MyPy 타입 검사 실패${NC}"
        echo "💡 설정: mypy.ini 또는 pyproject.toml [tool.mypy] 확인"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

# Pytest 테스트 실행
run_pytest() {
    if ! command -v pytest &> /dev/null; then
        echo -e "${YELLOW}⚠️  pytest 미설치 (pip install pytest)${NC}"
        WARNINGS=$((WARNINGS + 1))
        return 1
    fi

    # 테스트 파일 존재 확인
    if ! find . -name "test_*.py" -o -name "*_test.py" | grep -q .; then
        echo -e "${YELLOW}⚠️  테스트 파일 미발견${NC}"
        WARNINGS=$((WARNINGS + 1))
        return 1
    fi

    echo ""
    echo "🧪 Pytest 테스트 실행 중..."
    if pytest -v --tb=short --maxfail=5; then
        echo -e "${GREEN}✅ Pytest 테스트 통과${NC}"
        return 0
    else
        echo -e "${RED}❌ Pytest 테스트 실패${NC}"
        echo "💡 상세 로그: pytest -vv --tb=long"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

# 커버리지 검사 (선택)
run_coverage() {
    if ! command -v coverage &> /dev/null; then
        return 0  # 선택적 기능
    fi

    echo ""
    echo "📊 커버리지 검사 중..."
    if coverage run -m pytest && coverage report --skip-empty; then
        echo -e "${GREEN}✅ 커버리지 리포트 생성 완료${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  커버리지 검사 실패${NC}"
        WARNINGS=$((WARNINGS + 1))
        return 1
    fi
}

# 메인 실행
main() {
    detect_environment

    run_ruff
    run_mypy
    run_pytest
    run_coverage  # 선택적

    echo ""
    echo "============================================"
    if [[ $ERRORS -eq 0 ]]; then
        echo -e "${GREEN}✅ 전체 검증 완료: 에러 $ERRORS개, 경고 $WARNINGS개${NC}"
        exit 0
    else
        echo -e "${RED}❌ 검증 실패: 에러 $ERRORS개, 경고 $WARNINGS개${NC}"
        exit 1
    fi
}

main "$@"

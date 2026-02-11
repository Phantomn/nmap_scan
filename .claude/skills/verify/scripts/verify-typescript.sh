#!/usr/bin/env bash
# verify-typescript.sh - TypeScript/JavaScript 프로젝트 검증 스크립트
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERRORS=0
WARNINGS=0

echo "📘 TypeScript/JavaScript 프로젝트 검증 시작..."

# 환경 감지
detect_environment() {
    if [[ -f "package.json" ]]; then
        echo "✅ package.json 감지"

        # 프로젝트 타입 확인
        if [[ -f "tsconfig.json" ]]; then
            echo "  📘 TypeScript 프로젝트"
            PROJECT_TYPE="typescript"
        else
            echo "  📙 JavaScript 프로젝트"
            PROJECT_TYPE="javascript"
        fi
        return 0
    else
        echo -e "${RED}❌ package.json 미발견${NC}"
        ERRORS=$((ERRORS + 1))
        exit 1
    fi
}

# ESLint 검사
run_eslint() {
    if ! command -v eslint &> /dev/null && ! npm list eslint &> /dev/null; then
        echo -e "${YELLOW}⚠️  ESLint 미설치 (npm install -D eslint)${NC}"
        WARNINGS=$((WARNINGS + 1))
        return 1
    fi

    echo ""
    echo "📋 ESLint 검사 중..."
    if npx eslint . --ext .js,.jsx,.ts,.tsx --format=compact; then
        echo -e "${GREEN}✅ ESLint 통과${NC}"
        return 0
    else
        echo -e "${RED}❌ ESLint 실패${NC}"
        echo "💡 자동 수정: npx eslint . --fix"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

# TypeScript 컴파일 검사
run_tsc() {
    if [[ "$PROJECT_TYPE" != "typescript" ]]; then
        return 0  # JavaScript 프로젝트는 스킵
    fi

    if ! command -v tsc &> /dev/null && ! npm list typescript &> /dev/null; then
        echo -e "${YELLOW}⚠️  TypeScript 미설치 (npm install -D typescript)${NC}"
        WARNINGS=$((WARNINGS + 1))
        return 1
    fi

    echo ""
    echo "🔍 TypeScript 컴파일 검사 중..."
    if npx tsc --noEmit; then
        echo -e "${GREEN}✅ TypeScript 컴파일 통과${NC}"
        return 0
    else
        echo -e "${RED}❌ TypeScript 컴파일 실패${NC}"
        echo "💡 설정: tsconfig.json 확인"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

# 테스트 실행 (Vitest/Jest)
run_tests() {
    # package.json에서 테스트 스크립트 확인
    if ! grep -q '"test"' package.json; then
        echo -e "${YELLOW}⚠️  package.json에 test 스크립트 미정의${NC}"
        WARNINGS=$((WARNINGS + 1))
        return 1
    fi

    echo ""
    echo "🧪 테스트 실행 중..."
    if npm test -- --run; then
        echo -e "${GREEN}✅ 테스트 통과${NC}"
        return 0
    else
        echo -e "${RED}❌ 테스트 실패${NC}"
        echo "💡 상세 로그: npm test -- --reporter=verbose"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

# Prettier 포맷 검사
run_prettier() {
    if ! command -v prettier &> /dev/null && ! npm list prettier &> /dev/null; then
        return 0  # 선택적 기능
    fi

    echo ""
    echo "✨ Prettier 포맷 검사 중..."
    if npx prettier --check .; then
        echo -e "${GREEN}✅ Prettier 포맷 통과${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  Prettier 포맷 불일치${NC}"
        echo "💡 자동 수정: npx prettier --write ."
        WARNINGS=$((WARNINGS + 1))
        return 1
    fi
}

# 빌드 검사 (선택)
run_build() {
    if ! grep -q '"build"' package.json; then
        return 0  # 빌드 스크립트 없으면 스킵
    fi

    echo ""
    echo "🏗️  빌드 검사 중..."
    if npm run build; then
        echo -e "${GREEN}✅ 빌드 성공${NC}"
        return 0
    else
        echo -e "${RED}❌ 빌드 실패${NC}"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

# 메인 실행
main() {
    detect_environment

    run_eslint
    run_tsc
    run_prettier
    run_tests
    # run_build  # 필요 시 활성화

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

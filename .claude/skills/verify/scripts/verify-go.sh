#!/usr/bin/env bash
# verify-go.sh - Go 프로젝트 검증 스크립트
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERRORS=0
WARNINGS=0

echo "🐹 Go 프로젝트 검증 시작..."

# 환경 감지
detect_environment() {
    if [[ -f "go.mod" ]]; then
        echo "✅ go.mod 감지"
        MODULE=$(go list -m)
        echo "  모듈: $MODULE"
        return 0
    else
        echo -e "${RED}❌ go.mod 미발견${NC}"
        ERRORS=$((ERRORS + 1))
        exit 1
    fi
}

# Go fmt 검사
run_gofmt() {
    echo ""
    echo "📋 Go fmt 검사 중..."
    UNFORMATTED=$(gofmt -l . | grep -v vendor || true)

    if [[ -z "$UNFORMATTED" ]]; then
        echo -e "${GREEN}✅ Go fmt 통과${NC}"
        return 0
    else
        echo -e "${RED}❌ 포맷되지 않은 파일:${NC}"
        echo "$UNFORMATTED"
        echo "💡 자동 수정: gofmt -w ."
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

# Go vet 검사
run_govet() {
    echo ""
    echo "🔍 Go vet 검사 중..."
    if go vet ./...; then
        echo -e "${GREEN}✅ Go vet 통과${NC}"
        return 0
    else
        echo -e "${RED}❌ Go vet 실패${NC}"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

# golangci-lint 검사
run_golangcilint() {
    if ! command -v golangci-lint &> /dev/null; then
        echo -e "${YELLOW}⚠️  golangci-lint 미설치${NC}"
        echo "💡 설치: go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest"
        WARNINGS=$((WARNINGS + 1))
        return 1
    fi

    echo ""
    echo "🔧 golangci-lint 검사 중..."
    if golangci-lint run --timeout=5m; then
        echo -e "${GREEN}✅ golangci-lint 통과${NC}"
        return 0
    else
        echo -e "${RED}❌ golangci-lint 실패${NC}"
        echo "💡 자동 수정: golangci-lint run --fix"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

# Go test 실행
run_gotest() {
    echo ""
    echo "🧪 Go test 실행 중..."
    if go test -v -race -cover ./...; then
        echo -e "${GREEN}✅ Go test 통과${NC}"
        return 0
    else
        echo -e "${RED}❌ Go test 실패${NC}"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

# Go mod tidy 검사
run_gomodtidy() {
    echo ""
    echo "📦 Go mod tidy 검사 중..."
    go mod tidy

    if git diff --exit-code go.mod go.sum &> /dev/null; then
        echo -e "${GREEN}✅ Go mod 정리됨${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  go.mod/go.sum 변경됨 (자동 정리 완료)${NC}"
        WARNINGS=$((WARNINGS + 1))
        return 1
    fi
}

# Go build 검사
run_gobuild() {
    echo ""
    echo "🏗️  Go build 검사 중..."
    if go build -v ./...; then
        echo -e "${GREEN}✅ Go build 성공${NC}"
        return 0
    else
        echo -e "${RED}❌ Go build 실패${NC}"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

# 메인 실행
main() {
    detect_environment

    run_gofmt
    run_govet
    run_golangcilint
    run_gomodtidy
    run_gobuild
    run_gotest

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

#!/usr/bin/env bash
# verify-rust.sh - Rust 프로젝트 검증 스크립트
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERRORS=0
WARNINGS=0

echo "🦀 Rust 프로젝트 검증 시작..."

# 환경 감지
detect_environment() {
    if [[ -f "Cargo.toml" ]]; then
        echo "✅ Cargo.toml 감지"
        PACKAGE=$(cargo metadata --no-deps --format-version 1 | jq -r '.packages[0].name')
        echo "  패키지: $PACKAGE"
        return 0
    else
        echo -e "${RED}❌ Cargo.toml 미발견${NC}"
        ERRORS=$((ERRORS + 1))
        exit 1
    fi
}

# Cargo fmt 검사
run_cargofmt() {
    if ! command -v rustfmt &> /dev/null; then
        echo -e "${YELLOW}⚠️  rustfmt 미설치 (rustup component add rustfmt)${NC}"
        WARNINGS=$((WARNINGS + 1))
        return 1
    fi

    echo ""
    echo "📋 Cargo fmt 검사 중..."
    if cargo fmt -- --check; then
        echo -e "${GREEN}✅ Cargo fmt 통과${NC}"
        return 0
    else
        echo -e "${RED}❌ Cargo fmt 실패${NC}"
        echo "💡 자동 수정: cargo fmt"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

# Cargo clippy 검사
run_clippy() {
    if ! command -v cargo-clippy &> /dev/null; then
        echo -e "${YELLOW}⚠️  clippy 미설치 (rustup component add clippy)${NC}"
        WARNINGS=$((WARNINGS + 1))
        return 1
    fi

    echo ""
    echo "🔍 Cargo clippy 검사 중..."
    if cargo clippy -- -D warnings; then
        echo -e "${GREEN}✅ Clippy 통과${NC}"
        return 0
    else
        echo -e "${RED}❌ Clippy 실패${NC}"
        echo "💡 자동 수정: cargo clippy --fix --allow-dirty"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

# Cargo check 검사
run_cargocheck() {
    echo ""
    echo "🔧 Cargo check 검사 중..."
    if cargo check --all-targets; then
        echo -e "${GREEN}✅ Cargo check 통과${NC}"
        return 0
    else
        echo -e "${RED}❌ Cargo check 실패${NC}"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

# Cargo test 실행
run_cargotest() {
    echo ""
    echo "🧪 Cargo test 실행 중..."
    if cargo test --all-features; then
        echo -e "${GREEN}✅ Cargo test 통과${NC}"
        return 0
    else
        echo -e "${RED}❌ Cargo test 실패${NC}"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

# Cargo build 검사
run_cargobuild() {
    echo ""
    echo "🏗️  Cargo build 검사 중..."
    if cargo build --release; then
        echo -e "${GREEN}✅ Cargo build 성공${NC}"
        return 0
    else
        echo -e "${RED}❌ Cargo build 실패${NC}"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

# Cargo audit 검사 (선택)
run_cargoaudit() {
    if ! command -v cargo-audit &> /dev/null; then
        return 0  # 선택적 기능
    fi

    echo ""
    echo "🛡️  Cargo audit 검사 중..."
    if cargo audit; then
        echo -e "${GREEN}✅ Cargo audit 통과 (보안 취약점 없음)${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  보안 취약점 발견${NC}"
        echo "💡 업데이트: cargo update"
        WARNINGS=$((WARNINGS + 1))
        return 1
    fi
}

# 메인 실행
main() {
    detect_environment

    run_cargofmt
    run_clippy
    run_cargocheck
    run_cargotest
    run_cargobuild
    run_cargoaudit  # 선택적

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

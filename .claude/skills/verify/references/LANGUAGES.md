# 언어별 검증 도구 상세 가이드

## Python

### 필수 도구
- **ruff**: 초고속 린터/포매터 (Flake8 + Black 대체)
- **mypy**: 정적 타입 검사
- **pytest**: 테스트 프레임워크

### 설치
```bash
pip install ruff mypy pytest pytest-cov
```

### 설정 파일

**pyproject.toml** (권장):
```toml
[tool.ruff]
line-length = 88
target-version = "py311"
select = ["E", "F", "W", "I", "N"]
ignore = ["E501"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
```

### 실행 명령어
```bash
ruff check .              # 린트 검사
ruff check . --fix        # 자동 수정
mypy .                    # 타입 검사
pytest -v                 # 테스트
pytest --cov=src --cov-report=html  # 커버리지
```

---

## TypeScript/JavaScript

### 필수 도구
- **ESLint**: 린터
- **TypeScript**: 타입 검사
- **Prettier**: 포매터
- **Vitest/Jest**: 테스트

### 설치
```bash
npm install -D eslint @typescript-eslint/parser @typescript-eslint/eslint-plugin
npm install -D prettier eslint-config-prettier
npm install -D typescript
npm install -D vitest  # 또는 jest
```

### 설정 파일

**.eslintrc.json**:
```json
{
  "parser": "@typescript-eslint/parser",
  "extends": [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "prettier"
  ],
  "rules": {
    "no-console": "warn",
    "@typescript-eslint/no-unused-vars": "error"
  }
}
```

**tsconfig.json**:
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true
  }
}
```

**.prettierrc**:
```json
{
  "semi": true,
  "singleQuote": true,
  "tabWidth": 2,
  "trailingComma": "es5"
}
```

---

## Go

### 필수 도구
- **gofmt**: 공식 포매터
- **go vet**: 공식 린터
- **golangci-lint**: 통합 린터
- **go test**: 테스트

### 설치
```bash
go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest
```

### 설정 파일

**.golangci.yml**:
```yaml
linters:
  enable:
    - gofmt
    - govet
    - staticcheck
    - gosimple
    - unused
    - errcheck

linters-settings:
  gofmt:
    simplify: true

run:
  timeout: 5m
  tests: true
```

### 실행 명령어
```bash
gofmt -l .                # 포맷 검사
go vet ./...              # 린트
golangci-lint run         # 통합 린트
go test -v -race -cover ./...  # 테스트
go mod tidy               # 의존성 정리
```

---

## Rust

### 필수 도구
- **rustfmt**: 공식 포매터
- **clippy**: 공식 린터
- **cargo test**: 테스트

### 설치
```bash
rustup component add rustfmt clippy
```

### 설정 파일

**rustfmt.toml**:
```toml
edition = "2021"
max_width = 100
use_small_heuristics = "Default"
```

**Cargo.toml** (clippy 설정):
```toml
[lints.clippy]
all = "warn"
pedantic = "warn"
nursery = "warn"
```

### 실행 명령어
```bash
cargo fmt -- --check      # 포맷 검사
cargo clippy -- -D warnings  # 린트
cargo test                # 테스트
cargo build --release     # 빌드
cargo audit               # 보안 취약점 검사
```

---

## 공통 체크리스트

### 모든 프로젝트에서 확인할 것
- [ ] 린트 도구 설정 완료
- [ ] 타입 검사 설정 완료 (TypeScript, Python, Go 등)
- [ ] 테스트 프레임워크 설정
- [ ] CI/CD 파이프라인 통합
- [ ] 프리커밋 훅 설정
- [ ] 커버리지 목표 설정 (권장: 80%+)

### 설정 우선순위
1. **린트**: 코드 스타일 일관성
2. **타입**: 타입 안전성 보장
3. **테스트**: 기능 정확성 검증
4. **빌드**: 배포 가능성 확인
5. **보안**: 취약점 스캔 (선택)

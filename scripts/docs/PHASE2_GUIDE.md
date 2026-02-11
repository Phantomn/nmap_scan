# Phase 2: PortScanner 가이드

## 개요

Phase 2는 **rustscan**을 사용하여 활성 호스트의 **전체 포트**를 병렬로 스캔합니다.

## 핵심 기능

### 1. RTT 기반 자동 최적화

Phase 1에서 측정한 평균 RTT를 기반으로 rustscan 파라미터를 자동 최적화합니다.

| RTT 구간 | 환경 | batch_size | timeout | parallel |
|----------|------|------------|---------|----------|
| < 10ms | LAN | 65535 | 500ms | 15 |
| 10-50ms | 로컬 DC | 10000 | 1500ms | 12 |
| 50-150ms | WAN | 8000 | 2000ms | 10 |
| ≥ 150ms | 원격/해외 | 5000 | 5000ms | 8 |

### 2. 병렬 스캔

- **Main 스캔**: 전체 포트 (1-65535)
- **SAP 스캔**: SAP 특화 포트 (3200, 3300, 8000, 50000 등)

두 스캔을 **동시에 병렬 실행**하여 속도를 극대화합니다.

### 3. ulimit 자동 관리

rustscan은 많은 파일 디스크립터를 사용하므로, 필요한 만큼 **ulimit을 자동 증가**시킵니다.

```python
required_ulimit = parallel_limit * batch_size + 5000
```

실패 시 명확한 에러 메시지를 출력합니다.

## 입력 파일

Phase 1의 출력 파일을 입력으로 사용합니다.

- `alive_hosts_{label}.txt`: 활성 호스트 목록 (IP 리스트)
- `avg_rtt_{label}.txt`: 평균 RTT (밀리초)

## 출력 파일

### 중간 파일
- `phase2_rustscan_{host}.txt`: Main 스캔 원본 결과 (rustscan 출력)
- `phase2_sap_{host}.txt`: SAP 스캔 원본 결과

### 최종 파일
- `phase2_all_ports_{label}.txt`: IP:PORT 리스트 (중복 제거)
  ```
  192.168.1.100:22
  192.168.1.100:80
  192.168.1.100:443
  192.168.1.101:3306
  ```

- **`phase2_port_map_{label}.txt`**: IP:PORT1,PORT2,... 포맷 (**Phase 3 입력**)
  ```
  192.168.1.100:22,80,443
  192.168.1.101:3306
  ```

## 사용 예시

### Python API

```python
from phases.phase2 import PortScanner
from scanner.config import Config

config = Config(...)
scanner = PortScanner(config, scan_dir)

# 비동기 호출
port_map_file = await scanner.scan(subnet="192.168.1.0/24", label="192_168_1_0_24")

if port_map_file:
    print(f"포트 맵 생성: {port_map_file}")
else:
    print("포트 없음 - Phase 3 스킵")
```

### CLI (rustscan_massive.py)

Phase 2는 자동으로 실행됩니다. 별도 실행 불가.

```bash
# 전체 스캔 (Phase 1-4)
python3 rustscan_massive.py --json-file targets.json

# Phase 4 스킵 (Phase 1-3만 실행)
python3 rustscan_massive.py --skip-vuln
```

## 에러 처리

### 1. 활성 호스트 없음

```
⏭ Phase 2 건너뜀: 활성 호스트 없음 (192.168.1.0/24)
```

→ Phase 1에서 0개 호스트 발견 시 Phase 2-4 스킵

### 2. avg_rtt 파일 없음

```
avg_rtt_192_168_1_0_24.txt 파일을 찾을 수 없음
```

→ Phase 1이 정상 완료되지 않음 (중단되었거나 실패)

### 3. ulimit 증가 실패

```
ulimit 증가 실패: sudo를 사용하거나 /etc/security/limits.conf 수정 필요
현재: 1024, 필요: 988025
```

→ `/etc/security/limits.conf` 수정 필요:
```
* soft nofile 1048576
* hard nofile 1048576
```

### 4. rustscan 실행 실패

```
Main 스캔 실패 (192.168.1.100): Command 'rustscan' not found
```

→ rustscan 설치 필요:
```bash
cargo install rustscan
```

## 성능 최적화 팁

### 1. RTT 프로파일링 정확도 향상

Phase 1에서 더 많은 샘플을 사용하여 RTT를 측정하면 Phase 2 성능이 향상됩니다.

### 2. ulimit 사전 설정

스크립트 실행 전 ulimit을 미리 증가시키면 런타임 오버헤드를 줄일 수 있습니다.

```bash
ulimit -n 1048576
python3 rustscan_massive.py
```

### 3. SAP 포트 커스터마이징

SAP 환경이 아니면 SAP 스캔을 비활성화하여 속도를 높일 수 있습니다.

```python
# config.py 수정
sap_ports: str = ""  # 빈 문자열 = SAP 스캔 스킵
```

## 트러블슈팅

### rustscan이 너무 느림

**원인**: RTT가 높아서 timeout이 길게 설정됨

**해결**:
1. Phase 1의 RTT 프로파일링 결과 확인 (`avg_rtt_{label}.txt`)
2. 네트워크 환경 개선 (VPN, 라우팅)
3. 수동으로 파라미터 조정 (rtt_optimizer.py 수정)

### 포트가 발견되지 않음

**원인**:
- 방화벽/IPS가 포트 스캔 차단
- rustscan timeout이 너무 짧음
- 호스트가 실제로 서비스를 실행하지 않음

**해결**:
1. 방화벽 로그 확인
2. timeout 증가 (rtt_optimizer.py 수정)
3. nmap 직접 실행하여 확인:
   ```bash
   sudo nmap -sS -p- 192.168.1.100
   ```

### 중복 포트가 발견됨

**정상 동작**: Main 스캔과 SAP 스캔이 동일한 포트를 발견할 수 있습니다. `_merge_results()`에서 자동으로 중복 제거됩니다.

## 코드 구조

```
phases/
└── phase2.py (261줄)
    ├── PortScanner 클래스
    │   ├── scan()                      # 메인 진입점
    │   ├── _run_main_scan()            # Main 스캔 병렬 실행
    │   ├── _run_sap_scan()             # SAP 스캔 병렬 실행
    │   ├── _merge_results()            # 결과 통합 및 포트 맵 생성
    │   └── _verify_and_increase_ulimit() # ulimit 자동 증가

utils/
└── rtt_optimizer.py (58줄)
    ├── RustscanParams 클래스
    └── optimize_rustscan_params()  # RTT 기반 파라미터 최적화
```

## 테스트

### 단위 테스트

```bash
cd /home/phantom/nmap/scripts
python3 test_phase2.py
```

### 통합 테스트

```bash
python3 test_phase2_integration.py
```

## 참고

- rustscan 공식 문서: https://github.com/RustScan/RustScan
- ulimit 설정: `man limits.conf`
- Phase 1 가이드: `docs/PHASE1_GUIDE.md` (Phase 1 팀 작성)
- Phase 3 가이드: `docs/PHASE3_GUIDE.md` (Phase 3 팀 작성)

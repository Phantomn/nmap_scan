# Task #8: 통합 테스트 시나리오

**작성자**: report-dev
**일시**: 2026-02-11
**목적**: 전체 파이프라인 통합 테스트 및 검증

---

## 전제 조건

### 필수 도구
- [x] Python 3.10+
- [ ] fping
- [ ] rustscan
- [ ] nmap
- [ ] hydra (브루트포스용)

### 설치 확인
```bash
# Python
python3 --version

# fping
which fping || sudo apt-get install fping

# nmap
which nmap || sudo apt-get install nmap

# rustscan
which rustscan || echo "Docker 사용: docker pull rustscan/rustscan"

# hydra
which hydra || sudo apt-get install hydra
```

---

## 1. 소규모 네트워크 테스트 (10-20 호스트)

### 목표
기본 기능 검증 및 빠른 실행

### 테스트 타겟
```json
{
  "targets": ["192.168.1.0/28"],
  "exclude": []
}
```

### 실행
```bash
cd /home/phantom/nmap/scripts

# Python 버전
time python3 rustscan_massive.py \
  --json-file test_small.json \
  --skip-vuln

# Bash 버전 (비교)
cd ..
time ./rustscan_massive_4phase.sh \
  -j scripts/test_small.json \
  -s
```

### 검증 항목
- [ ] Phase 1: 활성 호스트 발견 (1-14개 예상)
- [ ] Phase 2: 포트 스캔 완료
- [ ] Phase 3: 서비스 탐지 완료
- [ ] Phase 4: 스킵 확인
- [ ] 최종 박스 출력 정상
- [ ] 실행 시간 < 10분

### 비교 검증
```bash
# alive_hosts 비교
diff scans/rustscan_massive_*/alive_hosts_*.txt \
     scans/rustscan_massive_4phase_*/alive_hosts_*.txt

# port_map 비교
diff scans/rustscan_massive_*/port_map_*.txt \
     scans/rustscan_massive_4phase_*/port_map_*.txt

# XML 파일 수 비교
ls -l scans/rustscan_massive_*/*.xml | wc -l
```

---

## 2. 중규모 네트워크 테스트 (50-100 호스트)

### 목표
성능 검증 및 확장성 확인

### 테스트 타겟
```json
{
  "targets": ["172.20.10.0/25"],
  "exclude": []
}
```

### 실행
```bash
# Python 버전
time python3 rustscan_massive.py \
  --json-file test_medium.json \
  --skip-vuln

# Bash 버전
time ../rustscan_massive_4phase.sh \
  -j scripts/test_medium.json \
  -s
```

### 검증 항목
- [ ] 메모리 사용량 < 500MB
- [ ] CPU 사용률 모니터링
- [ ] Phase 2 병렬 실행 확인
- [ ] RTT 프로파일링 정확성
- [ ] 실행 시간 < 30분

---

## 3. 다중 서브넷 테스트 (3-5개)

### 목표
서브넷별 순차 처리 검증

### 테스트 타겟
```json
{
  "targets": [
    "192.168.1.0/28",
    "192.168.2.0/28",
    "192.168.3.0/28"
  ],
  "exclude": []
}
```

### 실행
```bash
python3 rustscan_massive.py \
  --json-file test_multi.json \
  --skip-vuln
```

### 검증 항목
- [ ] 서브넷별 순차 처리
- [ ] 각 서브넷별 결과 파일 생성
- [ ] 통계 집계 정확성
- [ ] 최종 박스에 전체 합계 표시

---

## 4. 엣지 케이스 테스트

### 4.1 0개 호스트 발견
```bash
# 존재하지 않는 서브넷
python3 rustscan_massive.py \
  --json-file <(echo '{"targets":["10.255.255.0/24"],"exclude":[]}') \
  --skip-vuln
```

**예상 동작**:
- Phase 1에서 0개 호스트 발견
- "활성 호스트 없음, 스킵" 메시지
- Phase 2-4 스킵
- 정상 종료 (exit code 0)

### 4.2 모든 호스트 exclude
```json
{
  "targets": ["192.168.1.0/30"],
  "exclude": ["192.168.1.0/30"]
}
```

**예상 동작**:
- Phase 1에서 제외 후 0개
- 정상 종료

### 4.3 워드리스트 누락
```bash
mv wordlists/usernames.txt wordlists/usernames.txt.bak
python3 rustscan_massive.py --json-file targets.json
```

**예상 동작**:
- Config.validate()에서 오류 발생
- "워드리스트를 찾을 수 없음" 메시지
- exit code 1

```bash
mv wordlists/usernames.txt.bak wordlists/usernames.txt
```

### 4.4 nmap 미설치
```bash
PATH=/tmp python3 rustscan_massive.py \
  --json-file test_targets.json \
  --skip-vuln
```

**예상 동작**:
- Phase 1에서 nmap 실행 실패
- 명확한 에러 메시지
- exit code 1

---

## 5. 브루트포스 검증

### 전제 조건
테스트 FTP 서버 필요:
```bash
# Docker FTP 서버
docker run -d --name test-ftp \
  -p 21:21 -p 21000-21010:21000-21010 \
  -e FTP_USER=testuser \
  -e FTP_PASS=testpass \
  fauria/vsftpd
```

### 테스트
```bash
# 성공 케이스 (워드리스트에 testuser/testpass 포함)
echo "testuser" >> wordlists/usernames.txt
echo "testpass" >> wordlists/passwords.txt

python3 rustscan_massive.py \
  --json-file <(echo '{"targets":["127.0.0.1/32"],"exclude":[]}')
```

### 검증 항목
- [ ] hydra 실행 확인
- [ ] 성공 케이스 탐지
- [ ] phase4_results_*.json에 기록
- [ ] 최종 박스에 "브루트포스 성공: 1개"

### 정리
```bash
docker stop test-ftp && docker rm test-ftp
```

---

## 6. Resume 기능 테스트

### ⚠️ 전제 조건
**CheckpointManager save() 버그 수정 필요**

현재는 checkpoint.json이 생성되지 않아 테스트 불가.

### 테스트 시나리오 (버그 수정 후)
```bash
# 1. 중단 시뮬레이션
timeout 30 python3 rustscan_massive.py \
  --json-file test_medium.json

# 2. 체크포인트 확인
cat ~/nmap/scans/rustscan_massive_*/checkpoint.json

# 3. 재개
python3 rustscan_massive.py --resume
```

### 검증 항목
- [ ] checkpoint.json 생성
- [ ] 완료된 Phase 스킵
- [ ] 중단된 Phase부터 재개
- [ ] 중복 작업 없음

---

## 7. 문서 업데이트

### README.md
- [ ] 설치 방법
- [ ] 빠른 시작 가이드
- [ ] Python vs Bash 차이점

### USAGE.md
- [ ] 모든 CLI 플래그 설명
- [ ] 예제 추가
- [ ] Resume 기능 가이드
- [ ] 브루트포스 설정

---

## 실행 순서

1. **전제 조건 확인** (도구 설치)
2. **소규모 테스트** (기본 기능 검증)
3. **엣지 케이스** (에러 핸들링)
4. **중규모 테스트** (성능 검증)
5. **다중 서브넷** (통합 검증)
6. **브루트포스** (선택적)
7. **Resume 기능** (버그 수정 후)
8. **문서 업데이트**

---

## 예상 소요 시간

| 항목 | 시간 |
|------|------|
| 소규모 테스트 | 15분 |
| 중규모 테스트 | 45분 |
| 다중 서브넷 | 30분 |
| 엣지 케이스 | 20분 |
| 브루트포스 | 30분 |
| Resume 기능 | 15분 |
| 문서 업데이트 | 30분 |
| **총계** | **2.5-3시간** |

---

## 현재 차단 이슈

🔴 **CheckpointManager save() 호출 누락**
- scanner.py 수정 필요
- Resume 기능 테스트 불가
- 예상 수정 시간: 5분

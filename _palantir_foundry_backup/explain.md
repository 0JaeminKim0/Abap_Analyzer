# LLM 기반 ABAP Analyzer 설명 자료

> 파트 1은 "ABAP Analyzer가 무엇인가"라는 개념을 소개하고,
> 파트 2는 LLM(대규모 언어 모델)을 활용해 직접 만들 ABAP Analyzer 도구의 기획서입니다.

---

# 파트 1. ABAP Analyzer란 무엇인가 (개념 소개)

## 1.1 한 줄 정의

**ABAP Analyzer**는 SAP 시스템에서 작성된 **ABAP 소스 코드를 자동으로 분석하여 품질·성능·보안·표준 준수 문제를 찾아내는 도구**입니다. 사람이 코드를 일일이 읽지 않고도 문제 지점을 기계적으로 짚어 줍니다.

## 1.2 배경 지식 — ABAP이란?

- **ABAP** (Advanced Business Application Programming): SAP ERP(SAP ECC, S/4HANA 등)의 업무 로직을 개발하는 SAP 고유 언어입니다.
- 대기업의 회계·물류·인사·생산 등 **핵심 업무 로직 대부분이 ABAP으로 작성**되어 있습니다.
- 수십 년간 누적된 코드라 **규모가 방대하고, 오래된 레거시 코드가 많으며, 여러 개발자의 손을 거쳐** 일관성이 떨어지는 경우가 많습니다.

## 1.3 왜 Analyzer가 필요한가

수동 코드 리뷰만으로는 방대한 ABAP 코드의 문제를 다 잡을 수 없습니다. Analyzer는 아래 영역을 자동으로 검사합니다.

| 분석 영역 | 대표적으로 잡아내는 문제 |
|-----------|--------------------------|
| **성능 (Performance)** | `SELECT *`, 반복문 내부 DB 조회, `SELECT ... ENDSELECT`, 인덱스 미사용, `INTO TABLE` 미사용 |
| **품질 (Quality)** | 미사용 변수/모듈, 중복 코드, 지나치게 긴 함수, 하드코딩 값, 오류 처리 누락 |
| **보안 (Security)** | SQL Injection, 권한 검사(AUTHORITY-CHECK) 누락, 동적 코드 실행 위험 |
| **표준 준수 (Standard)** | SAP 명명 규칙, 코딩 가이드라인, 주석 규칙 위반 |
| **S/4HANA 전환** | 구버전 문법, HANA 마이그레이션 시 문제되는 코드 탐지 |

## 1.4 이미 존재하는 대표 도구

| 도구 | 성격 | 특징 |
|------|------|------|
| **SAP Code Inspector (SCI)** | SAP 기본 제공 | 규칙 기반 정적 분석의 표준 |
| **ABAP Test Cockpit (ATC)** | SAP 기본 제공 | SCI를 확장, 개발 프로세스에 통합 |
| **SAP Custom Code Migration** | SAP 제공 | S/4HANA 전환용 코드 영향도 분석 |
| **SonarQube (ABAP 플러그인)** | 서드파티 | CI/CD 파이프라인 통합, 대시보드 제공 |

## 1.5 기존 규칙 기반 도구의 한계

기존 도구(SCI/ATC 등)는 **미리 정의된 규칙(rule)** 에만 의존합니다. 그래서:

- ❌ 규칙에 없는 새로운 패턴의 문제는 못 잡음
- ❌ "이 코드가 무슨 의도인가"를 이해하지 못함 (문맥 파악 불가)
- ❌ 사람이 읽을 수 있는 **설명·개선안**을 자연어로 제시하지 못함
- ❌ 리팩터링 제안이나 코드 자동 수정이 어려움

→ **바로 이 지점에서 LLM 기반 접근이 필요합니다.**

---

# 파트 2. LLM 기반 ABAP Analyzer 도구 기획서

## 2.1 제품 개요

**"ABAP 코드를 넣으면, LLM이 문제를 찾아 자연어로 설명하고 개선안(수정 코드)까지 제시하는 분석 도구"**

기존 규칙 기반 도구가 놓치는 **문맥 이해**와 **자연어 설명·개선 제안**을 LLM으로 보완하는 것이 핵심 차별점입니다.

## 2.2 목표 (Goals) / 비목표 (Non-Goals)

**목표**
- ABAP 코드의 성능·품질·보안 이슈를 탐지하고 **이유를 설명**
- 문제별 **개선 코드(before → after)** 자동 생성
- 기존 SCI/ATC 규칙 결과를 LLM이 **재해석·우선순위화**
- 개발자가 이해하기 쉬운 **리포트** 산출

**비목표 (초기 버전 제외)**
- SAP 시스템 실시간 연동(온프렘 트랜스포트 자동 반영)
- 코드 자동 커밋/배포
- ABAP 문법 100% 완벽 파싱 (초기엔 LLM 이해에 의존)

## 2.3 핵심 사용자 & 시나리오

| 사용자 | 시나리오 |
|--------|----------|
| ABAP 개발자 | 작성한 프로그램을 붙여넣어 리뷰 받고 개선안 확인 |
| 리드/아키텍트 | 레거시 모듈의 위험도·우선순위 파악 |
| 마이그레이션 담당 | S/4HANA 전환 전 문제 코드 사전 진단 |

## 2.4 시스템 아키텍처 (개념도)

```
┌──────────────┐    ┌─────────────────┐    ┌──────────────────┐
│  입력 계층    │ →  │   분석 엔진      │ →  │   출력 계층       │
│              │    │                 │    │                  │
│ ABAP 소스    │    │ 1. 전처리/청킹  │    │ 이슈 리스트       │
│ (파일/붙여넣기│    │ 2. 규칙 프리체크 │    │ 심각도/카테고리   │
│  /Git 연동)  │    │ 3. LLM 분석     │    │ 설명 + 개선 코드  │
│              │    │ 4. 결과 검증    │    │ 리포트(MD/HTML)  │
└──────────────┘    └─────────────────┘    └──────────────────┘
```

### 분석 엔진 단계별 설명

1. **전처리/청킹(Chunking)**: 긴 ABAP 프로그램을 LLM 컨텍스트 한도에 맞게 논리 단위(FORM, METHOD, FUNCTION)로 분할.
2. **규칙 프리체크(선택)**: 정규식/AST로 명백한 안티패턴(`SELECT *` 등)을 먼저 표시 → LLM 비용 절감 + 정확도 보강.
3. **LLM 분석**: 각 청크를 프롬프트에 넣어 이슈·설명·개선안을 **구조화된 JSON**으로 받음.
4. **결과 검증**: LLM 환각(hallucination) 방지를 위해 스키마 검증 + 라인 번호 존재 여부 확인.

## 2.5 LLM 분석 상세 설계

### 프롬프트 전략
- **역할 부여**: "당신은 시니어 SAP ABAP 코드 리뷰어입니다."
- **체크리스트 주입**: 성능/품질/보안/표준 항목을 명시적으로 전달
- **출력 스키마 강제**: 아래와 같은 JSON 구조로만 응답하도록 지시

### 출력 데이터 스키마(예시)

```json
{
  "findings": [
    {
      "id": "PERF-001",
      "category": "performance",
      "severity": "high",
      "line": 42,
      "title": "반복문 내부 DB 조회",
      "explanation": "LOOP 내에서 SELECT를 실행해 DB 왕복이 반복됩니다.",
      "suggestion": "루프 전에 FOR ALL ENTRIES 또는 내부 테이블 조회로 대체하세요.",
      "before": "LOOP AT it_data ... SELECT ... ENDLOOP.",
      "after": "SELECT ... FOR ALL ENTRIES IN it_data ..."
    }
  ],
  "summary": { "high": 1, "medium": 3, "low": 5 }
}
```

### 검사 카테고리(초기 규칙셋)

- **성능**: 루프 내 SELECT, `SELECT *`, `SELECT ... ENDSELECT`, 인덱스 미사용, 정렬 미지정
- **품질**: 미사용 변수, 중복 로직, 매직 넘버, 예외 처리 누락, 과도한 중첩
- **보안**: 동적 SQL/Injection, AUTHORITY-CHECK 누락, `GENERATE SUBROUTINE` 등 위험 구문
- **표준**: 명명 규칙, 주석, 데드 코드

## 2.6 기술 스택(제안)

| 구성 | 후보 |
|------|------|
| LLM | Claude (Opus/Sonnet) — 긴 컨텍스트·코드 이해 강점 |
| 백엔드 | Python(FastAPI) 또는 Node.js |
| 프론트엔드 | React / Next.js (리포트·비교 뷰) |
| 저장소 | 분석 이력·규칙셋 저장용 DB(SQLite/Postgres) |
| 연동(선택) | Git, SAP ADT/RFC (후속 단계) |

## 2.7 개발 로드맵(단계별)

| 단계 | 범위 | 산출물 |
|------|------|--------|
| **1. PoC** | 단일 ABAP 파일 붙여넣기 → LLM 분석 → JSON 리포트 | 동작 검증 |
| **2. MVP** | 청킹 + 규칙 프리체크 + 웹 UI(이슈 목록/개선안) | 사용 가능한 도구 |
| **3. 확장** | 다중 파일/프로젝트, 심각도 대시보드, 리포트 export | 팀 활용 |
| **4. 통합** | Git/CI 연동, SAP 시스템 연동 검토 | 파이프라인화 |

## 2.8 리스크 & 대응

| 리스크 | 대응 방안 |
|--------|-----------|
| LLM 환각(없는 문제 지어냄) | 출력 스키마 검증 + 라인 번호 대조 + 규칙 프리체크 병행 |
| 긴 코드 컨텍스트 초과 | 논리 단위 청킹, 요약 후 재분석 |
| 코드 유출(보안) | 온프렘/사내 배포 옵션, 민감정보 마스킹 |
| 분석 비용 | 규칙으로 1차 필터 후 LLM 호출 최소화 |
| ABAP 도메인 지식 부족 | 프롬프트에 SAP 코딩 가이드·예시 주입(RAG) |

## 2.9 다음 액션

- [x] PoC 프롬프트 설계 및 샘플 ABAP 코드로 테스트 → **부록 A**
- [ ] 출력 JSON 스키마 확정 → 부록 A의 스키마 기준
- [x] 초기 규칙셋(체크리스트) 문서화 → **부록 B**
- [ ] MVP UI 와이어프레임 작성

---

# 부록 A. PoC 프롬프트 실제 설계

PoC 목표: **ABAP 소스 1개를 입력받아, 규칙셋 기준으로 이슈를 찾아 구조화된 JSON으로 출력**한다. 프롬프트는 3개 블록(① System ② Developer/Rules ③ User)으로 구성한다.

## A.1 System 프롬프트 (역할·원칙)

```text
당신은 20년 경력의 시니어 SAP ABAP 코드 리뷰어입니다.
주어진 ABAP 소스 코드를 정적 분석하여 성능, 품질, 보안, 표준 준수
관점의 문제를 찾아냅니다.

반드시 지켜야 할 원칙:
1. 실제 코드에 근거해서만 지적한다. 코드에 없는 문제를 지어내지 않는다.
2. 각 지적에는 반드시 실제 존재하는 라인 번호를 명시한다.
3. 확신이 없으면 severity를 낮추거나 보고하지 않는다. (거짓 양성 최소화)
4. 개선안(after 코드)은 컴파일 가능한 유효한 ABAP 구문으로 작성한다.
5. 출력은 지정된 JSON 스키마만 사용하며, 그 외 어떤 설명 문장도 덧붙이지 않는다.
6. 한국어로 explanation과 suggestion을 작성한다.
```

## A.2 Developer 프롬프트 (규칙셋 + 출력 스키마 주입)

```text
[검사 규칙셋]
아래 규칙 ID를 기준으로 코드를 검사하라. (상세는 부록 B 규칙셋과 동일)
- PERF-001 ~ PERF-006 : 성능
- QUAL-001 ~ QUAL-006 : 품질
- SEC-001  ~ SEC-004  : 보안
- STD-001  ~ STD-003  : 표준 준수

[severity 기준]
- high   : 운영 장애/보안 사고로 직결 (예: 루프 내 DB조회, SQL Injection)
- medium : 성능 저하/유지보수성 악화
- low    : 스타일/표준 위반

[출력 JSON 스키마] — 이 구조만 사용
{
  "findings": [
    {
      "id": "규칙ID (예: PERF-001)",
      "category": "performance | quality | security | standard",
      "severity": "high | medium | low",
      "line": <정수, 실제 라인 번호>,
      "title": "<한 줄 요약>",
      "explanation": "<왜 문제인지 근거>",
      "suggestion": "<어떻게 고칠지>",
      "before": "<문제 코드 스니펫>",
      "after": "<개선 코드 스니펫>"
    }
  ],
  "summary": { "high": <int>, "medium": <int>, "low": <int> }
}

발견된 문제가 없으면 findings는 빈 배열 [] 로, summary는 모두 0 으로 반환하라.
```

## A.3 User 프롬프트 (분석 대상 코드)

```text
다음 ABAP 코드를 분석하라. 각 줄 앞의 번호는 라인 번호이며 line 필드에 이 값을 사용하라.

001| REPORT z_order_report.
002| DATA: lt_orders TYPE TABLE OF vbak,
003|       ls_order  TYPE vbak.
004| SELECT * FROM vbak INTO TABLE lt_orders.
005| LOOP AT lt_orders INTO ls_order.
006|   SELECT SINGLE * FROM vbap INTO @DATA(ls_item)
007|     WHERE vbeln = @ls_order-vbeln.
008|   WRITE: / ls_order-vbeln, ls_item-matnr.
009| ENDLOOP.
```

## A.4 기대 출력 (검증용 정답 예시)

```json
{
  "findings": [
    {
      "id": "PERF-002",
      "category": "performance",
      "severity": "high",
      "line": 6,
      "title": "LOOP 내부에서 SELECT 실행 (N+1 조회)",
      "explanation": "LOOP AT lt_orders 안에서 라인 6의 SELECT SINGLE이 반복 실행되어, 주문 건수만큼 DB 왕복이 발생합니다.",
      "suggestion": "루프 진입 전에 FOR ALL ENTRIES로 vbap을 한 번에 조회해 내부 테이블에 담고, 루프 안에서는 READ TABLE로 조회하세요.",
      "before": "LOOP AT lt_orders INTO ls_order.\n  SELECT SINGLE * FROM vbap INTO @DATA(ls_item) WHERE vbeln = @ls_order-vbeln.",
      "after": "SELECT vbeln matnr FROM vbap INTO TABLE @DATA(lt_items)\n  FOR ALL ENTRIES IN @lt_orders WHERE vbeln = @lt_orders-vbeln.\nLOOP AT lt_orders INTO ls_order.\n  READ TABLE lt_items INTO DATA(ls_item) WITH KEY vbeln = ls_order-vbeln."
    },
    {
      "id": "PERF-001",
      "category": "performance",
      "severity": "medium",
      "line": 4,
      "title": "SELECT * 로 전체 컬럼 조회",
      "explanation": "라인 4에서 vbak의 모든 컬럼을 가져오지만 실제로는 vbeln만 사용됩니다. 불필요한 네트워크/메모리 비용이 발생합니다.",
      "suggestion": "필요한 컬럼만 명시하세요: SELECT vbeln FROM vbak INTO TABLE @DATA(lt_orders).",
      "before": "SELECT * FROM vbak INTO TABLE lt_orders.",
      "after": "SELECT vbeln FROM vbak INTO TABLE @DATA(lt_orders)."
    }
  ],
  "summary": { "high": 1, "medium": 1, "low": 0 }
}
```

## A.5 PoC 검증 방법

1. **골든셋 테스트**: 위처럼 "코드 ↔ 정답 JSON" 쌍을 10~20개 준비.
2. **평가 지표**: 정답 대비 탐지율(Recall)·오탐률(False Positive), 라인 번호 정확도.
3. **환각 체크**: 출력의 `line` 값이 입력 코드 라인 범위 내인지 자동 검증.
4. **스키마 검증**: JSON Schema로 필드/타입 강제(파이프라인 자동화).
5. **반복 튜닝**: 오탐이 잦은 규칙은 System 원칙에 예외 규정 추가.

---

# 부록 B. 규칙셋 상세 (초기 v1)

각 규칙은 `ID / 카테고리 / 기본 severity / 탐지 패턴 / 문제점 / 개선 방향`으로 정의한다.

## B.1 성능 (Performance)

| ID | 규칙 | 기본 severity | 탐지 패턴 | 개선 방향 |
|----|------|--------------|-----------|-----------|
| **PERF-001** | `SELECT *` 사용 | medium | `SELECT *` | 필요한 컬럼만 명시 |
| **PERF-002** | 루프 내부 DB 조회 (N+1) | high | `LOOP` 블록 내 `SELECT` | `FOR ALL ENTRIES` 또는 사전 조회 후 `READ TABLE` |
| **PERF-003** | `SELECT ... ENDSELECT` (단건 반복) | high | `SELECT`~`ENDSELECT` | `INTO TABLE`로 한 번에 조회 |
| **PERF-004** | `WHERE` 없는 전체 테이블 조회 | high | `SELECT` + `WHERE` 부재 | 조건절 추가, 인덱스 활용 |
| **PERF-005** | 정렬/인덱스 미활용 조회 | medium | 키 아닌 필드 조건, `ORDER BY` 남용 | 적절한 인덱스/`SORT` 사용 |
| **PERF-006** | 내부 테이블 선형 탐색 | medium | `READ TABLE ... WITH KEY` (비정렬/비해시) | `SORTED`/`HASHED` 테이블 사용 |

## B.2 품질 (Quality)

| ID | 규칙 | 기본 severity | 탐지 패턴 | 개선 방향 |
|----|------|--------------|-----------|-----------|
| **QUAL-001** | 미사용 변수/상수 | low | 선언 후 미참조 | 제거 |
| **QUAL-002** | 매직 넘버/하드코딩 값 | low | 리터럴 상수 직접 사용 | 상수(CONSTANTS)로 분리 |
| **QUAL-003** | 예외/오류 처리 누락 | medium | `SELECT`/`CALL` 후 `SY-SUBRC` 미확인 | `SY-SUBRC` 검사 또는 `TRY...CATCH` |
| **QUAL-004** | 과도하게 긴 루틴 | medium | FORM/METHOD 라인 수 초과(예:>100) | 기능 분리 리팩터링 |
| **QUAL-005** | 중복 코드 블록 | medium | 유사 코드 반복 | 공통 루틴/메서드로 추출 |
| **QUAL-006** | 데드 코드/도달 불가 코드 | low | 사용되지 않는 FORM, 주석 처리된 로직 | 제거 |

## B.3 보안 (Security)

| ID | 규칙 | 기본 severity | 탐지 패턴 | 개선 방향 |
|----|------|--------------|-----------|-----------|
| **SEC-001** | SQL Injection 위험 (동적 WHERE) | high | 사용자 입력이 문자열로 `WHERE`에 결합 | 파라미터 바인딩, 입력 검증 |
| **SEC-002** | 권한 검사 누락 | high | 민감 작업 전 `AUTHORITY-CHECK` 부재 | `AUTHORITY-CHECK` 추가 |
| **SEC-003** | 위험한 동적 코드 실행 | high | `GENERATE SUBROUTINE`, 동적 `PERFORM`, `INSERT REPORT` | 정적 구현으로 대체 |
| **SEC-004** | 하드코딩된 자격 증명/경로 | medium | 코드 내 비밀번호·서버 주소 리터럴 | 설정 테이블/보안 저장소 사용 |

## B.4 표준 준수 (Standard)

| ID | 규칙 | 기본 severity | 탐지 패턴 | 개선 방향 |
|----|------|--------------|-----------|-----------|
| **STD-001** | 명명 규칙 위반 | low | 변수 접두어(lt_/ls_/lv_ 등) 미준수 | SAP 헝가리안 표기 적용 |
| **STD-002** | 주석 부재/불충분 | low | 복잡 로직에 설명 주석 없음 | 핵심 로직 주석 보강 |
| **STD-003** | 구버전 문법 (S/4HANA 비권장) | medium | `OCCURS`, 헤더라인 테이블, `#`-없는 old syntax | 최신 ABAP 구문으로 전환 |

## B.5 규칙셋 운영 원칙

- **버전 관리**: 규칙셋은 v1 → v2로 문서로 관리하고, 각 릴리스에서 추가/변경 규칙을 기록.
- **심각도 조정**: 조직 정책에 따라 기본 severity를 상향/하향 커스터마이즈 가능.
- **규칙 on/off**: 프로젝트별로 특정 규칙 비활성화 지원(예: 레거시 프로젝트에서 STD-003 제외).
- **확장**: 신규 안티패턴 발견 시 규칙 ID를 추가하고 골든셋에 테스트 케이스를 함께 등록.

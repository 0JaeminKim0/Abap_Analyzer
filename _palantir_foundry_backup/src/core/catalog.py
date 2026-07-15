"""
ABAP Analyzer — 규칙 카탈로그 (Single Source of Truth)

이 파일 하나가 19개 규칙의 원천이다.
  - tools/make_template.py  : Severity 수집 Excel을 이 목록으로 프리필
  - core/ruleset.py         : (참고용) 규칙 설명 문구
런타임 severity는 여기 값이 아니라 조직이 채운 severity_policy 데이터셋을 따른다.
default_severity 는 Excel에 제안값으로만 표기된다.
"""

# category 는 4분류로 고정: performance | quality | security | standard
RULES = [
    # ---- Performance ----
    {"rule_id": "PERF-001", "category": "performance", "rule_name": "SELECT * 사용",
     "default_severity": "medium",
     "detection": "SELECT * ...",
     "remediation": "필요한 컬럼만 명시"},
    {"rule_id": "PERF-002", "category": "performance", "rule_name": "루프 내부 DB 조회 (N+1)",
     "default_severity": "high",
     "detection": "LOOP 블록 내 SELECT",
     "remediation": "FOR ALL ENTRIES 또는 사전 조회 후 READ TABLE"},
    {"rule_id": "PERF-003", "category": "performance", "rule_name": "SELECT ... ENDSELECT (단건 반복)",
     "default_severity": "high",
     "detection": "SELECT ~ ENDSELECT",
     "remediation": "INTO TABLE 로 한 번에 조회"},
    {"rule_id": "PERF-004", "category": "performance", "rule_name": "WHERE 없는 전체 테이블 조회",
     "default_severity": "high",
     "detection": "SELECT 에 WHERE 절 부재",
     "remediation": "조건절 추가, 인덱스 활용"},
    {"rule_id": "PERF-005", "category": "performance", "rule_name": "정렬/인덱스 미활용 조회",
     "default_severity": "medium",
     "detection": "키가 아닌 필드 조건, ORDER BY 남용",
     "remediation": "적절한 인덱스/SORT 사용"},
    {"rule_id": "PERF-006", "category": "performance", "rule_name": "내부 테이블 선형 탐색",
     "default_severity": "medium",
     "detection": "READ TABLE ... WITH KEY (비정렬/비해시 테이블)",
     "remediation": "SORTED/HASHED 테이블 사용"},

    # ---- Quality ----
    {"rule_id": "QUAL-001", "category": "quality", "rule_name": "미사용 변수/상수",
     "default_severity": "low",
     "detection": "선언 후 미참조",
     "remediation": "제거"},
    {"rule_id": "QUAL-002", "category": "quality", "rule_name": "매직 넘버/하드코딩 값",
     "default_severity": "low",
     "detection": "리터럴 상수 직접 사용",
     "remediation": "CONSTANTS 로 분리"},
    {"rule_id": "QUAL-003", "category": "quality", "rule_name": "예외/오류 처리 누락",
     "default_severity": "medium",
     "detection": "SELECT/CALL 후 SY-SUBRC 미확인",
     "remediation": "SY-SUBRC 검사 또는 TRY...CATCH"},
    {"rule_id": "QUAL-004", "category": "quality", "rule_name": "과도하게 긴 루틴",
     "default_severity": "medium",
     "detection": "FORM/METHOD 라인 수 초과 (기본 > 100)",
     "remediation": "기능 분리 리팩터링"},
    {"rule_id": "QUAL-005", "category": "quality", "rule_name": "중복 코드 블록",
     "default_severity": "medium",
     "detection": "유사 코드 반복",
     "remediation": "공통 루틴/메서드로 추출"},
    {"rule_id": "QUAL-006", "category": "quality", "rule_name": "데드 코드/도달 불가 코드",
     "default_severity": "low",
     "detection": "사용되지 않는 FORM, 주석 처리된 로직",
     "remediation": "제거"},

    # ---- Security ----
    {"rule_id": "SEC-001", "category": "security", "rule_name": "SQL Injection 위험 (동적 WHERE)",
     "default_severity": "high",
     "detection": "사용자 입력이 문자열로 WHERE 에 결합",
     "remediation": "파라미터 바인딩, 입력 검증"},
    {"rule_id": "SEC-002", "category": "security", "rule_name": "권한 검사 누락",
     "default_severity": "high",
     "detection": "민감 작업 전 AUTHORITY-CHECK 부재",
     "remediation": "AUTHORITY-CHECK 추가"},
    {"rule_id": "SEC-003", "category": "security", "rule_name": "위험한 동적 코드 실행",
     "default_severity": "high",
     "detection": "GENERATE SUBROUTINE, 동적 PERFORM, INSERT REPORT",
     "remediation": "정적 구현으로 대체"},
    {"rule_id": "SEC-004", "category": "security", "rule_name": "하드코딩된 자격 증명/경로",
     "default_severity": "medium",
     "detection": "코드 내 비밀번호·서버 주소 리터럴",
     "remediation": "설정 테이블/보안 저장소 사용"},

    # ---- Standard ----
    {"rule_id": "STD-001", "category": "standard", "rule_name": "명명 규칙 위반",
     "default_severity": "low",
     "detection": "변수 접두어(lt_/ls_/lv_ 등) 미준수",
     "remediation": "SAP 헝가리안 표기 적용"},
    {"rule_id": "STD-002", "category": "standard", "rule_name": "주석 부재/불충분",
     "default_severity": "low",
     "detection": "복잡 로직에 설명 주석 없음",
     "remediation": "핵심 로직 주석 보강"},
    {"rule_id": "STD-003", "category": "standard", "rule_name": "구버전 문법 (S/4HANA 비권장)",
     "default_severity": "medium",
     "detection": "OCCURS, 헤더라인 테이블, old syntax",
     "remediation": "최신 ABAP 구문으로 전환"},
]

SEVERITIES = ["high", "medium", "low"]          # off = 규칙 비활성
CATEGORIES = ["performance", "quality", "security", "standard"]

# 정책 정렬용 우선순위
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "off": 9}


def rule_by_id():
    """rule_id -> 규칙 dict 매핑."""
    return {r["rule_id"]: r for r in RULES}

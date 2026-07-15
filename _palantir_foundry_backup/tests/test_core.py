"""
오프라인 코어 검증 — AIP/Spark 없이 core 로직만 확인.

실행:
    pip install jsonschema
    python -m pytest tests/            # 또는
    python tests/test_core.py

가짜 complete_fn(fake model)을 주입해 프롬프트 조립 → 파싱 → 스키마검증 →
라인범위 환각제거 → 정책 필터가 end-to-end 로 동작하는지 본다.
"""
import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from core import analyze, ruleset  # noqa: E402

# 부록 A.3 의 예시 소스
SAMPLE = """\
REPORT z_customer_sales.
DATA: lt_kna1 TYPE TABLE OF kna1,
      ls_kna1 TYPE kna1,
      lv_unused TYPE i.
SELECT * FROM kna1 INTO TABLE lt_kna1.
LOOP AT lt_kna1 INTO ls_kna1.
  SELECT * FROM vbak INTO TABLE lt_vbak WHERE kunnr = ls_kna1-kunnr.
ENDLOOP."""

POLICY = [
    {"rule_id": "PERF-001", "category": "performance", "rule_name": "SELECT * 사용", "severity": "medium"},
    {"rule_id": "PERF-002", "category": "performance", "rule_name": "루프 내부 DB 조회", "severity": "high"},
    {"rule_id": "PERF-004", "category": "performance", "rule_name": "WHERE 없는 전체 조회", "severity": "high"},
    {"rule_id": "QUAL-001", "category": "quality", "rule_name": "미사용 변수", "severity": "low"},
    {"rule_id": "SEC-002", "category": "security", "rule_name": "권한 검사 누락", "severity": "off"},  # 비활성
]


def fake_complete(messages):
    """모델을 흉내: 라인 5(SELECT *)와 라인 7(루프 내 SELECT), 범위밖 라인 999(환각),
    그리고 정책에서 off 인 SEC-002 를 섞어 반환 → 필터가 잘 거르는지 검증."""
    return json.dumps({
        "findings": [
            {"id": "PERF-004", "category": "performance", "severity": "high", "line": 5,
             "title": "WHERE 없는 전체 조회", "explanation": "x", "suggestion": "y",
             "before": "SELECT *", "after": "SELECT kunnr"},
            {"id": "PERF-002", "category": "performance", "severity": "high", "line": 7,
             "title": "루프 내 SELECT", "explanation": "x", "suggestion": "y",
             "before": "b", "after": "a"},
            {"id": "SEC-002", "category": "security", "severity": "high", "line": 7,
             "title": "권한 누락(정책상 off)", "explanation": "x", "suggestion": "y",
             "before": "b", "after": "a"},
            {"id": "PERF-001", "category": "performance", "severity": "medium", "line": 999,
             "title": "환각 라인", "explanation": "x", "suggestion": "y",
             "before": "b", "after": "a"},
        ],
        "summary": {"high": 3, "medium": 1, "low": 0},
    })


def test_ruleset_excludes_off():
    block = ruleset.build_ruleset_block(POLICY)
    assert "SEC-002" not in block          # off 규칙 제외
    assert "PERF-002" in block
    assert "SEC-002" not in ruleset.active_rule_ids(POLICY)


def test_analyze_filters_hallucination_and_policy():
    res = analyze.analyze_source(SAMPLE, POLICY, fake_complete,
                                 merge_developer_into_system=True)
    ids = sorted(f["id"] for f in res["findings"])
    # 남아야 할 것: PERF-004, PERF-002 (라인 범위 내 + 정책 활성)
    # 걸러져야 할 것: SEC-002(off), PERF-001(라인 999 환각)
    assert ids == ["PERF-002", "PERF-004"], ids
    assert res["summary"] == {"high": 2, "medium": 0, "low": 0}, res["summary"]
    assert res["errors"] == []


if __name__ == "__main__":
    test_ruleset_excludes_off()
    test_analyze_filters_hallucination_and_policy()
    print("OK - all core tests passed")

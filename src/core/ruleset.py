"""
작업 2-b — 조직 정책(severity_policy)으로 프롬프트의 [검사 규칙셋] 블록을 동적 생성.

이것이 "정책 자동 삽입"의 실체다. Excel에서 SEC-002 를 medium 으로 낮추거나
enabled=N / off 로 끄면, 다음 분석부터 이 블록이 그렇게 바뀐다. 코드 재배포 불필요.

policy_rows 는 dict 리스트이며 최소 다음 키를 가진다:
    rule_id, category, rule_name, severity   (severity 는 이미 'off'/비활성이 걸러진 값)
"""
from core.catalog import SEVERITY_ORDER

_ALLOWED_SEV = {"high", "medium", "low"}


def _active(policy_rows):
    """활성 규칙만 남긴다. off / 잘못된 severity 는 제외."""
    out = []
    for r in policy_rows:
        sev = str(r.get("severity", "")).lower()
        if sev in _ALLOWED_SEV:
            out.append({**r, "severity": sev})
    return out


def build_ruleset_block(policy_rows):
    """정책 → 프롬프트에 넣을 텍스트 블록."""
    rows = _active(policy_rows)
    if not rows:
        # 방어: 정책이 비면 최소한 스키마는 유지하되 규칙 없음을 명시
        return "[검사 규칙셋 — 조직 정책 반영]\n(활성화된 규칙이 없습니다. 분석을 수행하지 마세요.)"

    rows.sort(key=lambda r: (r["category"], SEVERITY_ORDER.get(r["severity"], 9), r["rule_id"]))
    lines = ["[검사 규칙셋 — 조직 정책 반영] 아래 규칙 ID 기준으로만 검사한다."]
    current = None
    for r in rows:
        if r["category"] != current:
            current = r["category"]
            lines.append(f"# {current}")
        lines.append(f'- {r["rule_id"]} [{r["severity"].upper()}] {r["rule_name"]}')
    return "\n".join(lines)


def active_rule_ids(policy_rows):
    """검증 단계에서 허용 규칙 ID 집합으로 사용."""
    return {r["rule_id"] for r in _active(policy_rows)}

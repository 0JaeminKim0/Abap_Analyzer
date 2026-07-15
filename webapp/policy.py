"""
Railway 배포용 정책 로더.

Foundry 버전은 severity_policy 데이터셋(Excel→Dataset)에서 정책을 읽지만,
Railway 웹 서비스는 데이터셋이 없으므로 기본적으로 core.catalog 의 기본 severity 로
정책을 구성한다. 필요하면 SEVERITY_POLICY_CSV 환경변수로 CSV 를 덮어씌울 수 있다.

정책 행 형식: {"rule_id","category","rule_name","severity"}  (severity 는 high|medium|low)
"""
import csv
import os

from core.catalog import RULES


def _from_catalog():
    return [{
        "rule_id": r["rule_id"],
        "category": r["category"],
        "rule_name": r["rule_name"],
        "severity": r["default_severity"],
    } for r in RULES]


def _overlay_csv(base, csv_path):
    """CSV(rule_id,severity[,enabled]) 로 조직 정책을 덮어쓴다. off/N 은 제외."""
    by_id = {r["rule_id"]: dict(r) for r in base}
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rid = (row.get("rule_id") or "").strip()
            if rid not in by_id:
                continue
            enabled = (row.get("enabled") or "Y").strip().upper()
            sev = (row.get("severity") or row.get("org_severity") or "").strip().lower()
            if enabled == "N" or sev == "off":
                by_id.pop(rid, None)
            elif sev in ("high", "medium", "low"):
                by_id[rid]["severity"] = sev
    return list(by_id.values())


def load_policy():
    base = _from_catalog()
    csv_path = os.environ.get("SEVERITY_POLICY_CSV")
    if csv_path and os.path.exists(csv_path):
        return _overlay_csv(base, csv_path)
    return base

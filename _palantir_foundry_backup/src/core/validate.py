"""
결과 검증 (부록 A.5) — LLM 출력의 환각/스키마 위반 제거.

두 단계:
  1) jsonschema 로 구조 검증
  2) 라인번호가 실제 코드 범위 내인지 + 규칙 ID가 활성 규칙셋에 속하는지 확인
     → 벗어나는 finding 은 버린다(거짓 양성 방지). summary 는 재계산한다.
"""
import json

import jsonschema

from core.schema import FINDINGS_SCHEMA


class SchemaError(ValueError):
    pass


def parse_json(raw_text):
    """LLM 응답에서 JSON 객체를 안전하게 파싱. 코드펜스가 섞여도 복구 시도."""
    txt = raw_text.strip()
    if txt.startswith("```"):
        # ```json ... ``` 형태 방어
        txt = txt.strip("`")
        if txt.lower().startswith("json"):
            txt = txt[4:]
        txt = txt.strip()
    try:
        return json.loads(txt)
    except json.JSONDecodeError:
        # 앞뒤 잡음 제거: 첫 '{' ~ 마지막 '}'
        s, e = txt.find("{"), txt.rfind("}")
        if s != -1 and e != -1 and e > s:
            return json.loads(txt[s:e + 1])
        raise


def validate_and_clean(data, line_lo, line_hi, allowed_rule_ids=None):
    """
    data          : parse_json 결과(dict)
    line_lo/hi    : 이 청크의 유효 라인번호 범위(포함)
    allowed_rule_ids : 활성 규칙 ID 집합. None 이면 규칙 ID 필터 생략.

    반환: 정제된 dict (스키마 통과 보장). 스키마 위반 시 SchemaError.
    """
    try:
        jsonschema.validate(data, FINDINGS_SCHEMA)
    except jsonschema.ValidationError as e:
        raise SchemaError(str(e))

    kept = []
    for f in data["findings"]:
        if not (line_lo <= f["line"] <= line_hi):
            continue  # 환각: 범위 밖 라인
        if allowed_rule_ids is not None and f["id"] not in allowed_rule_ids:
            continue  # 정책에 없는/비활성 규칙
        kept.append(f)

    summary = {"high": 0, "medium": 0, "low": 0}
    for f in kept:
        summary[f["severity"]] += 1
    return {"findings": kept, "summary": summary}

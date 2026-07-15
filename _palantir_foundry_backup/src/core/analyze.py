"""
공유 코어 오케스트레이터 — 배치(transforms)와 인터랙티브(functions)가 공통으로 호출.

analyze_source(source, policy_rows, complete_fn) -> dict

핵심 설계: LLM 호출을 complete_fn(messages)->str 콜백으로 추상화한다.
  → 실제 AIP 모델 import(팀 Foundry 버전 의존)는 이 코어에 두지 않고
    transforms/functions 경계에서 주입한다. 코어는 모델-비의존이라 단위 테스트가 쉽다.

messages 규약(OpenAI 호환): [{"role","content"}] with roles system/developer/user.
AIP 모델이 developer 롤을 지원하지 않으면 build_messages(merge_developer_into_system=True).
"""
from core import prompts, ruleset, schema, chunking, validate


def build_messages(numbered_code, ruleset_block, merge_developer_into_system=False):
    dev = prompts.build_developer_prompt(ruleset_block, schema.SCHEMA_HINT)
    if merge_developer_into_system:
        return [
            {"role": "system", "content": prompts.SYSTEM_PROMPT + "\n\n" + dev},
            {"role": "user", "content": numbered_code},
        ]
    return [
        {"role": "system", "content": prompts.SYSTEM_PROMPT},
        {"role": "developer", "content": dev},
        {"role": "user", "content": numbered_code},
    ]


def analyze_chunk(text, start_line, end_line, ruleset_block, allowed_ids,
                  complete_fn, merge_developer_into_system=False):
    """
    단일 청크 분석 — 배치(transform, 청크당 1행)와 analyze_source 가 공통 사용.
    ruleset_block/allowed_ids 는 호출측에서 한 번만 계산해 넘긴다(배치 성능).
    반환: validate.validate_and_clean 결과 dict.
    """
    numbered = chunking.number_source(text, start_line=start_line)
    messages = build_messages(numbered, ruleset_block, merge_developer_into_system)
    raw = complete_fn(messages)
    data = validate.parse_json(raw)
    return validate.validate_and_clean(data, start_line, end_line, allowed_ids)


def analyze_source(source, policy_rows, complete_fn,
                   max_lines=400, merge_developer_into_system=False):
    """
    source       : ABAP 소스 전체(문자열)
    policy_rows  : severity_policy dict 리스트 (rule_id/category/rule_name/severity)
    complete_fn  : (messages) -> str  LLM 응답 원문 반환 콜백

    반환: {"findings": [...정렬됨...], "summary": {high,medium,low},
           "errors": [...청크별 실패 기록...]}
    라인번호는 원본 파일 기준 절대값(청킹이 절대번호를 부여하므로 별도 오프셋 보정 불필요).
    """
    ruleset_block = ruleset.build_ruleset_block(policy_rows)
    allowed = ruleset.active_rule_ids(policy_rows)
    if not allowed:
        return {"findings": [], "summary": {"high": 0, "medium": 0, "low": 0}, "errors": []}

    all_findings, errors = [], []
    for ch in chunking.chunk_source(source, max_lines=max_lines):
        try:
            cleaned = analyze_chunk(
                ch["text"], ch["start_line"], ch["end_line"],
                ruleset_block, allowed, complete_fn, merge_developer_into_system)
            all_findings.extend(cleaned["findings"])
        except Exception as e:  # 한 청크 실패가 전체를 죽이지 않게
            errors.append({"start_line": ch["start_line"],
                           "end_line": ch["end_line"], "error": str(e)})

    _order = {"high": 0, "medium": 1, "low": 2}
    all_findings.sort(key=lambda f: (_order.get(f["severity"], 9), f["line"]))
    summary = {"high": 0, "medium": 0, "low": 0}
    for f in all_findings:
        summary[f["severity"]] += 1
    return {"findings": all_findings, "summary": summary, "errors": errors}

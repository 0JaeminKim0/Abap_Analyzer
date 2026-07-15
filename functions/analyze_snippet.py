"""
작업 3 (인터랙티브) — 코드 붙여넣기 1건을 즉시 분석.

Workshop 앱이나 AIP Logic 에서 이 함수를 호출한다. 배치(run_analysis)와
동일한 core.analyze 를 쓰므로 결과 규칙이 완전히 일치한다.

입력:  source(문자열, ABAP 코드) — 붙여넣기
출력:  {"findings":[...], "summary":{...}, "errors":[...]} (JSON 문자열)

정책은 severity_policy 를 조회해 런타임에 자동 주입한다.
  - Foundry Function 에서 데이터셋을 직접 못 읽는 구성이면, 정책을 Ontology
    Object(SeverityPolicy)로 노출해 objectSet 으로 읽거나, AIP Logic 변수로 넘긴다.
    아래 _load_policy() 만 환경에 맞게 구현하면 된다.
"""
import json

from core import analyze as analyze_mod
from core.config import AIP_MODEL, GEN_PARAMS

# ─────────────────────────────────────────────────────────────
# ★ 버전 의존 지점 1: AIP Claude 모델 획득 (모델명은 core.config.AIP_MODEL)
def _get_model():
    from palantir_models.models import GenericChatCompletionLanguageModel  # 버전 의존
    return GenericChatCompletionLanguageModel.get(AIP_MODEL)


# ★ 버전 의존 지점 2: 정책 로드 (Ontology objectSet 또는 dataset)
def _load_policy():
    """
    severity_policy 를 dict 리스트로 반환:
        [{"rule_id","category","rule_name","severity"}, ...]
    구현 예시(Ontology):
        from ontology_sdk import FoundryClient
        client = FoundryClient()
        return [{"rule_id": o.rule_id, "category": o.category,
                 "rule_name": o.rule_name, "severity": o.severity}
                for o in client.ontology.objects.SeverityPolicy.iterate()]
    """
    raise NotImplementedError("환경에 맞게 severity_policy 로드를 구현하세요.")
# ─────────────────────────────────────────────────────────────


def _make_complete_fn(model):
    from palantir_models.models import ChatMessage, ChatCompletionRequest  # 버전 의존

    def complete(messages):
        chat = [ChatMessage(role=m["role"], content=m["content"]) for m in messages]
        resp = model.create_chat_completion(
            ChatCompletionRequest(messages=chat, **GEN_PARAMS))
        return resp.choices[0].message.content

    return complete


def analyze_snippet(source):
    """AIP Logic / Workshop 에서 호출하는 진입점."""
    if not source or not source.strip():
        return json.dumps({"findings": [], "summary": {"high": 0, "medium": 0, "low": 0},
                           "errors": []}, ensure_ascii=False)

    policy_rows = _load_policy()
    complete = _make_complete_fn(_get_model())
    result = analyze_mod.analyze_source(
        source, policy_rows, complete,
        merge_developer_into_system=True)   # 배치와 동일 설정
    return json.dumps(result, ensure_ascii=False)

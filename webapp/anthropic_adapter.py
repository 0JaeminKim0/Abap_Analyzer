"""
Railway 배포용 LLM 어댑터 — Anthropic API(Claude)를 직접 호출.

core.analyze 가 기대하는 complete_fn(messages)->str 규약으로 감싼다.
Foundry(palantir_models) 어댑터와 달리 여기서는 anthropic SDK 를 쓴다.

주의 (claude-api 스킬 기준):
  - 기본 모델은 claude-opus-4-8. ANTHROPIC_MODEL 환경변수로 교체 가능.
  - opus-4-8/4.7 은 temperature/top_p/top_k 를 넣으면 400 → 절대 전달하지 않는다.
  - Anthropic API 는 system 을 messages 안의 role 이 아니라 최상위 파라미터로 받으므로,
    core 가 만든 system 메시지를 top-level system 으로 옮기고 user 만 messages 로 보낸다.
    (core.analyze 는 merge_developer_into_system=True 로 호출되어 system+user 2개만 만든다)
"""
import os

import anthropic

# 기본 모델: 규칙상 opus-4-8. 저비용이 필요하면 ANTHROPIC_MODEL=claude-sonnet-5 등으로 교체.
DEFAULT_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-8")
MAX_TOKENS = int(os.environ.get("ANTHROPIC_MAX_TOKENS", "8000"))

_client = None


def _get_client():
    global _client
    if _client is None:
        # ANTHROPIC_API_KEY 환경변수에서 자동으로 키를 읽는다 (Railway 변수로 설정)
        _client = anthropic.Anthropic()
    return _client


def make_complete_fn(model: str = None):
    """core.analyze 에 넘길 complete_fn(messages)->str 을 만든다."""
    model = model or DEFAULT_MODEL
    client = _get_client()

    def complete(messages):
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        convo = [{"role": m["role"], "content": m["content"]}
                 for m in messages if m["role"] in ("user", "assistant")]

        kwargs = dict(model=model, max_tokens=MAX_TOKENS, messages=convo)
        if system:
            kwargs["system"] = system
        # temperature 등 샘플링 파라미터는 opus-4-8 에서 400 → 넣지 않는다.

        resp = client.messages.create(**kwargs)
        return "".join(b.text for b in resp.content if b.type == "text")

    return complete

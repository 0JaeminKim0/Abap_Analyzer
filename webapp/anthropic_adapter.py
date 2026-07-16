"""
Railway 배포용 LLM 어댑터 — Anthropic API(Claude)를 직접 호출.

core.analyze 가 기대하는 complete_fn(messages)->str 규약으로 감싼다.
호출마다 토큰 사용량을 UsageTracker 에 누적하고, 모델별 단가로 비용($)을 계산한다.

주의 (claude-api 스킬 기준):
  - 기본 모델은 claude-opus-4-6. ANTHROPIC_MODEL 환경변수로 교체 가능.
  - opus-4-7/4.8 은 temperature/top_p/top_k 를 넣으면 400 → 어차피 전달하지 않는다
    (opus-4-6 은 허용하지만 재현성/단순성을 위해 보내지 않음).
  - Anthropic API 는 system 을 최상위 파라미터로 받으므로, core 가 만든 system 메시지를
    top-level system 으로 옮기고 user 만 messages 로 보낸다.
"""
import os

import anthropic

# 기본 모델: claude-opus-4-6. 다른 모델은 ANTHROPIC_MODEL 환경변수로 교체.
DEFAULT_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-6")
MAX_TOKENS = int(os.environ.get("ANTHROPIC_MAX_TOKENS", "8000"))

# 모델별 단가 (USD per 1M tokens): {"in": 입력, "out": 출력}
PRICES = {
    "claude-opus-4-8": {"in": 5.0, "out": 25.0},
    "claude-opus-4-7": {"in": 5.0, "out": 25.0},
    "claude-opus-4-6": {"in": 5.0, "out": 25.0},
    "claude-opus-4-5": {"in": 5.0, "out": 25.0},
    "claude-sonnet-5": {"in": 3.0, "out": 15.0},
    "claude-sonnet-4-6": {"in": 3.0, "out": 15.0},
    "claude-haiku-4-5": {"in": 1.0, "out": 5.0},
    "claude-fable-5": {"in": 10.0, "out": 50.0},
    "_default": {"in": 5.0, "out": 25.0},
}

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic()  # ANTHROPIC_API_KEY 환경변수 사용
    return _client


class UsageTracker:
    """한 번의 분석(여러 청크 호출)에 걸친 토큰 사용량 누적."""
    def __init__(self):
        self.input = 0
        self.output = 0
        self.cache_read = 0
        self.cache_creation = 0
        self.calls = 0

    def add(self, u):
        self.input += getattr(u, "input_tokens", 0) or 0
        self.output += getattr(u, "output_tokens", 0) or 0
        self.cache_read += getattr(u, "cache_read_input_tokens", 0) or 0
        self.cache_creation += getattr(u, "cache_creation_input_tokens", 0) or 0
        self.calls += 1


def make_complete_fn(model: str = None, usage: "UsageTracker" = None):
    """core.analyze 에 넘길 complete_fn(messages)->str. usage 가 주어지면 사용량을 누적한다."""
    model = model or DEFAULT_MODEL
    client = _get_client()

    def complete(messages):
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        convo = [{"role": m["role"], "content": m["content"]}
                 for m in messages if m["role"] in ("user", "assistant")]
        kwargs = dict(model=model, max_tokens=MAX_TOKENS, messages=convo)
        if system:
            kwargs["system"] = system
        resp = client.messages.create(**kwargs)
        if usage is not None:
            usage.add(resp.usage)
        return "".join(b.text for b in resp.content if b.type == "text")

    return complete


def compute_cost(usage: "UsageTracker", model: str) -> float:
    """모델 단가로 예상 비용(USD) 계산. 캐시 읽기 0.1x, 캐시 쓰기 1.25x 반영."""
    p = PRICES.get(model, PRICES["_default"])
    inp = (usage.input * p["in"]
           + usage.cache_read * p["in"] * 0.1
           + usage.cache_creation * p["in"] * 1.25)
    out = usage.output * p["out"]
    return (inp + out) / 1_000_000.0


def usage_dict(usage: "UsageTracker", model: str) -> dict:
    return {
        "model": model,
        "calls": usage.calls,
        "input_tokens": usage.input,
        "output_tokens": usage.output,
        "cache_read_tokens": usage.cache_read,
        "cache_creation_tokens": usage.cache_creation,
        "total_tokens": usage.input + usage.output + usage.cache_read + usage.cache_creation,
        "cost_usd": round(compute_cost(usage, model), 6),
    }

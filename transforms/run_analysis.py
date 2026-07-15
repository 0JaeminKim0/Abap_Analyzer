"""
작업 3-④ — 배치 LLM 분석.

입력:
  /abap-analyzer/abap_chunks       (청크당 1행)
  /abap-analyzer/severity_policy   (조직 정책 → 프롬프트에 자동 주입)
출력:
  /abap-analyzer/findings          (finding 당 1행. 후처리/Ontology 는 이후 팀 내부에서)

동작:
  1) 정책을 드라이버에서 한 번만 읽어 ruleset 블록 + 활성 규칙 집합 계산
  2) 각 청크에 대해 core.analyze.analyze_chunk 호출 (인터랙티브와 동일 로직)
  3) LLM 응답을 스키마 검증 + 라인범위 환각제거 후 평탄화하여 저장

★ AIP 모델 바인딩(아래 _make_complete_fn 및 model 인자)만이 팀 Foundry 버전에
  의존하는 유일한 지점이다. 배포 시 이 부분의 import/메서드명을 확인할 것.
"""
from transforms.api import transform, Input, Output
from pyspark.sql import types as T

from core import ruleset as ruleset_mod
from core import analyze as analyze_mod
from core.config import AIP_MODEL, GEN_PARAMS

# ─────────────────────────────────────────────────────────────
# ★ 버전 의존 지점: AIP Claude 챗 모델 리소스를 transform 인자로 주입.
#   Claude 는 provider-agnostic 인 GenericChatCompletionLanguageModelInput 로 바인딩한다.
#   (팀 Foundry 버전에 따라 클래스명이 다를 수 있음)
from palantir_models.transforms import GenericChatCompletionLanguageModelInput
# ─────────────────────────────────────────────────────────────


def _make_complete_fn(model):
    """AIP Claude 모델을 core 가 기대하는 complete_fn(messages)->str 로 감싼다."""
    from palantir_models.models import ChatMessage, ChatCompletionRequest  # 버전 의존

    def complete(messages):
        # 배치에서는 developer 롤을 system 에 합쳐 롤 호환 문제를 피한다
        # (core.analyze 호출 시 merge_developer_into_system=True 로 이미 병합됨)
        chat = [ChatMessage(role=m["role"], content=m["content"]) for m in messages]
        resp = model.create_chat_completion(
            ChatCompletionRequest(messages=chat, **GEN_PARAMS))
        return resp.choices[0].message.content

    return complete


_OUT_SCHEMA = T.StructType([
    T.StructField("program_id", T.StringType()),
    T.StructField("chunk_index", T.IntegerType()),
    T.StructField("rule_id", T.StringType()),
    T.StructField("category", T.StringType()),
    T.StructField("severity", T.StringType()),
    T.StructField("line", T.IntegerType()),
    T.StructField("title", T.StringType()),
    T.StructField("explanation", T.StringType()),
    T.StructField("suggestion", T.StringType()),
    T.StructField("before", T.StringType()),
    T.StructField("after", T.StringType()),
    T.StructField("error", T.StringType()),   # 청크 분석 실패 기록(정상 시 null)
])


@transform(
    chunks=Input("/abap-analyzer/abap_chunks"),
    policy=Input("/abap-analyzer/severity_policy"),
    out=Output("/abap-analyzer/findings"),
    model=GenericChatCompletionLanguageModelInput(AIP_MODEL),   # Claude
)
def compute(ctx, chunks, policy, out, model):
    # 1) 정책 → 프롬프트 재료 (드라이버에서 1회)
    policy_rows = [r.asDict() for r in policy.dataframe().collect()]
    ruleset_block = ruleset_mod.build_ruleset_block(policy_rows)
    allowed = ruleset_mod.active_rule_ids(policy_rows)
    complete = _make_complete_fn(model)

    # 2) 청크별 분석 (드라이버 순회 — 대규모 시 모델 배치 API 로 전환 권장)
    out_rows = []
    for r in chunks.dataframe().collect():
        try:
            res = analyze_mod.analyze_chunk(
                r["text"], r["start_line"], r["end_line"],
                ruleset_block, allowed, complete,
                merge_developer_into_system=True)
            for f in res["findings"]:
                out_rows.append((
                    r["program_id"], r["chunk_index"], f["id"], f["category"],
                    f["severity"], f["line"], f["title"], f["explanation"],
                    f["suggestion"], f["before"], f["after"], None))
        except Exception as e:  # 청크 실패는 행으로 기록하고 계속
            out_rows.append((
                r["program_id"], r["chunk_index"], None, None, None, None,
                None, None, None, None, None, str(e)))

    out.write_dataframe(ctx.spark_session.createDataFrame(out_rows, _OUT_SCHEMA))

"""
작업 2-a — Excel 업로드본(severity_policy_raw) 을 정제하여 severity_policy 생성.

입력:  /abap-analyzer/severity_policy_raw   (make_template.py 로 만든 xlsx 업로드본)
출력:  /abap-analyzer/severity_policy        (Analyzer 가 읽는 정제본)

정제 규칙:
  - enabled = 'Y' 이고 org_severity != 'off' 인 행만 남긴다.
  - severity 는 org_severity 를 소문자로 정규화.
  - 컬럼: rule_id, category, rule_name, severity
이 데이터셋을 Ontology Object 'SeverityPolicy' 에 백킹시켜도 된다(선택).
"""
from transforms.api import transform, Input, Output
from pyspark.sql import functions as F


@transform(
    raw=Input("/abap-analyzer/severity_policy_raw"),
    out=Output("/abap-analyzer/severity_policy"),
)
def compute(raw, out):
    df = raw.dataframe()

    cleaned = (
        df
        .withColumn("enabled", F.upper(F.trim(F.col("enabled"))))
        .withColumn("severity", F.lower(F.trim(F.col("org_severity"))))
        .filter((F.col("enabled") == "Y") & (F.col("severity") != "off"))
        .filter(F.col("severity").isin("high", "medium", "low"))
        .select(
            F.trim(F.col("rule_id")).alias("rule_id"),
            F.lower(F.trim(F.col("category"))).alias("category"),
            F.col("rule_name"),
            F.col("severity"),
        )
        .dropDuplicates(["rule_id"])
    )

    out.write_dataframe(cleaned)

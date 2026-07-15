"""
작업 3-② — ABAP 소스를 논리 단위 청크로 분할.

입력:  /abap-analyzer/abap_source   (파일당 1행: program_id, source)
출력:  /abap-analyzer/abap_chunks   (청크당 1행: program_id, chunk_index, start_line, end_line, text)

core.chunking 을 재사용해 배치·인터랙티브가 동일한 분할 규칙을 쓴다.
"""
from transforms.api import transform, Input, Output
from pyspark.sql import functions as F, types as T
from pyspark.sql.window import Window

from core import chunking

_CHUNK_SCHEMA = T.ArrayType(T.StructType([
    T.StructField("start_line", T.IntegerType()),
    T.StructField("end_line", T.IntegerType()),
    T.StructField("text", T.StringType()),
]))


@F.udf(returnType=_CHUNK_SCHEMA)
def _chunk_udf(source):
    if not source:
        return []
    return chunking.chunk_source(source)


@transform(
    src=Input("/abap-analyzer/abap_source"),
    out=Output("/abap-analyzer/abap_chunks"),
)
def compute(src, out):
    df = (
        src.dataframe()
        .withColumn("chunk", F.explode(_chunk_udf(F.col("source"))))
        .select(
            "program_id",
            F.col("chunk.start_line").alias("start_line"),
            F.col("chunk.end_line").alias("end_line"),
            F.col("chunk.text").alias("text"),
        )
    )
    # program 내 청크 순번 부여
    w = Window.partitionBy("program_id").orderBy("start_line")
    df = df.withColumn("chunk_index", F.row_number().over(w) - 1)
    out.write_dataframe(df.select(
        "program_id", "chunk_index", "start_line", "end_line", "text"))

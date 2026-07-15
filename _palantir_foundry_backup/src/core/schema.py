"""
LLM 출력 JSON 스키마 (부록 A.2 / A.4).

FINDINGS_SCHEMA : jsonschema 검증용 정식 스키마
SCHEMA_HINT     : 프롬프트에 넣어 모델에게 형식을 지시하는 축약본
"""

FINDINGS_SCHEMA = {
    "type": "object",
    "required": ["findings", "summary"],
    "additionalProperties": False,
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "category", "severity", "line", "title",
                             "explanation", "suggestion", "before", "after"],
                "additionalProperties": False,
                "properties": {
                    "id": {"type": "string"},
                    "category": {"enum": ["performance", "quality", "security", "standard"]},
                    "severity": {"enum": ["high", "medium", "low"]},
                    "line": {"type": "integer", "minimum": 1},
                    "title": {"type": "string"},
                    "explanation": {"type": "string"},
                    "suggestion": {"type": "string"},
                    "before": {"type": "string"},
                    "after": {"type": "string"},
                },
            },
        },
        "summary": {
            "type": "object",
            "required": ["high", "medium", "low"],
            "additionalProperties": False,
            "properties": {
                "high": {"type": "integer", "minimum": 0},
                "medium": {"type": "integer", "minimum": 0},
                "low": {"type": "integer", "minimum": 0},
            },
        },
    },
}

SCHEMA_HINT = """\
{
  "findings": [{
    "id": "규칙ID",  "category": "performance|quality|security|standard",
    "severity": "high|medium|low",  "line": <정수>,
    "title": "<한 줄 요약>",  "explanation": "<왜 문제인지>",
    "suggestion": "<어떻게 고칠지>",  "before": "<문제 코드>",  "after": "<개선 코드>"
  }],
  "summary": { "high": <int>, "medium": <int>, "low": <int> }
}"""

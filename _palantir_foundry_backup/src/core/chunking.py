"""
청킹 — 긴 ABAP 프로그램을 논리 단위(FORM/METHOD/FUNCTION/MODULE)로 분할하고
각 청크에 원본 절대 라인번호를 부여한다.

목적:
  1) LLM 컨텍스트 한도 대응
  2) finding 의 line 을 '원본 파일 기준 절대 라인번호'로 되돌릴 수 있게 함
     (LLM 에는 절대 라인번호를 그대로 붙여서 보여주므로 매핑이 단순해진다)

number_source() 로 라인번호를 붙인 텍스트를 만들어 User 프롬프트에 넣는다.
"""
import re

# 논리 블록 시작 키워드 (대소문자 무시)
_BLOCK_START = re.compile(
    r"^\s*(FORM|METHOD|FUNCTION|MODULE)\b", re.IGNORECASE)
# 블록 종료 키워드
_BLOCK_END = re.compile(
    r"^\s*(ENDFORM|ENDMETHOD|ENDFUNCTION|ENDMODULE)\b", re.IGNORECASE)


def chunk_source(source, max_lines=400):
    """
    source(문자열) -> 청크 리스트.
    각 청크: {"start_line": int(1-based), "end_line": int, "text": str}

    논리 블록 경계에서 분할하되, 블록 밖의 선언부/톱레벨 코드도 하나의 청크로 보존한다.
    단일 블록이 max_lines 를 넘으면 그대로 둔다(의미 단위 보존 우선).
    """
    lines = source.splitlines()
    n = len(lines)
    chunks = []
    i = 0
    seg_start = 0  # 현재 세그먼트 시작 인덱스(0-based)
    depth = 0

    def flush(end_idx):
        nonlocal seg_start
        if end_idx >= seg_start and any(l.strip() for l in lines[seg_start:end_idx + 1]):
            chunks.append({
                "start_line": seg_start + 1,
                "end_line": end_idx + 1,
                "text": "\n".join(lines[seg_start:end_idx + 1]),
            })
        seg_start = end_idx + 1

    while i < n:
        line = lines[i]
        if depth == 0 and _BLOCK_START.match(line):
            # 블록 시작 직전까지의 톱레벨 세그먼트를 flush
            if i > seg_start:
                flush(i - 1)
            seg_start = i
            depth = 1
        elif depth > 0 and _BLOCK_END.match(line):
            depth = 0
            flush(i)
        # 세그먼트가 너무 길어지면(톱레벨) 안전 분할
        elif depth == 0 and (i - seg_start + 1) >= max_lines:
            flush(i)
        i += 1

    flush(n - 1)
    return chunks


def number_source(text, start_line=1):
    """
    청크 텍스트에 절대 라인번호를 접두어로 붙인다.
    LLM 이 이 번호를 그대로 finding.line 에 쓰도록 프롬프트에서 지시한다.

        001| REPORT ...
        002| DATA ...
    """
    out = []
    for offset, line in enumerate(text.splitlines()):
        out.append(f"{start_line + offset:03d}| {line}")
    return "\n".join(out)

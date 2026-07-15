# ABAP Analyzer (Palantir Foundry + AIP)

LLM 기반 ABAP 정적 분석기. 조직이 Excel로 정한 severity 정책을 분석 에이전트에
**자동 주입**하고, 배치·인터랙티브 두 경로가 **같은 코어 로직**으로 코드를 분석한다.

개념·기획 배경은 [explain.md](explain.md) / [explain.html](explain.html) 참고.

## 데이터 흐름

```
[작업1] make_template.py ─► severity_policy_template.xlsx ─(조직 작성)─►
        Foundry 업로드 ─► severity_policy_raw
[작업2] policy_clean.py  ─► severity_policy ─► ruleset.build_ruleset_block() 로 프롬프트 자동 주입
[작업3] abap_source ─► abap_chunks ─► run_analysis.py(+정책+AIP) ─► findings
        (인터랙티브) analyze_snippet.py ─ 같은 core.analyze 호출
```

## 디렉터리

| 경로 | 역할 |
|------|------|
| `src/core/config.py` | AI 모델 설정 (**우선 Claude** — `AIP_MODEL`) + 생성 파라미터 |
| `src/core/catalog.py` | 19개 규칙 단일 원천 |
| `src/core/prompts.py` | System/Developer 프롬프트 템플릿 |
| `src/core/ruleset.py` | 정책 → 프롬프트 규칙셋 블록 (작업 2 핵심) |
| `src/core/schema.py` | 출력 JSON 스키마 |
| `src/core/chunking.py` | 논리 단위 분할 + 라인번호 |
| `src/core/validate.py` | 스키마검증 + 라인범위 환각제거 |
| `src/core/analyze.py` | 오케스트레이터 (배치·인터랙티브 공용) |
| `transforms/policy_clean.py` | Excel → severity_policy (작업 2-a) |
| `transforms/abap_chunks.py` | 소스 청킹 배치 |
| `transforms/run_analysis.py` | 배치 LLM 분석 (작업 3) |
| `functions/analyze_snippet.py` | 인터랙티브 분석 (작업 3) |
| `tools/make_template.py` | Severity 수집 Excel 생성 (작업 1) |
| `tests/test_core.py` | 오프라인 코어 검증 |

## 로컬 검증 (AIP/Spark 불필요)

```bash
pip install openpyxl jsonschema
python tools/make_template.py          # Excel 템플릿 생성
python tests/test_core.py              # 코어 로직 end-to-end 검증
```

## 배포 시 확정할 지점 (★ 버전 의존)

AI 모델은 **Claude 로 구성**되어 있다. 모델 alias 는 `src/core/config.py` 의
`AIP_MODEL` 한 곳에서 관리하며, 팀 AIP 에 provisioning 된 Claude 리소스 이름과
일치시키면 된다 (예: `"Claude-Sonnet"`, `"Claude-Opus"`).

Foundry/AIP 버전에 따라 이름이 다를 수 있는 **유일한** 부분:

- `src/core/config.py` — `AIP_MODEL` 값을 팀 AIP 의 Claude alias 로 확정.
- `transforms/run_analysis.py` — 모델 Input 클래스(`GenericChatCompletionLanguageModelInput`)
  와 `_make_complete_fn` 의 `create_chat_completion` 호출부.
- `functions/analyze_snippet.py` — `_get_model()`, `_load_policy()`
  (정책을 Ontology objectSet 로 읽을지 dataset 으로 읽을지).

코어 로직(`src/core/analyze.py` 등)은 모델·플랫폼 비의존이라 수정 불필요.

## 정책 변경 = 분석 기준 변경 (재배포 없음)

Excel에서 `org_severity` 를 바꾸거나 `enabled=N`/`off` 로 끄고 다시 업로드하면,
`policy_clean` → `severity_policy` 갱신 → 다음 분석부터 프롬프트가 자동 반영된다.

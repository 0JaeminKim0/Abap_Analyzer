"""
Analyzer 런타임 설정 — 모델은 우선 Claude 로 구성.

AIP_MODEL 은 팀 Foundry/AIP 에 provisioning 된 Claude 모델 리소스의 alias 와
정확히 일치해야 한다. (AIP 관리 콘솔의 모델 이름을 그대로 사용)

AIP 에 노출되는 Claude alias 예시(환경마다 다름):
    "Claude-Sonnet", "Claude-Opus", "anthropic-claude-3-7-sonnet" 등
바꿀 때는 이 값 하나만 수정하면 배치·인터랙티브 모두 반영된다.
"""
AIP_MODEL = "Claude-Sonnet"

# 생성 파라미터 (모델 호출 시 사용; 지원되는 값만 전달)
GEN_PARAMS = {
    "temperature": 0,      # 정적 분석 → 재현성 우선, 창의성 억제
    "max_tokens": 4096,
}

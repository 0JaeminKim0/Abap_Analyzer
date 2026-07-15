# ABAP Analyzer — Railway 배포 가이드

LLM(Claude) 기반 ABAP 분석기를 **웹 서비스**로 Railway에 올린다.
Foundry 버전은 [_palantir_foundry_backup/](_palantir_foundry_backup/)에 백업돼 있고,
분석 로직 코어(`src/core`)는 두 버전이 공유한다.

## 구성

```
ABAP_Analyzer/
├── src/core/            ← 공유 코어 (모델·플랫폼 비의존)
├── webapp/              ← Railway 웹 앱
│   ├── app.py            FastAPI: GET / (UI) · GET /health · POST /analyze
│   ├── anthropic_adapter.py  Claude(Anthropic API) 호출 어댑터
│   └── policy.py         severity 정책 로더 (기본: catalog 기본값)
├── Dockerfile · railway.json · requirements.txt · .dockerignore
└── _palantir_foundry_backup/   ← Foundry 버전 백업
```

## 필요한 것

- **Anthropic API 키** (`sk-ant-...`) — [console.anthropic.com](https://console.anthropic.com) 에서 발급
- Railway 계정 + 이 폴더가 담긴 Git 저장소(GitHub 권장)

## 배포 절차 (GitHub 연동)

1. 이 프로젝트를 GitHub 저장소로 push.
2. Railway → **New Project → Deploy from GitHub repo** → 저장소 선택.
3. 저장소 루트가 `ABAP_Analyzer`가 아니면, 서비스 **Settings → Root Directory** 를 `ABAP_Analyzer`로 지정 (Dockerfile 이 여기 있음).
4. **Variables** 탭에서 환경변수 추가:
   - `ANTHROPIC_API_KEY` = `sk-ant-...`  (필수)
   - `ANTHROPIC_MODEL` = `claude-opus-4-8` (선택, 기본값. 저비용은 `claude-sonnet-5`)
   - `ANTHROPIC_MAX_TOKENS` = `8000` (선택)
5. 배포되면 Railway가 공개 URL을 발급. `/health` 로 상태 확인, `/` 로 UI 접속.

## 배포 절차 (Railway CLI 대안)

```bash
npm i -g @railway/cli
railway login
cd ABAP_Analyzer
railway init
railway variables set ANTHROPIC_API_KEY=sk-ant-...
railway up
```

## 로컬 실행 (배포 전 확인)

```powershell
pip install -r requirements.txt
$env:ANTHROPIC_API_KEY = "sk-ant-..."
uvicorn webapp.app:app --port 8000
# 브라우저에서 http://localhost:8000
```

## 동작

- `POST /analyze` `{ "source": "<ABAP 코드>" }` → 청킹 → Claude 분석(정책 프롬프트 주입) →
  JSON 스키마 검증 + 라인범위 환각제거 + 정책 외 규칙 필터 → `{findings, summary, errors}`
- 정책은 `webapp/policy.py`가 `core.catalog` 기본 severity로 구성. 조직 정책 CSV를 쓰려면
  `SEVERITY_POLICY_CSV` 환경변수에 파일 경로 지정(컬럼: `rule_id,severity[,enabled]`).

## 확인된 사항 (로컬 실측)

- FastAPI 앱: `/health`, `/`, `/analyze` 정상 (Claude 호출부 스텁으로 전체 경로 검증)
- 정책 외 규칙 자동 필터 + summary 재계산 동작
- 미검증: 실제 Claude 응답 품질 — API 키를 넣고 로컬/Railway에서 실제 소스로 확인 필요

## 비용·주의

- 분석 1건마다 Claude API 호출료 발생 (opus-4-8 기준 입력 $5 / 출력 $25 per 1M tokens).
- 공개 URL이므로 필요시 Railway 앞단에 인증/레이트리밋 추가 권장.
- 코드가 Anthropic API로 전송됨 — 민감 소스는 정책 검토 후 사용.

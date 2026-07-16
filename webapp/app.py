"""
ABAP Analyzer — Railway 배포용 FastAPI 웹 서비스.

엔드포인트:
  GET  /                 코드 붙여넣기 + 정책 관리 웹 UI
  GET  /health           상태(모델/활성 규칙 수/정책 출처)
  POST /analyze          {"source": "<ABAP 코드>"} → findings JSON
  GET  /policy           현재 활성 정책 조회
  POST /policy           severity 정책 파일(xlsx/csv) 업로드 → 활성 정책 교체
  POST /policy/reset     정책을 기본값(catalog)으로 되돌림
  GET  /policy/template.csv  작성용 CSV 템플릿 다운로드

실행: uvicorn webapp.app:app --host 0.0.0.0 --port ${PORT:-8000}
공유 코어(src/core)를 그대로 재사용한다.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "src"))

from fastapi import FastAPI, UploadFile, File  # noqa: E402
from fastapi.responses import HTMLResponse, Response, JSONResponse  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from core import analyze  # noqa: E402
from webapp import policy  # noqa: E402
from webapp.anthropic_adapter import make_complete_fn, DEFAULT_MODEL  # noqa: E402

app = FastAPI(title="ABAP Analyzer", version="1.1")


class AnalyzeIn(BaseModel):
    source: str


@app.get("/health")
def health():
    return {"status": "ok", "model": DEFAULT_MODEL,
            "active_rules": len(policy.get_active()),
            "policy_source": policy.get_source()}


@app.post("/analyze")
def analyze_endpoint(body: AnalyzeIn):
    if not body.source.strip():
        return {"findings": [], "summary": {"high": 0, "medium": 0, "low": 0}, "errors": []}
    complete = make_complete_fn()
    return analyze.analyze_source(
        body.source, policy.get_active(), complete, merge_developer_into_system=True)


# ---------- 정책 관리 ----------
@app.get("/policy")
def get_policy():
    rows = policy.get_active()
    return {"source": policy.get_source(), "count": len(rows), "rules": rows}


@app.post("/policy")
async def upload_policy(file: UploadFile = File(...)):
    data = await file.read()
    if not data:
        return JSONResponse(status_code=400, content={"error": "빈 파일입니다."})
    try:
        overrides = policy.parse_upload(file.filename, data)
    except Exception as e:  # 파싱 실패
        return JSONResponse(status_code=400, content={"error": f"파싱 실패: {e}"})
    if not overrides:
        return JSONResponse(status_code=400,
                            content={"error": "유효한 rule_id 행을 찾지 못했습니다."})
    rows = policy.set_from_overrides(overrides, source=f"upload:{file.filename}")
    return {"source": policy.get_source(), "count": len(rows), "rules": rows}


@app.post("/policy/reset")
def reset_policy():
    rows = policy.reset()
    return {"source": policy.get_source(), "count": len(rows), "rules": rows}


@app.get("/policy/template.csv")
def policy_template():
    csv_text = policy.template_csv()
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="severity_policy_template.csv"'},
    )


@app.get("/", response_class=HTMLResponse)
def index():
    return INDEX_HTML


INDEX_HTML = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ABAP Analyzer</title>
<style>
  :root {
    --bg:#0e1116; --surface:#161a21; --surface2:#1b2028; --ink:#e7eaef; --muted:#9aa4b2;
    --border:#262c36; --accent:#3bbccb; --accent2:#0b7285;
    --high:#ff6b9d; --high-bg:#3a1622; --med:#f0a862; --med-bg:#3a2916; --low:#97a3b3; --low-bg:#232a33;
    --mono:"Cascadia Code","Consolas",ui-monospace,monospace;
    --sans:system-ui,"Segoe UI",Roboto,sans-serif;
  }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--ink); font-family:var(--sans); }
  header { padding:18px 24px; border-bottom:1px solid var(--border); display:flex; align-items:baseline; gap:14px; }
  header h1 { margin:0; font-size:20px; letter-spacing:-.01em; }
  header .eyebrow { font-family:var(--mono); font-size:11px; letter-spacing:.12em; text-transform:uppercase; color:var(--accent); }
  header .model { margin-left:auto; font-family:var(--mono); font-size:12px; color:var(--muted); }

  .policybar { display:flex; align-items:center; gap:12px; flex-wrap:wrap; padding:12px 24px; border-bottom:1px solid var(--border); background:var(--surface); }
  .policybar .lbl { font-family:var(--mono); font-size:11px; letter-spacing:.1em; text-transform:uppercase; color:var(--accent); }
  .policybar .state { font-size:13px; color:var(--muted); }
  .policybar .spacer { flex:1; }
  .policybar input[type=file]{ font-size:12px; color:var(--muted); max-width:230px; }

  main { max-width:1100px; margin:0 auto; padding:24px; display:grid; grid-template-columns:1fr 1fr; gap:20px; }
  @media (max-width:820px){ main{ grid-template-columns:1fr; } }
  .panel { background:var(--surface); border:1px solid var(--border); border-radius:12px; overflow:hidden; display:flex; flex-direction:column; }
  .panel h2 { margin:0; padding:12px 16px; font-size:12px; font-family:var(--mono); letter-spacing:.08em; text-transform:uppercase; color:var(--muted); border-bottom:1px solid var(--border); background:var(--surface2); }
  textarea { width:100%; min-height:420px; border:0; background:transparent; color:var(--ink); font-family:var(--mono); font-size:13px; line-height:1.6; padding:14px 16px; resize:vertical; outline:none; }
  .bar { display:flex; gap:10px; align-items:center; padding:12px 16px; border-top:1px solid var(--border); }
  button, .btn { font-family:var(--sans); font-weight:600; font-size:13px; padding:8px 14px; border-radius:8px; border:0; cursor:pointer; background:var(--accent); color:#05222a; text-decoration:none; display:inline-block; }
  button:disabled { opacity:.55; cursor:default; }
  .ghost { background:transparent; color:var(--muted); border:1px solid var(--border); }
  .status { font-size:13px; color:var(--muted); }
  .results { padding:14px 16px; overflow-y:auto; min-height:420px; }
  .summary { display:flex; gap:8px; margin-bottom:14px; flex-wrap:wrap; }
  .chip { display:inline-flex; align-items:center; gap:6px; font-family:var(--mono); font-size:12px; font-weight:600; padding:4px 10px; border-radius:100px; }
  .chip::before { content:""; width:7px; height:7px; border-radius:50%; }
  .chip.high{ background:var(--high-bg); color:var(--high);} .chip.high::before{ background:var(--high);}
  .chip.med{ background:var(--med-bg); color:var(--med);} .chip.med::before{ background:var(--med);}
  .chip.low{ background:var(--low-bg); color:var(--low);} .chip.low::before{ background:var(--low);}
  .finding { border:1px solid var(--border); border-radius:10px; padding:12px 14px; margin-bottom:10px; background:var(--surface2); }
  .finding .top { display:flex; align-items:center; gap:8px; margin-bottom:6px; flex-wrap:wrap; }
  .finding .rid { font-family:var(--mono); font-size:12px; font-weight:600; color:var(--accent); }
  .finding .line { font-family:var(--mono); font-size:12px; color:var(--muted); margin-left:auto; }
  .finding .title { font-weight:650; font-size:14px; margin:2px 0 6px; }
  .finding p { margin:4px 0; font-size:13px; color:var(--muted); }
  .finding .fix { color:var(--ink); }
  .finding pre { background:var(--bg); border:1px solid var(--border); border-radius:8px; padding:8px 10px; margin:6px 0 0; overflow-x:auto; font-family:var(--mono); font-size:12px; }
  .finding pre.after { border-color:var(--accent2); }
  .empty { color:var(--muted); font-size:14px; text-align:center; padding:40px 0; }
  .err { color:var(--high); font-size:13px; }
</style>
</head>
<body>
  <header>
    <span class="eyebrow">SAP · LLM</span>
    <h1>ABAP Analyzer</h1>
    <span class="model" id="model"></span>
  </header>

  <div class="policybar">
    <span class="lbl">Severity 정책</span>
    <span class="state" id="pstate">로딩 중...</span>
    <span class="spacer"></span>
    <a class="btn ghost" href="/policy/template.csv">템플릿(CSV) 다운로드</a>
    <input type="file" id="pfile" accept=".csv,.xlsx,.xlsm">
    <button id="pupload">업로드</button>
    <button class="ghost" id="preset">기본값</button>
  </div>

  <main>
    <section class="panel">
      <h2>ABAP 소스 붙여넣기</h2>
      <textarea id="src" placeholder="여기에 ABAP 코드를 붙여넣으세요..."></textarea>
      <div class="bar">
        <button id="run">분석</button>
        <button class="ghost" id="sample">예시 넣기</button>
        <span class="status" id="status"></span>
      </div>
    </section>
    <section class="panel">
      <h2>분석 결과</h2>
      <div class="results" id="results"><div class="empty">코드를 넣고 "분석"을 누르세요.</div></div>
    </section>
  </main>
<script>
const SAMPLE = `REPORT z_customer_sales.
DATA: lt_kna1  TYPE TABLE OF kna1,
      ls_kna1  TYPE kna1,
      lt_vbak  TYPE TABLE OF vbak,
      lv_total TYPE p DECIMALS 2,
      lv_unused TYPE i.

PARAMETERS: p_land TYPE kna1-land1.

SELECT * FROM kna1 INTO TABLE lt_kna1.

LOOP AT lt_kna1 INTO ls_kna1.
  SELECT * FROM vbak INTO TABLE lt_vbak
    WHERE kunnr = ls_kna1-kunnr.
  lv_total = lv_total + lines( lt_vbak ).
  IF ls_kna1-land1 = 'KR'.
    WRITE: / ls_kna1-kunnr, ls_kna1-name1.
  ENDIF.
ENDLOOP.

WRITE: / 'Total Orders:', lv_total.`;

const $ = s => document.querySelector(s);
const sevClass = s => s === 'high' ? 'high' : s === 'medium' ? 'med' : 'low';
const esc = t => (t||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

function loadState(){
  fetch('/health').then(r=>r.json()).then(d=>{
    $('#model').textContent = 'model: '+d.model;
    $('#pstate').textContent = '활성 규칙 '+d.active_rules+'개 · 출처: '+d.policy_source;
  }).catch(()=>{ $('#pstate').textContent = '상태 조회 실패'; });
}
loadState();

$('#sample').onclick = () => { $('#src').value = SAMPLE; };

$('#pupload').onclick = async () => {
  const f = $('#pfile').files[0];
  if (!f) { $('#pstate').textContent = '파일을 선택하세요.'; return; }
  $('#pupload').disabled = true; $('#pstate').textContent = '업로드 중...';
  const fd = new FormData(); fd.append('file', f);
  try {
    const res = await fetch('/policy', {method:'POST', body:fd});
    const d = await res.json();
    if (!res.ok) throw new Error(d.error || ('HTTP '+res.status));
    $('#pstate').textContent = '반영됨 · 활성 규칙 '+d.count+'개 · 출처: '+d.source;
  } catch(e) {
    $('#pstate').textContent = '업로드 실패: '+e.message;
  } finally { $('#pupload').disabled = false; }
};

$('#preset').onclick = async () => {
  const res = await fetch('/policy/reset', {method:'POST'});
  const d = await res.json();
  $('#pstate').textContent = '기본값으로 복원 · 활성 규칙 '+d.count+'개';
  $('#pfile').value = '';
};

$('#run').onclick = async () => {
  const source = $('#src').value;
  if (!source.trim()) { $('#status').textContent = '코드를 입력하세요.'; return; }
  $('#run').disabled = true; $('#status').textContent = '분석 중... (Claude 호출)';
  $('#results').innerHTML = '<div class="empty">분석 중...</div>';
  try {
    const res = await fetch('/analyze', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({source})});
    if (!res.ok) throw new Error('HTTP '+res.status);
    render(await res.json());
    $('#status').textContent = '완료';
  } catch (e) {
    $('#results').innerHTML = '<div class="err">오류: '+esc(e.message)+'</div>';
    $('#status').textContent = '실패';
  } finally { $('#run').disabled = false; }
};

function render(data){
  const s = data.summary || {high:0,medium:0,low:0};
  let html = '<div class="summary">'
    + '<span class="chip high">high '+s.high+'</span>'
    + '<span class="chip med">medium '+s.medium+'</span>'
    + '<span class="chip low">low '+s.low+'</span></div>';
  const fs = data.findings || [];
  if (!fs.length) { html += '<div class="empty">발견된 이슈가 없습니다.</div>'; }
  for (const f of fs) {
    html += '<div class="finding"><div class="top">'
      + '<span class="rid">'+esc(f.id)+'</span>'
      + '<span class="chip '+sevClass(f.severity)+'">'+esc(f.severity)+'</span>'
      + '<span class="line">line '+f.line+'</span></div>'
      + '<div class="title">'+esc(f.title)+'</div>'
      + '<p>'+esc(f.explanation)+'</p>'
      + '<p class="fix">✔ '+esc(f.suggestion)+'</p>';
    if (f.before) html += '<pre>'+esc(f.before)+'</pre>';
    if (f.after)  html += '<pre class="after">'+esc(f.after)+'</pre>';
    html += '</div>';
  }
  if ((data.errors||[]).length) html += '<div class="err">일부 청크 분석 실패: '+data.errors.length+'건</div>';
  $('#results').innerHTML = html;
}
</script>
</body>
</html>"""

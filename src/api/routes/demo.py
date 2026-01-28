from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from src.agents.demo_runner import get_demo_leads, run_demo, run_demo_response
from src.agents.demo_storage import create_run, get_run, update_run

router = APIRouter()


class DemoRunRequest(BaseModel):
    lead_id: str | None = None
    lead: dict[str, Any] | None = None
    live_services: bool = False


class DemoRespondRequest(BaseModel):
    run_id: str
    response_type: Literal["positive", "objection", "no_response"]
    content: str | None = None


@router.get("/demo", response_class=HTMLResponse)
async def demo_ui() -> str:
    return _build_demo_html()


@router.get("/demo/leads", response_model=dict[str, Any])
async def list_demo_leads():
    return {"ok": True, "leads": get_demo_leads()}


@router.get("/demo/run/{run_id}", response_model=dict[str, Any])
async def get_demo_run(run_id: str):
    run = get_run(run_id)
    if not run:
        return {"ok": False, "error": "not_found"}
    return {"ok": True, "run": run}


@router.post("/demo/run", response_model=dict[str, Any])
async def start_demo(req: DemoRunRequest):
    lead = req.lead
    if not lead:
        leads = {l["lead_id"]: l for l in get_demo_leads()}
        lead = leads.get(req.lead_id or "")
    if not lead:
        return {"ok": False, "error": "lead_required"}

    result = await run_demo(lead, live_services=req.live_services)
    run = create_run(
        {
            "lead": lead,
            "timeline": result["timeline"],
            "state": result["state"],
            "live_services": req.live_services,
        }
    )
    return {"ok": True, "run": run}


@router.post("/demo/respond", response_model=dict[str, Any])
async def respond_demo(req: DemoRespondRequest):
    run = get_run(req.run_id)
    if not run:
        return {"ok": False, "error": "run_not_found"}

    response_map = {
        "positive": "Yes, I'm interested. Can we schedule a call next week?",
        "objection": "We already have a vendor for fire safety. Thanks.",
        "no_response": "",
    }
    content = req.content if req.content is not None else response_map[req.response_type]
    result = await run_demo_response(
        run["state"],
        response_type=req.response_type,
        response_content=content,
        live_services=bool(run.get("live_services")),
    )
    merged_timeline = list(run.get("timeline", [])) + list(result["timeline"])
    updated = update_run(
        req.run_id,
        {
            "timeline": merged_timeline,
            "state": result["state"],
            "last_response_type": req.response_type,
        },
    )
    return {"ok": True, "run": updated}


def _build_demo_html() -> str:
    return """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>AORO LangGraph Demo Simulator</title>
    <style>
      body {{
        font-family: ui-sans-serif, system-ui, -apple-system, sans-serif;
        margin: 24px;
        color: #111827;
        background: #f9fafb;
      }}
      header {{
        margin-bottom: 16px;
      }}
      .card {{
        background: white;
        border-radius: 10px;
        padding: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        margin-bottom: 16px;
      }}
      .row {{
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
      }}
      label {{
        font-size: 0.9rem;
        font-weight: 600;
      }}
      select, button, textarea {{
        padding: 8px 12px;
        border-radius: 8px;
        border: 1px solid #d1d5db;
        font-size: 0.95rem;
      }}
      button {{
        background: #2563eb;
        color: white;
        border: none;
        cursor: pointer;
      }}
      button.secondary {{
        background: #6b7280;
      }}
      button.warning {{
        background: #dc2626;
      }}
      pre {{
        background: #111827;
        color: #f9fafb;
        padding: 12px;
        border-radius: 8px;
        overflow-x: auto;
      }}
      .timeline {{
        display: grid;
        gap: 12px;
      }}
      .timeline-item {{
        background: #f3f4f6;
        border-radius: 8px;
        padding: 12px;
      }}
      .muted {{
        color: #6b7280;
        font-size: 0.85rem;
      }}
    </style>
  </head>
  <body>
    <header>
      <h2>LangGraph Demo Simulator</h2>
      <p class="muted">Run the workflow, then simulate a reply to see downstream nodes.</p>
    </header>

    <section class="card">
      <div class="row">
        <div>
          <label for="leadSelect">Demo lead</label><br />
          <select id="leadSelect"></select>
        </div>
        <div>
          <label for="liveToggle">Live services</label><br />
          <select id="liveToggle">
            <option value="false" selected>Simulated</option>
            <option value="true">Live (LLM + integrations)</option>
          </select>
        </div>
      </div>
      <div class="row" style="margin-top: 12px;">
        <button onclick="runDemo()">Run Demo</button>
        <button class="secondary" onclick="sendResponse('positive')">Send Positive Reply</button>
        <button class="secondary" onclick="sendResponse('objection')">Send Objection</button>
        <button class="warning" onclick="sendResponse('no_response')">Send No Response</button>
      </div>
      <div class="muted" id="runStatus" style="margin-top: 8px;"></div>
    </section>

    <section class="card">
      <h3>Timeline</h3>
      <div id="timeline" class="timeline"></div>
    </section>

    <section class="card">
      <h3>Final State</h3>
      <pre id="finalState"></pre>
    </section>

    <script>
      let currentRunId = null;
      const leadSelect = document.getElementById("leadSelect");
      const timelineEl = document.getElementById("timeline");
      const finalStateEl = document.getElementById("finalState");
      const runStatusEl = document.getElementById("runStatus");
      const liveToggle = document.getElementById("liveToggle");

      async function loadLeads() {{
        const res = await fetch("/demo/leads");
        const data = await res.json();
        leadSelect.innerHTML = "";
        data.leads.forEach((lead) => {{
          const option = document.createElement("option");
          option.value = lead.lead_id;
          option.textContent = `${{lead.company_name}} • ${{lead.permit_data.permit_type}}`;
          leadSelect.appendChild(option);
        }});
      }}

      function renderTimeline(timeline) {{
        timelineEl.innerHTML = "";
        timeline.forEach((item) => {{
          const container = document.createElement("div");
          container.className = "timeline-item";
          const header = document.createElement("div");
          header.innerHTML = `<strong>${{item.node}}</strong> <span class="muted">(${{
            item.duration_ms
          }}ms)</span>`;
          const changes = document.createElement("pre");
          changes.textContent = JSON.stringify(item.changes, null, 2);
          container.appendChild(header);
          container.appendChild(changes);
          timelineEl.appendChild(container);
        }});
      }}

      function renderState(state) {{
        finalStateEl.textContent = JSON.stringify(state, null, 2);
      }}

      async function runDemo() {{
        runStatusEl.textContent = "Running demo...";
        const res = await fetch("/demo/run", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            lead_id: leadSelect.value,
            live_services: liveToggle.value === "true",
          }}),
        }});
        const data = await res.json();
        if (!data.ok) {{
          runStatusEl.textContent = `Error: ${{data.error}}`;
          return;
        }}
        currentRunId = data.run.run_id;
        runStatusEl.textContent = `Run created: ${{currentRunId}}`;
        renderTimeline(data.run.timeline || []);
        renderState(data.run.state || {{}});
      }}

      async function sendResponse(type) {{
        if (!currentRunId) {{
          runStatusEl.textContent = "Run the demo first.";
          return;
        }}
        runStatusEl.textContent = `Sending ${{type}} response...`;
        const res = await fetch("/demo/respond", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            run_id: currentRunId,
            response_type: type,
          }}),
        }});
        const data = await res.json();
        if (!data.ok) {{
          runStatusEl.textContent = `Error: ${{data.error}}`;
          return;
        }}
        renderTimeline(data.run.timeline || []);
        renderState(data.run.state || {{}});
        runStatusEl.textContent = `Response applied: ${{type}}`;
      }}

      loadLeads();
    </script>
  </body>
 </html>
""".replace("{{", "{").replace("}}", "}")

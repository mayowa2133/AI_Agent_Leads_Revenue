from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from src.api.routes.demo import router as demo_router

app = FastAPI()
app.include_router(demo_router, tags=["demo"])


def main() -> None:
    client = TestClient(app)

    leads_resp = client.get("/demo/leads")
    assert leads_resp.status_code == 200
    leads_data = leads_resp.json()
    assert leads_data["ok"] is True
    assert leads_data["leads"], "Expected demo leads"

    lead_id = leads_data["leads"][0]["lead_id"]
    run_resp = client.post(
        "/demo/run",
        json={"lead_id": lead_id, "live_services": False},
    )
    assert run_resp.status_code == 200
    run_data = run_resp.json()
    assert run_data["ok"] is True
    run_id = run_data["run"]["run_id"]
    assert run_id
    assert run_data["run"]["timeline"], "Expected timeline events"

    respond_resp = client.post(
        "/demo/respond",
        json={"run_id": run_id, "response_type": "positive"},
    )
    assert respond_resp.status_code == 200
    respond_data = respond_resp.json()
    assert respond_data["ok"] is True
    state = respond_data["run"]["state"]
    assert state.get("response_classification") == "positive"
    assert state.get("booking_ready") is True

    print("Demo simulator test passed.")


if __name__ == "__main__":
    main()

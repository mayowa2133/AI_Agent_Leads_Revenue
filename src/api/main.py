from __future__ import annotations

from fastapi import FastAPI

from src.core.observability import init_observability

def create_app() -> FastAPI:
    app = FastAPI(title="AORO", version="0.1.0")

    init_observability()

    from src.api.routes.agents import router as agents_router
    from src.api.routes.leads import router as leads_router
    from src.api.routes.webhooks import router as webhooks_router

    app.include_router(leads_router, prefix="/leads", tags=["leads"])
    app.include_router(agents_router, prefix="/agents", tags=["agents"])
    app.include_router(webhooks_router, prefix="/webhooks", tags=["webhooks"])

    @app.get("/healthz")
    async def healthz():
        return {"ok": True}

    return app


app = create_app()



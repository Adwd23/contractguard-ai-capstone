"""FastAPI production endpoint for ContractGuard AI."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Response, status

from .config import Settings
from .models import AuditStartRequest, ResumeRequest
from .service import AuditConflictError, AuditNotFoundError, ContractGuardService


def create_app(settings: Settings | None = None) -> FastAPI:
    service = ContractGuardService(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        try:
            yield
        finally:
            service.close()

    app = FastAPI(
        title="ContractGuard AI",
        version="1.0.0",
        description="Secure, resumable multi-agent vendor-contract audit service.",
        lifespan=lifespan,
    )
    app.state.contractguard_service = service

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "contractguard-ai"}

    @app.get("/graph")
    def graph() -> dict:
        return service.graph_spec()

    @app.post("/audits", status_code=status.HTTP_201_CREATED)
    def start_audit(request: AuditStartRequest) -> dict:
        try:
            return service.start(request)
        except AuditConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/audits/{thread_id}")
    def get_audit(thread_id: str) -> dict:
        try:
            return service.get(thread_id)
        except AuditNotFoundError as exc:
            raise HTTPException(status_code=404, detail=f"Unknown thread: {thread_id}") from exc

    @app.get("/audits/{thread_id}/history")
    def get_history(thread_id: str) -> list[dict]:
        try:
            return service.history(thread_id)
        except AuditNotFoundError as exc:
            raise HTTPException(status_code=404, detail=f"Unknown thread: {thread_id}") from exc

    @app.post("/audits/{thread_id}/resume")
    def resume_audit(thread_id: str, request: ResumeRequest) -> dict:
        try:
            return service.resume(thread_id, request)
        except AuditNotFoundError as exc:
            raise HTTPException(status_code=404, detail=f"Unknown thread: {thread_id}") from exc
        except AuditConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/metrics", include_in_schema=False)
    def metrics() -> Response:
        return Response(service.observability.metrics_bytes(), media_type="text/plain; version=0.0.4")

    return app


app = create_app()

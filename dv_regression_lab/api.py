from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .analytics import build_review_pack, build_suite_trend
from .dashboard import render_dashboard
from .orchestrator import list_example_suites, resolve_suite_path, run_suite
from .simulator import available_simulators
from .store import RunStore
from .taxonomy import FAILURE_TAXONOMY


class RunRequest(BaseModel):
    suite_path: str


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_store_root() -> Path:
    raw = os.getenv("DV_REGRESSION_LAB_STORE")
    if raw:
        return Path(raw).resolve()
    return project_root() / ".data"


def create_app(store_root: Optional[Path] = None) -> FastAPI:
    store = RunStore((store_root or default_store_root()).resolve())
    root = project_root()

    app = FastAPI(
        title="DV Regression Lab",
        version="0.1.0",
        description="Local-first RTL/DV regression control tower.",
    )

    @app.get("/", response_class=HTMLResponse)
    def home() -> str:
        return render_dashboard(store.list_runs(limit=8), list_example_suites(root))

    @app.get("/v1/meta")
    def meta() -> dict:
        return {
            "service": "dv-regression-lab",
            "role_fit": ["design-platform", "design-verification"],
            "store_root": str(store.root),
            "example_suite_count": len(list_example_suites(root)),
            "available_simulators": available_simulators(),
            "reviewer_fast_path": [
                "/v1/proof-map",
                "/v1/meta",
                "/v1/runs",
                "/v1/runs/{run_id}/review-pack",
                "/v1/suites/{suite_id}/trend",
            ],
            "links": {
                "proof_map": "/v1/proof-map",
                "runs": "/v1/runs",
            },
        }

    @app.get("/v1/proof-map")
    def proof_map() -> dict:
        latest_runs = store.list_runs(limit=1)
        latest_run_id = latest_runs[0].run_id if latest_runs else None
        latest_suite_id = latest_runs[0].suite_id if latest_runs else "soc_smoke_matrix"
        return {
            "service": "dv-regression-lab",
            "contract_version": "dv-regression-proof-map-v1",
            "headline": "Front-door proof map for choosing the shortest regression review path.",
            "reviewer_fast_path": [
                "/v1/proof-map",
                "/v1/meta",
                "/v1/runs",
                f"/v1/runs/{latest_run_id}/review-pack"
                if latest_run_id
                else "/v1/runs/{run_id}/review-pack",
                f"/v1/suites/{latest_suite_id}/trend",
            ],
            "decision_support": [
                {
                    "need": "environment simulator support and role-fit first",
                    "route": "/v1/meta",
                },
                {
                    "need": "promotion posture and next actions for one run",
                    "route": f"/v1/runs/{latest_run_id}/review-pack"
                    if latest_run_id
                    else "/v1/runs/{run_id}/review-pack",
                },
                {
                    "need": "nightly drift and recurring failures across history",
                    "route": f"/v1/suites/{latest_suite_id}/trend",
                },
            ],
        }

    @app.get("/v1/failure-taxonomy")
    def failure_taxonomy() -> dict:
        return FAILURE_TAXONOMY

    @app.get("/v1/suites/examples")
    def suites_examples() -> list:
        return list_example_suites(root)

    @app.get("/v1/runs")
    def runs() -> list:
        return [run.summary() for run in store.list_runs()]

    @app.post("/v1/runs")
    def create_run(request: RunRequest) -> dict:
        suite_path = resolve_suite_path(root, request.suite_path)
        if not suite_path.exists():
            raise HTTPException(status_code=404, detail=f"Suite not found: {suite_path}")
        run = run_suite(suite_path, store)
        return run.to_dict()

    @app.get("/v1/runs/{run_id}")
    def run_detail(run_id: str) -> dict:
        run = store.load_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
        return run.to_dict()

    @app.get("/v1/runs/{run_id}/triage")
    def run_triage(run_id: str) -> dict:
        run = store.load_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
        if not run.triage:
            raise HTTPException(status_code=404, detail=f"Triage not found for run: {run_id}")
        return run.triage.to_dict()

    @app.get("/v1/runs/{run_id}/review-pack")
    def run_review_pack(run_id: str) -> dict:
        run = store.load_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
        return build_review_pack(run)

    @app.get("/v1/suites/{suite_id}/trend")
    def suite_trend(suite_id: str) -> dict:
        runs = store.list_runs_for_suite(suite_id)
        if not runs:
            raise HTTPException(status_code=404, detail=f"No runs found for suite: {suite_id}")
        return build_suite_trend(runs)

    return app


app = create_app()

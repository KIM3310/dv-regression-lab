from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import uvicorn

from .analytics import build_review_pack, build_suite_trend
from .api import default_store_root, project_root
from .orchestrator import resolve_suite_path, run_suite
from .store import RunStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DV Regression Lab CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="Run a regression suite")
    run_parser.add_argument("suite_path", help="Suite YAML path")
    run_parser.add_argument("--store", default=str(default_store_root()), help="Store root path")

    list_parser = sub.add_parser("list-runs", help="List stored regression runs")
    list_parser.add_argument("--store", default=str(default_store_root()), help="Store root path")

    triage_parser = sub.add_parser("triage", help="Print triage for a run")
    triage_parser.add_argument("run_id", help="Regression run id")
    triage_parser.add_argument("--store", default=str(default_store_root()), help="Store root path")

    review_pack_parser = sub.add_parser("review-pack", help="Print review pack for a run")
    review_pack_parser.add_argument("run_id", help="Regression run id")
    review_pack_parser.add_argument(
        "--store", default=str(default_store_root()), help="Store root path"
    )

    trend_parser = sub.add_parser("suite-trend", help="Print trend summary for a suite")
    trend_parser.add_argument("suite_id", help="Suite identifier")
    trend_parser.add_argument("--store", default=str(default_store_root()), help="Store root path")

    serve_parser = sub.add_parser("serve", help="Serve the API")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8787)
    serve_parser.add_argument("--store", default=str(default_store_root()), help="Store root path")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "run":
        store = RunStore(Path(args.store).resolve())
        suite_path = resolve_suite_path(project_root(), args.suite_path)
        run = run_suite(suite_path, store)
        print(json.dumps(run.to_dict(), indent=2))
        return

    if args.command == "list-runs":
        store = RunStore(Path(args.store).resolve())
        print(json.dumps([run.summary() for run in store.list_runs()], indent=2))
        return

    if args.command == "triage":
        store = RunStore(Path(args.store).resolve())
        run = store.load_run(args.run_id)
        if not run or not run.triage:
            raise SystemExit(f"Triage not found for run: {args.run_id}")
        print(json.dumps(run.triage.to_dict(), indent=2))
        return

    if args.command == "review-pack":
        store = RunStore(Path(args.store).resolve())
        run = store.load_run(args.run_id)
        if not run:
            raise SystemExit(f"Run not found: {args.run_id}")
        print(json.dumps(build_review_pack(run), indent=2))
        return

    if args.command == "suite-trend":
        store = RunStore(Path(args.store).resolve())
        runs = store.list_runs_for_suite(args.suite_id)
        if not runs:
            raise SystemExit(f"No runs found for suite: {args.suite_id}")
        print(json.dumps(build_suite_trend(runs), indent=2))
        return

    if args.command == "serve":
        os.environ["DV_REGRESSION_LAB_STORE"] = str(Path(args.store).resolve())
        uvicorn.run("dv_regression_lab.api:app", host=args.host, port=args.port, reload=False)
        return


if __name__ == "__main__":
    main()

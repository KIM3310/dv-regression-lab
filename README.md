# DV Regression Lab

> **Archived / Supporting repo**  
> The active runtime reliability and regression-proof story is now centered on **stage-pilot**.  
> Keep this repo as historical proof for the dedicated DV regression control-tower lane.

[![CI](https://github.com/KIM3310/dv-regression-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/KIM3310/dv-regression-lab/actions/workflows/ci.yml)

`dv-regression-lab` is a local-first regression control tower for RTL and Design Verification workflows.
It is built to answer a very specific platform question:

> If a DV team hands me a nightly regression, can I orchestrate it, preserve evidence, classify failures,
> detect flaky tests, and hand back operator-friendly triage without pretending I designed the silicon myself?

This repo is the answer.

GitHub Actions continuously checks lint, unit tests, mock regressions, and the real `iverilog` smoke path.

## Review this first

1. `GET /v1/proof-map` — choose whether the first proof should be meta, one run, or suite trend
2. `GET /v1/meta` — confirm simulator availability and platform role-fit
3. `GET /v1/runs` — inspect recent regression history
4. `GET /v1/runs/{run_id}/review-pack` — read promotion posture and next actions
5. `GET /v1/suites/{suite_id}/trend` — inspect recurring failure drift across nightly history

## Why this project exists

For `Design Platform & RTL` and `Design Verification` roles, generic AI demos are not enough. Hiring teams want
to see platform thinking around:

- regression execution
- artifact retention
- reproducible failure signatures
- rerun prioritization
- flaky detection
- operator-facing APIs

`dv-regression-lab` turns those ideas into an actual working service.

## What it does

- Runs RTL/DV regression suites from YAML specs
- Supports a deterministic `mock` simulator adapter for local demos
- Supports a real `iverilog` adapter for compile-and-run RTL smoke checks
- Persists run history and artifacts to a local store
- Builds a failure taxonomy for compile, timeout, assertion, protocol, and X-propagation classes
- Flags flaky cases across repeated runs
- Produces operator-facing review packs for promotion and triage meetings
- Tracks suite-level trend deltas and recurring failing cases across nightly history
- Surfaces hot design units touched by failing tests
- Exposes a FastAPI control plane and a CLI
- Ships with example suites that look like real SoC verification workloads

## Platform story

This is not a toy chatbot with a semiconductor label on top. The repo is deliberately shaped like a real internal DV platform:

- `suite spec` -> describes tests, seeds, owners, design units, and expected runtime
- `orchestrator` -> schedules cases and writes artifacts
- `simulator adapter` -> can stay local with `mock` or execute checked-in RTL/tb sources through `iverilog`
- `triage engine` -> classifies failures and recommends reruns
- `review pack` -> packages promotion posture, riskiest cases, and next actions
- `trend view` -> compares nightly history for one suite
- `API + dashboard` -> gives reviewers a control-plane surface instead of a notebook dump

## Quick start

```bash
cd dv-regression-lab
python3 -m pip install -e ".[dev]"
python3 -m dv_regression_lab run examples/soc_smoke.yaml
python3 -m dv_regression_lab serve --port 8787
```

Then open `http://127.0.0.1:8787`.

## Example commands

Run a regression:

```bash
python3 -m dv_regression_lab run examples/soc_smoke.yaml
```

Run the real RTL smoke example when `iverilog` and `vvp` are installed:

```bash
python3 -m dv_regression_lab run examples/rtl_smoke_iverilog.yaml
```

Inspect stored runs:

```bash
python3 -m dv_regression_lab list-runs
```

Read triage for one run:

```bash
python3 -m dv_regression_lab triage <run-id>
```

Read the promotion-oriented review pack:

```bash
python3 -m dv_regression_lab review-pack <run-id>
```

Inspect suite trend across stored history:

```bash
python3 -m dv_regression_lab suite-trend soc_smoke_matrix
```

Serve the API:

```bash
python3 -m dv_regression_lab serve --host 127.0.0.1 --port 8787
```

If your user bin is already on `PATH`, the installed shortcut `dvrl` works too.

## API surface

- `GET /`
- `GET /v1/meta`
- `GET /v1/proof-map`
- `GET /v1/failure-taxonomy`
- `GET /v1/suites/examples`
- `GET /v1/runs`
- `POST /v1/runs`
- `GET /v1/runs/{run_id}`
- `GET /v1/runs/{run_id}/triage`
- `GET /v1/runs/{run_id}/review-pack`
- `GET /v1/suites/{suite_id}/trend`

`GET /v1/meta` also reports detected simulator availability so reviewers can see whether the environment can execute `mock`, `iverilog`, or both.

Example run request:

```json
{
  "suite_path": "examples/soc_smoke.yaml"
}
```

## Example output

When a run finishes, the triage report includes:

- failure bucket counts
- rerun candidates
- flaky cases
- hot design units
- operator brief

The review pack adds:

- promotion posture
- riskiest failing cases
- recurring failure signatures
- concrete next actions for the owning team

Representative operator brief:

```text
4/6 cases failed. quality gate=hold.
Compile failures block promotion and should be fixed before reruns.
Flaky cases detected across run history. Stabilize seeds before claiming closure.
```

## Example suites

- [examples/soc_smoke.yaml](examples/soc_smoke.yaml)
- [examples/power_intent_nightly.yaml](examples/power_intent_nightly.yaml)
- [examples/rtl_smoke_iverilog.yaml](examples/rtl_smoke_iverilog.yaml)

## Repo layout

- [dv_regression_lab/api.py](dv_regression_lab/api.py)
- [dv_regression_lab/orchestrator.py](dv_regression_lab/orchestrator.py)
- [dv_regression_lab/simulator.py](dv_regression_lab/simulator.py)
- [dv_regression_lab/taxonomy.py](dv_regression_lab/taxonomy.py)
- [dv_regression_lab/store.py](dv_regression_lab/store.py)
- [tests/test_api.py](tests/test_api.py)
- [rtl/irq_router.sv](rtl/irq_router.sv)
- [tb/tb_irq_router_smoke.sv](tb/tb_irq_router_smoke.sv)

## What to say in interview

Use this repo to position yourself as someone who can support semiconductor design teams with platform software:

- "I built a regression control plane instead of another generic dashboard."
- "The core value is reproducibility: suite specs, stored artifacts, failure signatures, and rerun logic."
- "I treated DV failures as platform data and operator workflow problems."
- "The simulator is abstracted so the same control layer can wrap mock, shell, or real EDA flows."
- "I added review-pack and trend surfaces because design organizations care about promotion decisions, not just raw test logs."
- "I moved beyond a mock-only demo and added a real Icarus Verilog execution path with checked-in RTL and testbenches."

## Why This Fits Platform Roles

This repo is strongest for:

- `Design Platform & RTL`
- `Design Verification`
- internal CAD / productivity platform teams around regression, triage, and evidence retention

It is intentionally not pretending to be:

- an RTL design repo
- a UVM library
- a physical design flow

That makes the positioning cleaner. It shows platform leverage around semiconductor verification work.

## Current scope

The repo now ships with two execution paths:

- `mock` for deterministic demos
- `iverilog` for real compile-and-run RTL smoke cases

The next extension is adding `verilator` or internal farm-wrapper commands behind the same adapter interface.

## Tooling Note

This repo includes tests that validate the `iverilog` adapter with fake shims, so CI can still verify command construction
when the actual simulator is absent. To run the real RTL path locally, install Icarus Verilog so both `iverilog` and `vvp`
are on `PATH`, then run:

```bash
python3 -m dv_regression_lab run examples/rtl_smoke_iverilog.yaml
```

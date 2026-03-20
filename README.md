# DV Regression Lab

`dv-regression-lab` is a local-first regression control tower for RTL and Design Verification workflows.
It is built to answer a very specific platform question:

> If a DV team hands me a nightly regression, can I orchestrate it, preserve evidence, classify failures,
> detect flaky tests, and hand back operator-friendly triage without pretending I designed the silicon myself?

This repo is the answer.

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
- `simulator adapter` -> can stay local with `mock` or be swapped for real simulator commands later
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
- `GET /v1/failure-taxonomy`
- `GET /v1/suites/examples`
- `GET /v1/runs`
- `POST /v1/runs`
- `GET /v1/runs/{run_id}`
- `GET /v1/runs/{run_id}/triage`
- `GET /v1/runs/{run_id}/review-pack`
- `GET /v1/suites/{suite_id}/trend`

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

## Repo layout

- [dv_regression_lab/api.py](dv_regression_lab/api.py)
- [dv_regression_lab/orchestrator.py](dv_regression_lab/orchestrator.py)
- [dv_regression_lab/simulator.py](dv_regression_lab/simulator.py)
- [dv_regression_lab/taxonomy.py](dv_regression_lab/taxonomy.py)
- [dv_regression_lab/store.py](dv_regression_lab/store.py)
- [tests/test_api.py](tests/test_api.py)

## What to say in interview

Use this repo to position yourself as someone who can support semiconductor design teams with platform software:

- "I built a regression control plane instead of another generic dashboard."
- "The core value is reproducibility: suite specs, stored artifacts, failure signatures, and rerun logic."
- "I treated DV failures as platform data and operator workflow problems."
- "The simulator is abstracted so the same control layer can wrap mock, shell, or real EDA flows."
- "I added review-pack and trend surfaces because design organizations care about promotion decisions, not just raw test logs."

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

The checked-in adapter is `mock` so the project runs anywhere. The extension point is intentional:
the next step is wiring real `iverilog`, `verilator`, or internal shell-based flows behind the same adapter interface.

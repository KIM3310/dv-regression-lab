# Review Guide - DV Regression Lab

Updated: 2026-05-30

This repository is archived as a supporting proof. Review it for the reusable pattern, domain evidence, and portfolio relationship; do not treat it as the current flagship unless it is explicitly revived.

## Summary

| Field | Notes |
|---|---|
| Repository | `dv-regression-lab` |
| Status | Archived supporting repository |
| Lane | Semiconductor DV regression control tower |
| Primary reader | ASIC verification managers, EDA platform teams, CI owners, and silicon program leads. |
| Why it exists | DV teams need a clearer loop from nightly regression evidence to flaky-test triage and operator handoff. |
| Stack | Python |

## Open First

1. Read the README archived-status note and relationship to active repositories.
2. Inspect `docs/monetization-playbook.md` for the buyer lane and offer ladder.
3. Use the commands below to confirm the proof surface still has a review path.
4. Check CI workflows before making quality claims.
5. Keep the archived status visible in any portfolio conversation.

## Checks

| Purpose | Command |
|---|---|
| Full local gate | `make verify` |
| Test suite | `make test` |

## CI

- .github/workflows/architecture-blueprint.yml
- .github/workflows/ci.yml
- .github/workflows/dependency-review.yml
- .github/workflows/repository-health.yml
- .github/workflows/repository-surface.yml
- .github/workflows/secret-scan.yml

## Evidence

- Regression examples remain synthetic or permission-safe
- Flake and failure taxonomy is explicit
- Stage-pilot relationship is described as the active runtime lane

## Commercial Notes

| Possible offer | Working price assumption | Scope |
|---|---|---|
| Regression triage assessment | $8k-$20k | Review current regression logs, flake posture, and evidence retention gaps. |
| DV control-tower pilot | $40k-$150k | Adapt the scheduler, classifier, and evidence pack to one verification block. |
| EDA workflow extension | $100k+/year | License or maintain the triage workflow as part of a platform toolchain. |

## Boundaries

- Do not claim silicon design ownership
- Keep customer logs out of public artifacts
- Avoid production readiness claims without partner validation

## Useful Metrics

- Assessment calls
- Nightly triage time saved
- Flake detection precision
- Pilot renewal

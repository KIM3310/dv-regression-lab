from pathlib import Path

from fastapi.testclient import TestClient

from dv_regression_lab.api import create_app


def test_api_runs_suite_and_returns_triage(tmp_path):
    app = create_app(tmp_path / "store")
    client = TestClient(app)
    project_root = Path(__file__).resolve().parents[1]
    suite_path = project_root / "examples" / "soc_smoke.yaml"

    meta_response = client.get("/v1/meta")
    assert meta_response.status_code == 200
    assert meta_response.json()["service"] == "dv-regression-lab"

    create_response = client.post("/v1/runs", json={"suite_path": str(suite_path)})
    assert create_response.status_code == 200
    payload = create_response.json()
    run_id = payload["run_id"]
    assert payload["case_total"] == 6

    triage_response = client.get(f"/v1/runs/{run_id}/triage")
    assert triage_response.status_code == 200
    triage = triage_response.json()
    assert "failure_buckets" in triage
    assert "operator_brief" in triage

    review_pack_response = client.get(f"/v1/runs/{run_id}/review-pack")
    assert review_pack_response.status_code == 200
    review_pack = review_pack_response.json()
    assert review_pack["promotion_posture"] == "blocked"
    assert "next_actions" in review_pack

    trend_response = client.get("/v1/suites/soc_smoke_matrix/trend")
    assert trend_response.status_code == 200
    trend = trend_response.json()
    assert trend["suite_id"] == "soc_smoke_matrix"
    assert trend["run_count"] == 1


def test_examples_endpoint_lists_bundled_suites(tmp_path):
    app = create_app(tmp_path / "store")
    client = TestClient(app)

    response = client.get("/v1/suites/examples")
    assert response.status_code == 200
    suite_ids = {item["suite_id"] for item in response.json()}
    assert "soc_smoke_matrix" in suite_ids
    assert "power_intent_nightly" in suite_ids

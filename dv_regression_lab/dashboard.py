from __future__ import annotations

from typing import List, Optional

from .analytics import build_review_pack, build_suite_trend
from .models import RegressionRun


def render_dashboard(runs: List[RegressionRun], example_suites: List[dict]) -> str:
    latest = runs[0] if runs else None
    latest_summary = ""
    review_pack_html = ""
    trend_html = ""
    if latest:
        review_pack = build_review_pack(latest)
        trend = build_suite_trend([run for run in runs if run.suite_id == latest.suite_id])
        operator_brief_html = "".join(f"<li>{line}</li>" for line in review_pack["operator_brief"])
        flaky_cases_label = ", ".join(review_pack["flaky_cases"]) or "none"
        recurring_failures_html = (
            "".join(
                f"<li>{item['case_id']}: failed in {item['failed_runs']} run(s)</li>"
                for item in trend["recurring_failures"][:4]
            )
            or "<li>No recurring failures yet.</li>"
        )
        latest_summary = f"""
      <section class="hero-grid">
        <article class="card metric">
          <span class="label">Latest Run</span>
          <h2>{latest.title}</h2>
          <p>{latest.run_id}</p>
        </article>
        <article class="card metric">
          <span class="label">Pass Rate</span>
          <h2>{latest.pass_rate:.1%}</h2>
          <p>{latest.passed}/{latest.case_total} passed</p>
        </article>
        <article class="card metric">
          <span class="label">Quality Gate</span>
          <h2>{latest.quality_gate.upper()}</h2>
          <p>{latest.failed} failures, {latest.duration_sec:.2f}s runtime</p>
        </article>
      </section>
      """
        review_pack_html = f"""
      <article class="card">
        <span class="badge">Review Pack</span>
        <h3>{review_pack["promotion_posture"]}</h3>
        <p class="muted">Latest operator posture for {latest.suite_id}.</p>
        <ul class="stack">
          {operator_brief_html}
        </ul>
        <p class="muted">Flaky cases: {flaky_cases_label}</p>
      </article>
        """
        trend_html = f"""
      <article class="card">
        <span class="badge">Trend</span>
        <h3>{latest.suite_id}</h3>
        <p class="muted">Runs: {trend["run_count"]} · pass-rate delta: {_format_delta(trend["pass_rate_delta"])}</p>
        <ul class="stack">
          {recurring_failures_html}
        </ul>
      </article>
        """

    example_cards = "".join(
        f"""
    <article class="card">
      <span class="badge">{item["simulator_kind"]}</span>
      <h3>{item["suite_id"]}</h3>
      <p>{item["title"]}</p>
      <small>{item["case_total"]} cases · owner={item["owner"]}</small>
    </article>
    """
        for item in example_suites
    )

    recent_rows = "".join(
        f"""
    <tr>
      <td>{run.run_id}</td>
      <td>{run.title}</td>
      <td>{run.pass_rate:.1%}</td>
      <td>{run.quality_gate}</td>
      <td>{run.failed}</td>
    </tr>
    """
        for run in runs[:8]
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>DV Regression Lab</title>
  <style>
    :root {{
      --bg: #08111f;
      --panel: rgba(9, 24, 42, 0.8);
      --panel-border: rgba(122, 215, 255, 0.18);
      --text: #eff7ff;
      --muted: #9bb7cf;
      --accent: #70f0ff;
      --accent-2: #ff9a52;
      --accent-3: #96ff9c;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "IBM Plex Sans", "Avenir Next", "Segoe UI", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(112, 240, 255, 0.16), transparent 30%),
        radial-gradient(circle at top right, rgba(255, 154, 82, 0.14), transparent 28%),
        linear-gradient(180deg, #06101d, var(--bg));
      min-height: 100vh;
    }}
    main {{
      width: min(1120px, calc(100% - 32px));
      margin: 0 auto;
      padding: 48px 0 64px;
    }}
    .eyebrow {{
      color: var(--accent);
      letter-spacing: 0.18em;
      text-transform: uppercase;
      font-size: 12px;
      font-weight: 700;
    }}
    h1 {{
      margin: 10px 0 12px;
      font-size: clamp(2.2rem, 5vw, 4.4rem);
      line-height: 0.95;
      max-width: 10ch;
    }}
    .lead {{
      max-width: 62ch;
      color: var(--muted);
      line-height: 1.7;
      margin-bottom: 28px;
    }}
    .hero-grid, .card-grid {{
      display: grid;
      gap: 16px;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    }}
    .hero-grid {{ margin: 24px 0 36px; }}
    .card {{
      border: 1px solid var(--panel-border);
      background: var(--panel);
      border-radius: 20px;
      padding: 20px;
      box-shadow: 0 24px 80px rgba(0, 0, 0, 0.24);
      backdrop-filter: blur(12px);
    }}
    .metric h2, .card h3 {{
      margin: 8px 0;
    }}
    .badge, .label {{
      display: inline-block;
      font-size: 12px;
      font-weight: 700;
      border-radius: 999px;
      padding: 6px 10px;
      background: rgba(112, 240, 255, 0.12);
      color: var(--accent);
    }}
    .split {{
      display: grid;
      grid-template-columns: 1.2fr 1fr;
      gap: 16px;
      margin-top: 24px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
    }}
    th, td {{
      text-align: left;
      padding: 12px 10px;
      border-bottom: 1px solid rgba(155, 183, 207, 0.12);
      font-size: 14px;
    }}
    th {{ color: var(--muted); }}
    .muted {{ color: var(--muted); }}
    .callout {{
      border-left: 4px solid var(--accent-2);
      padding-left: 16px;
      color: var(--muted);
      line-height: 1.7;
    }}
    .stack {{
      padding-left: 18px;
      line-height: 1.8;
      color: var(--muted);
    }}
    code {{
      font-family: "IBM Plex Mono", "SFMono-Regular", monospace;
      color: var(--accent-3);
    }}
    @media (max-width: 860px) {{
      .split {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <span class="eyebrow">Design Verification Platform</span>
    <h1>Regression control tower for RTL and DV teams.</h1>
    <p class="lead">
      Run suite specs, preserve artifacts, classify failures, detect flaky cases, and return an operator-ready triage pack.
      This is a platform portfolio project for semiconductor design organizations, not a generic AI wrapper.
    </p>
    {latest_summary}
    <section class="card-grid">
      {example_cards}
    </section>
    <section class="split">
      <article class="card">
        <span class="badge">Recent Runs</span>
        <table>
          <thead>
            <tr>
              <th>Run</th>
              <th>Suite</th>
              <th>Pass Rate</th>
              <th>Gate</th>
              <th>Failures</th>
            </tr>
          </thead>
          <tbody>
            {recent_rows or '<tr><td colspan="5">No runs recorded yet.</td></tr>'}
          </tbody>
        </table>
      </article>
      <article class="card">
        <span class="badge">API</span>
        <p class="callout">
          Use <code>POST /v1/runs</code> with a suite path such as
          <code>examples/soc_smoke.yaml</code>. The service records run history under
          <code>.data/runs</code> and stores case artifacts under <code>.data/artifacts</code>.
        </p>
        <p class="callout">
          Triage surfaces failure buckets, rerun candidates, flaky cases, and hot design units so a reviewer can move from
          "something failed" to "what should we do next" without digging through raw logs first.
        </p>
      </article>
    </section>
    <section class="hero-grid">
      {review_pack_html}
      {trend_html}
    </section>
  </main>
</body>
</html>"""


def _format_delta(delta: Optional[float]) -> str:
    if delta is None:
        return "n/a"
    if delta > 0:
        return f"+{delta:.1%}"
    return f"{delta:.1%}"

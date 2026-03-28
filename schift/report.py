"""Bench report — MapleStory recalibration UI style."""

from __future__ import annotations

from pathlib import Path
from typing import Optional


def generate_report_html(
    bench_data: dict,
    output_path: Optional[str | Path] = None,
) -> str:
    source_model = bench_data.get("source_model", "Current Model")
    target_model = bench_data.get("target_model", "Target Model")
    verdict = bench_data.get("verdict", "SAFE")
    original = bench_data.get("original", {})
    projected = bench_data.get("projected", {})

    verdict_color = {"SAFE": "#a3e635", "WARN": "#fbbf24", "FAIL": "#f87171"}.get(verdict, "#94a3b8")

    metrics = [
        ("Top-1 Accuracy", "R@1"),
        ("Top-10 Recall", "R@10"),
        ("Top-100 Recall", "R@100"),
        ("Ranking Quality", "nDCG@10"),
    ]

    def make_rows(vals, color):
        rows = ""
        for label, key in metrics:
            v = vals.get(key, 0)
            rows += f"""
          <div class="stat-row">
            <span class="stat-icon" style="background:{color};"></span>
            <span class="stat-text">{label} <strong>{v:.1%}</strong></span>
          </div>"""
        return rows

    # Delta
    before_r10 = original.get("R@10", 0)
    after_r10 = projected.get("R@10", 0)
    delta = after_r10 - before_r10
    delta_sign = "+" if delta >= 0 else ""
    delta_pct = f"{delta_sign}{delta:.1%}"

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Schift Report</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    font-family: 'Inter', sans-serif;
    background: #15171e;
    color: #c8ccd4;
    min-height: 100vh;
    display: flex;
    justify-content: center;
    padding: 48px 16px;
  }}
  .wrap {{ width: 640px; }}

  .panels {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
    margin-bottom: 16px;
  }}
  .panel {{
    background: #1c1f2b;
    border: 1px solid #2a2e3d;
    border-radius: 10px;
    overflow: hidden;
  }}
  .panel-label {{
    padding: 12px 18px;
    font-size: 14px;
    font-weight: 800;
    letter-spacing: 1px;
  }}
  .panel.before .panel-label {{
    color: #e2e847;
  }}
  .panel.after .panel-label {{
    color: #a3e635;
  }}
  .tier {{
    margin: 0 18px;
    padding: 8px 0;
    text-align: center;
    font-size: 13px;
    font-weight: 700;
    border-radius: 4px;
    letter-spacing: 0.5px;
  }}
  .panel.before .tier {{
    background: #e2e847;
    color: #1c1f2b;
  }}
  .panel.after .tier {{
    background: #a3e635;
    color: #1c1f2b;
  }}
  .stats {{
    padding: 16px 18px;
  }}
  .stat-row {{
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 7px 0;
    font-size: 14px;
  }}
  .stat-icon {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    display: inline-block;
    flex-shrink: 0;
  }}
  .stat-text {{
    color: #c8ccd4;
  }}
  .stat-text strong {{
    color: #f0f0f0;
  }}

  /* Bottom box — delta */
  .delta-section {{
    background: #1c1f2b;
    border: 1px solid #2a2e3d;
    border-radius: 10px;
    overflow: hidden;
  }}
  .delta-panels {{
    display: grid;
    grid-template-columns: 1fr 1fr;
  }}
  .delta-cell {{
    padding: 20px;
    text-align: center;
  }}
  .delta-cell.before {{
    border-right: 1px solid #2a2e3d;
  }}
  .delta-cell .label {{
    font-size: 12px;
    color: #64748b;
    margin-bottom: 8px;
    font-weight: 600;
  }}
  .delta-cell .number {{
    font-size: 28px;
    font-weight: 800;
    font-variant-numeric: tabular-nums;
  }}
  .delta-cell.before .number {{
    color: #64748b;
  }}
  .delta-cell.after .number {{
    color: {verdict_color};
  }}
  .delta-cell.after .label {{
    color: {verdict_color};
  }}

  /* Verdict bar */
  .verdict-bar {{
    padding: 14px;
    text-align: center;
    font-size: 13px;
    color: #64748b;
    border-top: 1px solid #2a2e3d;
  }}
  .verdict-bar strong {{
    color: {verdict_color};
  }}
</style>
</head>
<body>
<div class="wrap">

  <div class="panels">
    <div class="panel before">
      <div class="panel-label">BEFORE</div>
      <div class="tier">{source_model}</div>
      <div class="stats">{make_rows(original, "#e2e847")}</div>
    </div>

    <div class="panel after">
      <div class="panel-label">AFTER</div>
      <div class="tier">{target_model}</div>
      <div class="stats">{make_rows(projected, "#a3e635")}</div>
    </div>
  </div>

  <div class="delta-section">
    <div class="delta-panels">
      <div class="delta-cell before">
        <div class="label">Search Quality Change</div>
        <div class="number">0</div>
      </div>
      <div class="delta-cell after">
        <div class="label">Search Quality Change</div>
        <div class="number">{delta_pct}</div>
      </div>
    </div>
    <div class="verdict-bar">
      Switching to <strong>AFTER</strong> will apply the new configuration.
    </div>
  </div>

</div>
</body>
</html>"""

    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html)
    return html


def demo_report(output_path: str = "bench_report.html") -> str:
    data = {
        "source_model": "openai/text-embedding-3-small",
        "target_model": "google/gemini-embedding-001",
        "verdict": "SAFE",
        "original": {"R@1": 0.5883, "R@10": 0.8542, "R@100": 0.9733, "nDCG@10": 0.7296},
        "projected": {"R@1": 0.6052, "R@10": 0.9382, "R@100": 0.9933, "nDCG@10": 0.7925},
    }
    return generate_report_html(data, output_path)

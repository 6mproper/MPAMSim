from __future__ import annotations

import argparse
import csv
import html
import json
from pathlib import Path
from typing import Dict, Iterable, List


COLORS = ["#146C94", "#D35400", "#2E8B57", "#8E44AD", "#C0392B", "#5D6D7E"]


def _read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _line_chart(rows: List[Dict[str, str]], y_key: str, title: str) -> str:
    points_by_partid: Dict[str, List[tuple]] = {}
    for row in rows:
        try:
            points_by_partid.setdefault(row["partid"], []).append(
                (float(row["time_ns"]), float(row[y_key]))
            )
        except (KeyError, TypeError, ValueError):
            continue
    if not points_by_partid:
        return "<p class='empty'>No data</p>"
    all_points = [point for points in points_by_partid.values() for point in points]
    min_x = min(point[0] for point in all_points)
    max_x = max(point[0] for point in all_points)
    min_y = min(0.0, min(point[1] for point in all_points))
    max_y = max(point[1] for point in all_points)
    width, height, pad = 760, 260, 38

    def sx(value: float) -> float:
        return pad + (value - min_x) / max(1e-9, max_x - min_x) * (width - 2 * pad)

    def sy(value: float) -> float:
        return height - pad - (value - min_y) / max(1e-9, max_y - min_y) * (height - 2 * pad)

    paths = []
    legends = []
    for index, (partid, points) in enumerate(sorted(points_by_partid.items())):
        color = COLORS[index % len(COLORS)]
        path = " ".join(
            ("M" if idx == 0 else "L") + "{:.1f},{:.1f}".format(sx(x), sy(y))
            for idx, (x, y) in enumerate(points)
        )
        paths.append("<path d='{}' fill='none' stroke='{}' stroke-width='2'/>".format(path, color))
        legends.append(
            "<span><i style='background:{}'></i>PARTID {}</span>".format(color, html.escape(partid))
        )
    return """
    <div class="chart">
      <h3>{}</h3>
      <svg viewBox="0 0 {} {}" role="img" aria-label="{}">
        <line x1="{}" y1="{}" x2="{}" y2="{}" stroke="#8b949e"/>
        <line x1="{}" y1="{}" x2="{}" y2="{}" stroke="#8b949e"/>
        {}
        <text x="{}" y="{}">{:.2f}</text>
        <text x="{}" y="{}">{:.2f}</text>
      </svg>
      <div class="legend">{}</div>
    </div>
    """.format(
        html.escape(title),
        width,
        height,
        html.escape(title),
        pad,
        height - pad,
        width - pad,
        height - pad,
        pad,
        pad,
        pad,
        height - pad,
        "".join(paths),
        4,
        pad + 4,
        max_y,
        4,
        height - pad,
        min_y,
        "".join(legends),
    )


def _table(rows: Iterable[Dict[str, object]], limit: int = 20) -> str:
    rows = list(rows)[:limit]
    if not rows:
        return "<p class='empty'>No data</p>"
    columns = list(rows[0])
    header = "".join("<th>{}</th>".format(html.escape(str(column))) for column in columns)
    body = []
    for row in rows:
        body.append(
            "<tr>{}</tr>".format(
                "".join(
                    "<td>{}</td>".format(html.escape(str(row.get(column, ""))))
                    for column in columns
                )
            )
        )
    return "<table><thead><tr>{}</tr></thead><tbody>{}</tbody></table>".format(
        header, "".join(body)
    )


def render_report(run_dir: Path) -> Path:
    run_dir = Path(run_dir)
    summary = json.loads((run_dir / "run_summary.json").read_text(encoding="utf-8"))
    topology = json.loads((run_dir / "topology.json").read_text(encoding="utf-8"))
    metrics = _read_csv(run_dir / "metrics.csv")
    controls = _read_csv(run_dir / "control_trace.csv")
    summary_rows = [
        {"metric": key, "value": value}
        for key, value in summary.get("summary_metrics", {}).items()
    ]
    topology_rows = [
        {"type": node.get("type"), "id": node.get("id"), "parent": node.get("parent", "")}
        for node in topology.get("nodes", [])
    ]
    document = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>SoC Flow / MPAM Simulation Report</title>
<style>
body {{ margin: 0; font: 14px Arial, sans-serif; color: #17202a; background: #f5f7f8; }}
header {{ background: #17202a; color: white; padding: 18px 28px; }}
main {{ max-width: 1180px; margin: auto; padding: 24px; }}
section {{ background: white; border: 1px solid #d5d8dc; margin-bottom: 18px; padding: 18px; overflow-x: auto; }}
h1, h2, h3 {{ letter-spacing: 0; }}
.flow {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 8px; align-items: stretch; }}
.flow div {{ border: 1px solid #85929e; padding: 12px 8px; text-align: center; background: #fdfefe; }}
.chart {{ display: inline-block; width: min(100%, 780px); vertical-align: top; margin-right: 18px; }}
svg {{ width: 100%; background: #fbfcfc; border: 1px solid #d5d8dc; }}
svg text {{ font-size: 11px; fill: #566573; }}
.legend span {{ margin-right: 14px; }}
.legend i {{ display: inline-block; width: 12px; height: 3px; margin-right: 5px; vertical-align: middle; }}
table {{ border-collapse: collapse; width: 100%; font-size: 12px; }}
th, td {{ border: 1px solid #d5d8dc; padding: 6px; text-align: left; }}
th {{ background: #eaecee; }}
.empty {{ color: #7b7d7d; }}
@media (max-width: 520px) {{
  header {{ padding: 16px 20px; }}
  main {{ padding: 16px; }}
  section {{ padding: 14px; }}
  .flow {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
  .flow div {{ overflow-wrap: anywhere; }}
}}
</style>
</head>
<body>
<header><h1>SoC Flow Control / MPAM Simulation</h1><div>{scenario}</div></header>
<main>
<section><h2>Modeled Flow</h2><div class="flow">
<div>Requesters</div><div>NoC queue</div><div>L3/SLC MSC</div>
<div>MC token bucket</div><div>Priority scheduler</div><div>Completion</div>
</div></section>
<section><h2>Run Summary</h2>{summary_table}</section>
<section><h2>Control and Performance Timeline</h2>
{latency_chart}
{bandwidth_chart}
{throttle_chart}
</section>
<section><h2>Control Updates</h2>{control_table}</section>
<section><h2>Resolved Topology</h2>{topology_table}</section>
</main></body></html>
""".format(
        scenario=html.escape(str(summary.get("scenario", "run"))),
        summary_table=_table(summary_rows, 100),
        latency_chart=_line_chart(metrics, "p99_latency_ns", "P99 latency over time (ns)"),
        bandwidth_chart=_line_chart(metrics, "throughput_gbps", "Bandwidth over time (Gbps)"),
        throttle_chart=_line_chart(metrics, "avg_throttle_delay_ns", "Average throttle delay (ns)"),
        control_table=_table(controls, 100),
        topology_table=_table(topology_rows, 200),
    )
    output = run_dir / "report.html"
    output.write_text(document, encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a static SoC flow/MPAM HTML report")
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--format", default="html", choices=["html"])
    args = parser.parse_args()
    output = render_report(args.run)
    print(output)


if __name__ == "__main__":
    main()

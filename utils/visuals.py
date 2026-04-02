import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from typing import List, Dict
from simulator.models import Process, GanttBlock

# ─── Color palette ───────────────────────────────────────────────────────────
PROCESS_COLORS = [
    "#6C5CE7", "#00CEC9", "#FD79A8", "#FDCB6E", "#55EFC4",
    "#E17055", "#74B9FF", "#A29BFE", "#FF7675", "#81ECEC",
    "#FAB1A0", "#DFE6E9", "#00B894", "#E84393", "#0984E3",
]

QUEUE_COLORS = [
    "rgba(108, 92, 231, 0.3)",   # Purple
    "rgba(0, 206, 201, 0.3)",    # Teal
    "rgba(253, 121, 168, 0.3)",  # Pink
    "rgba(253, 203, 110, 0.3)",  # Yellow
    "rgba(85, 239, 196, 0.3)",   # Green
]

BG_COLOR = "rgba(0,0,0,0)"
GRID_COLOR = "rgba(255,255,255,0.06)"
TEXT_COLOR = "#E0E0E0"


def _get_process_color(pid: str, pid_list: list) -> str:
    """Get consistent color for a process."""
    if pid == "IDLE":
        return "rgba(255,255,255,0.08)"
    idx = pid_list.index(pid) if pid in pid_list else 0
    return PROCESS_COLORS[idx % len(PROCESS_COLORS)]


def create_gantt_chart(gantt_chart: List[GanttBlock]):
    """Create a horizontal bar-based Gantt chart using integer time ticks."""
    if not gantt_chart:
        return None

    # Collect unique PIDs (excluding IDLE)
    pid_list = []
    for block in gantt_chart:
        if block.pid != "IDLE" and block.pid not in pid_list:
            pid_list.append(block.pid)

    fig = go.Figure()

    # Determine all queue IDs
    queue_ids = sorted(set(b.queue_id for b in gantt_chart if b.queue_id >= 0))
    if not queue_ids:
        queue_ids = [0]

    # Map queue_id to y-position
    queue_y_map = {qid: i for i, qid in enumerate(queue_ids)}

    for block in gantt_chart:
        if block.pid == "IDLE":
            continue

        color = _get_process_color(block.pid, pid_list)
        q_y = queue_y_map.get(block.queue_id, 0)
        duration = block.end - block.start

        fig.add_trace(go.Bar(
            x=[duration],
            y=[f"Queue {block.queue_id}"],
            base=[block.start],
            orientation='h',
            name=block.pid,
            marker=dict(
                color=color,
                line=dict(color="rgba(255,255,255,0.2)", width=1),
            ),
            text=f"{block.pid}",
            textposition="inside",
            textfont=dict(color="white", size=11, family="Inter"),
            hovertemplate=(
                f"<b>{block.pid}</b><br>"
                f"Queue {block.queue_id}<br>"
                f"Time: {block.start} → {block.end}<br>"
                f"Duration: {duration} ticks"
                "<extra></extra>"
            ),
            showlegend=block.pid not in [t.name for t in fig.data],
        ))

    fig.update_layout(
        barmode='stack',
        plot_bgcolor=BG_COLOR,
        paper_bgcolor=BG_COLOR,
        font=dict(color=TEXT_COLOR, family="Inter, sans-serif", size=12),
        xaxis=dict(
            title=dict(text="Time (ticks)", font=dict(size=13)),
            gridcolor=GRID_COLOR,
            dtick=1,
            tick0=0,
            showgrid=True,
            zeroline=False,
        ),
        yaxis=dict(
            autorange="reversed",
            gridcolor=GRID_COLOR,
            showgrid=False,
        ),
        margin=dict(l=20, r=20, t=40, b=40),
        height=max(180, 80 * len(queue_ids) + 80),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11),
            bgcolor="rgba(0,0,0,0)",
        ),
    )

    return fig


def create_comparison_chart(comparison_data: Dict[str, Dict]) -> go.Figure:
    """Create a grouped bar chart comparing metrics across algorithms."""
    algorithms = list(comparison_data.keys())
    metrics = ["Avg Waiting Time", "Avg Turnaround Time", "Avg Response Time"]
    metric_keys = ["avg_wt", "avg_tat", "avg_rt"]
    colors = ["#6C5CE7", "#00CEC9", "#FD79A8"]

    fig = go.Figure()
    for i, (metric, key) in enumerate(zip(metrics, metric_keys)):
        values = [comparison_data[alg].get(key, 0) for alg in algorithms]
        fig.add_trace(go.Bar(
            name=metric,
            x=algorithms,
            y=values,
            marker=dict(
                color=colors[i],
                line=dict(color="rgba(255,255,255,0.1)", width=1),
            ),
            text=[f"{v:.1f}" for v in values],
            textposition="outside",
            textfont=dict(size=11, color=TEXT_COLOR),
        ))

    fig.update_layout(
        barmode='group',
        plot_bgcolor=BG_COLOR,
        paper_bgcolor=BG_COLOR,
        font=dict(color=TEXT_COLOR, family="Inter, sans-serif", size=12),
        xaxis=dict(gridcolor=GRID_COLOR, showgrid=False),
        yaxis=dict(title=dict(text="Time (ms)"), gridcolor=GRID_COLOR, showgrid=True, zeroline=False),
        margin=dict(l=20, r=20, t=40, b=40),
        height=400,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11),
            bgcolor="rgba(0,0,0,0)",
        ),
    )
    return fig


def create_throughput_comparison(comparison_data: Dict[str, Dict]) -> go.Figure:
    """Create a horizontal bar chart for throughput comparison."""
    algorithms = list(comparison_data.keys())
    throughputs = [comparison_data[alg].get("throughput", 0) for alg in algorithms]

    fig = go.Figure(go.Bar(
        x=throughputs,
        y=algorithms,
        orientation='h',
        marker=dict(
            color=throughputs,
            colorscale=[[0, "#6C5CE7"], [0.5, "#00CEC9"], [1, "#55EFC4"]],
            line=dict(color="rgba(255,255,255,0.1)", width=1),
        ),
        text=[f"{t:.4f}" for t in throughputs],
        textposition="outside",
        textfont=dict(size=12, color=TEXT_COLOR),
    ))

    fig.update_layout(
        plot_bgcolor=BG_COLOR,
        paper_bgcolor=BG_COLOR,
        font=dict(color=TEXT_COLOR, family="Inter, sans-serif", size=12),
        xaxis=dict(title=dict(text="Throughput (processes/ms)"), gridcolor=GRID_COLOR, showgrid=True, zeroline=False),
        yaxis=dict(gridcolor=GRID_COLOR, showgrid=False),
        margin=dict(l=20, r=20, t=20, b=40),
        height=max(200, 50 * len(algorithms) + 80),
    )
    return fig


def calculate_metrics(processes: List[Process]) -> dict:
    """Calculate scheduling performance metrics."""
    if not processes:
        return {"avg_wt": 0, "avg_tat": 0, "avg_rt": 0, "throughput": 0, "cpu_util": 0}

    total_wt = sum(p.waiting_time for p in processes)
    total_tat = sum(p.turnaround_time for p in processes)
    total_rt = sum(p.response_time for p in processes)
    n = len(processes)

    max_finish = max(p.finish_time for p in processes)
    min_arrival = min(p.arrival_time for p in processes)
    total_time = max_finish - min_arrival
    total_burst = sum(p.burst_time for p in processes)

    cpu_util = round((total_burst / total_time * 100) if total_time > 0 else 0, 1)

    return {
        "avg_wt": round(total_wt / n, 2),
        "avg_tat": round(total_tat / n, 2),
        "avg_rt": round(total_rt / n, 2),
        "throughput": round(n / total_time if total_time > 0 else 0, 4),
        "cpu_util": cpu_util,
    }

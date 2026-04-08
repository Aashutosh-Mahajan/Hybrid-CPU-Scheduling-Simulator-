"""
utils/visuals.py
────────────────
All Plotly chart builders and metric calculation functions used by the
Streamlit UI (app.py).

This module is purely concerned with presentation — it takes already-simulated
data (lists of Process / GanttBlock objects and metrics dicts) and converts
them into Plotly Figure objects or plain Python dicts.

Functions
─────────
  create_gantt_chart(gantt_chart, queue_labels)
      → go.Figure   — horizontal stacked-bar Gantt timeline.

  calculate_metrics(processes)
      → dict        — aggregate scheduling metrics (avg WT, TAT, RT, throughput,
                       CPU utilisation) for a completed run.

  calculate_metrics_by_type(processes)
      → Dict[str, dict] — same metrics broken down by process_type.

  create_comparison_chart(comparison_data)
      → go.Figure   — grouped bar chart comparing WT / TAT / RT across
                       multiple algorithms.

  create_throughput_comparison(comparison_data)
      → go.Figure   — horizontal bar chart for throughput comparison.

Design notes
────────────
  • All charts use a transparent background (BG_COLOR) so they blend into the
    dark Streamlit theme defined in app.py's custom CSS.
  • Process colours are assigned by PID index into PROCESS_COLORS so the same
    process always gets the same colour across multiple charts.
  • QUEUE_COLORS is available for future per-queue background shading but is
    not currently rendered (reserved for extension).
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from simulator.models import Process, GanttBlock


# ─────────────────────────────────────────────────────────────────────────────
# Theme constants — keep these in sync with the CSS variables in app.py
# ─────────────────────────────────────────────────────────────────────────────

# Distinct colours for individual processes (cycled by PID index).
PROCESS_COLORS = [
    "#6C5CE7", "#00CEC9", "#FD79A8", "#FDCB6E", "#55EFC4",
    "#E17055", "#74B9FF", "#A29BFE", "#FF7675", "#81ECEC",
    "#FAB1A0", "#DFE6E9", "#00B894", "#E84393", "#0984E3",
]

# Semi-transparent overlay colours for queue-lane backgrounds (reserved).
QUEUE_COLORS = [
    "rgba(108, 92, 231, 0.3)",   # Purple — queue 0
    "rgba(0, 206, 201, 0.3)",    # Teal   — queue 1
    "rgba(253, 121, 168, 0.3)",  # Pink   — queue 2
    "rgba(253, 203, 110, 0.3)",  # Yellow — queue 3
    "rgba(85, 239, 196, 0.3)",   # Green  — queue 4
]

BG_COLOR   = "rgba(0,0,0,0)"              # fully transparent (dark theme blends through)
GRID_COLOR = "rgba(255,255,255,0.06)"     # barely-visible grid lines
TEXT_COLOR = "#E0E0E0"                    # light-grey axis text


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_process_color(pid: str, pid_list: list) -> str:
    """
    Return a consistent hex colour for a given process PID.

    IDLE gets a near-transparent white so idle gaps are clearly distinct.
    All other PIDs are mapped to PROCESS_COLORS by their position in pid_list,
    cycling if there are more processes than colours.
    """
    if pid == "IDLE":
        return "rgba(255,255,255,0.08)"
    idx = pid_list.index(pid) if pid in pid_list else 0
    return PROCESS_COLORS[idx % len(PROCESS_COLORS)]


# ─────────────────────────────────────────────────────────────────────────────
# Gantt chart
# ─────────────────────────────────────────────────────────────────────────────

def create_gantt_chart(
    gantt_chart: List[GanttBlock],
    queue_labels: Optional[Dict[int, str]] = None,
):
    """
    Build a horizontal stacked-bar Gantt chart from a list of GanttBlocks.

    Each queue lane occupies one row on the Y-axis (highest priority at top,
    controlled by autorange="reversed").  Each process is a coloured bar segment
    spanning [block.start, block.end) on the X-axis (time ticks).

    IDLE blocks are skipped — idle time shows as a gap between bars.

    Args:
        gantt_chart  : List[GanttBlock] produced by a simulator run.
        queue_labels : Optional mapping of queue_id → display label.
                       E.g. {0: "real-time (Priority)", 1: "interactive (RR q=3)"}.
                       Falls back to "Queue N" if not provided.

    Returns:
        A Plotly Figure, or None if gantt_chart is empty.
    """
    if not gantt_chart:
        return None

    # Collect unique PIDs (IDLE excluded) to assign stable colours.
    pid_list = []
    for block in gantt_chart:
        if block.pid != "IDLE" and block.pid not in pid_list:
            pid_list.append(block.pid)

    fig = go.Figure()

    # Determine the set of queue IDs that appear in the chart (excluding -1/IDLE).
    queue_ids = sorted(set(b.queue_id for b in gantt_chart if b.queue_id >= 0))
    if not queue_ids:
        queue_ids = [0]

    # Map each queue_id to a Y-axis position index (used internally by Plotly).
    queue_y_map = {qid: i for i, qid in enumerate(queue_ids)}

    # Add one Bar trace per GanttBlock (IDLE blocks are skipped).
    for block in gantt_chart:
        if block.pid == "IDLE":
            continue  # idle time shows as empty space, not a bar

        color = _get_process_color(block.pid, pid_list)
        q_y   = queue_y_map.get(block.queue_id, 0)
        duration = block.end - block.start  # width of the bar in ticks

        # Resolve the human-readable lane name for the Y-axis.
        lane_name = (
            queue_labels.get(block.queue_id, f"Queue {block.queue_id}")
            if queue_labels
            else f"Queue {block.queue_id}"
        )

        fig.add_trace(go.Bar(
            x=[duration],            # bar width = duration
            y=[lane_name],           # lane label on Y-axis
            base=[block.start],      # bar starts at this tick (Plotly 'base')
            orientation='h',
            name=block.pid,          # used for the legend entry
            marker=dict(
                color=color,
                line=dict(color="rgba(255,255,255,0.2)", width=1),
            ),
            text=f"{block.pid}",     # label inside the bar
            textposition="inside",
            textfont=dict(color="white", size=11, family="Inter"),
            hovertemplate=(
                f"<b>{block.pid}</b><br>"
                f"Queue {block.queue_id}<br>"
                f"Time: {block.start} → {block.end}<br>"
                f"Duration: {duration} ticks"
                "<extra></extra>"
            ),
            # Only add a legend entry the first time this PID appears.
            showlegend=block.pid not in [t.name for t in fig.data],
        ))

    # ── Chart layout ─────────────────────────────────────────────────────────
    fig.update_layout(
        barmode='stack',                         # bars share the same lane row
        plot_bgcolor=BG_COLOR,
        paper_bgcolor=BG_COLOR,
        font=dict(color=TEXT_COLOR, family="Inter, sans-serif", size=12),
        xaxis=dict(
            title=dict(text="Time (ticks)", font=dict(size=13)),
            gridcolor=GRID_COLOR,
            dtick=1,                             # one grid line per tick
            tick0=0,
            showgrid=True,
            zeroline=False,
        ),
        yaxis=dict(
            autorange="reversed",                # highest-priority queue at top
            gridcolor=GRID_COLOR,
            showgrid=False,
        ),
        margin=dict(l=20, r=20, t=40, b=40),
        height=max(180, 80 * len(queue_ids) + 80),  # taller for more lanes
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


# ─────────────────────────────────────────────────────────────────────────────
# Algorithm comparison charts (used by the now-removed Hybrid vs Single tab;
# kept here in case the comparison feature is re-added in future).
# ─────────────────────────────────────────────────────────────────────────────

def create_comparison_chart(comparison_data: Dict[str, Dict]) -> go.Figure:
    """
    Grouped bar chart comparing Avg Waiting, Turnaround, and Response Time
    across multiple scheduling algorithms.

    Args:
        comparison_data : { algorithm_name: metrics_dict, … }
                          where metrics_dict has keys "avg_wt", "avg_tat", "avg_rt".

    Returns:
        A Plotly grouped-bar Figure.
    """
    algorithms  = list(comparison_data.keys())
    metrics     = ["Avg Waiting Time", "Avg Turnaround Time", "Avg Response Time"]
    metric_keys = ["avg_wt", "avg_tat", "avg_rt"]
    colors      = ["#6C5CE7", "#00CEC9", "#FD79A8"]

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
        yaxis=dict(
            title=dict(text="Time (ms)"),
            gridcolor=GRID_COLOR,
            showgrid=True,
            zeroline=False,
        ),
        margin=dict(l=20, r=20, t=40, b=40),
        height=400,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="right", x=1, font=dict(size=11),
            bgcolor="rgba(0,0,0,0)",
        ),
    )
    return fig


def create_throughput_comparison(comparison_data: Dict[str, Dict]) -> go.Figure:
    """
    Horizontal colour-scaled bar chart showing throughput for each algorithm.

    Throughput = (number of processes completed) / (total elapsed time).
    Higher is better.

    Args:
        comparison_data : { algorithm_name: metrics_dict, … }
                          where metrics_dict has key "throughput".

    Returns:
        A Plotly horizontal-bar Figure.
    """
    algorithms  = list(comparison_data.keys())
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
        xaxis=dict(
            title=dict(text="Throughput (processes/ms)"),
            gridcolor=GRID_COLOR,
            showgrid=True,
            zeroline=False,
        ),
        yaxis=dict(gridcolor=GRID_COLOR, showgrid=False),
        margin=dict(l=20, r=20, t=20, b=40),
        height=max(200, 50 * len(algorithms) + 80),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Metric calculators
# ─────────────────────────────────────────────────────────────────────────────

def calculate_metrics(processes: List[Process]) -> dict:
    """
    Calculate aggregate scheduling performance metrics across all processes.

    Formulas:
        Waiting Time (WT)    = Turnaround Time − Burst Time
        Turnaround Time (TAT)= Finish Time − Arrival Time
        Response Time (RT)   = First CPU Time − Arrival Time
        Throughput           = N / (max_finish − min_arrival)
        CPU Utilisation      = (Σ burst_time / total_time) × 100 %

    Args:
        processes : List of completed Process objects (all fields populated).

    Returns:
        A dict with keys:
            avg_wt      — average waiting time (ticks)
            avg_tat     — average turnaround time (ticks)
            avg_rt      — average response time (ticks)
            throughput  — processes per tick
            cpu_util    — CPU utilisation percentage
        All values are 0 if the processes list is empty.
    """
    if not processes:
        return {"avg_wt": 0, "avg_tat": 0, "avg_rt": 0, "throughput": 0, "cpu_util": 0}

    n          = len(processes)
    total_wt   = sum(p.waiting_time for p in processes)
    total_tat  = sum(p.turnaround_time for p in processes)
    total_rt   = sum(p.response_time for p in processes)

    max_finish   = max(p.finish_time for p in processes)
    min_arrival  = min(p.arrival_time for p in processes)
    total_time   = max_finish - min_arrival   # makespan
    total_burst  = sum(p.burst_time for p in processes)

    cpu_util = round((total_burst / total_time * 100) if total_time > 0 else 0, 1)

    return {
        "avg_wt":      round(total_wt  / n, 2),
        "avg_tat":     round(total_tat / n, 2),
        "avg_rt":      round(total_rt  / n, 2),
        "throughput":  round(n / total_time if total_time > 0 else 0, 4),
        "cpu_util":    cpu_util,
    }


def calculate_metrics_by_type(processes: List[Process]) -> Dict[str, Dict[str, float]]:
    """
    Calculate scheduling metrics broken down by process_type.

    Useful for understanding how each class of work (real-time, interactive,
    batch) performed individually inside a hybrid scheduling run.

    Args:
        processes : List of completed Process objects.

    Returns:
        A dict mapping each process_type string to its own metrics dict.
        Each inner dict contains:
            count      — number of processes of this type
            avg_wt     — average waiting time
            avg_tat    — average turnaround time
            avg_rt     — average response time
            throughput — processes of this type per overall tick
            cpu_util   — CPU time share for this type (%)
        Returns an empty dict if processes is empty.
    """
    if not processes:
        return {}

    # Group processes by their normalised type label.
    grouped: Dict[str, List[Process]] = {}
    for process in processes:
        ptype = (getattr(process, "process_type", "") or "batch").strip().lower()
        grouped.setdefault(ptype, []).append(process)

    # Overall time span (same denominator for all types so throughput is comparable).
    max_finish  = max(p.finish_time for p in processes)
    min_arrival = min(p.arrival_time for p in processes)
    total_time  = max_finish - min_arrival

    metrics_by_type: Dict[str, Dict[str, float]] = {}
    for ptype, items in grouped.items():
        n           = len(items)
        total_wt    = sum(p.waiting_time for p in items)
        total_tat   = sum(p.turnaround_time for p in items)
        total_rt    = sum(p.response_time for p in items)
        total_burst = sum(p.burst_time for p in items)

        metrics_by_type[ptype] = {
            "count":      n,
            "avg_wt":     round(total_wt  / n, 2),
            "avg_tat":    round(total_tat / n, 2),
            "avg_rt":     round(total_rt  / n, 2),
            "throughput": round(n / total_time if total_time > 0 else 0, 4),
            "cpu_util":   round((total_burst / total_time * 100) if total_time > 0 else 0, 1),
        }

    return metrics_by_type

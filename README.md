# Hybrid CPU Scheduling Simulator

An interactive CPU scheduling simulator built with Python, Streamlit, and Plotly.

This project focuses on a hybrid, type-based scheduling model where each process type is routed to its own queue and scheduling policy. The app also includes side-by-side comparison against single-policy baselines.

## Overview

Instead of applying one algorithm to all processes, the simulator lets you:

- Route real-time, interactive, and batch processes into different queues.
- Assign a dedicated algorithm to each type queue.
- Run the system with fixed queue precedence (higher-priority type queues preempt lower ones).
- Analyze outcomes with a Gantt chart, aggregate metrics, and per-type metrics.

## Implemented Features

- Hybrid type routing with three supported types:
  - real-time
  - interactive
  - batch
- Configurable per-type queue algorithm from the UI sidebar.
- Built-in workload generator with controllable counts and random seed.
- Editable process table for manual test cases.
- Optional auto-classification for missing/invalid process types:
  - priority <= 1 -> real-time
  - burst time <= 4 -> interactive
  - otherwise -> batch
- Hybrid execution trace and queue-aware Gantt timeline.
- Metrics:
  - Average Waiting Time (WT)
  - Average Turnaround Time (TAT)
  - Average Response Time (RT)
  - Throughput
  - CPU Utilization
- Per-type metrics table (count, WT/TAT/RT, throughput, CPU utilization share).
- Hybrid vs single-policy comparison tab.

## Supported Scheduling Algorithms

- FCFS (non-preemptive)
- SJF (non-preemptive)
- SRTF (preemptive SJF)
- Priority (preemptive)
- Round Robin (preemptive, configurable quantum)

## Hybrid Scheduling Behavior

The hybrid scheduler in simulator/hybrid.py follows these rules:

1. Arriving processes are normalized/classified into a process type.
2. Each type is routed to its configured queue.
3. The CPU always selects from the highest-priority non-empty queue.
4. A newly ready higher-priority queue preempts the currently running lower-priority queue process.
5. Within the same queue, preemptive non-RR algorithms (SRTF, Priority) may replace the running process if a better candidate appears.
6. Round Robin rotation occurs when quantum expires.

Safety limit:

- Simulation stops at 10,000 ticks to avoid runaway loops.

## Quick Start

### 1. Clone and enter the project

```bash
git clone <your-repository-url>
cd Hybrid-CPU-Scheduling-Simulator-
```

### 2. Create and activate a virtual environment

Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the app

```bash
streamlit run app.py
```

Then open the local URL shown by Streamlit (typically http://localhost:8501).

## How To Use

1. In the sidebar, choose one algorithm for each process type queue.
2. Use the generator or edit the process table directly.
3. Keep auto-classification enabled if some Type values are missing/invalid.
4. Run Hybrid Simulation to view:
   - Overall metrics
   - Queue-lane Gantt chart
   - Per-type metrics
   - Detailed per-process results
   - Execution trace
5. Open Hybrid vs Single to compare against FCFS, SJF, SRTF, Priority, and RR baseline runs on the same workload.

## Process Table Schema

Each process row uses:

- PID: unique process ID
- Type: real-time | interactive | batch
- Arrival Time: integer >= 0
- Burst Time: integer > 0
- Priority: integer (lower number means higher priority)

Validation performed by the app:

- Duplicate PID values are rejected.
- Arrival/Burst/Priority must be integers.
- Arrival Time cannot be negative.
- Burst Time must be positive.

## Notes On Metrics and Time Units

- The simulation engine is tick-based.
- Chart axes and scheduling progression are in ticks.
- Some UI labels show "ms", but values are produced from discrete simulation ticks.

## Project Structure

```text
Hybrid-CPU-Scheduling-Simulator-/
|-- app.py
|-- README.md
|-- requirements.txt
|-- simulator/
|   |-- __init__.py
|   |-- algorithms.py
|   |-- hybrid.py
|   |-- mlfq.py
|   `-- models.py
`-- utils/
    |-- __init__.py
    `-- visuals.py
```

## Module Guide

- app.py
  - Streamlit UI, process input flow, hybrid execution, and comparison tab logic.
- simulator/algorithms.py
  - Algorithm selection logic for FCFS, SJF/SRTF, Priority, and Round Robin.
- simulator/hybrid.py
  - Type-based routing and multi-queue hybrid scheduling engine.
- simulator/mlfq.py
  - Generic multi-queue simulator used by the comparison baseline runs.
- simulator/models.py
  - Data models for Process and GanttBlock.
- utils/visuals.py
  - Plotly charts and metric calculators.

## Dependencies

- streamlit
- pandas
- plotly
- numpy

(See requirements.txt for version constraints.)


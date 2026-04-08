# Hybrid CPU Scheduling Simulator

> An interactive, tick-based CPU scheduling simulator built with **Python**, **Streamlit**, and **Plotly**.

Instead of applying one algorithm uniformly to every process, this simulator implements a **type-based hybrid scheduling model** where each class of process is routed to its own dedicated queue running its own algorithm — mirroring how real operating systems treat real-time tasks, interactive applications, and background jobs differently.

---

## Table of Contents

1. [What Is Hybrid Scheduling?](#what-is-hybrid-scheduling)
2. [Features](#features)
3. [Supported Algorithms](#supported-algorithms)
4. [Project Structure](#project-structure)
5. [File-by-File Explanation](#file-by-file-explanation)
   - [app.py](#apppy--streamlit-ui--main-entry-point)
   - [simulator/models.py](#simulatormodelspy--core-data-structures)
   - [simulator/algorithms.py](#simulatoralgorithmspy--scheduling-algorithm-classes)
   - [simulator/hybrid.py](#simulatorhybridpy--hybrid-scheduler-engine)
   - [utils/visuals.py](#utilsvisualspy--charts--metrics)
6. [How the Simulation Works (Step by Step)](#how-the-simulation-works-step-by-step)
7. [Key Metrics Explained](#key-metrics-explained)
8. [Process Table Schema](#process-table-schema)
9. [Auto-Classification Rules](#auto-classification-rules)
10. [Quick Start](#quick-start)
11. [How to Use the App](#how-to-use-the-app)
12. [Dependencies](#dependencies)

---

## What Is Hybrid Scheduling?

Traditional CPU scheduling applies **one algorithm to all processes**.  
This simulator instead assigns each process a **type** (`real-time`, `interactive`, `batch`, or any custom label you create) and routes it to a dedicated **type queue**, each running its own algorithm:

| Process Type  | Typical Algorithm        | Why?                                      |
|---------------|--------------------------|-------------------------------------------|
| `real-time`   | Priority (Preemptive)    | Must meet deadlines; latency is critical  |
| `interactive` | Round Robin              | Fair time-sharing; good responsiveness    |
| `batch`       | FCFS / SJF               | Throughput over latency                   |

**Queue precedence** is fixed: a higher-priority type queue will preempt a running process from a lower-priority queue the moment it has a ready process.  
Within a queue, the configured algorithm handles intra-queue selection and preemption.

---

## Features

- **Configurable queue setup** — create 1–12 type queues from the sidebar, each with a custom name and algorithm.
- **Seven algorithm variants** — FCFS, SJF, SRTF, SRTN, Round Robin, and Priority (both Non-Preemptive and Preemptive).
- **Interactive process table** — edit PIDs, type, arrival time, burst time, and priority directly in the UI.
- **Adjustable process count** — add or remove process rows instantly with a number input.
- **Auto-classification** — automatically routes processes with missing/invalid types using a heuristic (priority/burst-time rules).
- **Gantt chart** — per-queue-lane horizontal bar timeline showing exactly when each process ran.
- **Overall metrics** — Average Waiting Time, Turnaround Time, Response Time, Throughput, CPU Utilisation.
- **Per-type metrics** — same metrics broken down by process class.
- **Detailed Math Calculations** — an expander explicitly showing step-by-step formulas for how each process metric was calculated.
- **Execution trace** — tick-by-tick textual trace of every scheduling event.
- **Theory reference tab** — concise explanations of every algorithm and metric.

---

## Supported Algorithms

| Algorithm | Class | Preemptive | Key Property |
|-----------|-------|-----------|--------------|
| **FCFS** | `FCFS` | No | Simplest; may cause convoy effect |
| **SJF** | `SJF(is_preemptive=False)` | No | Optimal avg WT for known burst times |
| **Priority** | `Priority(is_preemptive=False)` | No | Highest priority runs first; to completion |
| **SRTF** | `SJF(is_preemptive=True)` | Yes | Preemptive SJF; lowest avg WT theoretically |
| **SRTN** | `SJF(is_preemptive=True)` | Yes | Same as SRTF mathematically; available via UI |
| **Priority** | `Priority(is_preemptive=True)` | Yes | Used for real-time urgency ordering |
| **Round Robin** | `RoundRobin(quantum=N)` | Yes | Fair time-sharing; quantum configurable |

---

## Project Structure

```
Hybrid-CPU-Scheduling-Simulator-/
│
├── app.py                  ← Streamlit UI, all user interaction logic
├── requirements.txt        ← Python package dependencies
├── README.md               ← This file
│
├── simulator/              ← Core scheduling engine (no UI dependencies)
│   ├── __init__.py
│   ├── models.py           ← Process and GanttBlock data structures
│   ├── algorithms.py       ← FCFS, SJF, SRTF, Priority, RoundRobin classes
│   └── hybrid.py           ← Type-based hybrid scheduler (main engine)
│
└── utils/                  ← Visualisation and analytics helpers
    ├── __init__.py
    └── visuals.py          ← Plotly chart builders + metric calculators
```

---

## File-by-File Explanation

### `app.py` — Streamlit UI & Main Entry Point

**Role:** Renders the entire web application, handles user input, calls the `simulator` engine, and displays results.

**Key sections inside `app.py`:**

| Lines (approx.) | Section | What it does |
|-----------------|---------|--------------|
| 1–30 | Imports & page config | Sets the Streamlit page title, icon, and layout. |
| 30–337 | Custom CSS | Dark glassmorphism theme using CSS variables, card styles, button styles, tab styles, and animations. |
| 340–352 | Hero header | Renders the animated gradient title at the top of the page. |
| 355–458 | Sidebar — Queue config | Number-of-queues input, per-queue name + algorithm + RR quantum configuration, auto-classify toggle. |
| 460–470 | Tab definition | Creates the two main tabs: Hybrid Simulator and Theory. |
| 465–645 | Helper functions | `generate_processes()`, `resize_process_dataframe()`, `parse_processes()`, `clone_processes()`, `build_classifier()`. |
| 651–830 | Tab 1 — Hybrid Simulator | Process count input, editable data table, Run button, metrics display, Gantt chart, per-type breakdown, results table, execution trace. |
| 920–1023 | Tab 2 — Theory | Static educational cards explaining each algorithm and metric. |
| 1025–1034 | Footer | Project attribution line. |

**Important helper functions:**

```python
generate_processes(count, queue_names, max_arrival, seed)
```
Creates a random set of processes spread across the configured queue types.  
Uses a seeded RNG so results are reproducible.

```python
resize_process_dataframe(df, target_count, queue_names)
```
Adds or removes rows from the process table without discarding existing data.  
New rows get auto-numbered PIDs (P6, P7, …) and default values.

```python
parse_processes(df, auto_classify)
```
Validates the data-editor DataFrame and converts it to `List[Process]`.  
Raises clear errors for duplicate PIDs, negative arrival times, or non-positive burst times.

```python
build_classifier(auto_classify)
```
Returns a closure that maps a `Process` to a type string using the configured queue names and the heuristic fallback.

---

### `simulator/models.py` — Core Data Structures

**Role:** Defines the two dataclasses that every other module uses. Has no dependencies on any other project file.

#### `Process`

Represents one CPU process throughout its lifecycle.

| Field | Type | Set by | Description |
|-------|------|--------|-------------|
| `pid` | `str` | User | Unique identifier (e.g. `"P1"`) |
| `arrival_time` | `int` | User | Tick when the process enters the system |
| `burst_time` | `int` | User | Total CPU time needed |
| `priority` | `int` | User | Lower = more urgent (used by Priority algorithm) |
| `process_type` | `str` | User / auto | Type label for hybrid queue routing |
| `remaining_time` | `int` | `__post_init__` | Counts down tick-by-tick during execution |
| `start_time` | `int` | Simulator | Tick of first CPU access (`-1` until started) |
| `finish_time` | `int` | Simulator | Tick of completion (`-1` until finished) |
| `current_queue` | `int` | Simulator | queue index currently assigned to |
| `time_in_current_queue` | `int` | Simulator | Used for aging (promotion) |
| `waiting_time` | `int` | Simulator | Computed on completion: `TAT − burst_time` |
| `turnaround_time` | `int` | Simulator | Computed on completion: `finish − arrival` |
| `response_time` | `int` | Simulator | Computed on first CPU access: `start − arrival` |

#### `GanttBlock`

Records one contiguous time slice for the Gantt chart.

| Field | Description |
|-------|-------------|
| `queue_id` | Which type lane (`-1` for IDLE) |
| `pid` | Process name or `"IDLE"` |
| `start` | First tick of the slice (inclusive) |
| `end` | Tick after the last (exclusive) — covers `[start, end)` |

The simulator extends the `end` of the last block rather than appending a new one when the same process continues running — this keeps the list compact.

---

### `simulator/algorithms.py` — Scheduling Algorithm Classes

**Role:** Provides the `select_process()` logic for each algorithm.  
The simulators call `algorithm.select_process(ready_queue, current_process)` each tick.

#### Class hierarchy

```
SchedulingAlgorithm  (base)
├── FCFS
├── SJF                (handles both SJF and SRTF via is_preemptive flag)
├── Priority
└── RoundRobin
```

#### How `select_process()` works

Each algorithm receives:
- `ready_queue` — all processes currently waiting in this queue's ready list.
- `current_process` — the process that was running before this call (may be `None`).

It returns the process that should run next, or `None` if the queue is empty.

| Algorithm | Selection logic |
|-----------|----------------|
| `FCFS` | Keep current if still running; else take `ready_queue[0]` (first-in) |
| `SJF` | Shortest `burst_time` among all ready (non-preemptive keeps current) |
| `SRTF` | Shortest `remaining_time`; always re-evaluates even against running process |
| `Priority` | Lowest `priority` number; ties broken by `arrival_time` |
| `RoundRobin` | Always returns `ready_queue[0]`; quantum enforcement is in the simulator |

---

### `simulator/hybrid.py` — Hybrid Scheduler Engine

**Role:** The main simulation engine of the project. Implements the type-based multi-queue hybrid scheduler.

#### Key components

**`normalize_process_type(s)`**  
Converts any type label to lowercase-hyphenated canonical form.  
`"Real_Time"` → `"real-time"`, `""` → `"batch"`.

**`heuristic_classifier(process)`**  
When a process has an unrecognised type, this function guesses:
- `priority <= 1` → `"real-time"`
- `burst_time <= 4` → `"interactive"`
- otherwise → `"batch"`

**`HybridQueueConfig`**  
Dataclass holding one type lane's configuration: the type label, algorithm instance, priority rank, and live ready queue list.

**`HybridScheduler`**  
The main engine. Accepts a list of processes, a list of `HybridQueueConfig` objects, an optional classifier callable, and a fallback type.

#### Simulation loop steps (executed each tick)

```
Step 1 → Admit arrivals       — classify and route newly arrived processes
Step 2 → RR quantum expiry    — re-queue process if quantum consumed
Step 3 → Find highest queue   — locate highest-priority non-empty type lane
Step 4 → Cross-queue preempt  — preempt if a higher-priority lane now has work
Step 5 → Same-queue preempt   — SRTF/Priority: check for better candidate in same lane
Step 6 → Schedule             — pick and dispatch the best process if CPU is free
Step 7 → Execute one tick     — decrement remaining_time, update Gantt, collect if done
```

---

### `utils/visuals.py` — Charts & Metrics

**Role:** Purely presentation. Turns simulator output into Plotly figures and calculated metric dicts. Has no scheduling logic.

#### Functions

| Function | Returns | Purpose |
|----------|---------|---------|
| `create_gantt_chart(gantt_chart, queue_labels)` | `go.Figure` | Horizontal stacked-bar Gantt timeline, one row per queue lane |
| `calculate_metrics(processes)` | `dict` | Aggregate WT, TAT, RT, throughput, CPU util for all processes |
| `calculate_metrics_by_type(processes)` | `Dict[str, dict]` | Same metrics split by process_type |
| `create_comparison_chart(comparison_data)` | `go.Figure` | Grouped bar: WT/TAT/RT across algorithms |
| `create_throughput_comparison(comparison_data)` | `go.Figure` | Horizontal bar: throughput per algorithm |

#### Colour scheme

Process colours are assigned by PID index from `PROCESS_COLORS` (15 distinct colours, cycling).  
The same PID always gets the same colour across all charts within one session.  
IDLE blocks are rendered as near-transparent white bars.

---

## How the Simulation Works (Step by Step)

```
t=0  Process P2 arrives (real-time) → routed to real-time queue
     CPU free → P2 scheduled → starts running
t=1  Process P1 arrives (interactive) → routed to interactive queue
     P2 is real-time (higher priority) → continues running
t=4  P2 finishes → CPU free → next highest queue is interactive
     P1 selected from Round Robin queue → starts running
...
```

Every tick, the scheduler:
1. Admits any process whose `arrival_time <= current_time`.
2. Checks Round Robin quantum expiry.
3. Finds the highest-priority non-empty queue.
4. Preempts the running process if a higher-priority queue became non-empty.
5. Checks within-queue preemption for SRTF/Priority.
6. Schedules a new process if the CPU is free.
7. Executes one tick: decrements `remaining_time`, extends the Gantt block, collects the process if done.

---

## Key Metrics Explained

| Metric | Formula | What it measures |
|--------|---------|-----------------|
| **Waiting Time (WT)** | `Turnaround − Burst Time` | Time spent in ready queue, not executing |
| **Turnaround Time (TAT)** | `Finish Time − Arrival Time` | Total time from submission to completion |
| **Response Time (RT)** | `Start Time − Arrival Time` | Time until first CPU touch |
| **Throughput** | `N / (max_finish − min_arrival)` | Processes completed per tick |
| **CPU Utilisation** | `Σ burst / makespan × 100%` | Fraction of time CPU was busy |

> **Note:** The simulator is purely tick-based. Labels in the UI say "ms" for readability, but values are discrete simulation ticks.

---

## Process Table Schema

| Column | Type | Constraint | Description |
|--------|------|-----------|-------------|
| `PID` | string | Unique, non-empty | Process identifier (e.g. `P1`) |
| `Type` | string (dropdown) | Must match a configured queue name | Determines which type lane this process goes to |
| `Arrival Time` | integer | `>= 0` | Tick when process enters the system |
| `Burst Time` | integer | `> 0` | CPU cycles the process needs |
| `Priority` | integer | Any int | Lower = higher urgency for Priority algorithm |

**Validation rules enforced by `parse_processes()`:**
- Duplicate PID values → error.
- Non-integer Arrival / Burst / Priority → error.
- Arrival Time < 0 → error.
- Burst Time ≤ 0 → error.

---

## Auto-Classification Rules

When the sidebar toggle **"Auto-classify missing/invalid process type"** is ON, processes whose `Type` does not match any configured queue name are classified by `heuristic_classifier()`:

```
priority <= 1                →  "real-time"
burst_time <= 4 (and not RT) →  "interactive"
otherwise                    →  "batch"
```

When OFF, any unrecognised type is sent to the **last configured queue** (fallback).

---

## Quick Start

### 1. Clone the repository

```bash
git clone <your-repository-url>
cd Hybrid-CPU-Scheduling-Simulator-
```

### 2. Create and activate a virtual environment

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**macOS / Linux:**
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

Open the URL shown in the terminal (typically `http://localhost:8501`).

---

## How to Use the App

### Sidebar — Configure Queues

1. Set **Number of Queues** (1–12).
2. For each queue, expand its panel and:
   - Give it a **Queue Name** (this becomes a valid `Type` value in the process table).
   - Choose an **Algorithm** (FCFS, SJF, SRTF, Priority, Round Robin).
   - If Round Robin, set the **Time Quantum**.
3. Toggle **Auto-classify** on/off.

### Main Tab — Hybrid Simulator

1. Use the **Number of processes** input to add or remove process rows.
2. Edit the table directly — change PID, Type, Arrival/Burst/Priority for any row.
3. Click **▶ Run Hybrid Simulation**.
4. Review:
   - **Overall Metrics** (5 metric cards)
   - **Gantt Chart** (click/hover over bars for details)
   - **Per-Type Metrics** (table broken down by queue type)
   - **Detailed Process Results** (full table for every process)
   - **Execution Trace** (tick-by-tick text log)

### Theory Tab

Browse concise reference cards explaining each scheduling algorithm and all metric definitions. Useful for understanding why results differ between queue configurations.

---

## Dependencies

| Package | Min Version | Used for |
|---------|------------|---------|
| `streamlit` | ≥ 1.30.0 | Web UI framework |
| `pandas` | ≥ 2.0.0 | DataFrame manipulation for the process table |
| `plotly` | ≥ 5.18.0 | Interactive charts (Gantt, bar charts) |
| `numpy` | ≥ 1.24.0 | Numerical utilities in visuals.py |

Install all with:
```bash
pip install -r requirements.txt
```

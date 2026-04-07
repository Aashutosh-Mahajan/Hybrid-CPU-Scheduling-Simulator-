import streamlit as st
import pandas as pd
import copy
import random
from simulator.models import Process
from simulator.algorithms import FCFS, SJF, Priority, RoundRobin
from simulator.mlfq import MLFQSimulator, QueueConfig
from simulator.hybrid import HybridScheduler, HybridQueueConfig, heuristic_classifier, normalize_process_type
from utils.visuals import (
    create_gantt_chart,
    calculate_metrics,
    calculate_metrics_by_type,
    create_comparison_chart,
    create_throughput_comparison,
)

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Hybrid CPU Scheduler · Multi-Policy Simulator",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════════════════════════
# CUSTOM CSS — Dark glassmorphism theme
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* ── Google Font ───────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Root variables ────────────────────────────────────────────────────── */
:root {
    --bg-primary: #0a0a0f;
    --bg-card: rgba(18, 18, 30, 0.7);
    --bg-card-hover: rgba(28, 28, 45, 0.8);
    --border-card: rgba(108, 92, 231, 0.15);
    --accent-purple: #6C5CE7;
    --accent-teal: #00CEC9;
    --accent-pink: #FD79A8;
    --accent-yellow: #FDCB6E;
    --accent-green: #55EFC4;
    --text-primary: #F0F0F5;
    --text-secondary: #9B9BB4;
    --text-muted: #5A5A7A;
    --glow-purple: rgba(108, 92, 231, 0.3);
    --glow-teal: rgba(0, 206, 201, 0.25);
}

/* ── Global ────────────────────────────────────────────────────────────── */
html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg-primary) !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', sans-serif !important;
}

[data-testid="stAppViewContainer"] {
    background: linear-gradient(160deg, #0a0a0f 0%, #0d0d1a 40%, #0f0a1a 70%, #0a0a0f 100%) !important;
}

.stApp {
    background: transparent !important;
}

/* ── Sidebar ───────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(12,12,22,0.97) 0%, rgba(8,8,18,0.99) 100%) !important;
    border-right: 1px solid var(--border-card) !important;
}
[data-testid="stSidebar"] * {
    color: var(--text-primary) !important;
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stNumberInput label,
[data-testid="stSidebar"] .stSlider label {
    color: var(--text-secondary) !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.02em;
}

/* ── Headings ──────────────────────────────────────────────────────────── */
h1, h2, h3, h4, h5, h6 {
    font-family: 'Inter', sans-serif !important;
    color: var(--text-primary) !important;
}

/* ── Cards (metrics, sections) ─────────────────────────────────────────── */
.glass-card {
    background: var(--bg-card);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--border-card);
    border-radius: 16px;
    padding: 1.4rem;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.glass-card:hover {
    background: var(--bg-card-hover);
    border-color: rgba(108, 92, 231, 0.3);
    box-shadow: 0 8px 32px var(--glow-purple);
    transform: translateY(-2px);
}

/* ── Metric card ───────────────────────────────────────────────────────── */
.metric-card {
    background: var(--bg-card);
    backdrop-filter: blur(12px);
    border: 1px solid var(--border-card);
    border-radius: 14px;
    padding: 1.2rem 1.4rem;
    text-align: center;
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
}
.metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    border-radius: 14px 14px 0 0;
}
.metric-card.purple::before { background: linear-gradient(90deg, #6C5CE7, #A29BFE); }
.metric-card.teal::before   { background: linear-gradient(90deg, #00CEC9, #81ECEC); }
.metric-card.pink::before   { background: linear-gradient(90deg, #FD79A8, #FF7675); }
.metric-card.yellow::before { background: linear-gradient(90deg, #FDCB6E, #FAB1A0); }
.metric-card.green::before  { background: linear-gradient(90deg, #55EFC4, #00B894); }

.metric-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 12px 40px rgba(108, 92, 231, 0.2);
    border-color: rgba(108, 92, 231, 0.35);
}
.metric-label {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-secondary);
    margin-bottom: 0.4rem;
}
.metric-value {
    font-size: 1.7rem;
    font-weight: 800;
    font-family: 'JetBrains Mono', monospace;
    background: linear-gradient(135deg, #F0F0F5 0%, #A29BFE 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.metric-unit {
    font-size: 0.7rem;
    color: var(--text-muted);
    margin-top: 0.15rem;
}

/* ── Hero header ───────────────────────────────────────────────────────── */
.hero-container {
    text-align: center;
    padding: 2rem 0 1.5rem;
}
.hero-title {
    font-size: 2.6rem;
    font-weight: 900;
    letter-spacing: -0.03em;
    background: linear-gradient(135deg, #6C5CE7 0%, #00CEC9 50%, #FD79A8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: gradient-shift 4s ease-in-out infinite;
    background-size: 200% 200%;
    margin-bottom: 0.3rem;
    line-height: 1.15;
}
@keyframes gradient-shift {
    0%, 100% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
}
.hero-subtitle {
    font-size: 1rem;
    color: var(--text-secondary);
    font-weight: 400;
    letter-spacing: 0.01em;
    max-width: 600px;
    margin: 0 auto;
}
.hero-badge {
    display: inline-block;
    background: rgba(108, 92, 231, 0.15);
    border: 1px solid rgba(108, 92, 231, 0.3);
    border-radius: 100px;
    padding: 0.3rem 1rem;
    font-size: 0.72rem;
    font-weight: 600;
    color: #A29BFE;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-bottom: 0.8rem;
}

/* ── Tabs ──────────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    background: rgba(18,18,30,0.5);
    border-radius: 12px;
    padding: 4px;
    border: 1px solid var(--border-card);
}
.stTabs [data-baseweb="tab"] {
    border-radius: 10px;
    padding: 0.6rem 1.4rem;
    font-weight: 600;
    font-size: 0.85rem;
    color: var(--text-secondary) !important;
    background: transparent;
    border: none !important;
    transition: all 0.2s ease;
}
.stTabs [aria-selected="true"] {
    background: rgba(108, 92, 231, 0.2) !important;
    color: var(--text-primary) !important;
    box-shadow: 0 2px 12px rgba(108, 92, 231, 0.15);
}
.stTabs [data-baseweb="tab-highlight"] {
    display: none;
}
.stTabs [data-baseweb="tab-border"] {
    display: none;
}

/* ── Data editor ───────────────────────────────────────────────────────── */
[data-testid="stDataEditor"] {
    border: 1px solid var(--border-card) !important;
    border-radius: 12px !important;
    overflow: hidden;
}

/* ── Buttons ───────────────────────────────────────────────────────────── */
.stButton > button[kind="primary"],
.stButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    letter-spacing: 0.02em;
    transition: all 0.25s ease !important;
    border: none !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #6C5CE7, #4834d4) !important;
    color: white !important;
    box-shadow: 0 4px 15px rgba(108, 92, 231, 0.3) !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 6px 25px rgba(108, 92, 231, 0.5) !important;
    transform: translateY(-1px);
}

/* ── Expander ──────────────────────────────────────────────────────────── */
.streamlit-expanderHeader {
    background: var(--bg-card) !important;
    border-radius: 12px !important;
    border: 1px solid var(--border-card) !important;
    font-weight: 600 !important;
}

/* ── Dividers ──────────────────────────────────────────────────────────── */
hr {
    border-color: var(--border-card) !important;
}

/* ── Section header ────────────────────────────────────────────────────── */
.section-header {
    font-size: 1.15rem;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 0.8rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

/* ── Theory cards ──────────────────────────────────────────────────────── */
.theory-card {
    background: var(--bg-card);
    border: 1px solid var(--border-card);
    border-radius: 14px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    transition: all 0.3s ease;
}
.theory-card:hover {
    border-color: rgba(108, 92, 231, 0.3);
    box-shadow: 0 4px 20px rgba(108, 92, 231, 0.1);
}
.theory-title {
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--accent-purple);
    margin-bottom: 0.5rem;
}
.theory-body {
    font-size: 0.88rem;
    color: var(--text-secondary);
    line-height: 1.65;
}

/* ── Footer ────────────────────────────────────────────────────────────── */
.footer {
    text-align: center;
    padding: 2rem 0 1rem;
    color: var(--text-muted);
    font-size: 0.78rem;
    border-top: 1px solid var(--border-card);
    margin-top: 3rem;
}

/* ── Scrollbar ─────────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(108,92,231,0.3); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(108,92,231,0.5); }

/* ── Success / Error ───────────────────────────────────────────────────── */
.stSuccess {
    background: rgba(85, 239, 196, 0.1) !important;
    border: 1px solid rgba(85, 239, 196, 0.3) !important;
    border-radius: 10px !important;
}
.stError, [data-testid="stNotification"] {
    border-radius: 10px !important;
}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# HERO HEADER
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="hero-container">
    <div class="hero-badge">⚡ Operating Systems Project</div>
    <div class="hero-title">Hybrid CPU Scheduling<br>Simulator</div>
    <div class="hero-subtitle">
        Type-based multi-policy CPU scheduling with queue routing,
        Gantt timeline visualization, per-type analytics, and baseline comparison.
    </div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR — Hybrid Queue Configuration
# ═══════════════════════════════════════════════════════════════════════════════
DEFAULT_QUEUE_NAMES = ["real-time", "interactive", "batch"]

with st.sidebar:
    st.markdown("### ⚙️ Hybrid Queue Routing")
    st.caption("Configure any number of queues and map each process to one queue.")
    st.divider()

    queue_count = int(
        st.number_input(
            "Number of Queues",
            min_value=1,
            max_value=12,
            value=int(st.session_state.get("queue_count", 3)),
            step=1,
            key="queue_count",
            help="Increase or decrease total queue lanes used by the hybrid scheduler.",
        )
    )

    algorithms_map = {
        "FCFS": lambda _q: FCFS(),
        "SJF (Non-Preemptive)": lambda _q: SJF(is_preemptive=False),
        "SRTF (Preemptive SJF)": lambda _q: SJF(is_preemptive=True),
        "Priority (Preemptive)": lambda _q: Priority(is_preemptive=True),
        "Round Robin": lambda q: RoundRobin(quantum=q),
    }

    default_alg_by_type = {
        "real-time": "Priority (Preemptive)",
        "interactive": "Round Robin",
        "batch": "FCFS",
    }

    hybrid_queue_config: list[HybridQueueConfig] = []
    configured_queue_names: list[str] = []
    seen_queue_names: set[str] = set()
    algo_names = list(algorithms_map.keys())

    for queue_priority in range(queue_count):
        default_queue_name = st.session_state.get(
            f"queue_name_{queue_priority}",
            DEFAULT_QUEUE_NAMES[queue_priority]
            if queue_priority < len(DEFAULT_QUEUE_NAMES)
            else f"queue-{queue_priority + 1}",
        )

        with st.expander(
            f"🔹 Queue {queue_priority + 1} (Priority {queue_priority})",
            expanded=(queue_priority == 0),
        ):
            queue_name_input = st.text_input(
                "Queue Name",
                value=str(default_queue_name),
                key=f"queue_name_{queue_priority}",
                help="This name appears in the process table Type dropdown.",
            )
            queue_name = normalize_process_type(queue_name_input)
            if not str(queue_name_input).strip():
                queue_name = f"queue-{queue_priority + 1}"
            if queue_name in seen_queue_names:
                queue_name = f"{queue_name}-{queue_priority + 1}"
                st.caption(f"Duplicate name detected. Using unique label: {queue_name}")
            seen_queue_names.add(queue_name)
            configured_queue_names.append(queue_name)

            default_alg = default_alg_by_type.get(queue_name, "FCFS")
            alg_name = st.selectbox(
                "Algorithm",
                algo_names,
                key=f"hybrid_alg_{queue_priority}",
                index=algo_names.index(default_alg),
            )

            quantum = 4
            if alg_name == "Round Robin":
                quantum = st.number_input(
                    "Time Quantum",
                    min_value=1,
                    value=3 if queue_name == "interactive" else 4,
                    key=f"hybrid_q_{queue_priority}",
                    help="Number of ticks before rotation in Round Robin.",
                )

            hybrid_queue_config.append(
                HybridQueueConfig(
                    process_type=queue_name,
                    algorithm=algorithms_map[alg_name](quantum),
                    queue_priority=queue_priority,
                )
            )

    SUPPORTED_PROCESS_TYPES = configured_queue_names or ["queue-1"]

    st.divider()
    auto_classify_unknown = st.toggle(
        "Auto-classify missing/invalid process type",
        value=True,
        help="If Type is invalid, map heuristically when possible, otherwise use last queue.",
    )
    st.caption(f"CPU queue precedence: {' → '.join(SUPPORTED_PROCESS_TYPES)}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN CONTENT — Tabs
# ═══════════════════════════════════════════════════════════════════════════════
tab_sim, tab_compare, tab_theory = st.tabs(["🖥️  Hybrid Simulator", "📊  Hybrid vs Single", "📖  Theory"])

# ── Default process data ──────────────────────────────────────────────────────
default_data = [
    {"PID": "P1", "Type": "interactive", "Arrival Time": 0, "Burst Time": 6, "Priority": 3},
    {"PID": "P2", "Type": "real-time", "Arrival Time": 1, "Burst Time": 3, "Priority": 0},
    {"PID": "P3", "Type": "batch", "Arrival Time": 2, "Burst Time": 9, "Priority": 5},
    {"PID": "P4", "Type": "interactive", "Arrival Time": 3, "Burst Time": 4, "Priority": 2},
    {"PID": "P5", "Type": "batch", "Arrival Time": 5, "Burst Time": 7, "Priority": 4},
]


def build_classifier(auto_classify: bool):
    queue_types = list(SUPPORTED_PROCESS_TYPES)
    fallback_type = queue_types[-1] if queue_types else "queue-1"

    def _classifier(process: Process) -> str:
        normalized = normalize_process_type(process.process_type)
        if normalized in queue_types:
            return normalized

        if auto_classify:
            predicted = heuristic_classifier(process)
            if predicted in queue_types:
                return predicted

        return fallback_type

    return _classifier


def parse_processes(df: pd.DataFrame, auto_classify: bool) -> list[Process]:
    """Parse DataFrame rows into Process objects with type classification."""
    processes: list[Process] = []
    seen_pids: set[str] = set()
    supported_types = list(SUPPORTED_PROCESS_TYPES)
    fallback_type = supported_types[-1] if supported_types else "queue-1"

    for _, row in df.iterrows():
        raw_pid = row.get("PID")
        if pd.isna(raw_pid) or str(raw_pid).strip() == "":
            continue

        pid = str(raw_pid).strip()
        if pid in seen_pids:
            raise ValueError(f"Duplicate PID detected: {pid}")
        seen_pids.add(pid)

        try:
            arrival_time = int(row.get("Arrival Time", 0))
            burst_time = int(row.get("Burst Time", 0))
            priority = int(row.get("Priority", 0))
        except (TypeError, ValueError):
            raise ValueError(f"Arrival, Burst, and Priority must be integers for {pid}.")

        if arrival_time < 0:
            raise ValueError(f"Arrival Time cannot be negative for {pid}.")
        if burst_time <= 0:
            raise ValueError(f"Burst Time must be greater than 0 for {pid}.")

        process_type = normalize_process_type(str(row.get("Type", "")))
        if process_type not in supported_types:
            if auto_classify:
                temp_process = Process(
                    pid=pid,
                    arrival_time=arrival_time,
                    burst_time=burst_time,
                    priority=priority,
                    process_type=process_type,
                )
                predicted = heuristic_classifier(temp_process)
                process_type = predicted if predicted in supported_types else fallback_type
            else:
                process_type = fallback_type

        processes.append(
            Process(
                pid=pid,
                arrival_time=arrival_time,
                burst_time=burst_time,
                priority=priority,
                process_type=process_type,
            )
        )

    return processes


def clone_processes(processes: list[Process]) -> list[Process]:
    return [
        Process(
            pid=p.pid,
            arrival_time=p.arrival_time,
            burst_time=p.burst_time,
            priority=p.priority,
            process_type=p.process_type,
        )
        for p in processes
    ]


def resize_process_dataframe(df: pd.DataFrame, target_count: int, queue_names: list[str]) -> pd.DataFrame:
    """Resize process table to target rows while preserving existing data."""
    columns = ["PID", "Type", "Arrival Time", "Burst Time", "Priority"]
    if df is None or df.empty:
        normalized_df = pd.DataFrame(columns=columns)
    else:
        normalized_df = df.copy()
        for col in columns:
            if col not in normalized_df.columns:
                default_value = "" if col in ("PID", "Type") else 0
                normalized_df[col] = default_value
        normalized_df = normalized_df[columns]

    target_count = max(0, int(target_count))
    current_count = len(normalized_df)

    if target_count < current_count:
        return normalized_df.iloc[:target_count].reset_index(drop=True)

    if target_count == current_count:
        return normalized_df

    valid_existing_pids: list[int] = []
    for pid in normalized_df["PID"].tolist():
        text_pid = str(pid).strip()
        if text_pid.startswith("P") and text_pid[1:].isdigit():
            valid_existing_pids.append(int(text_pid[1:]))
    next_pid = max(valid_existing_pids, default=0) + 1

    fallback_type = queue_names[0] if queue_names else "queue-1"
    for _ in range(target_count - current_count):
        normalized_df.loc[len(normalized_df)] = {
            "PID": f"P{next_pid}",
            "Type": fallback_type,
            "Arrival Time": 0,
            "Burst Time": 1,
            "Priority": 0,
        }
        next_pid += 1

    return normalized_df.reset_index(drop=True)


def generate_processes(
    process_count: int,
    queue_names: list[str],
    max_arrival: int,
    seed: int,
) -> pd.DataFrame:
    rng = random.Random(seed)
    rows = []

    queue_names = queue_names or ["queue-1"]
    process_count = max(0, int(process_count))

    for idx in range(process_count):
        process_type = queue_names[idx % len(queue_names)]
        if idx == 0:
            burst_range = (1, 4)
            priority_range = (0, 1)
        elif idx == 1:
            burst_range = (2, 6)
            priority_range = (2, 4)
        else:
            burst_range = (6, 14)
            priority_range = (3, 8)

        rows.append(
            {
                "PID": f"P{idx + 1}",
                "Type": process_type,
                "Arrival Time": rng.randint(0, max_arrival),
                "Burst Time": rng.randint(burst_range[0], burst_range[1]),
                "Priority": rng.randint(priority_range[0], priority_range[1]),
            }
        )

    rows.sort(key=lambda item: (item["Arrival Time"], item["PID"]))
    if not rows:
        return pd.DataFrame(columns=["PID", "Type", "Arrival Time", "Burst Time", "Priority"])
    return pd.DataFrame(rows)


if "process_df" not in st.session_state:
    st.session_state.process_df = pd.DataFrame(default_data)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — HYBRID SIMULATOR
# ═══════════════════════════════════════════════════════════════════════════════
with tab_sim:
    st.markdown('<div class="section-header">📝 Process Generator & Table</div>', unsafe_allow_html=True)
    st.caption("Define process attributes and type labels. Hybrid routing sends each type to its configured queue.")

    active_queue_names = list(SUPPORTED_PROCESS_TYPES)
    fallback_queue_name = active_queue_names[-1]

    with st.expander("🎲 Process Generator"):
        c1, c2, c3 = st.columns(3)
        with c1:
            gen_process_count = st.number_input(
                "Number of processes",
                min_value=0,
                value=max(len(st.session_state.process_df), 5),
                key="gen_count",
                help="Generate this many processes and spread them across configured queues.",
            )
        with c2:
            gen_max_arrival = st.number_input("Max arrival time", min_value=0, value=10, key="gen_arr")
        with c3:
            seed = st.number_input("Random seed", min_value=0, value=42, key="gen_seed")

        c4, c5 = st.columns(2)
        with c4:
            st.write("")
            st.write("")
            if st.button("Generate Workload", key="gen_btn", use_container_width=True):
                st.session_state.process_df = generate_processes(
                    process_count=int(gen_process_count),
                    queue_names=active_queue_names,
                    max_arrival=int(gen_max_arrival),
                    seed=int(seed),
                )

        with c5:
            st.write("")
            st.write("")
            if st.button("Reset to Default Example", key="reset_default", use_container_width=True):
                st.session_state.process_df = pd.DataFrame(default_data)

        st.write("")
        c6, c7 = st.columns([3, 1])
        with c6:
            table_target_count = st.number_input(
                "Adjust process rows",
                min_value=0,
                value=len(st.session_state.process_df),
                step=1,
                key="table_process_count",
                help="Increase or decrease rows without regenerating all process values.",
            )
        with c7:
            st.write("")
            st.write("")
            if st.button("Apply Count", key="apply_process_count", use_container_width=True):
                st.session_state.process_df = resize_process_dataframe(
                    st.session_state.process_df,
                    int(table_target_count),
                    active_queue_names,
                )

    st.session_state.process_df = resize_process_dataframe(
        st.session_state.process_df,
        len(st.session_state.process_df),
        active_queue_names,
    )

    def coerce_type(value: object) -> str:
        normalized = normalize_process_type(str(value))
        return normalized if normalized in active_queue_names else fallback_queue_name

    st.session_state.process_df["Type"] = st.session_state.process_df["Type"].apply(coerce_type)

    df_input = st.data_editor(
        st.session_state.process_df,
        num_rows="dynamic",
        use_container_width=True,
        key="process_editor",
        column_config={
            "Type": st.column_config.SelectboxColumn(
                "Type",
                options=active_queue_names,
                help="Pick the queue this process should be routed to.",
            )
        },
    )
    st.session_state.process_df = df_input

    st.write("")
    run_clicked = st.button("▶  Run Hybrid Simulation", type="primary", use_container_width=True)

    if run_clicked:
        try:
            processes = parse_processes(df_input, auto_classify=auto_classify_unknown)
            if not processes:
                st.warning("⚠️ Please add at least one process.")
                st.stop()

            classifier = build_classifier(auto_classify_unknown)
            simulator = HybridScheduler(
                clone_processes(processes),
                copy.deepcopy(hybrid_queue_config),
                classifier=classifier,
                fallback_type=SUPPORTED_PROCESS_TYPES[-1],
            )
            simulator.run()

            st.success(
                f"✅ Hybrid simulation complete — {len(simulator.completed_processes)} processes scheduled in {simulator.current_time} ticks"
            )

            metrics = calculate_metrics(simulator.completed_processes)

            st.write("")
            st.markdown('<div class="section-header">📈 Overall Metrics</div>', unsafe_allow_html=True)
            m1, m2, m3, m4, m5 = st.columns(5)

            with m1:
                st.markdown(f"""
                <div class="metric-card purple">
                    <div class="metric-label">Avg Waiting Time</div>
                    <div class="metric-value">{metrics['avg_wt']}</div>
                    <div class="metric-unit">milliseconds</div>
                </div>
                """, unsafe_allow_html=True)
            with m2:
                st.markdown(f"""
                <div class="metric-card teal">
                    <div class="metric-label">Avg Turnaround</div>
                    <div class="metric-value">{metrics['avg_tat']}</div>
                    <div class="metric-unit">milliseconds</div>
                </div>
                """, unsafe_allow_html=True)
            with m3:
                st.markdown(f"""
                <div class="metric-card pink">
                    <div class="metric-label">Avg Response</div>
                    <div class="metric-value">{metrics['avg_rt']}</div>
                    <div class="metric-unit">milliseconds</div>
                </div>
                """, unsafe_allow_html=True)
            with m4:
                st.markdown(f"""
                <div class="metric-card yellow">
                    <div class="metric-label">Throughput</div>
                    <div class="metric-value">{metrics['throughput']}</div>
                    <div class="metric-unit">proc / ms</div>
                </div>
                """, unsafe_allow_html=True)
            with m5:
                st.markdown(f"""
                <div class="metric-card green">
                    <div class="metric-label">CPU Utilization</div>
                    <div class="metric-value">{metrics['cpu_util']}%</div>
                    <div class="metric-unit">of total time</div>
                </div>
                """, unsafe_allow_html=True)

            st.write("")
            st.markdown('<div class="section-header">📊 Gantt Timeline</div>', unsafe_allow_html=True)
            fig = create_gantt_chart(simulator.gantt_chart, queue_labels=simulator.queue_label_map)
            if fig:
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

            st.write("")
            st.markdown('<div class="section-header">🧮 Metrics by Process Type</div>', unsafe_allow_html=True)
            by_type = calculate_metrics_by_type(simulator.completed_processes)
            if by_type:
                type_rows = []
                for process_type, values in by_type.items():
                    type_rows.append(
                        {
                            "Type": process_type,
                            "Processes": values["count"],
                            "Avg WT": values["avg_wt"],
                            "Avg TAT": values["avg_tat"],
                            "Avg RT": values["avg_rt"],
                            "Throughput": values["throughput"],
                            "CPU Util %": values["cpu_util"],
                        }
                    )
                st.dataframe(pd.DataFrame(type_rows), use_container_width=True, hide_index=True)

            st.write("")
            st.markdown('<div class="section-header">📋 Detailed Process Results</div>', unsafe_allow_html=True)
            results = [
                {
                    "PID": p.pid,
                    "Type": p.process_type,
                    "Arrival": p.arrival_time,
                    "Burst": p.burst_time,
                    "Priority": p.priority,
                    "Start": p.start_time,
                    "Finish": p.finish_time,
                    "Turnaround (TAT)": p.turnaround_time,
                    "Waiting (WT)": p.waiting_time,
                    "Response (RT)": p.response_time,
                }
                for p in simulator.completed_processes
            ]
            st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)

            with st.expander("🔍 Execution Trace"):
                for block in simulator.gantt_chart:
                    if block.pid == "IDLE":
                        st.text(f"  t={block.start:>3}–{block.end:<3}  │  ⏸  CPU Idle")
                    else:
                        lane = simulator.queue_label_map.get(block.queue_id, f"Queue {block.queue_id}")
                        st.text(f"  t={block.start:>3}–{block.end:<3}  │  {lane:<28}  │  {block.pid}")

        except Exception as e:
            st.error(f"❌ Simulation error: {str(e)}")
            import traceback
            st.code(traceback.format_exc(), language="python")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — HYBRID COMPARISON
# ═══════════════════════════════════════════════════════════════════════════════
with tab_compare:
    st.markdown('<div class="section-header">📊 Hybrid vs Single-Algorithm Comparison</div>', unsafe_allow_html=True)
    st.caption(
        "Compare your type-based hybrid policy against classic one-policy schedulers "
        "on the same workload."
    )

    rr_quantum = st.slider("Round Robin quantum for baseline RR", min_value=1, max_value=10, value=4, key="cmp_q")

    if st.button("▶  Run Hybrid Comparison", type="primary", key="run_compare"):
        try:
            processes = parse_processes(st.session_state.process_df, auto_classify=auto_classify_unknown)
            if not processes:
                st.warning("⚠️ Please add processes in the Hybrid Simulator tab first.")
                st.stop()

            comparison_data = {}
            classifier = build_classifier(auto_classify_unknown)

            hybrid_sim = HybridScheduler(
                clone_processes(processes),
                copy.deepcopy(hybrid_queue_config),
                classifier=classifier,
                fallback_type=SUPPORTED_PROCESS_TYPES[-1],
            )
            hybrid_sim.run()
            comparison_data["Hybrid (Type-Based)"] = calculate_metrics(hybrid_sim.completed_processes)

            baseline_algorithms = {
                "FCFS": FCFS(),
                "SJF": SJF(is_preemptive=False),
                "SRTF": SJF(is_preemptive=True),
                "Priority": Priority(is_preemptive=True),
                f"RR (q={rr_quantum})": RoundRobin(quantum=rr_quantum),
            }

            for alg_name, alg_inst in baseline_algorithms.items():
                procs_copy = clone_processes(processes)
                single_q = QueueConfig(0, alg_inst, upgrade_time=-1, downgrade_quantum=-1)
                sim = MLFQSimulator(procs_copy, [single_q])
                sim.run()
                comparison_data[alg_name] = calculate_metrics(sim.completed_processes)

            st.success("✅ Comparison complete!")

            best_algo = min(comparison_data.items(), key=lambda item: item[1]["avg_wt"])
            st.info(
                f"Lowest average waiting time: {best_algo[0]} ({best_algo[1]['avg_wt']} ms)"
            )

            st.write("")
            st.markdown('<div class="section-header">⏱️ Time Metrics</div>', unsafe_allow_html=True)
            fig_cmp = create_comparison_chart(comparison_data)
            st.plotly_chart(fig_cmp, use_container_width=True, config={"displayModeBar": False})

            st.write("")
            st.markdown('<div class="section-header">🚀 Throughput</div>', unsafe_allow_html=True)
            fig_tp = create_throughput_comparison(comparison_data)
            st.plotly_chart(fig_tp, use_container_width=True, config={"displayModeBar": False})

            st.write("")
            st.markdown('<div class="section-header">📋 Raw Numbers</div>', unsafe_allow_html=True)
            cmp_rows = []
            for algorithm_name, m in comparison_data.items():
                cmp_rows.append(
                    {
                        "Algorithm": algorithm_name,
                        "Avg WT": m["avg_wt"],
                        "Avg TAT": m["avg_tat"],
                        "Avg RT": m["avg_rt"],
                        "Throughput": m["throughput"],
                        "CPU Util %": m["cpu_util"],
                    }
                )
            st.dataframe(pd.DataFrame(cmp_rows), use_container_width=True, hide_index=True)

        except Exception as e:
            st.error(f"❌ Comparison error: {str(e)}")
            import traceback
            st.code(traceback.format_exc(), language="python")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — THEORY
# ═══════════════════════════════════════════════════════════════════════════════
with tab_theory:
    st.markdown('<div class="section-header">📖 CPU Scheduling Theory</div>', unsafe_allow_html=True)
    st.caption("Quick reference for the scheduling algorithms used in this simulator.")

    st.markdown("""
    <div class="theory-card">
        <div class="theory-title">🔀 Hybrid Multi-Queue Scheduling</div>
        <div class="theory-body">
            Hybrid scheduling classifies each process into a type queue and applies a dedicated policy per queue. 
            Example mapping: <strong>real-time → Priority</strong>, <strong>interactive → Round Robin</strong>, 
            <strong>batch → FCFS/SJF</strong>. The CPU always picks from the highest-priority non-empty queue.<br><br>
            <strong>Key rules:</strong><br>
            1. Classify incoming process by type<br>
            2. Route to that type's configured algorithm queue<br>
            3. Serve queues by global precedence (real-time first, then interactive, then batch)<br>
            4. Inside each queue, run the selected algorithm exactly as defined
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_t1, col_t2 = st.columns(2)

    with col_t1:
        st.markdown("""
        <div class="theory-card">
            <div class="theory-title">📌 FCFS — First Come First Serve</div>
            <div class="theory-body">
                Processes are executed in order of arrival. Simple but causes the 
                <strong>convoy effect</strong> — short processes stuck behind long ones.<br><br>
                • Non-preemptive<br>
                • No starvation<br>
                • Poor average waiting time for mixed workloads
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="theory-card">
            <div class="theory-title">📌 SJF — Shortest Job First</div>
            <div class="theory-body">
                Picks the process with the shortest burst time. Provably <strong>optimal</strong> 
                for minimizing average waiting time (non-preemptive case).<br><br>
                • Non-preemptive variant<br>
                • Can cause starvation of long processes<br>
                • Requires burst time prediction in practice
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_t2:
        st.markdown("""
        <div class="theory-card">
            <div class="theory-title">📌 SRTF — Shortest Remaining Time First</div>
            <div class="theory-body">
                Preemptive version of SJF. If a new process arrives with a shorter remaining time 
                than the currently running process, it <strong>preempts</strong> immediately.<br><br>
                • Preemptive<br>
                • Optimal average waiting time<br>
                • Higher context-switch overhead
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="theory-card">
            <div class="theory-title">📌 Round Robin (RR)</div>
            <div class="theory-body">
                Each process gets a fixed <strong>time quantum</strong>. After the quantum expires, 
                the process moves to the back of the queue. Balances fairness and responsiveness.<br><br>
                • Preemptive<br>
                • No starvation<br>
                • Performance depends heavily on quantum size<br>
                • Small quantum → high overhead, large quantum → approaches FCFS
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div class="theory-card">
        <div class="theory-title">📌 Priority Scheduling</div>
        <div class="theory-body">
            Each process is assigned a priority. The CPU always runs the highest-priority ready process. 
            Can be preemptive or non-preemptive. <strong>Aging</strong> is used to prevent starvation 
            of low-priority processes.<br><br>
            • Lower number = Higher priority (in this simulator)<br>
            • Preemptive variant implemented here<br>
            • Starvation possible without aging
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="theory-card">
        <div class="theory-title">📐 Key Metrics</div>
        <div class="theory-body">
            <strong>Turnaround Time (TAT)</strong> = Finish Time − Arrival Time<br>
            <strong>Waiting Time (WT)</strong> = TAT − Burst Time<br>
            <strong>Response Time (RT)</strong> = First CPU Time − Arrival Time<br>
            <strong>Throughput</strong> = Number of Processes / Total Time<br>
            <strong>CPU Utilization</strong> = (Total Burst Time / Total Time) × 100%
        </div>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="footer">
    Hybrid CPU Scheduling Simulator · Type-Based Multi-Policy Engine<br>
    Built with Streamlit & Plotly · Operating Systems Project
</div>
""", unsafe_allow_html=True)

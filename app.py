import streamlit as st
import pandas as pd
import copy
from simulator.models import Process
from simulator.algorithms import FCFS, SJF, Priority, RoundRobin
from simulator.mlfq import MLFQSimulator, QueueConfig
from utils.visuals import (
    create_gantt_chart,
    calculate_metrics,
    create_comparison_chart,
    create_throughput_comparison,
)

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Hybrid CPU Scheduler · MLFQ Simulator",
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
        Interactive Multi-Level Feedback Queue simulator with real-time 
        Gantt chart visualization, performance analytics, and algorithm comparison.
    </div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR — Queue Configuration
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### ⚙️ Queue Configuration")
    st.caption("Configure the MLFQ levels below")
    st.divider()

    num_queues = st.slider(
        "Number of Queue Levels",
        min_value=1, max_value=5, value=3,
        help="More levels allow finer-grained scheduling."
    )

    algorithms_map = {
        "FCFS": lambda _q: FCFS(),
        "SJF (Non-Preemptive)": lambda _q: SJF(is_preemptive=False),
        "SRTF (Preemptive SJF)": lambda _q: SJF(is_preemptive=True),
        "Priority (Preemptive)": lambda _q: Priority(is_preemptive=True),
        "Round Robin": lambda q: RoundRobin(quantum=q),
    }

    queues_config: list[QueueConfig] = []

    for i in range(num_queues):
        label = f"🔹 Queue {i} — {'Highest Priority' if i == 0 else ('Lowest Priority' if i == num_queues - 1 else f'Level {i}')}"
        with st.expander(label, expanded=(i == 0)):
            alg_name = st.selectbox(
                "Algorithm",
                list(algorithms_map.keys()),
                key=f"alg_{i}",
                index=4 if i < num_queues - 1 else 0,  # Default: RR for top queues, FCFS for last
            )

            quantum = 4
            if alg_name == "Round Robin":
                quantum = st.number_input(
                    "Time Quantum",
                    min_value=1, value=4, key=f"q_{i}",
                    help="Number of ticks before context switch."
                )

            alg_inst = algorithms_map[alg_name](quantum)

            upgrade = -1
            if i > 0:
                upgrade = st.number_input(
                    f"Aging upgrade to Q{i-1} (ticks)",
                    min_value=-1, value=10, key=f"up_{i}",
                    help="-1 disables aging. Otherwise, after this many ticks waiting, process promotes up."
                )

            dq = -1
            if i < num_queues - 1 and alg_name == "Round Robin":
                dq = st.number_input(
                    f"Quantum limit to demote to Q{i+1}",
                    min_value=-1, value=1, key=f"dq_{i}",
                    help="-1 disables demotion."
                )

            queues_config.append(QueueConfig(i, alg_inst, upgrade_time=upgrade, downgrade_quantum=dq))

    st.divider()
    st.caption("Built for OS Course · MLFQ Simulator")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN CONTENT — Tabs
# ═══════════════════════════════════════════════════════════════════════════════
tab_sim, tab_compare, tab_theory = st.tabs(["🖥️  Simulator", "📊  Algorithm Comparison", "📖  Theory"])

# ── Default process data ──────────────────────────────────────────────────────
default_data = [
    {"PID": "P1", "Arrival Time": 0, "Burst Time": 8,  "Priority": 2},
    {"PID": "P2", "Arrival Time": 1, "Burst Time": 4,  "Priority": 0},
    {"PID": "P3", "Arrival Time": 2, "Burst Time": 9,  "Priority": 1},
    {"PID": "P4", "Arrival Time": 3, "Burst Time": 5,  "Priority": 3},
    {"PID": "P5", "Arrival Time": 5, "Burst Time": 2,  "Priority": 4},
]


def parse_processes(df: pd.DataFrame) -> list[Process]:
    """Parse DataFrame rows into Process objects."""
    processes = []
    for _, row in df.iterrows():
        if pd.isna(row.get("PID")):
            continue
        processes.append(Process(
            pid=str(row["PID"]),
            arrival_time=int(row["Arrival Time"]),
            burst_time=int(row["Burst Time"]),
            priority=int(row.get("Priority", 0)),
        ))
    return processes


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — SIMULATOR
# ═══════════════════════════════════════════════════════════════════════════════
with tab_sim:
    st.markdown('<div class="section-header">📝 Process Table</div>', unsafe_allow_html=True)
    st.caption("Add, edit, or remove processes. Click ➕ at the bottom to add rows.")

    df_input = st.data_editor(
        pd.DataFrame(default_data),
        num_rows="dynamic",
        width="stretch",
        key="process_editor",
    )

    st.write("")  # spacing
    col_btn, col_space = st.columns([1, 3])
    with col_btn:
        run_clicked = st.button("▶  Run Simulation", type="primary", use_container_width=True)

    if run_clicked:
        try:
            processes = parse_processes(df_input)
            if not processes:
                st.warning("⚠️ Please add at least one process.")
                st.stop()

            simulator = MLFQSimulator(processes, queues_config)
            simulator.run()

            st.success(f"✅ Simulation complete — {len(simulator.completed_processes)} processes scheduled in {simulator.current_time} ticks")

            # ── KPI Metrics Row ───────────────────────────────────────────
            metrics = calculate_metrics(simulator.completed_processes)

            st.write("")
            st.markdown('<div class="section-header">📈 Performance Metrics</div>', unsafe_allow_html=True)

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

            # ── Gantt Chart ───────────────────────────────────────────────
            st.write("")
            st.write("")
            st.markdown('<div class="section-header">📊 Gantt Chart</div>', unsafe_allow_html=True)

            fig = create_gantt_chart(simulator.gantt_chart)
            if fig:
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
            else:
                st.info("No execution data to display.")

            # ── Process Results Table ─────────────────────────────────────
            st.write("")
            st.markdown('<div class="section-header">📋 Detailed Results</div>', unsafe_allow_html=True)

            results = [{
                "PID": p.pid,
                "Arrival": p.arrival_time,
                "Burst": p.burst_time,
                "Priority": p.priority,
                "Start": p.start_time,
                "Finish": p.finish_time,
                "Turnaround (TAT)": p.turnaround_time,
                "Waiting (WT)": p.waiting_time,
                "Response (RT)": p.response_time,
            } for p in simulator.completed_processes]

            st.dataframe(
                pd.DataFrame(results),
                width="stretch",
                hide_index=True,
            )

            # ── Execution Log ─────────────────────────────────────────────
            with st.expander("🔍 Execution Trace (Gantt Blocks)"):
                for block in simulator.gantt_chart:
                    if block.pid == "IDLE":
                        st.text(f"  t={block.start:>3}–{block.end:<3}  │  ⏸  CPU Idle")
                    else:
                        st.text(f"  t={block.start:>3}–{block.end:<3}  │  Q{block.queue_id}  │  {block.pid}")

        except Exception as e:
            st.error(f"❌ Simulation error: {str(e)}")
            import traceback
            st.code(traceback.format_exc(), language="python")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — ALGORITHM COMPARISON
# ═══════════════════════════════════════════════════════════════════════════════
with tab_compare:
    st.markdown('<div class="section-header">📊 Compare Scheduling Algorithms</div>', unsafe_allow_html=True)
    st.caption(
        "Run the same process set through different classic scheduling algorithms "
        "and compare their performance metrics side-by-side."
    )

    rr_quantum = st.slider("Round Robin Quantum for comparison", min_value=1, max_value=10, value=4, key="cmp_q")

    if st.button("▶  Run Comparison", type="primary", key="run_compare"):
        try:
            processes = parse_processes(df_input)
            if not processes:
                st.warning("⚠️ Please add processes in the Simulator tab first.")
                st.stop()

            comparison_algos = {
                "FCFS": FCFS(),
                "SJF": SJF(is_preemptive=False),
                "SRTF": SJF(is_preemptive=True),
                "Priority": Priority(is_preemptive=True),
                f"RR (q={rr_quantum})": RoundRobin(quantum=rr_quantum),
            }

            comparison_data = {}

            for alg_name, alg_inst in comparison_algos.items():
                # Deep-copy processes for each run
                procs_copy = [
                    Process(
                        pid=p.pid,
                        arrival_time=p.arrival_time,
                        burst_time=p.burst_time,
                        priority=p.priority,
                    )
                    for p in processes
                ]
                # Single-queue simulation
                q_cfg = QueueConfig(0, alg_inst, upgrade_time=-1, downgrade_quantum=-1)
                sim = MLFQSimulator(procs_copy, [q_cfg])
                sim.run()
                comparison_data[alg_name] = calculate_metrics(sim.completed_processes)

            st.success("✅ Comparison complete!")

            # ── Metrics comparison chart ──────────────────────────────────
            st.write("")
            st.markdown('<div class="section-header">⏱️ Time Metrics</div>', unsafe_allow_html=True)
            fig_cmp = create_comparison_chart(comparison_data)
            st.plotly_chart(fig_cmp, width="stretch", config={"displayModeBar": False})

            # ── Throughput chart ───────────────────────────────────────────
            st.write("")
            st.markdown('<div class="section-header">🚀 Throughput</div>', unsafe_allow_html=True)
            fig_tp = create_throughput_comparison(comparison_data)
            st.plotly_chart(fig_tp, width="stretch", config={"displayModeBar": False})

            # ── Raw numbers table ─────────────────────────────────────────
            st.write("")
            st.markdown('<div class="section-header">📋 Raw Numbers</div>', unsafe_allow_html=True)
            cmp_rows = []
            for alg, m in comparison_data.items():
                cmp_rows.append({
                    "Algorithm": alg,
                    "Avg WT": m["avg_wt"],
                    "Avg TAT": m["avg_tat"],
                    "Avg RT": m["avg_rt"],
                    "Throughput": m["throughput"],
                    "CPU Util %": m["cpu_util"],
                })
            st.dataframe(pd.DataFrame(cmp_rows), width="stretch", hide_index=True)

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
        <div class="theory-title">🔄 Multi-Level Feedback Queue (MLFQ)</div>
        <div class="theory-body">
            MLFQ uses multiple ready queues with different priority levels and scheduling algorithms. 
            New processes enter the highest-priority queue. If a process uses its full time quantum without completing, 
            it is <strong>demoted</strong> to a lower-priority queue. Processes that wait too long in a lower queue 
            can be <strong>promoted (aged)</strong> back up to prevent starvation.<br><br>
            <strong>Key rules:</strong><br>
            1. If Priority(A) > Priority(B) → A runs<br>
            2. If Priority(A) = Priority(B) → Run in RR order<br>
            3. New jobs start at highest priority<br>
            4. If a job uses its time allotment → demote<br>
            5. Periodically boost all jobs to prevent starvation
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
    Hybrid CPU Scheduling Simulator · Multi-Level Feedback Queue<br>
    Built with Streamlit & Plotly · Operating Systems Project
</div>
""", unsafe_allow_html=True)

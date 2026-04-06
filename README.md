# ⚡ Hybrid CPU Scheduling Simulator

A modern, interactive **type-based multi-policy CPU scheduler** built with **Python**, **Streamlit**, and **Plotly**. Instead of one global policy, the simulator routes each process type to its own queue and algorithm (for example: real-time → Priority, interactive → Round Robin, batch → FCFS/SJF).

## ✨ Features

- **Hybrid Type Routing**: Configure separate queues for `real-time`, `interactive`, and `batch` processes.
- **Process Generator + Classifier**:
  - Generate workloads with custom counts per process type.
  - Auto-classify missing/invalid types with heuristics.
- **Multiple Scheduling Algorithms**:
  - First Come First Serve (FCFS)
  - Shortest Job First (SJF)
  - Shortest Remaining Time First (SRTF) - Preemptive SJF
  - Round Robin (RR) with customizable time quanta
  - Priority Scheduling (Preemptive)
- **Hybrid Scheduling Engine**:
  - Type-aware queues run independently with their own algorithm.
  - CPU picks from queues using global precedence (real-time > interactive > batch).
- **Interactive Visualizations**:
  - Gantt timeline with lane labels per type/algorithm queue.
  - Overall performance metrics (WT, TAT, RT, Throughput, CPU Utilization).
  - Per-type metrics table including per-type CPU share.
- **Hybrid vs Single Comparison Toolkit**: Compare hybrid scheduling against FCFS/SJF/SRTF/Priority/RR on the same workload.
- **Educational "Theory" Section**: Built-in quick references for OS scheduling concepts.
- **Premium UI**: Dark glassmorphism theme, smooth animations, and responsive layout.

---

## 🛠️ Installation

### 1. Prerequisites
Ensure you have [Python 3.8+](https://www.python.org/downloads/) installed.

### 2. Clone the Repository
```bash
git clone <your-repository-url>
cd Hybrid-CPU-Scheduling-Simulator-
```

### 3. Set Up a Virtual Environment (Recommended)
```bash
python -m venv .venv

# On Windows:
.venv\Scripts\activate

# On macOS/Linux:
source .venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 🚀 Usage

Run the Streamlit application:
```bash
streamlit run app.py
```

The simulator will open automatically in your default web browser at `http://localhost:8501`.

### How to use the Simulator:
1. **Configure Hybrid Routing**: In the sidebar, choose one algorithm per process type queue.
2. **Create Workload**: Use the built-in generator or manually edit the process table (`PID`, `Type`, `Arrival Time`, `Burst Time`, `Priority`).
3. **Classify**: Keep auto-classifier enabled to infer type when `Type` is blank/invalid.
4. **Run Hybrid**: Click "Run Hybrid Simulation" to render Gantt output and metrics.
5. **Compare**: Use the "Hybrid vs Single" tab to benchmark hybrid scheduling against classic single-policy baselines.

---

## 📁 Project Structure

```text
Hybrid-CPU-Scheduling-Simulator-/
├── app.py                  # Main Streamlit application and UI definitions
├── requirements.txt        # Python package dependencies
├── simulator/              # Core simulation logic package
│   ├── __init__.py
│   ├── algorithms.py       # Implementation of FCFS, SJF/SRTF, RR, Priority
│   ├── hybrid.py           # Type-based hybrid scheduling engine and classifier helpers
│   ├── mlfq.py             # Multi-Level Feedback Queue engine
│   └── models.py           # Data classes for Process and GanttBlock
└── utils/                  # Utility functions package
    ├── __init__.py
    └── visuals.py          # Plotly charting functions (Gantt, metrics, etc.)
```

## 🧠 Core Architecture Highlights
- **Classifier + Router**: Every arriving process is normalized/classified, then routed to the queue mapped to its process type.
- **Independent Queue Policies**: Each type queue runs its own scheduling rule while the CPU applies global queue precedence.
- **Tick-Based Engine**: The simulation runs on a discrete tick loop capped at 10,000 ticks to avoid runaway configs.
- **Evaluation-Friendly Output**: Provides Gantt timeline, overall metrics, per-type metrics, and hybrid-vs-single comparison charts.

---

## 🤝 Contributing
Contributions, issues, and feature requests are welcome! Feel free to check the issues page.

## 📝 License
This project is open-source and available under the [MIT License](LICENSE).

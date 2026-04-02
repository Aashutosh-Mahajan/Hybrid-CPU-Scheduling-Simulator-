# ⚡ Hybrid CPU Scheduling Simulator

A modern, interactive **Multi-Level Feedback Queue (MLFQ)** CPU scheduling simulator built with **Python**, **Streamlit**, and **Plotly**. This tool allows students and professionals to visualize and analyze how different operating system scheduling algorithms perform under various workloads.

## ✨ Features

- **Dynamic MLFQ Configuration**: Build complex multi-level queues with up to 5 tiers.
- **Multiple Scheduling Algorithms**:
  - First Come First Serve (FCFS)
  - Shortest Job First (SJF)
  - Shortest Remaining Time First (SRTF) - Preemptive SJF
  - Round Robin (RR) with customizable time quanta
  - Priority Scheduling (Preemptive)
- **Advanced Queue Mechanics**: 
  - **Aging / Promotion**: Prevent starvation by promoting processes that wait too long.
  - **Demotion**: Downgrade processes that exhaust their Round Robin time quantum.
- **Interactive Visualizations**:
  - Real-time Gantt Chart rendering.
  - Performance metric dashboards (Turnaround Time, Waiting Time, Response Time, Throughput, CPU Utilization).
- **Algorithm Comparison Toolkit**: Run a single set of processes against multiple classic algorithms and compare their performance side-by-side using interactive bar charts.
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
1. **Configure Queues**: Use the left sidebar to define the number of queue levels, set their core algorithms, and adjust aging/demotion thresholds.
2. **Define Processes**: In the main "Simulator" tab, add processes by specifying PID, Arrival Time, Burst Time, and Priority. 
3. **Run**: Click exactly "Run Simulation" to generate the Gantt chart and metric tables.
4. **Compare**: Switch over to the "Algorithm Comparison" tab to test your process dataset against individual algorithms to see which performs best.

---

## 📁 Project Structure

```text
Hybrid-CPU-Scheduling-Simulator-/
├── app.py                  # Main Streamlit application and UI definitions
├── requirements.txt        # Python package dependencies
├── simulator/              # Core simulation logic package
│   ├── __init__.py
│   ├── algorithms.py       # Implementation of FCFS, SJF, RR, Priority
│   ├── mlfq.py             # Multi-Level Feedback Queue engine
│   └── models.py           # Data classes for Process and GanttBlock
└── utils/                  # Utility functions package
    ├── __init__.py
    └── visuals.py          # Plotly charting functions (Gantt, metrics, etc.)
```

## 🧠 Core Architecture Highlights
- **Process State Management**: The MLFQ engine rigidly maintains the invariant that a running process is decoupled from the waiting queues, accurately reflecting real OS context switching.
- **Tick-Based Engine**: The simulation runs on a discrete tick loop safely capped at 10,000 ticks to prevent infinite loops from poorly configured aging/demotion rules.

---

## 🤝 Contributing
Contributions, issues, and feature requests are welcome! Feel free to check the issues page.

## 📝 License
This project is open-source and available under the [MIT License](LICENSE).

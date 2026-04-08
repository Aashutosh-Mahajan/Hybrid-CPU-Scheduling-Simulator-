"""
simulator/mlfq.py
─────────────────
Multi-Level Feedback Queue (MLFQ) simulator.

Purpose
───────
Implements a generic, configurable MLFQ engine.  In this project it is used
mainly as a single-queue baseline runner (when the comparison tab runs classic
algorithms like FCFS or RR against the hybrid scheduler on the same workload).

How MLFQ works
──────────────
  • There are N priority queues (Q0 = highest priority, QN-1 = lowest).
  • New processes always enter Q0.
  • A process is demoted to a lower queue when it exhausts its time quantum
    (configurable per-queue via downgrade_quantum).
  • A process waiting too long in a lower queue can be promoted back to a
    higher queue (aging, controlled by upgrade_time).
  • The CPU always serves the highest non-empty queue.

Key invariant (maintained throughout the run loop)
──────────────────────────────────────────────────
  The currently-running process is NEVER inside any queue's .queue list.
  It is held in the local variable `current_running`.  When the scheduler
  needs to stop it (quantum expiry, preemption, completion) it explicitly
  re-inserts it into the appropriate queue — or drops it if finished.

Safety limit
────────────
  MAX_SIMULATION_TICKS = 10 000.  The loop exits if this is reached, preventing
  infinite loops on malformed inputs.

Classes
───────
  QueueConfig    — Configuration for one queue level.
  MLFQSimulator  — The main simulation engine.
"""

from typing import List, Optional
from simulator.models import Process, GanttBlock
from simulator.algorithms import SchedulingAlgorithm

# Hard limit on simulation length to prevent runaway loops.
MAX_SIMULATION_TICKS = 10000


# ─────────────────────────────────────────────────────────────────────────────
# QueueConfig — describes one level in the MLFQ hierarchy
# ─────────────────────────────────────────────────────────────────────────────

class QueueConfig:
    """
    Configuration for a single MLFQ queue level.

    Attributes:
        id               : Queue index (0 = highest priority).
        algorithm        : SchedulingAlgorithm instance that decides which
                           process to pick from this queue each tick.
        upgrade_time     : After a process has waited this many ticks in this
                           queue it is promoted one level up (aging).
                           Set to -1 to disable aging for this queue.
        downgrade_quantum: When the running process exhausts this many ticks it
                           is moved to the next-lower queue.
                           Set to -1 to keep the process in the same queue on
                           quantum expiry (useful for single-queue baselines).
        queue            : The live list of ready processes at this level.
                           Managed entirely by MLFQSimulator.run().
    """

    def __init__(
        self,
        id: int,
        algorithm: SchedulingAlgorithm,
        upgrade_time: int = -1,
        downgrade_quantum: int = -1,
    ):
        self.id = id
        self.algorithm = algorithm
        self.upgrade_time = upgrade_time       # ticks before promotion (-1 = off)
        self.downgrade_quantum = downgrade_quantum  # ticks before demotion (-1 = off)
        self.queue: List[Process] = []         # ready processes at this level


# ─────────────────────────────────────────────────────────────────────────────
# MLFQSimulator — tick-based simulation engine
# ─────────────────────────────────────────────────────────────────────────────

class MLFQSimulator:
    """
    Tick-based Multi-Level Feedback Queue scheduler.

    Usage:
        queues = [QueueConfig(0, FCFS())]            # single-queue baseline
        sim    = MLFQSimulator(processes, queues)
        sim.run()
        # results: sim.completed_processes, sim.gantt_chart

    Attributes (available after run()):
        current_time         : Total ticks elapsed (makespan).
        gantt_chart          : List[GanttBlock] in chronological order.
        completed_processes  : Processes in completion order with metrics filled.
    """

    def __init__(self, processes: List[Process], queues: List[QueueConfig]):
        self.processes = processes
        self.queues = queues
        self.current_time = 0
        self.gantt_chart: List[GanttBlock] = []
        self.completed_processes: List[Process] = []

    def run(self):
        """
        Execute the full MLFQ simulation.

        The loop advances one tick at a time and performs these steps:
          1. Admit arrivals — move processes whose arrival_time <= current_time
             into Q0.
          2. Check quantum expiry — demote or re-queue the running process if
             its time-slice is up.
          3. Aging — promote processes that have waited too long in a lower queue.
          4. Find the highest-priority non-empty queue.
          5. Preempt across queues — if a higher-priority queue has become
             non-empty while a lower-priority process is running, preempt it.
          6. Preempt within queue — for preemptive non-RR algorithms (SRTF,
             Priority) check whether a better process has arrived in the same queue.
          7. Schedule — if CPU is free, pick the best process from the highest queue.
          8. Execute one tick — decrement remaining_time, extend/append Gantt block,
             collect the process if it finishes.
        """

        # ── Reset all process state from a previous run ───────────────────────
        for p in self.processes:
            p.remaining_time = p.burst_time
            p.start_time = -1
            p.finish_time = -1
            p.waiting_time = 0
            p.turnaround_time = 0
            p.response_time = -1
            p.current_queue = 0
            p.time_in_current_queue = 0

        # Clear queue lists from any previous run.
        for q in self.queues:
            q.queue.clear()

        self.gantt_chart.clear()
        self.completed_processes.clear()
        self.current_time = 0

        # Sort by arrival so we can pop from the front efficiently.
        remaining_processes = sorted(self.processes, key=lambda x: x.arrival_time)

        # Track the currently-running process (None = CPU idle).
        current_running: Optional[Process] = None
        current_queue_id: int = -1   # queue the running process belongs to
        current_running_slice: int = 0  # ticks consumed from the current quantum

        # ── Main simulation loop ──────────────────────────────────────────────
        # Continue while there are un-admitted, queued, or running processes.
        iterations = 0
        while remaining_processes or any(q.queue for q in self.queues) or current_running:

            # Safety guard — stop if the simulation runs too long (iteration based).
            iterations += 1
            if iterations >= 1000000:
                break

            # ┌─ Speedhack: Fast-forward idle time if queues are completely empty ─┐
            if not current_running and not any(q.queue for q in self.queues) and remaining_processes:
                next_arrival = remaining_processes[0].arrival_time
                if self.current_time < next_arrival:
                    if self.gantt_chart and self.gantt_chart[-1].pid == "IDLE":
                        self.gantt_chart[-1].end = next_arrival
                    else:
                        self.gantt_chart.append(
                            GanttBlock(-1, "IDLE", self.current_time, next_arrival)
                        )
                    self.current_time = next_arrival
                    continue
            # └─────────────────────────────────────────────────────────────┘

            # ┌─ Step 1: Admit arrivals ─────────────────────────────────────┐
            # All processes that have arrived by the current tick go into Q0.
            while remaining_processes and remaining_processes[0].arrival_time <= self.current_time:
                p = remaining_processes.pop(0)
                self.queues[0].queue.append(p)  # always start in the highest queue
            # └─────────────────────────────────────────────────────────────┘

            # ┌─ Step 2: Round-Robin quantum expiry ────────────────────────┐
            # If the running process has used up its full quantum, move it
            # either to the next-lower queue (demotion) or back of same queue.
            if current_running and current_queue_id >= 0:
                q_cfg = self.queues[current_queue_id]
                quantum_up = (
                    q_cfg.algorithm.quantum is not None
                    and current_running_slice >= q_cfg.algorithm.quantum
                    and not current_running.is_finished()
                )
                if quantum_up:
                    if q_cfg.downgrade_quantum > -1 and current_queue_id < len(self.queues) - 1:
                        # Demote to the next lower queue.
                        next_q = current_queue_id + 1
                        current_running.current_queue = next_q
                        current_running.time_in_current_queue = 0
                        self.queues[next_q].queue.append(current_running)
                    else:
                        # No demotion configured — put back at end of the same queue.
                        q_cfg.queue.append(current_running)
                    # CPU is now free.
                    current_running = None
                    current_queue_id = -1
                    current_running_slice = 0
            # └─────────────────────────────────────────────────────────────┘

            # ┌─ Step 3: Aging — promote long-waiting processes ────────────┐
            # Check queues Q1..QN-1; processes that have waited long enough
            # are moved one level up to prevent starvation.
            for i in range(1, len(self.queues)):
                q_cfg = self.queues[i]
                if q_cfg.upgrade_time > 0:
                    to_upgrade = []
                    for p in q_cfg.queue:
                        p.time_in_current_queue += 1
                        if p.time_in_current_queue >= q_cfg.upgrade_time:
                            to_upgrade.append(p)
                    for p in to_upgrade:
                        q_cfg.queue.remove(p)
                        target = max(0, i - 1)  # one level up (never below 0)
                        p.current_queue = target
                        p.time_in_current_queue = 0
                        self.queues[target].queue.append(p)
            # └─────────────────────────────────────────────────────────────┘

            # ┌─ Step 4: Find the highest-priority non-empty queue ─────────┐
            highest_q = -1
            for q in self.queues:
                if q.queue:
                    highest_q = q.id
                    break  # queues are sorted by priority; first non-empty wins
            # └─────────────────────────────────────────────────────────────┘

            # ┌─ Step 5: Cross-queue preemption ────────────────────────────┐
            # If a higher-priority queue has work and a lower-priority process
            # is running, preempt the running process immediately.
            if current_running and highest_q >= 0 and highest_q < current_queue_id:
                # Push the preempted process back to the front of its old queue.
                self.queues[current_queue_id].queue.insert(0, current_running)
                current_running = None
                current_queue_id = -1
                current_running_slice = 0
            # └─────────────────────────────────────────────────────────────┘

            # ┌─ Step 6: Within-queue preemption (SRTF / Priority) ─────────┐
            # For preemptive algorithms that are NOT Round Robin (quantum=None):
            # compare the running process against newly arrived processes in the
            # same queue and preempt if a better candidate exists.
            if current_running and highest_q == current_queue_id and highest_q >= 0:
                q_cfg = self.queues[current_queue_id]
                if q_cfg.algorithm.is_preemptive and q_cfg.algorithm.quantum is None:
                    # Temporarily insert the running process into the queue
                    # so select_process() can compare it against all candidates.
                    q_cfg.queue.insert(0, current_running)
                    best = q_cfg.algorithm.select_process(q_cfg.queue, current_running)
                    if best != current_running:
                        # A better process won — leave current_running in the queue
                        # (already inserted above) and free the CPU.
                        current_running = None
                        current_queue_id = -1
                        current_running_slice = 0
                    else:
                        # Current is still the best — remove the temporary insertion.
                        q_cfg.queue.remove(current_running)
            # └─────────────────────────────────────────────────────────────┘

            # ┌─ Step 7: Schedule if CPU is free ───────────────────────────┐
            # Scan from the highest-priority queue downward and pick the first
            # available process using that queue's algorithm.
            if not current_running:
                for q in self.queues:
                    if q.queue:
                        selected = q.algorithm.select_process(q.queue, None)
                        if selected:
                            q.queue.remove(selected)       # take it out of the queue
                            current_running = selected
                            current_queue_id = q.id
                            current_running_slice = 0
                            # Record first CPU touch (response time).
                            if current_running.start_time == -1:
                                current_running.start_time = self.current_time
                                current_running.response_time = (
                                    self.current_time - current_running.arrival_time
                                )
                            break
            # └─────────────────────────────────────────────────────────────┘

            # ┌─ Step 8: Execute one tick ──────────────────────────────────┐
            if current_running:
                # Extend the last Gantt block if it is the same process/queue,
                # otherwise append a new block.
                if (
                    self.gantt_chart
                    and self.gantt_chart[-1].pid == current_running.pid
                    and self.gantt_chart[-1].queue_id == current_queue_id
                ):
                    self.gantt_chart[-1].end += 1
                else:
                    self.gantt_chart.append(
                        GanttBlock(
                            current_queue_id,
                            current_running.pid,
                            self.current_time,
                            self.current_time + 1,
                        )
                    )

                current_running.remaining_time -= 1
                current_running_slice += 1

                # Check if the process has finished this tick.
                if current_running.is_finished():
                    current_running.finish_time = self.current_time + 1
                    current_running.turnaround_time = (
                        current_running.finish_time - current_running.arrival_time
                    )
                    current_running.waiting_time = (
                        current_running.turnaround_time - current_running.burst_time
                    )
                    self.completed_processes.append(current_running)
                    # Free the CPU.
                    current_running = None
                    current_queue_id = -1
                    current_running_slice = 0
            else:
                # CPU is idle this tick — record in Gantt chart.
                if self.gantt_chart and self.gantt_chart[-1].pid == "IDLE":
                    self.gantt_chart[-1].end += 1
                else:
                    self.gantt_chart.append(
                        GanttBlock(-1, "IDLE", self.current_time, self.current_time + 1)
                    )
            # └─────────────────────────────────────────────────────────────┘

            self.current_time += 1  # advance the clock by one tick

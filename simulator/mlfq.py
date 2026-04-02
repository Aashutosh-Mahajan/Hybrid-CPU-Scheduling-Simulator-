from typing import List, Optional
from simulator.models import Process, GanttBlock
from simulator.algorithms import SchedulingAlgorithm

MAX_SIMULATION_TICKS = 10000  # Safety limit


class QueueConfig:
    def __init__(self, id: int, algorithm: SchedulingAlgorithm,
                 upgrade_time: int = -1, downgrade_quantum: int = -1):
        self.id = id
        self.algorithm = algorithm
        self.upgrade_time = upgrade_time
        self.downgrade_quantum = downgrade_quantum
        self.queue: List[Process] = []


class MLFQSimulator:
    def __init__(self, processes: List[Process], queues: List[QueueConfig]):
        self.processes = processes
        self.queues = queues
        self.current_time = 0
        self.gantt_chart: List[GanttBlock] = []
        self.completed_processes: List[Process] = []

    def run(self):
        """
        Run the MLFQ simulation.

        Design invariant: the currently-running process is NEVER inside any
        queue's .queue list.  It is tracked separately via `current_running`.
        When we need to stop running it (preemption, quantum expiry, …), we
        explicitly put it back into the appropriate queue.
        """

        # ── Reset state ──────────────────────────────────────────────────
        for p in self.processes:
            p.remaining_time = p.burst_time
            p.start_time = -1
            p.finish_time = -1
            p.waiting_time = 0
            p.turnaround_time = 0
            p.response_time = -1
            p.current_queue = 0
            p.time_in_current_queue = 0

        for q in self.queues:
            q.queue.clear()

        self.gantt_chart.clear()
        self.completed_processes.clear()
        self.current_time = 0

        remaining_processes = sorted(self.processes, key=lambda x: x.arrival_time)

        current_running: Optional[Process] = None
        current_queue_id: int = -1
        current_running_slice: int = 0

        # ── Main loop ────────────────────────────────────────────────────
        while remaining_processes or any(q.queue for q in self.queues) or current_running:
            if self.current_time >= MAX_SIMULATION_TICKS:
                break

            # ┌─ 1. Handle arrivals ──────────────────────────────────────┐
            while remaining_processes and remaining_processes[0].arrival_time <= self.current_time:
                p = remaining_processes.pop(0)
                self.queues[0].queue.append(p)
            # └───────────────────────────────────────────────────────────┘

            # ┌─ 2. Check Round-Robin quantum expiry ─────────────────────┐
            if current_running and current_queue_id >= 0:
                q_cfg = self.queues[current_queue_id]
                if (q_cfg.algorithm.quantum is not None
                        and current_running_slice >= q_cfg.algorithm.quantum
                        and not current_running.is_finished()):
                    # Quantum expired — demote or re-enqueue
                    if (q_cfg.downgrade_quantum > -1
                            and current_queue_id < len(self.queues) - 1):
                        next_q = current_queue_id + 1
                        current_running.current_queue = next_q
                        current_running.time_in_current_queue = 0
                        self.queues[next_q].queue.append(current_running)
                    else:
                        q_cfg.queue.append(current_running)  # back of same queue
                    current_running = None
                    current_queue_id = -1
                    current_running_slice = 0
            # └───────────────────────────────────────────────────────────┘

            # ┌─ 3. Aging (promote waiting processes) ────────────────────┐
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
                        target = max(0, i - 1)
                        p.current_queue = target
                        p.time_in_current_queue = 0
                        self.queues[target].queue.append(p)
            # └───────────────────────────────────────────────────────────┘

            # ┌─ 4. Find highest-priority non-empty queue ────────────────┐
            highest_q = -1
            for q in self.queues:
                if q.queue:
                    highest_q = q.id
                    break
            # └───────────────────────────────────────────────────────────┘

            # ┌─ 5. Preemption by higher-priority queue ──────────────────┐
            if (current_running
                    and highest_q >= 0
                    and highest_q < current_queue_id):
                # A higher-priority queue has work — preempt unconditionally
                self.queues[current_queue_id].queue.insert(0, current_running)
                current_running = None
                current_queue_id = -1
                current_running_slice = 0
            # └───────────────────────────────────────────────────────────┘

            # ┌─ 6. Preemption within same queue (SRTF / Priority only) ─┐
            if (current_running
                    and highest_q == current_queue_id
                    and highest_q >= 0):
                q_cfg = self.queues[current_queue_id]
                # Only for preemptive algorithms that are NOT round-robin
                if q_cfg.algorithm.is_preemptive and q_cfg.algorithm.quantum is None:
                    # Temporarily add running process to queue for comparison
                    q_cfg.queue.insert(0, current_running)
                    best = q_cfg.algorithm.select_process(q_cfg.queue, current_running)
                    if best != current_running:
                        # A better process arrived — preempt (leave current in queue)
                        current_running = None
                        current_queue_id = -1
                        current_running_slice = 0
                    else:
                        # Current is still best — take it back out
                        q_cfg.queue.remove(current_running)
            # └───────────────────────────────────────────────────────────┘

            # ┌─ 7. Select a new process if CPU is free ──────────────────┐
            if not current_running:
                for q in self.queues:
                    if q.queue:
                        selected = q.algorithm.select_process(q.queue, None)
                        if selected:
                            q.queue.remove(selected)
                            current_running = selected
                            current_queue_id = q.id
                            current_running_slice = 0
                            if current_running.start_time == -1:
                                current_running.start_time = self.current_time
                                current_running.response_time = (
                                    self.current_time - current_running.arrival_time
                                )
                            break
            # └───────────────────────────────────────────────────────────┘

            # ┌─ 8. Execute one tick ─────────────────────────────────────┐
            if current_running:
                # Extend or create Gantt block
                if (self.gantt_chart
                        and self.gantt_chart[-1].pid == current_running.pid
                        and self.gantt_chart[-1].queue_id == current_queue_id):
                    self.gantt_chart[-1].end += 1
                else:
                    self.gantt_chart.append(
                        GanttBlock(current_queue_id, current_running.pid,
                                   self.current_time, self.current_time + 1)
                    )

                current_running.remaining_time -= 1
                current_running_slice += 1

                # Check completion
                if current_running.is_finished():
                    current_running.finish_time = self.current_time + 1
                    current_running.turnaround_time = (
                        current_running.finish_time - current_running.arrival_time
                    )
                    current_running.waiting_time = (
                        current_running.turnaround_time - current_running.burst_time
                    )
                    self.completed_processes.append(current_running)
                    current_running = None
                    current_queue_id = -1
                    current_running_slice = 0
            else:
                # CPU idle
                if self.gantt_chart and self.gantt_chart[-1].pid == "IDLE":
                    self.gantt_chart[-1].end += 1
                else:
                    self.gantt_chart.append(
                        GanttBlock(-1, "IDLE",
                                   self.current_time, self.current_time + 1)
                    )
            # └───────────────────────────────────────────────────────────┘

            self.current_time += 1

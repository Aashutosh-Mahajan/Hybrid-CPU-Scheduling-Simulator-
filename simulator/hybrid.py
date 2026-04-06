from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from simulator.algorithms import SchedulingAlgorithm
from simulator.models import GanttBlock, Process

MAX_SIMULATION_TICKS = 10000


def normalize_process_type(process_type: str) -> str:
    """Normalize process type labels for stable routing."""
    normalized = (process_type or "").strip().lower().replace("_", "-")
    return normalized or "batch"


def heuristic_classifier(process: Process) -> str:
    """Classify a process when no explicit type is provided."""
    if process.priority <= 1:
        return "real-time"
    if process.burst_time <= 4:
        return "interactive"
    return "batch"


@dataclass
class HybridQueueConfig:
    process_type: str
    algorithm: SchedulingAlgorithm
    queue_priority: int
    queue: List[Process] = field(default_factory=list)


class HybridScheduler:
    """Type-based hybrid scheduler using multiple algorithms and fixed queue priorities."""

    def __init__(
        self,
        processes: List[Process],
        queues: List[HybridQueueConfig],
        classifier: Optional[Callable[[Process], str]] = None,
        fallback_type: str = "batch",
    ):
        if not queues:
            raise ValueError("At least one hybrid queue must be configured.")

        self.processes = processes
        self.queues = sorted(queues, key=lambda q: q.queue_priority)

        # Re-index priorities into a dense [0..N-1] order for deterministic lanes.
        for idx, queue in enumerate(self.queues):
            queue.process_type = normalize_process_type(queue.process_type)
            queue.queue_priority = idx

        self.classifier = classifier
        self.fallback_type = normalize_process_type(fallback_type)
        self._queue_by_type: Dict[str, HybridQueueConfig] = {
            q.process_type: q for q in self.queues
        }

        if self.fallback_type not in self._queue_by_type:
            self.fallback_type = self.queues[-1].process_type

        self.current_time = 0
        self.gantt_chart: List[GanttBlock] = []
        self.completed_processes: List[Process] = []
        self.queue_label_map = {
            q.queue_priority: f"{q.process_type} ({q.algorithm.name})" for q in self.queues
        }

    def _resolve_type(self, process: Process) -> str:
        if self.classifier:
            candidate = normalize_process_type(self.classifier(process))
        else:
            candidate = normalize_process_type(process.process_type)

        if candidate not in self._queue_by_type:
            return self.fallback_type
        return candidate

    def _highest_ready_queue(self) -> Optional[HybridQueueConfig]:
        for queue in self.queues:
            if queue.queue:
                return queue
        return None

    def run(self):
        # Reset process state.
        for process in self.processes:
            process.remaining_time = process.burst_time
            process.start_time = -1
            process.finish_time = -1
            process.waiting_time = 0
            process.turnaround_time = 0
            process.response_time = -1
            process.current_queue = 0
            process.time_in_current_queue = 0

        for queue in self.queues:
            queue.queue.clear()

        self.current_time = 0
        self.gantt_chart.clear()
        self.completed_processes.clear()

        pending = sorted(self.processes, key=lambda p: (p.arrival_time, p.pid))

        current_running: Optional[Process] = None
        current_queue: Optional[HybridQueueConfig] = None
        current_slice = 0

        while pending or any(queue.queue for queue in self.queues) or current_running:
            if self.current_time >= MAX_SIMULATION_TICKS:
                break

            # Enqueue arrivals according to process type.
            while pending and pending[0].arrival_time <= self.current_time:
                arrived = pending.pop(0)
                process_type = self._resolve_type(arrived)
                arrived.process_type = process_type
                target_queue = self._queue_by_type[process_type]
                arrived.current_queue = target_queue.queue_priority
                arrived.time_in_current_queue = 0
                target_queue.queue.append(arrived)

            # Round Robin quantum expiry for the currently running process.
            if current_running and current_queue:
                quantum = current_queue.algorithm.quantum
                if quantum is not None and current_slice >= quantum and not current_running.is_finished():
                    current_queue.queue.append(current_running)
                    current_running = None
                    current_queue = None
                    current_slice = 0

            highest_ready = self._highest_ready_queue()

            # Preempt when a higher-priority process type is waiting.
            if (
                current_running
                and current_queue
                and highest_ready
                and highest_ready.queue_priority < current_queue.queue_priority
            ):
                current_queue.queue.insert(0, current_running)
                current_running = None
                current_queue = None
                current_slice = 0

            # Preemptive decision inside the same type queue (SRTF / Priority).
            if (
                current_running
                and current_queue
                and highest_ready
                and highest_ready.process_type == current_queue.process_type
                and current_queue.algorithm.is_preemptive
                and current_queue.algorithm.quantum is None
            ):
                current_queue.queue.insert(0, current_running)
                selected = current_queue.algorithm.select_process(
                    current_queue.queue,
                    current_running,
                )
                if selected is current_running:
                    current_queue.queue.remove(current_running)
                else:
                    current_running = None
                    current_queue = None
                    current_slice = 0

            # Pick a process if CPU is free.
            if not current_running:
                chosen_queue = self._highest_ready_queue()
                if chosen_queue:
                    selected = chosen_queue.algorithm.select_process(chosen_queue.queue, None)
                    if selected:
                        chosen_queue.queue.remove(selected)
                        current_running = selected
                        current_queue = chosen_queue
                        current_slice = 0
                        if current_running.start_time == -1:
                            current_running.start_time = self.current_time
                            current_running.response_time = (
                                self.current_time - current_running.arrival_time
                            )

            # Execute one simulation tick.
            if current_running and current_queue:
                queue_id = current_queue.queue_priority
                if (
                    self.gantt_chart
                    and self.gantt_chart[-1].pid == current_running.pid
                    and self.gantt_chart[-1].queue_id == queue_id
                ):
                    self.gantt_chart[-1].end += 1
                else:
                    self.gantt_chart.append(
                        GanttBlock(
                            queue_id=queue_id,
                            pid=current_running.pid,
                            start=self.current_time,
                            end=self.current_time + 1,
                        )
                    )

                current_running.remaining_time -= 1
                current_slice += 1

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
                    current_queue = None
                    current_slice = 0
            else:
                if self.gantt_chart and self.gantt_chart[-1].pid == "IDLE":
                    self.gantt_chart[-1].end += 1
                else:
                    self.gantt_chart.append(
                        GanttBlock(
                            queue_id=-1,
                            pid="IDLE",
                            start=self.current_time,
                            end=self.current_time + 1,
                        )
                    )

            self.current_time += 1

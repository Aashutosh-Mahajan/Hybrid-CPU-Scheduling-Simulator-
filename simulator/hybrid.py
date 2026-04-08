"""
simulator/hybrid.py
───────────────────
Type-based Hybrid Scheduler — the core scheduling engine of this project.

Concept
───────
Instead of applying a single algorithm to every process, the hybrid scheduler
assigns each process to a *type queue* based on its process_type label
(e.g. "real-time", "interactive", "batch").  Each type queue runs its own
independent scheduling algorithm, and queues are served in fixed priority order
(higher-priority type queues preempt lower ones).

This mimics real operating-system designs where different classes of work
(ISR/RT tasks, UI threads, background jobs) get different treatment.

Key rules (in order of precedence each tick):
  1. Admit arrivals → classify process type → route to the correct queue.
  2. Round Robin quantum expiry → return the running process to its queue.
  3. Cross-queue preemption → if a higher-priority type has a waiting process,
     preempt the currently running lower-priority process.
  4. Same-queue preemption → for preemptive non-RR algorithms (SRTF, Priority),
     check whether a newer arrival is a better candidate in the same queue.
  5. Schedule → pick the best process from the highest non-empty queue.
  6. Execute one tick → update Gantt chart, decrement remaining_time.

Public API
──────────
  normalize_process_type(s) → str          — canonical label form
  heuristic_classifier(p)   → str          — fallback classification by priority/burst
  HybridQueueConfig                         — per-queue configuration dataclass
  HybridScheduler                           — the simulation engine
"""

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from simulator.algorithms import SchedulingAlgorithm
from simulator.models import GanttBlock, Process

# Hard upper limit to protect against infinite loops on degenerate inputs.
MAX_SIMULATION_TICKS = 10000


# ─────────────────────────────────────────────────────────────────────────────
# Helper utilities
# ─────────────────────────────────────────────────────────────────────────────

def normalize_process_type(process_type: str) -> str:
    """
    Convert a raw type label into a canonical, lower-cased, hyphenated form.

    Examples:
        "Real-Time"  → "real-time"
        "INTERACTIVE"→ "interactive"
        "batch_job"  → "batch-job"
        ""  or None  → "batch"   (default fallback)

    This is applied to both queue names (from the sidebar) and process Type
    values (from the data editor) so that routing comparisons are always
    case- and whitespace-insensitive.
    """
    normalized = (process_type or "").strip().lower().replace("_", "-")
    return normalized or "batch"  # default to "batch" if empty


def heuristic_classifier(process: Process) -> str:
    """
    Classify a process into a type queue when its Type field is missing or
    does not match any configured queue name.

    Rules (applied in priority order):
      1. priority <= 1  →  "real-time"   (urgent, low-number priority)
      2. burst_time <= 4 → "interactive" (short tasks, likely UI/IO-bound)
      3. otherwise      →  "batch"       (long, background tasks)

    Used when the UI toggle "Auto-classify missing/invalid process type" is on.
    """
    if process.priority <= 1:
        return "real-time"
    if process.burst_time <= 4:
        return "interactive"
    return "batch"


# ─────────────────────────────────────────────────────────────────────────────
# HybridQueueConfig — configuration for one type lane
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class HybridQueueConfig:
    """
    Describes one type queue in the hybrid scheduler.

    Attributes:
        process_type  : Canonical type label that processes are routed to
                        (e.g. "real-time", "interactive", "batch").
        algorithm     : SchedulingAlgorithm instance governing selection within
                        this queue (FCFS, SJF, Priority, RoundRobin, …).
        queue_priority: Integer rank — 0 = highest priority (served first).
                        When two queues both have ready processes, the one with
                        the lower queue_priority number wins.
        queue         : Live list of ready processes for this type lane.
                        Managed by HybridScheduler.run(); do not modify externally.
    """

    process_type: str               # routing label
    algorithm: SchedulingAlgorithm  # intra-queue selection policy
    queue_priority: int             # 0 = highest precedence
    queue: List[Process] = field(default_factory=list)  # ready list


# ─────────────────────────────────────────────────────────────────────────────
# HybridScheduler — the simulation engine
# ─────────────────────────────────────────────────────────────────────────────

class HybridScheduler:
    """
    Type-based hybrid CPU scheduler.

    Instantiation:
        scheduler = HybridScheduler(
            processes       = list_of_Process_objects,
            queues          = [HybridQueueConfig(...)],
            classifier      = optional_callable,   # maps Process → type string
            fallback_type   = "batch",             # used when type is unknown
        )
        scheduler.run()

    Results after run():
        scheduler.completed_processes  : List[Process] with metrics populated.
        scheduler.gantt_chart          : List[GanttBlock] for the Gantt chart.
        scheduler.current_time         : Total ticks (makespan).
        scheduler.queue_label_map      : Dict[queue_priority → display label].
    """

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

        # Sort queues by their declared priority and re-index them 0..N-1
        # so that priority comparisons are always dense integers.
        self.queues = sorted(queues, key=lambda q: q.queue_priority)
        for idx, queue in enumerate(self.queues):
            queue.process_type = normalize_process_type(queue.process_type)
            queue.queue_priority = idx  # re-index to 0-based dense order

        # Callable used to determine a process's type when routing.
        # If None, the process's own process_type field is used directly.
        self.classifier = classifier

        self.fallback_type = normalize_process_type(fallback_type)

        # Fast lookup: type string → HybridQueueConfig
        self._queue_by_type: Dict[str, HybridQueueConfig] = {
            q.process_type: q for q in self.queues
        }

        # Ensure the fallback type actually exists; if not, use the last queue.
        if self.fallback_type not in self._queue_by_type:
            self.fallback_type = self.queues[-1].process_type

        # Output / state
        self.current_time = 0
        self.gantt_chart: List[GanttBlock] = []
        self.completed_processes: List[Process] = []

        # Human-readable labels for Gantt chart lanes, keyed by queue_priority.
        # Example: {0: "real-time (Priority)", 1: "interactive (RR (q=3))"}
        self.queue_label_map = {
            q.queue_priority: f"{q.process_type} ({q.algorithm.name})"
            for q in self.queues
        }

    # ── Private helpers ───────────────────────────────────────────────────────

    def _resolve_type(self, process: Process) -> str:
        """
        Determine the canonical type queue for a process.

        Uses the classifier callable if provided; otherwise uses the process's
        own process_type field.  Falls back to self.fallback_type when the
        resolved type does not match any configured queue.
        """
        if self.classifier:
            candidate = normalize_process_type(self.classifier(process))
        else:
            candidate = normalize_process_type(process.process_type)

        # If the resolved type has no matching queue, use the fallback.
        if candidate not in self._queue_by_type:
            return self.fallback_type
        return candidate

    def _highest_ready_queue(self) -> Optional[HybridQueueConfig]:
        """
        Return the highest-priority (lowest queue_priority number) queue that
        currently has at least one ready process, or None if all queues are empty.
        """
        for queue in self.queues:  # already sorted by queue_priority ascending
            if queue.queue:
                return queue
        return None

    # ── Main simulation loop ──────────────────────────────────────────────────

    def run(self):
        """
        Execute the full hybrid simulation tick by tick.

        The simulation loop runs until:
          • All processes have been admitted and completed, AND
          • All queues are empty, AND
          • The CPU is idle.
        OR until MAX_SIMULATION_TICKS is reached (safety guard).
        """

        # ── Reset process state from any previous run ─────────────────────
        for process in self.processes:
            process.remaining_time = process.burst_time
            process.start_time = -1
            process.finish_time = -1
            process.waiting_time = 0
            process.turnaround_time = 0
            process.response_time = -1
            process.current_queue = 0
            process.time_in_current_queue = 0

        # Clear the queue lists from any previous run.
        for queue in self.queues:
            queue.queue.clear()

        self.current_time = 0
        self.gantt_chart.clear()
        self.completed_processes.clear()

        # Sort by arrival time (then by PID for stable ordering among ties).
        pending = sorted(self.processes, key=lambda p: (p.arrival_time, p.pid))

        # CPU state
        current_running: Optional[Process] = None        # process on CPU (None = idle)
        current_queue: Optional[HybridQueueConfig] = None  # queue it belongs to
        current_slice = 0                                # ticks used in current quantum

        # ── Main loop ─────────────────────────────────────────────────────
        while pending or any(queue.queue for queue in self.queues) or current_running:

            # Safety guard — stop on runaway simulations.
            if self.current_time >= MAX_SIMULATION_TICKS:
                break

            # ┌─ Step 1: Admit arrivals ─────────────────────────────────┐
            # Classify each newly arrived process and route it to the
            # appropriate type queue.
            while pending and pending[0].arrival_time <= self.current_time:
                arrived = pending.pop(0)
                process_type = self._resolve_type(arrived)  # classify
                arrived.process_type = process_type         # normalise label
                target_queue = self._queue_by_type[process_type]
                arrived.current_queue = target_queue.queue_priority
                arrived.time_in_current_queue = 0
                target_queue.queue.append(arrived)          # enqueue
            # └─────────────────────────────────────────────────────────┘

            # ┌─ Step 2: Round-Robin quantum expiry ─────────────────────┐
            # If the running process has consumed its full quantum, place
            # it back at the end of its type queue and free the CPU.
            if current_running and current_queue:
                quantum = current_queue.algorithm.quantum
                if (
                    quantum is not None
                    and current_slice >= quantum
                    and not current_running.is_finished()
                ):
                    current_queue.queue.append(current_running)  # re-queue
                    current_running = None
                    current_queue = None
                    current_slice = 0
            # └─────────────────────────────────────────────────────────┘

            # ┌─ Step 3: Find the highest-priority ready queue ──────────┐
            highest_ready = self._highest_ready_queue()
            # └─────────────────────────────────────────────────────────┘

            # ┌─ Step 4: Cross-queue preemption ─────────────────────────┐
            # A higher-priority type queue now has a waiting process while
            # a lower-priority process is on the CPU → preempt.
            if (
                current_running
                and current_queue
                and highest_ready
                and highest_ready.queue_priority < current_queue.queue_priority
            ):
                # Re-insert the preempted process at the front of its queue.
                current_queue.queue.insert(0, current_running)
                current_running = None
                current_queue = None
                current_slice = 0
            # └─────────────────────────────────────────────────────────┘

            # ┌─ Step 5: Same-queue preemption (SRTF / Priority) ────────┐
            # For preemptive, non-RR algorithms within the same type queue,
            # check if a newly arrived process should replace the running one.
            if (
                current_running
                and current_queue
                and highest_ready
                and highest_ready.process_type == current_queue.process_type
                and current_queue.algorithm.is_preemptive
                and current_queue.algorithm.quantum is None  # not Round Robin
            ):
                # Temporarily put the running process back into the queue so
                # select_process() can compare it against all candidates.
                current_queue.queue.insert(0, current_running)
                selected = current_queue.algorithm.select_process(
                    current_queue.queue, current_running
                )
                if selected is current_running:
                    # Running process is still best — remove the temp insertion.
                    current_queue.queue.remove(current_running)
                else:
                    # A different process was selected — preempt.
                    # current_running stays in the queue (already inserted).
                    current_running = None
                    current_queue = None
                    current_slice = 0
            # └─────────────────────────────────────────────────────────┘

            # ┌─ Step 6: Schedule if CPU is free ────────────────────────┐
            # Ask the highest-priority non-empty queue to select a process.
            if not current_running:
                chosen_queue = self._highest_ready_queue()
                if chosen_queue:
                    selected = chosen_queue.algorithm.select_process(chosen_queue.queue, None)
                    if selected:
                        chosen_queue.queue.remove(selected)  # take off the queue
                        current_running = selected
                        current_queue = chosen_queue
                        current_slice = 0
                        # Record first CPU access (response time).
                        if current_running.start_time == -1:
                            current_running.start_time = self.current_time
                            current_running.response_time = (
                                self.current_time - current_running.arrival_time
                            )
            # └─────────────────────────────────────────────────────────┘

            # ┌─ Step 7: Execute one simulation tick ────────────────────┐
            if current_running and current_queue:
                queue_id = current_queue.queue_priority

                # Extend the last Gantt block if it is the same process in
                # the same queue, otherwise open a new block.
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

                current_running.remaining_time -= 1  # consume one tick
                current_slice += 1                   # accumulate quantum usage

                # Check completion.
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
                    current_queue = None
                    current_slice = 0
            else:
                # CPU is idle — record in Gantt chart.
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
            # └─────────────────────────────────────────────────────────┘

            self.current_time += 1  # advance the simulation clock

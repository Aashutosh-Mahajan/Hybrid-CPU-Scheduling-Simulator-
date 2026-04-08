"""
simulator/models.py
───────────────────
Defines the core data structures used throughout the simulator.

Two dataclasses live here:
  • Process    — represents a single CPU process with all its scheduling attributes
                 and lifecycle state.
  • GanttBlock — a single time-slice entry recorded by the scheduler for drawing
                 the Gantt chart.

These classes are intentionally kept minimal and dependency-free so every other
module can import from here without creating circular imports.
"""

from dataclasses import dataclass, field
from typing import List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Process
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Process:
    """
    Represents a single CPU process.

    Constructor arguments (set by the caller):
        pid          : Unique string identifier, e.g. "P1".
        arrival_time : Clock tick at which the process enters the ready queue.
        burst_time   : Total CPU time the process needs to finish.
        priority     : Scheduling priority (lower number = higher urgency).
                       Used by Priority and hybrid real-time queues.
        process_type : Category label used for hybrid queue routing.
                       Typical values: "real-time", "interactive", "batch".

    Auto-initialised state (not set by caller, managed by the simulator):
        remaining_time        : CPU time left; starts equal to burst_time and
                                counts down one tick at a time.
        start_time            : Tick when the process first touches the CPU
                                (-1 until first scheduled).
        finish_time           : Tick when remaining_time reaches 0
                                (-1 until completion).
        current_queue         : MLFQ queue index the process currently belongs to
                                (0 = highest-priority queue).
        time_in_current_queue : How long the process has waited in its current
                                queue — used for aging (promotion).

    Computed metrics (filled in by the simulator on completion):
        waiting_time    : Time spent waiting in ready queues
                          = turnaround_time - burst_time.
        turnaround_time : Total time from arrival to finish
                          = finish_time - arrival_time.
        response_time   : Time from arrival until first CPU access
                          = start_time - arrival_time.
    """

    # ── Constructor fields ────────────────────────────────────────────────────
    pid: str
    arrival_time: int
    burst_time: int
    priority: int = 0
    process_type: str = "batch"

    # ── Runtime state (not user-supplied) ────────────────────────────────────
    remaining_time: int = field(init=False)          # counts down each tick
    start_time: int = field(default=-1, init=False)  # -1 = not started yet
    finish_time: int = field(default=-1, init=False) # -1 = not finished yet

    # MLFQ / hybrid queue tracking
    current_queue: int = field(default=0, init=False)
    time_in_current_queue: int = field(default=0, init=False)

    # ── Output metrics ────────────────────────────────────────────────────────
    waiting_time: int = field(default=0, init=False)
    turnaround_time: int = field(default=0, init=False)
    response_time: int = field(default=-1, init=False)  # -1 = not responded yet

    # ── Post-init hook ────────────────────────────────────────────────────────
    def __post_init__(self):
        """Initialise remaining_time from burst_time after dataclass construction."""
        self.remaining_time = self.burst_time

    # ── Helpers ───────────────────────────────────────────────────────────────
    def is_finished(self) -> bool:
        """Return True when there is no CPU time left to execute."""
        return self.remaining_time <= 0


# ─────────────────────────────────────────────────────────────────────────────
# GanttBlock
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class GanttBlock:
    """
    Records a contiguous time slice on the Gantt chart.

    Attributes:
        queue_id : Which queue/lane the process was running in.
                   -1 is used for "IDLE" blocks (CPU idle periods).
        pid      : PID of the running process, or "IDLE" for idle time.
        start    : First tick of this block (inclusive).
        end      : Last tick of this block (exclusive), i.e. the block covers
                   [start, end).

    The simulator extends the `end` of the last block instead of appending a
    new one whenever the same process keeps running in the same queue —
    this keeps the Gantt list compact.
    """

    queue_id: int   # queue lane (-1 for idle)
    pid: str        # process identifier or "IDLE"
    start: int      # block starts at this tick
    end: int        # block ends before this tick

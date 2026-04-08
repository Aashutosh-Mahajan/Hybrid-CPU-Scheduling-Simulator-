"""
simulator/algorithms.py
───────────────────────
Contains the scheduling algorithm classes used by the hybrid scheduler (simulator/hybrid.py).

Architecture
────────────
All algorithms share a common base class (SchedulingAlgorithm) that declares
the select_process() interface.  The scheduler calls select_process() each tick
to ask "given this ready queue, which process should run next?".

Classes
───────
  SchedulingAlgorithm  — Abstract base; stores name, preemption flag, quantum.
  FCFS                 — First Come, First Served (non-preemptive).
  SJF                  — Shortest Job First / SRTF (optionally preemptive).
  Priority             — Priority-based selection (optionally preemptive).
  RoundRobin           — Time-sliced round-robin (always preemptive, needs quantum).

Extending
─────────
To add a new algorithm, subclass SchedulingAlgorithm, pass the appropriate
name/is_preemptive/quantum to super().__init__(), and implement select_process().
Then register it in the algorithms_map dict inside app.py.
"""

from typing import List, Optional
from simulator.models import Process


# ─────────────────────────────────────────────────────────────────────────────
# Base class
# ─────────────────────────────────────────────────────────────────────────────

class SchedulingAlgorithm:
    """
    Abstract base for all scheduling algorithms.

    Attributes:
        name          : Human-readable label shown in the UI and Gantt legend.
        is_preemptive : If True, the scheduler may kick out the running process
                        when a better candidate arrives.
        quantum       : Time-slice size for Round Robin.  None for all other
                        algorithms.
    """

    def __init__(self, name: str, is_preemptive: bool, quantum: Optional[int] = None):
        self.name = name
        self.is_preemptive = is_preemptive
        self.quantum = quantum  # None unless RR

    def select_process(
        self,
        ready_queue: List[Process],
        current_process: Optional[Process],
    ) -> Optional[Process]:
        """
        Choose the next process to execute.

        Args:
            ready_queue     : All processes currently in this queue's ready list.
                              The running process is NOT in this list (it is held
                              separately by the simulator) unless the calling code
                              temporarily inserts it for comparison.
            current_process : The process that was running just before this call,
                              or None if the CPU was idle.

        Returns:
            The chosen Process, or None if the queue is empty.
        """
        pass  # Subclasses must override


# ─────────────────────────────────────────────────────────────────────────────
# FCFS — First Come, First Served
# ─────────────────────────────────────────────────────────────────────────────

class FCFS(SchedulingAlgorithm):
    """
    Non-preemptive First Come, First Served.

    Behaviour:
      • Keeps running the current process until it finishes — never preempts.
      • When the CPU is free, picks the process at the front of the ready queue
        (processes are appended in arrival order, so index 0 is the earliest).

    Drawback: long processes can block short ones — the classic 'convoy effect'.
    """

    def __init__(self):
        super().__init__(name="FCFS", is_preemptive=False)

    def select_process(
        self,
        ready_queue: List[Process],
        current_process: Optional[Process],
    ) -> Optional[Process]:
        # If the current process is still running and hasn't finished, keep it.
        if current_process and not current_process.is_finished() and current_process in ready_queue:
            return current_process
        # Otherwise pick the first process in the queue (earliest arrival).
        if not ready_queue:
            return None
        return ready_queue[0]


# ─────────────────────────────────────────────────────────────────────────────
# SJF / SRTF — Shortest Job First / Shortest Remaining Time First
# ─────────────────────────────────────────────────────────────────────────────

class SJF(SchedulingAlgorithm):
    """
    Shortest Job First (non-preemptive) or
    Shortest Remaining Time First / SRTF (preemptive).

    Set is_preemptive=False for SJF, True for SRTF.

    Non-preemptive (SJF):
      • Among all ready processes, picks the one with the smallest burst_time.
      • Once a process starts, it runs to completion without interruption.
      • Optimal for minimising average waiting time in batch workloads.

    Preemptive (SRTF / SRTN):
      • Picks the process with the smallest REMAINING_time.
      • If a new arrival is shorter than what is currently running, it preempts.
      • Lowest average waiting/turnaround time theoretically, but higher
        context-switch overhead.
    """

    def __init__(self, is_preemptive: bool = False):
        name = "SRTF" if is_preemptive else "SJF"
        super().__init__(name=name, is_preemptive=is_preemptive)

    def select_process(
        self,
        ready_queue: List[Process],
        current_process: Optional[Process],
    ) -> Optional[Process]:
        if not ready_queue:
            return None

        # Non-preemptive: stick with the current process if it is still running.
        if not self.is_preemptive:
            if current_process and not current_process.is_finished() and current_process in ready_queue:
                return current_process
            # If the CPU was yielded due to cross-queue preemption, a partially
            # executed process might be in the queue. It must be resumed to honour
            # non-preemption within this tier.
            for p in ready_queue:
                if p.start_time != -1 and not p.is_finished():
                    return p

        # Preemptive or CPU is free: pick the shortest remaining time.
        # Ties are broken by arrival_time (earlier arrival wins).
        return min(ready_queue, key=lambda p: (p.remaining_time, p.arrival_time))


# ─────────────────────────────────────────────────────────────────────────────
# Priority Scheduling
# ─────────────────────────────────────────────────────────────────────────────

class Priority(SchedulingAlgorithm):
    """
    Priority-based scheduling (optionally preemptive).

    Convention: lower priority number = higher urgency
    (e.g. priority 0 runs before priority 5).

    Non-preemptive:
      • Picks the highest-priority ready process when the CPU is free.
      • Once started, runs to completion.
      • Risk: low-priority processes may starve without aging.

    Preemptive:
      • At every tick, if a higher-priority process arrives it preempts the
        current one immediately.
      • Real-time queues in the hybrid scheduler use this mode.
    """

    def __init__(self, is_preemptive: bool = False):
        name = "Priority (Preemptive)" if is_preemptive else "Priority"
        super().__init__(name=name, is_preemptive=is_preemptive)

    def select_process(
        self,
        ready_queue: List[Process],
        current_process: Optional[Process],
    ) -> Optional[Process]:
        if not ready_queue:
            return None

        # Non-preemptive: keep the current process if it is still running.
        if not self.is_preemptive:
            if current_process and not current_process.is_finished() and current_process in ready_queue:
                return current_process
            # Honour non-preemption for previously started processes that were
            # suspended by higher-level queues.
            for p in ready_queue:
                if p.start_time != -1 and not p.is_finished():
                    return p

        # Pick the process with the lowest priority number (highest urgency).
        # Ties are broken by arrival_time.
        return min(ready_queue, key=lambda p: (p.priority, p.arrival_time))


# ─────────────────────────────────────────────────────────────────────────────
# Round Robin
# ─────────────────────────────────────────────────────────────────────────────

class RoundRobin(SchedulingAlgorithm):
    """
    Preemptive Round Robin with a fixed time quantum.

    Behaviour:
      • Each process gets at most `quantum` ticks of CPU time per turn.
      • When the quantum expires, the process is placed at the back of the
        queue and the next waiting process runs.
      • select_process() always returns the first element of the queue because
        For Round Robin, time quantum enforcement is handled by the overall engine
        (hybrid.py) before this method is called.

    Choosing the quantum:
      • Small quantum  → more responsive but higher context-switch overhead.
      • Large quantum  → approaches FCFS behaviour.
      • Typical range for interactive queues: 2–6 ticks.
    """

    def __init__(self, quantum: int):
        super().__init__(name=f"RR (q={quantum})", is_preemptive=True, quantum=quantum)

    def select_process(
        self,
        ready_queue: List[Process],
        current_process: Optional[Process],
    ) -> Optional[Process]:
        # Always take the first process in the queue.
        # The simulator has already moved the just-expired process to the back
        # before calling this method, so index 0 is the "next in line".
        if not ready_queue:
            return None
        return ready_queue[0]

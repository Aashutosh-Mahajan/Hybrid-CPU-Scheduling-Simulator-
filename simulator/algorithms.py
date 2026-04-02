from typing import List, Optional
from simulator.models import Process

class SchedulingAlgorithm:
    def __init__(self, name: str, is_preemptive: bool, quantum: Optional[int] = None):
        self.name = name
        self.is_preemptive = is_preemptive
        self.quantum = quantum

    def select_process(self, ready_queue: List[Process], current_process: Optional[Process]) -> Optional[Process]:
        """Selects the next process to run from the queue."""
        pass

class FCFS(SchedulingAlgorithm):
    def __init__(self):
        super().__init__(name="FCFS", is_preemptive=False)

    def select_process(self, ready_queue: List[Process], current_process: Optional[Process]) -> Optional[Process]:
        if current_process and not current_process.is_finished() and current_process in ready_queue:
            return current_process
        if not ready_queue:
            return None
        return ready_queue[0]

class SJF(SchedulingAlgorithm):
    def __init__(self, is_preemptive: bool = False):
        super().__init__(name="SRTF" if is_preemptive else "SJF", is_preemptive=is_preemptive)

    def select_process(self, ready_queue: List[Process], current_process: Optional[Process]) -> Optional[Process]:
        if not ready_queue:
            return None
            
        if not self.is_preemptive and current_process and not current_process.is_finished() and current_process in ready_queue:
            return current_process
            
        return min(ready_queue, key=lambda p: (p.remaining_time, p.arrival_time))

class Priority(SchedulingAlgorithm):
    def __init__(self, is_preemptive: bool = False):
        super().__init__(name="Priority (Preemptive)" if is_preemptive else "Priority", is_preemptive=is_preemptive)

    def select_process(self, ready_queue: List[Process], current_process: Optional[Process]) -> Optional[Process]:
        if not ready_queue:
            return None
            
        if not self.is_preemptive and current_process and not current_process.is_finished() and current_process in ready_queue:
            return current_process
            
        return min(ready_queue, key=lambda p: (p.priority, p.arrival_time))

class RoundRobin(SchedulingAlgorithm):
    def __init__(self, quantum: int):
        super().__init__(name=f"RR (q={quantum})", is_preemptive=True, quantum=quantum)

    def select_process(self, ready_queue: List[Process], current_process: Optional[Process]) -> Optional[Process]:
        if not ready_queue:
            return None
        return ready_queue[0]

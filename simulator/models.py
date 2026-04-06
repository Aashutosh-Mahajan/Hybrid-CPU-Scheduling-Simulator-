from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Process:
    pid: str
    arrival_time: int
    burst_time: int
    priority: int = 0
    process_type: str = "batch"
    
    # State tracking
    remaining_time: int = field(init=False)
    start_time: int = field(default=-1, init=False)
    finish_time: int = field(default=-1, init=False)
    
    # MLFQ specific tracking
    current_queue: int = field(default=0, init=False)
    time_in_current_queue: int = field(default=0, init=False)
    
    # Metrics
    waiting_time: int = field(default=0, init=False)
    turnaround_time: int = field(default=0, init=False)
    response_time: int = field(default=-1, init=False)

    def __post_init__(self):
        self.remaining_time = self.burst_time

    def is_finished(self):
        return self.remaining_time <= 0

@dataclass
class GanttBlock:
    queue_id: int
    pid: str
    start: int
    end: int

from enum import Enum
from typing import Optional


class RequestStatus(Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Request:
    def __init__(self, req_id, trigger_time, user, task_chain):
        self.id = req_id
        self.trigger_time = trigger_time
        self.user = user
        self.task_chain = task_chain
        self.status: RequestStatus = RequestStatus.PENDING
        self.assigned_node = None
        self.start_processing_time: Optional[float] = None
        self.finish_time: Optional[float] = None

    def __repr__(self):
        assigned = self.assigned_node.id if self.assigned_node else "None"
        return (f"<Request[{self.id}] "
                f"Time:{self.trigger_time:.2f} | "
                f"User:{self.user.id} -> DT:{self.task_chain.id} | "
                f"Status:{self.status.value} | Node:{assigned}>")

import datetime

from core.shared.enums import TaskState
from core.shared.base.model import BaseModel


class TaskHistoryInCRUDResponse(BaseModel):
    state: TaskState
    process: str
    thinking: str
    created_at: datetime.datetime


class TaskHistoryCreateRequestModel(BaseModel):
    state: TaskState
    process: str
    thinking: str

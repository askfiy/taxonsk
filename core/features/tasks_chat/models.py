import datetime

from core.shared.enums import MessageRole
from core.shared.base.model import BaseModel


class TaskChatInCRUDResponse(BaseModel):
    message: str
    role: MessageRole
    created_at: datetime.datetime


class TaskChatCreateRequestModel(BaseModel):
    message: str
    role: MessageRole

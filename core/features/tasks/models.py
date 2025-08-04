import datetime

from pydantic import field_validator, model_validator, Field

from core.shared.enums import TaskState, TaskAuditSource
from core.shared.base.model import BaseModel
from ..tasks_chat.models import TaskChatInCRUDResponse
from ..tasks_history.models import TaskHistoryInCRUDResponse
from ..tasks_metadata.models import (
    TaskMetaDataCreateModel,
    TaskMetaDataInDispatchModel,
)


# scheme
class TaskInCRUDResponseModel(BaseModel):
    id: int
    state: TaskState

    name: str
    deep_level: int
    expect_execute_time: datetime.datetime
    background: str
    objective: str
    details: str
    dependencies: list[int] | None
    parent_id: int | None
    created_at: datetime.datetime

    chats: list[TaskChatInCRUDResponse]
    histories: list[TaskHistoryInCRUDResponse]

    @field_validator("expect_execute_time", mode="before")
    @classmethod
    def assume_utc_if_naive(
        cls, expect_execute_time: datetime.datetime | None
    ) -> datetime.datetime | None:
        """
        如果传入的 datetime 对象是“天真”的，就强制为它附加 UTC 时区。
        我们知道数据库存的是 UTC，所以这是安全的。
        """
        if (
            isinstance(expect_execute_time, datetime.datetime)
            and expect_execute_time.tzinfo is None
        ):
            utc_aware_time = expect_execute_time.replace(tzinfo=datetime.timezone.utc)
            return utc_aware_time
        return expect_execute_time


class TaskCreateModel(BaseModel):
    name: str
    expect_execute_time: datetime.datetime
    background: str
    objective: str
    details: str

    dependencies: list[int] = []
    parent_id: int | None = None
    metadata: TaskMetaDataCreateModel | None = None


class TaskUpdateModel(BaseModel):
    name: str | None = None
    state: TaskState | None = None
    priority: int | None = None
    expect_execute_time: datetime.datetime | None = None
    lasted_execute_time: datetime.datetime | None = None

    background: str | None = None
    objective: str | None = None
    details: str | None = None

    dependencies: list[int] | None = None
    parent_id: int | None = None
    metadata: TaskMetaDataCreateModel | None = None

    # 审计
    source: TaskAuditSource | None = None
    source_context: str | None = None
    comment: str | None = None

    @model_validator(mode="after")
    def validate_audit_dependency(self) -> "TaskUpdateModel":
        """
        验证规则：'state' 和所有审计字段必须“同生共死”。
        要么全部提供，要么全部不提供。
        """

        validation_set = {
            bool(self.state),
            bool(self.source),
            bool(self.source_context),
            bool(self.comment),
        }

        if len(validation_set) > 1:
            raise ValueError(
                "When updating state, 'state' and all audit fields ('source', 'source_context', 'comment') must be provided together."
            )

        return self


class TaskInDispatchModel(TaskInCRUDResponseModel):
    metadata: TaskMetaDataInDispatchModel = Field(alias="metadata_info")

from core.shared.enums import TaskState, TaskAuditSource
from ..tasks import service as task_service
from ..tasks.table import Tasks
from ..tasks.models import TaskInDispatchModel, TaskUpdateModel


class TaskProxy(TaskInDispatchModel):
    async def update(self, model: TaskUpdateModel):
        task_obj = await task_service.update(task_id=self.id, request_model=model)

        # 将 task_obj 的字段, 重新赋值到 self 身上 ..
        for field_name in __class__.model_fields:
            if hasattr(task_obj, field_name):
                field_value = getattr(task_obj, field_name)
                setattr(self, field_name, field_value)


class TaskAgentProxy:
    def __init__(self, task_obj: Tasks):
        self.task = TaskProxy.model_validate(task_obj)

    async def execute(self):
        await self.task.update(
            TaskUpdateModel(
                state=TaskState.ACTIVATING,
                source=TaskAuditSource.AGENT,
                source_context=__class__.__name__,
                comment="Agent 开始处理任务 ..",
            )
        )

        print(self.task)

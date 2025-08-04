from core.shared.models.http import Paginator
from core.shared.database.session import (
    get_async_session_direct,
    get_async_tx_session_direct,
)
from core.shared.exceptions import ServiceNotFoundException
from .table import TasksAudit
from .models import TaskAuditCreateRequestModel
from .repository import TasksAuditRepository
from ..tasks.repository import TasksCRUDRepository


async def upget_paginator(task_id: int, paginator: Paginator) -> Paginator:
    async with get_async_session_direct() as session:
        tasks_audit_repo = TasksAuditRepository(session=session)

        return await tasks_audit_repo.upget_paginator(
            task_id=task_id,
            paginator=paginator,
        )


async def create(
    task_id: int, request_model: TaskAuditCreateRequestModel
) -> TasksAudit:
    async with get_async_tx_session_direct() as session:
        tasks_repo = TasksCRUDRepository(
            session=session,
        )
        task_exists = await tasks_repo.exists(pk=task_id)

        if not task_exists:
            raise ServiceNotFoundException(f"任务: {task_id} 不存在")

        tasks_audit_repo = TasksAuditRepository(session=session)

        return await tasks_audit_repo.create(
            create_info={"task_id": task_id, **request_model.model_dump()}
        )

from core.shared.models.http import Paginator
from core.shared.database.session import (
    get_async_session_direct,
    get_async_tx_session_direct,
)
from core.shared.exceptions import ServiceNotFoundException
from .table import TasksHistory
from .models import TaskHistoryCreateRequestModel
from .repository import TasksHistoryRepository
from ..tasks.repository import TasksCRUDRepository


async def upget_paginator(task_id: int, paginator: Paginator) -> Paginator:
    async with get_async_session_direct() as session:
        tasks_history_repo = TasksHistoryRepository(session=session)

        return await tasks_history_repo.upget_paginator(
            task_id=task_id,
            paginator=paginator,
        )


async def create(
    task_id: int, request_model: TaskHistoryCreateRequestModel
) -> TasksHistory:
    async with get_async_tx_session_direct() as session:
        tasks_repo = TasksCRUDRepository(
            session=session,
        )
        task_exists = await tasks_repo.exists(pk=task_id)

        if not task_exists:
            raise ServiceNotFoundException(f"任务: {task_id} 不存在")

        tasks_history_repo = TasksHistoryRepository(session=session)

        return await tasks_history_repo.create(
            create_info={"task_id": task_id, **request_model.model_dump()}
        )

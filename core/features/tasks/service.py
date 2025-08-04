from collections.abc import Sequence

from core.shared.models.http import Paginator
from core.shared.database.session import (
    get_async_session_direct,
    get_async_tx_session_direct,
)
from core.shared.exceptions import ServiceNotFoundException, ServiceMissMessageException
from .table import Tasks
from .models import TaskCreateModel, TaskUpdateModel
from .repository import TasksCRUDRepository
from ..tasks_metadata.repository import TasksMetadataRepository
from ..tasks_audit.repository import TasksAuditRepository
from ..tasks_audit.models import TaskAuditCreateRequestModel


async def get(task_id: int) -> Tasks:
    async with get_async_session_direct() as session:
        tasks_repo = TasksCRUDRepository(session=session)
        task = await tasks_repo.get(pk=task_id, joined_loads=[Tasks.metadata_info])

        if not task:
            raise ServiceNotFoundException(
                f"任务: {task_id} 不存在",
            )
    return task


async def delete(task_id: int) -> bool:
    async with get_async_tx_session_direct() as session:
        tasks_repo = TasksCRUDRepository(session=session)
        # 我们会在 repo 层涉及到是否删除 metadata_info, 所以先将其 JOIN LOAD 出来
        task = await tasks_repo.get(
            pk=task_id, joined_loads=[Tasks.metadata_info, Tasks.parent]
        )

        if not task:
            raise ServiceNotFoundException(
                f"任务: {task_id} 不存在",
            )

        task = await tasks_repo.delete(db_obj=task)
        return bool(task.is_deleted)


async def create(request_model: TaskCreateModel) -> Tasks:
    async with get_async_tx_session_direct() as session:
        task_info = request_model.model_dump()

        tasks_repo = TasksCRUDRepository(
            session=session,
        )
        if request_model.parent_id:
            parent_task = await tasks_repo.get(pk=request_model.parent_id)

            if not parent_task:
                raise ServiceNotFoundException(
                    f"父任务: {request_model.parent_id} 不存在"
                )

            task_info["metadata_id"] = parent_task.metadata_id
            task_info["deep_level"] = parent_task.deep_level + 1
        else:
            raise ServiceMissMessageException(
                "创建任务时，必须提供 parent_id 或 metadata"
            )

        return await tasks_repo.create(create_info=task_info)


async def update(task_id: int, request_model: TaskUpdateModel) -> Tasks:
    async with get_async_tx_session_direct() as session:
        tasks_repo = TasksCRUDRepository(
            session=session,
        )
        task = await tasks_repo.get(pk=task_id)

        if not task:
            raise ServiceNotFoundException(f"任务: {task_id} 不存在")

        if request_model.metadata:
            tasks_metadata_repo = TasksMetadataRepository(
                session=session,
            )

            task_metadata = await tasks_metadata_repo.get(
                pk=task.metadata_id,
            )

            if not task_metadata:
                raise ServiceMissMessageException(
                    f"任务: {task_id} 元信息不存在",
                )

            await tasks_metadata_repo.update(
                task_metadata,
                update_info=request_model.metadata.model_dump(),
            )

        from_state = task.state
        to_state = request_model.state or from_state

        if from_state != to_state:
            assert request_model.source is not None
            assert request_model.source_context is not None
            assert request_model.comment is not None

            tasks_audit_repo = TasksAuditRepository(
                session=session,
            )
            await tasks_audit_repo.create(
                TaskAuditCreateRequestModel(
                    task_id=task_id,
                    from_state=from_state,
                    to_state=to_state,
                    source=request_model.source,
                    source_context=request_model.source_context,
                    comment=request_model.comment,
                ).model_dump()
            )

        # 自动更新, metadata 也会保存. 这里我们排除掉未设置的字段，就能进行部分更新了.
        return await tasks_repo.update(
            task,
            update_info=request_model.model_dump(
                exclude_unset=True, exclude={"metadata"}
            ),
        )


async def upget_paginator(paginator: Paginator) -> Paginator:
    async with get_async_session_direct() as session:
        tasks_repo = TasksCRUDRepository(session=session)
        return await tasks_repo.upget_paginator(paginator=paginator)


async def get_dispatch_tasks_id() -> Sequence[int]:
    async with get_async_tx_session_direct() as session:
        tasks_repo = TasksCRUDRepository(session=session)
        return await tasks_repo.get_dispatch_tasks_id()

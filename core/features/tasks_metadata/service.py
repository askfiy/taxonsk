from core.shared.database.session import (
    get_async_session_direct,
    get_async_tx_session_direct,
)
from core.shared.exceptions import ServiceNotFoundException
from .table import TasksMetadata
from .models import TaskMetaDataCreateModel
from .repository import TasksMetadataRepository


async def get(metadata_id: int) -> TasksMetadata:
    async with get_async_session_direct() as session:
        metadata_repo = TasksMetadataRepository(session=session)
        metadata = await metadata_repo.get(pk=metadata_id)

        if not metadata:
            raise ServiceNotFoundException(
                f"任务元信息: {metadata_id} 不存在",
            )
    return metadata


async def create(request_model: TaskMetaDataCreateModel) -> TasksMetadata:
    async with get_async_tx_session_direct() as session:
        metadata_repo = TasksMetadataRepository(session=session)
        metadata = await metadata_repo.create(request_model)
        return metadata


async def update(update_model: )

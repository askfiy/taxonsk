import fastapi

from core.shared.models.http import (
    ResponseModel,
)

from . import service as metadata_service
from .models import TaskMetaDataInCRUDResponseModel, TaskMetaDataCreateModel

metadata_route = fastapi.APIRouter(prefix="/metadata", tags=["Tasks-metadata"])


@metadata_route.get(
    path="/{metadata_id}",
    name="获取某个元数据",
    status_code=fastapi.status.HTTP_200_OK,
    response_model=ResponseModel[TaskMetaDataInCRUDResponseModel],
)
async def get_by_id(
    metadata_id: int = fastapi.Path(description="元数据 ID"),
) -> ResponseModel[TaskMetaDataInCRUDResponseModel]:
    metadata = await metadata_service.get(metadata_id=metadata_id)
    return ResponseModel(result=TaskMetaDataInCRUDResponseModel.model_validate(metadata))


@metadata_route.post(
    path="",
    name="创建元数据",
    status_code=fastapi.status.HTTP_201_CREATED,
    response_model=ResponseModel[TaskMetaDataInCRUDResponseModel],
)
async def create(
    request_model: TaskMetaDataCreateModel,
) -> ResponseModel[TaskMetaDataInCRUDResponseModel]:
    metadata = await metadata_service.create()
    return ResponseModel(result=TaskMetaDataInCRUDResponseModel.model_validate(metadata))

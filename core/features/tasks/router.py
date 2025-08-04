import fastapi
from fastapi import Depends

from core.shared.models.http import (
    ResponseModel,
    Paginator,
    PaginationRequest,
    PaginationResponse,
)
from . import service as task_service
from .models import (
    TaskCreateModel,
    TaskUpdateModel,
    TaskInCRUDResponseModel,
)

tasks_route = fastapi.APIRouter(prefix="/tasks", tags=["Tasks"])


@tasks_route.post(
    path="",
    name="创建任务",
    status_code=fastapi.status.HTTP_201_CREATED,
    response_model=ResponseModel[TaskInCRUDResponseModel],
)
async def create(
    request_model: TaskCreateModel,
) -> ResponseModel[TaskInCRUDResponseModel]:
    task = await task_service.create(request_model=request_model)
    return ResponseModel(result=TaskInCRUDResponseModel.model_validate(task))


@tasks_route.get(
    path="",
    name="获取全部任务",
    status_code=fastapi.status.HTTP_200_OK,
    response_model=PaginationResponse,
)
async def get(
    request: PaginationRequest = Depends(PaginationRequest),
) -> PaginationResponse:
    paginator = Paginator(
        request=request,
        serializer_cls=TaskInCRUDResponseModel,
    )
    paginator = await task_service.upget_paginator(paginator=paginator)
    return paginator.response


@tasks_route.get(
    path="/{task_id}",
    name="获取某个任务",
    status_code=fastapi.status.HTTP_200_OK,
    response_model=ResponseModel[TaskInCRUDResponseModel],
)
async def get_by_id(
    task_id: int = fastapi.Path(description="任务 ID"),
) -> ResponseModel[TaskInCRUDResponseModel]:
    task = await task_service.get(task_id=task_id)
    return ResponseModel(result=TaskInCRUDResponseModel.model_validate(task))


@tasks_route.put(
    path="/{task_id}",
    name="更新某个任务",
    status_code=fastapi.status.HTTP_200_OK,
    response_model=ResponseModel[TaskInCRUDResponseModel],
)
async def update(
    request_model: TaskUpdateModel,
    task_id: int = fastapi.Path(description="任务 ID"),
) -> ResponseModel[TaskInCRUDResponseModel]:
    task = await task_service.update(task_id=task_id, request_model=request_model)
    return ResponseModel(result=TaskInCRUDResponseModel.model_validate(task))


@tasks_route.delete(
    path="/{task_id}",
    name="删除某个任务",
    status_code=fastapi.status.HTTP_200_OK,
    response_model=ResponseModel[bool],
)
async def delete(
    task_id: int = fastapi.Path(description="任务 ID"),
) -> ResponseModel[bool]:
    result = await task_service.delete(task_id=task_id)
    return ResponseModel(result=result)

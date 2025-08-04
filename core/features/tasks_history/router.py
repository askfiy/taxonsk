import fastapi
from fastapi import Depends

from core.shared.models.http import (
    ResponseModel,
    Paginator,
    PaginationRequest,
    PaginationResponse,
)

from . import service as histories_service
from .models import TaskHistoryInCRUDResponse, TaskHistoryCreateRequestModel


histories_router = fastapi.APIRouter(
    prefix="/{task_id}/histories", tags=["Tasks-histories"]
)


@histories_router.get(
    path="",
    name="获取执行记录",
    status_code=fastapi.status.HTTP_200_OK,
    response_model=PaginationResponse,
)
async def get(
    task_id: int = fastapi.Path(description="任务 ID"),
    request: PaginationRequest = Depends(PaginationRequest),
) -> PaginationResponse:
    paginator = Paginator(
        request=request,
        serializer_cls=TaskHistoryInCRUDResponse,
    )
    paginator = await histories_service.upget_paginator(
        task_id=task_id, paginator=paginator
    )
    return paginator.response


@histories_router.post(
    path="",
    name="插入执行记录",
    status_code=fastapi.status.HTTP_201_CREATED,
    response_model=ResponseModel[TaskHistoryInCRUDResponse],
)
async def insert_task_history(
    request_model: TaskHistoryCreateRequestModel,
    task_id: int = fastapi.Path(description="任务 ID"),
) -> ResponseModel[TaskHistoryInCRUDResponse]:
    history = await histories_service.create(
        task_id=task_id, request_model=request_model
    )
    return ResponseModel(result=TaskHistoryInCRUDResponse.model_validate(history))

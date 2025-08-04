import fastapi
from fastapi import Depends

from core.shared.models.http import (
    ResponseModel,
    Paginator,
    PaginationRequest,
    PaginationResponse,
)

from . import service as chat_service
from .models import TaskChatInCRUDResponse, TaskChatCreateRequestModel


chats_route = fastapi.APIRouter(prefix="/{task_id}/chat", tags=["Tasks-chat"])


@chats_route.get(
    path="",
    name="获取聊天记录",
    status_code=fastapi.status.HTTP_200_OK,
    response_model=PaginationResponse,
)
async def get(
    task_id: int = fastapi.Path(description="任务 ID"),
    request: PaginationRequest = Depends(PaginationRequest),
) -> PaginationResponse:
    paginator = Paginator(
        request=request,
        serializer_cls=TaskChatInCRUDResponse,
    )
    paginator = await chat_service.upget_paginator(
        task_id=task_id, paginator=paginator
    )
    return paginator.response


@chats_route.post(
    path="",
    name="插入聊天记录",
    status_code=fastapi.status.HTTP_201_CREATED,
    response_model=ResponseModel[TaskChatInCRUDResponse],
)
async def insert_task_chat(
    request_model: TaskChatCreateRequestModel,
    task_id: int = fastapi.Path(description="任务 ID"),
) -> ResponseModel[TaskChatInCRUDResponse]:
    result = await chat_service.create(task_id=task_id, request_model=request_model)
    return ResponseModel(result=TaskChatInCRUDResponse.model_validate(result))

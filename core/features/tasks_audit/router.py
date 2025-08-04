import fastapi
from fastapi import Depends

from core.shared.models.http import (
    ResponseModel,
    Paginator,
    PaginationRequest,
    PaginationResponse,
)

from . import service as audit_service
from .models import TaskAuditInCRUDResponse, TaskAuditCreateRequestModel

audits_route = fastapi.APIRouter(prefix="/{task_id}/audit", tags=["Tasks-audit"])


@audits_route.get(
    path="",
    name="获取审查记录",
    status_code=fastapi.status.HTTP_200_OK,
    response_model=PaginationResponse,
)
async def get(
    task_id: int = fastapi.Path(description="任务 ID"),
    request: PaginationRequest = Depends(PaginationRequest),
) -> PaginationResponse:
    paginator = Paginator(
        request=request,
        serializer_cls=TaskAuditInCRUDResponse,
    )
    paginator = await audit_service.upget_paginator(
        task_id=task_id, paginator=paginator
    )
    return paginator.response


@audits_route.post(
    path="",
    name="插入审查记录",
    status_code=fastapi.status.HTTP_201_CREATED,
    response_model=ResponseModel[TaskAuditInCRUDResponse],
)
async def insert_task_chat(
    request_model: TaskAuditCreateRequestModel,
    task_id: int = fastapi.Path(description="任务 ID"),
) -> ResponseModel[TaskAuditInCRUDResponse]:
    task_audit = await audit_service.create(
        task_id=task_id, request_model=request_model
    )
    return ResponseModel(result=TaskAuditInCRUDResponse.model_validate(task_audit))

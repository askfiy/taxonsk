import fastapi
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException

from core.shared.models.http import ResponseModel
from core.shared.exceptions import (
    ServiceException,
    ServiceNotFoundException,
    ServiceMissMessageException,
)


async def exception_handler(request: Request, exc: Exception):
    status_code = fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR
    message = str(exc)

    return JSONResponse(
        status_code=status_code,
        content=ResponseModel(
            code=status_code,
            message=message,
            is_failed=True,
            result=None,
        ).model_dump(by_alias=True),
    )


async def service_exception_handler(request: Request, exc: ServiceException):
    if isinstance(exc, ServiceNotFoundException):
        raise HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)
    if isinstance(exc, ServiceMissMessageException):
        raise HTTPException(status_code=fastapi.status.HTTP_400_BAD_REQUEST)

    raise HTTPException(status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR)

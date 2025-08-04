import uuid
import logging
from contextlib import asynccontextmanager
from collections.abc import Awaitable, Callable

import uvicorn
import fastapi
from fastapi import Request, Response, Depends

from core.router import api_router
from core.logger import setup_logging
from core.handlers import exception_handler
from core.features.dispatch import open_dispatch, stop_dispatch
from core.shared.dependencies import global_headers
from core.shared.globals import g
from core.shared.middleware import GlobalContextMiddleware, GlobalMonitorMiddleware

logger = logging.getLogger("Taxonsk")


@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    setup_logging()

    await open_dispatch()
    yield
    await stop_dispatch()


app = fastapi.FastAPI(
    title="Taxonsk",
    lifespan=lifespan,
    dependencies=[Depends(global_headers)],
)

app.add_middleware(GlobalContextMiddleware)
app.add_middleware(GlobalMonitorMiddleware)
app.add_exception_handler(Exception, exception_handler)


@app.middleware("http")
async def trace(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    g.trace_id = request.headers.get("X-Trace-Id") or str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Trace-Id"] = g.trace_id
    return response


@app.get(
    path="/heart",
    name="心跳检测",
    status_code=fastapi.status.HTTP_200_OK,
)
async def heart():
    return {"success": True}


app.include_router(api_router, prefix="/api/v1")


def main():
    uvicorn.run(app="main:app", host="0.0.0.0", port=9091)


if __name__ == "__main__":
    main()

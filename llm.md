
## `/Users/askfiy/project/coding/taxonsk/Makefile`

```
# Makefile for Taxonsk Project

# --- Variables ---
# Default environment is 'local' if not specified.
# Usage: make serve ENV="test"
ENV ?= local

# Default migration message if not specified.
# Usage: make db-generate M="your message"
M ?= "new migration"

# --- Phony Targets ---
# .PHONY declares targets that are not files.
.PHONY: all help serve db-generate db-upgrade

all: help

help:
	@echo "Usage: make <command> [OPTIONS]"
	@echo ""
	@echo "Commands:"
	@echo "  serve          Start the application server on 0.0.0.0:9091 (default ENV=local)."
	@echo "  db-generate    Generate a new database migration file."
	@echo "  db-upgrade     Upgrade the database to the latest version."
	@echo ""
	@echo "Options:"
	@echo "  ENV=<env>      Specify the environment (e.g., local, test, production). Default: local."
	@echo "  M=<message>    Specify the migration message for db-generate."
	@echo ""
	@echo "Examples:"
	@echo "  make serve"
	@echo "  make serve ENV=test"
	@echo "  make db-generate M=\"create user table\""
	@echo "  make db-upgrade ENV=prod"


# --- Application Commands ---
serve:
	@echo "Starting server in [$(ENV)]..."
	@ENV=$(ENV) uvicorn --host 0.0.0.0 --port 9091 main:app

# --- Database Migration Commands ---
db-generate:
	@echo "Generating DB migration for [$(ENV)]..."
	@ENV=$(ENV) alembic revision --autogenerate -m "$(M)"

db-upgrade:
	@echo "Upgrading DB for [$(ENV)] to head..."
	@ENV=$(ENV) alembic upgrade head

```

## `/Users/askfiy/project/coding/taxonsk/core/config.py`

```python
import os
from typing import Any

from pydantic import Field, MySQLDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


env = os.getenv("ENV")
assert env, "Invalid env."
configure_path = os.path.join(".", ".env", f".{env}.env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=True, env_file=configure_path)

    SYNC_DB_URL: str = Field(examples=["mysql+pymysql://root:123@127.0.0.1:3306/db1"])
    ASYNC_DB_URL: str = Field(examples=["mysql+asyncmy://root:123@127.0.0.1:3306/db1"])
    OPENAI_API_KEY: str = Field(examples=["sk-proj-..."])
    ASYNC_REDIS_URL: str = Field(examples=["redis://127.0.0.1:6379"])

    @field_validator("SYNC_DB_URL", "ASYNC_DB_URL", mode="before")
    @classmethod
    def _validate_db_url(cls, db_url: Any) -> str:
        if not isinstance(db_url, str):
            raise TypeError("Database URL must be a string")
        try:
            # 验证是否符合 MySQLDsn 类型.
            MySQLDsn(db_url)
        except Exception as e:
            raise ValueError(f"Invalid MySQL DSN: {e}") from e

        return str(db_url)

    @field_validator("ASYNC_REDIS_URL", mode="before")
    @classmethod
    def _validate_redis_url(cls, redis_url: Any) -> str:
        if not isinstance(redis_url, str):
            raise TypeError("Redis URL must be a string")
        try:
            # 验证是否符合 RedisDsn 类型.
            RedisDsn(redis_url)
        except Exception as e:
            raise ValueError(f"Invalid redis_url DSN: {e}") from e

        return str(redis_url)


env_helper = Settings()  # pyright: ignore[reportCallIssue]

```

## `/Users/askfiy/project/coding/taxonsk/core/features/__init__.py`

```python

```

## `/Users/askfiy/project/coding/taxonsk/core/features/dispatch/__init__.py`

```python

```

## `/Users/askfiy/project/coding/taxonsk/core/features/tasks/__init__.py`

```python

```

## `/Users/askfiy/project/coding/taxonsk/core/features/tasks/models.py`

```python
import datetime

from pydantic import field_validator

from core.shared.enums import TaskState
from core.shared.base.model import BaseModel
from ..tasks_chat.models import TaskChatInCRUDResponse
from ..tasks_history.models import TaskHistoryInCRUDResponse
from ..tasks_metadata.models import TaskMetaDataRequestModel


class TaskInCRUDResponse(BaseModel):
    id: int
    state: TaskState

    name: str
    deep_level: int
    expect_execute_time: datetime.datetime
    background: str
    objective: str
    details: str
    dependencies: list[int] | None
    parent_id: int | None

    chats: list[TaskChatInCRUDResponse]
    histories: list[TaskHistoryInCRUDResponse]

    @field_validator("expect_execute_time", mode="before")
    @classmethod
    def assume_utc_if_naive(
        cls, v: datetime.datetime | None
    ) -> datetime.datetime | None:
        """
        如果传入的 datetime 对象是“天真”的，就强制为它附加 UTC 时区。
        我们知道数据库存的是 UTC，所以这是安全的。
        """
        if isinstance(v, datetime.datetime) and v.tzinfo is None:
            utc_aware_time = v.replace(tzinfo=datetime.timezone.utc)
            return utc_aware_time
        return v


class TaskCreateRequestModel(BaseModel):
    name: str
    expect_execute_time: datetime.datetime
    background: str
    objective: str
    details: str

    dependencies: list[int] = []
    parent_id: int | None = None
    metadata: TaskMetaDataRequestModel | None = None


class TaskUpdateRequestModel(BaseModel):
    name: str | None = None
    state: TaskState | None = None
    priority: int | None = None
    expect_execute_time: datetime.datetime | None = None
    lasted_execute_time: datetime.datetime | None = None

    background: str | None = None
    objective: str | None = None
    details: str | None = None

    dependencies: list[int] | None = None
    parent_id: int | None = None
    metadata: TaskMetaDataRequestModel | None = None

```

## `/Users/askfiy/project/coding/taxonsk/core/features/tasks/repository.py`

```python
from typing import override, Any
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.orm import aliased, subqueryload, with_loader_criteria, joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm.strategy_options import _AbstractLoad  # pyright: ignore[reportPrivateUsage]
from sqlalchemy.orm.util import LoaderCriteriaOption

from core.shared.enums import TaskState
from core.shared.models.http import Paginator
from core.shared.base.repository import BaseCRUDRepository
from .table import Tasks
from ..tasks_chat.table import TasksChat
from ..tasks_history.table import TasksHistory
from ..tasks_metadata.repository import TasksMetadataRepository


class TasksCRUDRepository(BaseCRUDRepository[Tasks]):
    def __init__(self, session: AsyncSession):
        super().__init__(session=session)

        self.default_limit_count = 10
        self.default_joined_loads = [Tasks.chats, Tasks.histories]
        self.tasks_metadata_repo = TasksMetadataRepository(session=self.session)

    def _get_history_loader_options(
        self, limit_count: int
    ) -> list[_AbstractLoad | LoaderCriteriaOption]:
        history_alias_for_ranking = aliased(TasksHistory)
        ranked_histories_cte = (
            sa.select(
                history_alias_for_ranking.id,
                sa.func.row_number()
                .over(
                    partition_by=history_alias_for_ranking.task_id,
                    order_by=history_alias_for_ranking.created_at.desc(),
                )
                .label("rn"),
            )
            .where(history_alias_for_ranking.task_id == Tasks.id)
            .cte("ranked_histories_cte")
        )

        return [
            subqueryload(Tasks.histories),
            with_loader_criteria(
                TasksHistory,
                TasksHistory.id.in_(
                    sa.select(ranked_histories_cte.c.id).where(
                        ranked_histories_cte.c.rn <= limit_count
                    )
                ),
            ),
        ]

    def _get_chat_loader_options(
        self, limit_count: int
    ) -> list[_AbstractLoad | LoaderCriteriaOption]:
        chat_alias_for_ranking = aliased(TasksChat)
        ranked_chats_cte = (
            sa.select(
                chat_alias_for_ranking.id,
                sa.func.row_number()
                .over(
                    partition_by=chat_alias_for_ranking.task_id,
                    order_by=chat_alias_for_ranking.created_at.desc(),
                )
                .label("rn"),
            )
            .where(chat_alias_for_ranking.task_id == Tasks.id)
            .cte("ranked_chats_cte")
        )

        return [
            subqueryload(Tasks.chats),
            with_loader_criteria(
                TasksChat,
                TasksChat.id.in_(
                    sa.select(ranked_chats_cte.c.id).where(
                        ranked_chats_cte.c.rn <= limit_count
                    )
                ),
            ),
        ]

    @override
    async def create(self, create_info: dict[str, Any]) -> Tasks:
        task = await super().create(create_info=create_info)
        # 创建 task 后需要手动 load 一下 chats 和 histories.
        await self.session.refresh(task, [Tasks.chats.key, Tasks.histories.key])
        return task

    @override
    async def get(
        self, pk: int, joined_loads: list[InstrumentedAttribute[Any]] | None = None
    ) -> Tasks | None:
        extend_joined_loads = self.default_joined_loads.copy()
        extend_joined_loads.extend(joined_loads or [])

        stmt = sa.select(self.model).where(
            self.model.id == pk, sa.not_(self.model.is_deleted)
        )

        if extend_joined_loads:
            for join_field in extend_joined_loads:
                if Tasks.chats is join_field:
                    stmt = stmt.options(
                        *self._get_chat_loader_options(self.default_limit_count)
                    )
                elif Tasks.histories is join_field:
                    stmt = stmt.options(
                        *self._get_history_loader_options(self.default_limit_count)
                    )
                else:
                    stmt = stmt.options(joinedload(join_field))

        result = await self.session.execute(stmt)

        return result.unique().scalar_one_or_none()

    @override
    async def get_all(
        self, joined_loads: list[InstrumentedAttribute[Any]] | None = None
    ) -> Sequence[Tasks]:
        extend_joined_loads = self.default_joined_loads.copy()
        extend_joined_loads.extend(joined_loads or [])

        return await super().get_all(joined_loads=extend_joined_loads)

    @override
    async def delete(self, db_obj: Tasks) -> Tasks:
        task = db_obj

        cte = (
            sa.select(Tasks.id)
            .where(Tasks.id == task.id)
            .cte("descendants", recursive=True)
        )
        aliased_tasks = aliased(Tasks)  # 给 Tasks 表起个别名

        cte = cte.union_all(
            sa.select(aliased_tasks.id).where(aliased_tasks.parent_id == cte.c.id)
        )

        # 获得需要删除的所有的任务, 子任务和当前任务
        related_task_ids = sa.select(cte.c.id)

        # 软删除 tasks
        await self.session.execute(
            sa.update(Tasks)
            .where(Tasks.id.in_(related_task_ids), sa.not_(Tasks.is_deleted))
            .values(is_deleted=True, deleted_at=sa.func.now())
        )

        # 软删除若有任务的 chats
        await self.session.execute(
            sa.update(TasksChat)
            .where(
                TasksChat.task_id.in_(related_task_ids),
                sa.not_(TasksChat.is_deleted),
            )
            .values(is_deleted=True, deleted_at=sa.func.now())
        )

        # 软删除所有任务的 histories
        await self.session.execute(
            sa.update(TasksHistory)
            .where(
                TasksHistory.task_id.in_(related_task_ids),
                sa.not_(TasksHistory.is_deleted),
            )
            .values(is_deleted=True, deleted_at=sa.func.now())
        )

        # 若为根任务. 且 metainfo 未被删除, 则软删除.
        if db_obj.parent is None and not task.metadata_info.is_deleted:
            await self.tasks_metadata_repo.delete(db_obj.metadata_info)

        # 因为有事务装饰器的存在， 故这里所有的操作均为原子操作.
        await self.session.refresh(task)

        return task

    async def upget_paginator(
        self,
        paginator: Paginator,
    ) -> Paginator:
        query_stmt = sa.select(self.model).where(sa.not_(self.model.is_deleted))
        query_stmt = query_stmt.options(
            *self._get_chat_loader_options(self.default_limit_count)
        )
        query_stmt = query_stmt.options(
            *self._get_history_loader_options(self.default_limit_count)
        )

        return await super().upget_paginator_by_stmt(
            paginator=paginator,
            stmt=query_stmt,
        )

    async def get_dispatch_tasks_id(self) -> Sequence[int]:
        stmt = (
            sa.select(self.model.id)
            .where(
                sa.not_(self.model.is_deleted),
                self.model.state.in_([TaskState.INITIAL, TaskState.SCHEDULED]),
                self.model.expect_execute_time < sa.func.now(),
            )
            .order_by(
                self.model.expect_execute_time.asc(),
                self.model.priority.desc(),
                self.model.created_at.asc(),
            )
            .with_for_update(skip_locked=True)
        )

        result = await self.session.execute(stmt)

        tasks_id = result.scalars().unique().all()

        await self.session.execute(
            sa.update(self.model)
            .where(self.model.id.in_(tasks_id))
            .values(state=TaskState.ENQUEUED)
        )

        return tasks_id

```

## `/Users/askfiy/project/coding/taxonsk/core/features/tasks/router.py`

```python
import fastapi
from fastapi import Depends

from core.shared.models.http import (
    ResponseModel,
    Paginator,
    PaginationRequest,
    PaginationResponse,
)
from . import service as task_service
from .models import TaskInCRUDResponse, TaskCreateRequestModel, TaskUpdateRequestModel

tasks_route = fastapi.APIRouter(prefix="/tasks", tags=["Tasks"])


@tasks_route.post(
    path="",
    name="创建任务",
    status_code=fastapi.status.HTTP_201_CREATED,
    response_model=ResponseModel[TaskInCRUDResponse],
)
async def create(
    request_model: TaskCreateRequestModel,
) -> ResponseModel[TaskInCRUDResponse]:
    task = await task_service.create(request_model=request_model)
    return ResponseModel(result=TaskInCRUDResponse.model_validate(task))


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
        serializer_cls=TaskInCRUDResponse,
    )
    paginator = await task_service.upget_paginator(paginator=paginator)
    return paginator.response


@tasks_route.get(
    path="/{task_id}",
    name="获取某个任务",
    status_code=fastapi.status.HTTP_200_OK,
    response_model=ResponseModel[TaskInCRUDResponse],
)
async def get_by_id(
    task_id: int = fastapi.Path(description="任务 ID"),
) -> ResponseModel[TaskInCRUDResponse]:
    task = await task_service.get(task_id=task_id)
    return ResponseModel(result=TaskInCRUDResponse.model_validate(task))


@tasks_route.put(
    path="/{task_id}",
    name="更新某个任务",
    status_code=fastapi.status.HTTP_200_OK,
    response_model=ResponseModel[TaskInCRUDResponse],
)
async def update(
    request_model: TaskUpdateRequestModel,
    task_id: int = fastapi.Path(description="任务 ID"),
) -> ResponseModel[TaskInCRUDResponse]:
    task = await task_service.update(task_id=task_id, request_model=request_model)
    return ResponseModel(result=TaskInCRUDResponse.model_validate(task))


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

```

## `/Users/askfiy/project/coding/taxonsk/core/features/tasks/service.py`

```python
from collections.abc import Sequence

from core.shared.models.http import Paginator
from core.shared.database.session import (
    get_async_session_direct,
    get_async_tx_session_direct,
)
from core.shared.exceptions import ServiceNotFoundException, ServiceMissMessageException
from .table import Tasks
from .models import TaskCreateRequestModel, TaskUpdateRequestModel
from .repository import TasksCRUDRepository
from ..tasks_metadata.repository import TasksMetadataRepository


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


async def create(request_model: TaskCreateRequestModel) -> Tasks:
    async with get_async_tx_session_direct() as session:
        task_info = request_model.model_dump(exclude={"metadata"})

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

        elif request_model.metadata:
            tasks_metadata_repo = TasksMetadataRepository(
                session=session,
            )
            task_metadata = await tasks_metadata_repo.create(
                request_model.metadata.model_dump()
            )
            task_info["metadata_id"] = task_metadata.id
        else:
            raise ServiceMissMessageException(
                "创建任务时，必须提供 parent_id 或 metadata"
            )

        return await tasks_repo.create(create_info=task_info)


async def update(task_id: int, request_model: TaskUpdateRequestModel) -> Tasks:
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

```

## `/Users/askfiy/project/coding/taxonsk/core/features/tasks/table.py`

```python
import uuid
import datetime
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.shared.enums import TaskState
from core.shared.base.table import BaseTableModel
from core.shared.util.func import to_enum_values
from ..tasks_chat.table import TasksChat
from ..tasks_history.table import TasksHistory
from ..tasks_metadata.table import TasksMetadata


class Tasks(BaseTableModel):
    __tablename__ = "tasks"
    __table_args__ = (
        sa.Index(
            "idx_tasks_state_priority_time", "state", "priority", "expect_execute_time"
        ),
        {"comment": "任务表"},
    )

    name: Mapped[str] = mapped_column(
        sa.String(255), index=True, nullable=False, comment="任务的名称"
    )
    identifier: Mapped[uuid.UUID] = mapped_column(
        sa.CHAR(36),
        unique=True,
        nullable=False,
        default=uuid.uuid4,
        server_default=sa.text("UUID()"),
        comment="任务的标识符",
    )
    deep_level: Mapped[int] = mapped_column(
        sa.Integer,
        index=True,
        nullable=False,
        default=0,
        comment="任务的层级",
        server_default=sa.text("0"),
    )
    priority: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=0,
        index=True,
        comment="任务优先级",
        server_default=sa.text("0"),
    )
    expect_execute_time: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="任务预期执行时间",
        server_default=sa.func.now(),
    )
    lasted_execute_time: Mapped[Optional[datetime.datetime]] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
        default=None,
        index=True,
        comment="任务最终执行时间",
    )
    state: Mapped[TaskState] = mapped_column(
        sa.Enum(TaskState, values_callable=to_enum_values),
        nullable=False,
        default=TaskState.INITIAL,
        index=True,
        comment="任务当前状态",
        server_default=TaskState.INITIAL.value,
    )
    background: Mapped[str] = mapped_column(sa.Text, nullable=False, comment="任务背景")
    objective: Mapped[str] = mapped_column(sa.Text, nullable=False, comment="任务目标")
    details: Mapped[str] = mapped_column(
        sa.Text, nullable=False, comment="任务的详细信息"
    )
    is_decomposed: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        default=False,
        comment="已分解任务",
        server_default=sa.text("0"),
    )
    dependencies: Mapped[Optional[list[int]]] = mapped_column(
        sa.JSON,
        default=sa.func.json_array(),
        comment="同级任务依赖关系",
        server_default=sa.text("JSON_ARRAY()"),
    )

    parent_id: Mapped[Optional[int]] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("tasks.id"),
        nullable=True,
        index=True,
        comment="任务的父任务ID",
    )

    metadata_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("tasks_metadata.id"),
        nullable=False,
        index=True,
        comment="任务的元信息ID",
    )

    metadata_info: Mapped["TasksMetadata"] = relationship(
        back_populates="tasks_rel",
    )

    chats: Mapped[list["TasksChat"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by=TasksChat.created_at.desc(),
    )

    histories: Mapped[list["TasksHistory"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by=TasksHistory.created_at.desc(),
    )

    parent: Mapped[Optional["Tasks"]] = relationship(
        remote_side="Tasks.id",
        back_populates="children",
    )
    children: Mapped[list["Tasks"]] = relationship(
        back_populates="parent",
    )

```

## `/Users/askfiy/project/coding/taxonsk/core/features/tasks_audit/__init__.py`

```python

```

## `/Users/askfiy/project/coding/taxonsk/core/features/tasks_audit/models.py`

```python
import datetime

from core.shared.enums import TaskState, TaskAuditSource
from core.shared.base.model import BaseModel


class TaskAuditInCRUDResponse(BaseModel):
    from_state: TaskState
    to_state: TaskState
    source: TaskAuditSource
    source_context: str
    comment: str
    created_at: datetime.datetime


class TaskAuditCreateRequestModel(BaseModel):
    from_state: TaskState
    to_state: TaskState
    source: TaskAuditSource
    source_context: str
    comment: str

```

## `/Users/askfiy/project/coding/taxonsk/core/features/tasks_audit/repository.py`

```python
import sqlalchemy as sa

from core.shared.models.http import Paginator
from core.shared.base.repository import BaseCRUDRepository
from .table import TasksAudit


class TasksAuditRepository(BaseCRUDRepository[TasksAudit]):
    async def upget_paginator(
        self,
        task_id: int,
        paginator: Paginator,
    ) -> Paginator:
        query_stmt = sa.select(self.model).where(
            self.model.task_id == task_id, sa.not_(self.model.is_deleted)
        )

        return await super().upget_paginator_by_stmt(
            paginator=paginator,
            stmt=query_stmt,
        )

```

## `/Users/askfiy/project/coding/taxonsk/core/features/tasks_audit/router.py`

```python
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

```

## `/Users/askfiy/project/coding/taxonsk/core/features/tasks_audit/service.py`

```python
from core.shared.models.http import Paginator
from core.shared.database.session import (
    get_async_session_direct,
    get_async_tx_session_direct,
)
from core.shared.exceptions import ServiceNotFoundException
from .table import TasksAudit
from .models import TaskAuditCreateRequestModel
from .repository import TasksAuditRepository
from ..tasks.repository import TasksCRUDRepository


async def upget_paginator(task_id: int, paginator: Paginator) -> Paginator:
    async with get_async_session_direct() as session:
        tasks_audit_repo = TasksAuditRepository(session=session)

        return await tasks_audit_repo.upget_paginator(
            task_id=task_id,
            paginator=paginator,
        )


async def create(
    task_id: int, request_model: TaskAuditCreateRequestModel
) -> TasksAudit:
    async with get_async_tx_session_direct() as session:
        tasks_repo = TasksCRUDRepository(
            session=session,
        )
        task_exists = await tasks_repo.exists(pk=task_id)

        if not task_exists:
            raise ServiceNotFoundException(f"任务: {task_id} 不存在")

        tasks_audit_repo = TasksAuditRepository(session=session)

        return await tasks_audit_repo.create(
            create_info={"task_id": task_id, **request_model.model_dump()}
        )

```

## `/Users/askfiy/project/coding/taxonsk/core/features/tasks_audit/table.py`

```python
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from core.shared.enums import TaskState, TaskAuditSource
from core.shared.base.table import BaseTableModel
from core.shared.util.func import to_enum_values


class TasksAudit(BaseTableModel):
    __tablename__ = "tasks_audit"
    __table_args__ = (
        sa.Index("idx_tasks_audit_task_id_created_at", "task_id", "created_at"),
        {"comment": "任务状态审计表"},
    )

    task_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("tasks.id"),
        nullable=False,
        index=True,
        comment="关联任务ID",
    )

    from_state: Mapped[TaskState] = mapped_column(
        sa.Enum(TaskState, values_callable=to_enum_values),
        nullable=False,
        index=True,
        comment="任务执行状态",
    )

    to_state: Mapped[TaskState] = mapped_column(
        sa.Enum(TaskState, values_callable=to_enum_values),
        nullable=False,
        index=True,
        comment="任务执行状态",
    )

    source: Mapped[TaskAuditSource] = mapped_column(
        sa.Enum(TaskAuditSource, values_callable=to_enum_values),
        nullable=False,
        index=True,
        comment="触发变更的来源",
    )

    source_context: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
        comment="变更来源的上下文信息, 如 user_id, worker_id 等等 ..",
    )

    comment: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
        comment="变更上下文的注释, 为什么要变更. 变更背景是什么 ..",
    )

```

## `/Users/askfiy/project/coding/taxonsk/core/features/tasks_chat/__init__.py`

```python

```

## `/Users/askfiy/project/coding/taxonsk/core/features/tasks_chat/models.py`

```python
import datetime

from core.shared.enums import MessageRole
from core.shared.base.model import BaseModel


class TaskChatInCRUDResponse(BaseModel):
    message: str
    role: MessageRole
    created_at: datetime.datetime


class TaskChatCreateRequestModel(BaseModel):
    message: str
    role: MessageRole

```

## `/Users/askfiy/project/coding/taxonsk/core/features/tasks_chat/repository.py`

```python
import sqlalchemy as sa

from core.shared.models.http import Paginator
from core.shared.base.repository import BaseCRUDRepository
from .table import TasksChat


class TasksChatRepository(BaseCRUDRepository[TasksChat]):
    async def upget_paginator(
        self,
        task_id: int,
        paginator: Paginator,
    ) -> Paginator:
        query_stmt = sa.select(self.model).where(
            self.model.task_id == task_id, sa.not_(self.model.is_deleted)
        )

        return await super().upget_paginator_by_stmt(
            paginator=paginator,
            stmt=query_stmt,
        )

```

## `/Users/askfiy/project/coding/taxonsk/core/features/tasks_chat/router.py`

```python
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

```

## `/Users/askfiy/project/coding/taxonsk/core/features/tasks_chat/service.py`

```python
from core.shared.models.http import Paginator
from core.shared.database.session import (
    get_async_session_direct,
    get_async_tx_session_direct,
)
from core.shared.exceptions import ServiceNotFoundException
from .table import TasksChat
from .models import TaskChatCreateRequestModel
from .repository import TasksChatRepository
from ..tasks.repository import TasksCRUDRepository


async def upget_paginator(task_id: int, paginator: Paginator) -> Paginator:
    async with get_async_session_direct() as session:
        tasks_chat_repo = TasksChatRepository(session=session)

        return await tasks_chat_repo.upget_paginator(
            task_id=task_id,
            paginator=paginator,
        )


async def create(task_id: int, request_model: TaskChatCreateRequestModel) -> TasksChat:
    async with get_async_tx_session_direct() as session:
        tasks_repo = TasksCRUDRepository(
            session=session,
        )
        task_exists = await tasks_repo.exists(pk=task_id)

        if not task_exists:
            raise ServiceNotFoundException(f"任务: {task_id} 不存在")

        tasks_chat_repo = TasksChatRepository(session=session)

        return await tasks_chat_repo.create(
            create_info={"task_id": task_id, **request_model.model_dump()}
        )

```

## `/Users/askfiy/project/coding/taxonsk/core/features/tasks_chat/table.py`

```python
import typing
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.shared.enums import MessageRole
from core.shared.base.table import BaseTableModel
from core.shared.util.func import to_enum_values

if typing.TYPE_CHECKING:
    from ..tasks.table import Tasks


class TasksChat(BaseTableModel):
    __tablename__ = "tasks_chat"
    __table_args__ = (
        sa.Index("idx_tasks_chat_task_role", "task_id", "role"),
        {"comment": "任务聊天记录表"},
    )

    task_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("tasks.id"),
        nullable=False,
        index=True,
        comment="关联任务ID",
    )

    role: Mapped[MessageRole] = mapped_column(
        sa.Enum(MessageRole, values_callable=to_enum_values),
        nullable=False,
        index=True,
        comment="发送消息的角色",
    )

    message: Mapped[str] = mapped_column(sa.Text, nullable=False, comment="对话消息")

    task: Mapped["Tasks"] = relationship(
        back_populates="chats",
    )

```

## `/Users/askfiy/project/coding/taxonsk/core/features/tasks_history/__init__.py`

```python

```

## `/Users/askfiy/project/coding/taxonsk/core/features/tasks_history/models.py`

```python
import datetime

from core.shared.enums import TaskState
from core.shared.base.model import BaseModel


class TaskHistoryInCRUDResponse(BaseModel):
    state: TaskState
    process: str
    thinking: str
    created_at: datetime.datetime


class TaskHistoryCreateRequestModel(BaseModel):
    state: TaskState
    process: str
    thinking: str

```

## `/Users/askfiy/project/coding/taxonsk/core/features/tasks_history/repository.py`

```python
import sqlalchemy as sa

from core.shared.models.http import Paginator
from core.shared.base.repository import BaseCRUDRepository
from .table import TasksHistory


class TasksHistoryRepository(BaseCRUDRepository[TasksHistory]):
    async def upget_paginator(
        self,
        task_id: int,
        paginator: Paginator,
    ) -> Paginator:
        query_stmt = sa.select(self.model).where(
            self.model.task_id == task_id, sa.not_(self.model.is_deleted)
        )

        return await super().upget_paginator_by_stmt(
            paginator=paginator,
            stmt=query_stmt,
        )

```

## `/Users/askfiy/project/coding/taxonsk/core/features/tasks_history/router.py`

```python
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

```

## `/Users/askfiy/project/coding/taxonsk/core/features/tasks_history/service.py`

```python
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

```

## `/Users/askfiy/project/coding/taxonsk/core/features/tasks_history/table.py`

```python
import typing

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.shared.enums import TaskState
from core.shared.base.table import BaseTableModel
from core.shared.util.func import to_enum_values

if typing.TYPE_CHECKING:
    from ..tasks.table import Tasks


class TasksHistory(BaseTableModel):
    __tablename__ = "tasks_history"
    __table_args__ = (
        sa.Index("idx_tasks_history_task_state", "task_id", "state"),
        {"comment": "任务历史记录表"},
    )

    task_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("tasks.id"),
        nullable=False,
        index=True,
        comment="关联任务ID",
    )

    state: Mapped[TaskState] = mapped_column(
        sa.Enum(TaskState, values_callable=to_enum_values),
        nullable=False,
        index=True,
        comment="任务执行状态",
    )

    process: Mapped[str] = mapped_column(
        sa.Text, nullable=False, comment="任务执行过程"
    )

    thinking: Mapped[str] = mapped_column(
        sa.Text, nullable=False, comment="Agent 的思考过程"
    )

    task: Mapped["Tasks"] = relationship(
        back_populates="histories",
    )

```

## `/Users/askfiy/project/coding/taxonsk/core/features/tasks_metadata/__init__.py`

```python

```

## `/Users/askfiy/project/coding/taxonsk/core/features/tasks_metadata/models.py`

```python
from pydantic import field_serializer

from core.shared.base.model import BaseModel


# Tips: 我们的 keywords 入站规则是 list[str]. 但是 db 中是 str.
# 若要返回给外部。 则需要保持设计的一致性将其反序列化为 list[str].
# 目前 meta_info 不会出站. 故暂时搁置.
class TaskMetaDataRequestModel(BaseModel):
    owner: str
    owner_timezone: str
    keywords: list[str]
    original_user_input: str
    planning: str
    description: str
    accept_criteria: str

    @field_serializer("keywords")
    def _validator_keywords(self, keywords: list[str]) -> str:
        return ",".join(keywords)

```

## `/Users/askfiy/project/coding/taxonsk/core/features/tasks_metadata/repository.py`

```python
from core.shared.base.repository import BaseCRUDRepository
from .table import TasksMetadata


class TasksMetadataRepository(BaseCRUDRepository[TasksMetadata]):
    pass

```

## `/Users/askfiy/project/coding/taxonsk/core/features/tasks_metadata/table.py`

```python
from typing import TYPE_CHECKING


import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.shared.base.table import BaseTableModel

if TYPE_CHECKING:
    from ..tasks.table import Tasks


class TasksMetadata(BaseTableModel):
    __tablename__ = "tasks_metadata"
    __table_args__ = (
        sa.Index("idx_keywords_fulltext", "keywords", mysql_prefix="FULLTEXT"),
        {"comment": "任务元信息表"},
    )

    owner: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
        comment="任务所有者",
        index=True,
    )
    owner_timezone: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
        default="UTC",
        comment="所有者所在时区",
        server_default=sa.text("'UTC'"),
    )
    keywords: Mapped[str] = mapped_column(sa.Text, nullable=False, comment="关键字信息")
    original_user_input: Mapped[str] = mapped_column(
        sa.Text, nullable=False, comment="原始用户输入"
    )
    planning: Mapped[str] = mapped_column(sa.Text, nullable=False, comment="执行规划")
    description: Mapped[str] = mapped_column(
        sa.Text, nullable=False, comment="描述信息"
    )
    accept_criteria: Mapped[str] = mapped_column(
        sa.Text, nullable=False, comment="验收标准"
    )

    tasks_rel: Mapped[list["Tasks"]] = relationship(
        back_populates="metadata_info",
        foreign_keys="[Tasks.metadata_id]",
    )

```

## `/Users/askfiy/project/coding/taxonsk/core/handlers.py`

```python
import fastapi
from fastapi import Request
from fastapi.responses import JSONResponse

from core.shared.models.http import ResponseModel


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

```

## `/Users/askfiy/project/coding/taxonsk/core/logger.py`

```python
import sys
import logging
from typing import override

from colorlog import ColoredFormatter

from core.shared.globals import g


class Formatter(ColoredFormatter):
    @override
    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        super_time = super().formatTime(record, datefmt)
        return f"{super_time}.{int(record.msecs):03d}"

    @override
    def format(self, record: logging.LogRecord) -> str:
        record.space = " "
        record.trace_id = g.get("trace_id", "X-Trace-ID")

        record.timestamp = self.formatTime(record, self.datefmt)
        return super().format(record)


formatter = (
    "%(log_color)s%(levelname)s%(reset)s:"
    "%(white)s%(space)-5s%(reset)s"
    "[%(light_green)s%(timestamp)s%(reset)s] "
    "[%(light_blue)s%(name)s%(reset)s] - "
    "[%(light_yellow)s%(funcName)s:%(lineno)s]%(reset)s - "
    "[%(cyan)s%(trace_id)s%(reset)s] "
    "%(bold_white)s%(message)s%(reset)s"
)

console_formatter = Formatter(
    formatter,
    reset=True,
    log_colors={
        "DEBUG": "cyan",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "red,bg_white",
    },
    datefmt="%Y-%m-%d %H:%M:%S",
    secondary_log_colors={},
    style="%",
)


def setup_logging(level: int | str = logging.INFO) -> None:
    root_logger = logging.getLogger()

    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    root_logger.setLevel(level)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)

    root_logger.addHandler(console_handler)

    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_errors_logger = logging.getLogger("uvicorn.error")

    uvicorn_errors_logger.handlers.clear()
    uvicorn_access_logger.handlers.clear()

    uvicorn_errors_logger.propagate = True
    uvicorn_access_logger.propagate = False

```

## `/Users/askfiy/project/coding/taxonsk/core/router.py`

```python
import fastapi

from core.features.tasks.router import tasks_route
from core.features.tasks_chat.router import chats_route
from core.features.tasks_audit.router import audits_route
from core.features.tasks_history.router import histories_router

api_router = fastapi.APIRouter()

tasks_route.include_router(chats_route)
tasks_route.include_router(audits_route)
tasks_route.include_router(histories_router)

api_router.include_router(tasks_route)

```

## `/Users/askfiy/project/coding/taxonsk/core/shared/__init__.py`

```python

```

## `/Users/askfiy/project/coding/taxonsk/core/shared/base/model.py`

```python
import datetime
from typing import TypeVar
from pydantic.alias_generators import to_camel

import pydantic

T = TypeVar("T")

model_config = pydantic.ConfigDict(
    # 自动将 snake_case 字段名生成 camelCase 别名，用于 JSON 输出
    alias_generator=to_camel,
    # 允许在创建模型时使用别名（如 'taskId'）
    populate_by_name=True,
    # 允许从 ORM 对象等直接转换
    from_attributes=True,
    # 允许任意类型作为字段
    arbitrary_types_allowed=True,
    # 统一处理所有 datetime 对象的 JSON 序列化格式
    json_encoders={datetime.datetime: lambda dt: dt.isoformat().replace("+00:00", "Z")},
)


class BaseModel(pydantic.BaseModel):
    model_config = model_config


__all__ = ["BaseModel", "T"]

```

## `/Users/askfiy/project/coding/taxonsk/core/shared/base/repository.py`

```python
import typing
from typing import Any, Generic, TypeVar
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.ext.asyncio import AsyncSession

from .table import BaseTableModel
from core.shared.models.http import Paginator

ModelType = TypeVar("ModelType", bound=BaseTableModel)


class BaseCRUDRepository(Generic[ModelType]):
    """
    基本的 Crud Repository. 将自动提供 get/get_all/create/delete 等方法.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.model: type[ModelType] = typing.get_args(self.__class__.__orig_bases__[0])[  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
            0
        ]

    async def exists(self, pk: int) -> bool:
        exists_stmt = (
            sa.select(self.model.id)
            .where(self.model.id == pk, sa.not_(self.model.is_deleted))
            .exists()
        )

        stmt = sa.select(sa.literal(True)).where(exists_stmt)

        result = await self.session.execute(stmt)

        return result.scalar_one_or_none() is not None

    async def get(
        self, pk: int, joined_loads: list[InstrumentedAttribute[Any]] | None = None
    ) -> ModelType | None:
        """根据主键 ID 获取单个对象"""
        stmt = sa.select(self.model).where(
            self.model.id == pk, sa.not_(self.model.is_deleted)
        )

        if joined_loads:
            for join_field in joined_loads:
                stmt = stmt.options(joinedload(join_field))

        result = await self.session.execute(stmt)

        return result.unique().scalar_one_or_none()

    async def get_all(
        self, joined_loads: list[InstrumentedAttribute[Any]] | None = None
    ) -> Sequence[ModelType]:
        """获取所有未被软删除的对象"""
        stmt = sa.select(self.model).where(sa.not_(self.model.is_deleted))

        if joined_loads:
            for join_field in joined_loads:
                stmt = stmt.options(joinedload(join_field))

        result = await self.session.execute(stmt)
        return result.scalars().unique().all()

    async def create(self, create_info: dict[str, Any]) -> ModelType:
        """创建一个新对象"""
        db_obj = self.model(**create_info)
        self.session.add(db_obj)
        await self.session.flush()

        return db_obj

    async def delete(self, db_obj: ModelType) -> ModelType:
        """根据主键 ID 软删除一个对象"""
        db_obj.is_deleted = True

        self.session.add(db_obj)
        return db_obj

    async def update(self, db_obj: ModelType, update_info: dict[str, Any]) -> ModelType:
        """更新一个已有的对象"""
        for key, value in update_info.items():
            setattr(db_obj, key, value)

        self.session.add(db_obj)
        return db_obj

    async def upget_paginator_by_self(
        self,
        paginator: Paginator,
        joined_loads: list[InstrumentedAttribute[Any]] | None = None,
    ) -> Paginator:
        """
        更新返回默认的分页器.
        """
        stmt = sa.select(self.model).where(sa.not_(self.model.is_deleted))

        if joined_loads:
            for join_field in joined_loads:
                stmt = stmt.options(joinedload(join_field))

        return await self.upget_paginator_by_stmt(
            paginator=paginator,
            stmt=stmt,
        )

    async def upget_paginator_by_stmt(
        self,
        paginator: Paginator,
        stmt: sa.Select[Any],
    ) -> Paginator:
        """
        执行 stmt 语句. 更新返回分页器.
        """

        # 应用排序逻辑
        for field_name, order_direction in paginator.request.order_by_rule:
            if not hasattr(self.model, field_name):
                raise ValueError(
                    f"{self.model.__name__} is not has field'{field_name}'"
                )
            order_func = sa.asc if order_direction == "asc" else sa.desc
            stmt = stmt.order_by(order_func(getattr(self.model, field_name)))

        # 计算总记录数
        count_stmt = sa.select(sa.func.count()).select_from(stmt.subquery())
        total_items_result = await self.session.execute(count_stmt)

        # 应用分页逻辑
        paginated_stmt = stmt.offset(
            (paginator.request.page - 1) * paginator.request.size
        ).limit(paginator.request.size)

        result = await self.session.execute(paginated_stmt)

        paginator.with_serializer_response(
            total_counts=total_items_result.scalar_one(),
            orm_sequence=result.scalars().unique().all(),
        )

        return paginator

```

## `/Users/askfiy/project/coding/taxonsk/core/shared/base/table.py`

```python
from typing import Any
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.engine import Connection
from sqlalchemy.orm import DeclarativeBase, Mapped, Mapper, mapped_column
from sqlalchemy.orm.attributes import get_history


class BaseTableModel(DeclarativeBase):
    __abstract__ = True
    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        index=True,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=sa.func.now(),
        comment="创建时间",
    )

    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        index=True,
        nullable=True,
        onupdate=sa.func.now(),
        server_onupdate=sa.func.now(),
        comment="更新时间",
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
        comment="删除时间",
    )

    is_deleted: Mapped[bool] = mapped_column(
        sa.Boolean,
        index=True,
        default=False,
        server_default=sa.text("0"),
        nullable=False,
        comment="0：未删除 1：已删除",
    )

    @classmethod
    def __table_cls__(
        cls, table_name: str, metadata: sa.MetaData, *args: Any, **kwargs: Any
    ):
        # 在生成 table 时, 必须确保 ID 排在第一个
        columns = sorted(
            args,
            key=lambda field: 0
            if (isinstance(field, sa.Column) and field.name == "id")
            else 1,
        )
        return sa.Table(table_name, metadata, *columns, **kwargs)


@event.listens_for(BaseTableModel, "before_update", propagate=True)
def set_deleted_at_on_soft_delete(
    mapper: Mapper[Any], connection: Connection, obj: BaseTableModel
) -> None:
    """
    当 is_deleted 变更时，自动设置 deleted_at 字段。
    """
    history = get_history(obj, "is_deleted")

    if (
        history.added
        and history.added[0] is True
        and history.deleted
        and history.deleted[0] is False
    ):
        obj.deleted_at = datetime.now(timezone.utc)
    elif (
        history.added
        and history.added[0] is False
        and history.deleted
        and history.deleted[0] is True
    ):
        obj.deleted_at = None

```

## `/Users/askfiy/project/coding/taxonsk/core/shared/components/__init__.py`

```python
from .broker import RBroker
from .cacher import RCacher

__all__ = ["RBroker", "RCacher"]

```

## `/Users/askfiy/project/coding/taxonsk/core/shared/components/broker.py`

```python
import logging
import asyncio
from typing import Any, TypeAlias
from collections.abc import Callable, Coroutine
from datetime import datetime, timezone

import redis.asyncio as redis
from redis.typing import FieldT, EncodableT
from redis.exceptions import ResponseError
from pydantic import BaseModel, Field

RbrokerMessage: TypeAlias = Any


class RbrokerPayloadMetadata(BaseModel):
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RbrokerPayloadExcInfo(BaseModel):
    message: str
    type: str
    failed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RbrokerPayload(BaseModel):
    metadata: dict[str, Any] = Field(default_factory=dict)
    content: RbrokerMessage
    exc_info: RbrokerPayloadExcInfo | None = Field(default=None)


class RBroker:
    """
    基于 Redis Streams 实现的发布订阅系统
    """

    def __init__(self, redis_client: redis.Redis):
        self._client = redis_client
        self._consumer_tasks: list[asyncio.Task[None]] = []
        self._dlq_maxlen = 1000

    async def _handle_callback_ack(
        self,
        topic: str,
        group_id: str,
        message_id: str,
        rbroker_message: RbrokerPayload,
        callback: Callable[[RbrokerMessage], Coroutine[Any, Any, None]],
    ):
        try:
            await callback(rbroker_message.content)
        except Exception as exc:
            rbroker_message.exc_info = RbrokerPayloadExcInfo(
                message=str(exc), type=exc.__class__.__name__
            )
            # 放入死信队列. 后续可通过消费该死信队列获得新的讯息
            await self._client.xadd(
                f"{topic}-dlq",
                {"message": rbroker_message.model_dump_json()},
                maxlen=self._dlq_maxlen,
            )
            logging.error(
                f"Error in background task for message {message_id}: {exc}",
                exc_info=True,
            )
        finally:
            await self._client.xack(topic, group_id, message_id)

    async def _consume_worker(
        self,
        topic: str,
        group_id: str,
        consumer_name: str,
        callback: Callable[[RbrokerMessage], Coroutine[Any, Any, None]],
    ):
        while True:
            try:
                # xreadgroup 会阻塞，但只会阻塞当前这一个任务，不会影响其他任务
                # block 0 一直阻塞
                response = await self._client.xreadgroup(
                    group_id, consumer_name, {topic: ">"}, count=1, block=0
                )
                if not response:
                    continue

                stream_key, messages = response[0]
                message_id, data = messages[0]

                try:
                    rbroker_message = RbrokerPayload.model_validate_json(
                        data["message"]
                    )

                    asyncio.create_task(
                        self._handle_callback_ack(
                            topic=topic,
                            group_id=group_id,
                            message_id=message_id,
                            rbroker_message=rbroker_message,
                            callback=callback,
                        )
                    )

                except Exception as e:
                    logging.error(
                        f"Error processing message {message_id.decode()}: {e}",
                        exc_info=True,
                    )

            except asyncio.CancelledError:
                logging.info(f"Consumer '{consumer_name}' is shutting down.")
                break

            except Exception as e:
                logging.error(
                    f"Consumer '{consumer_name}' loop error: {e}", exc_info=True
                )
                await asyncio.sleep(5)

    async def send(self, topic: str, message: RbrokerMessage) -> str:
        rbroker_message = RbrokerPayload(content=message)

        message_payload: dict[FieldT, EncodableT] = {
            "message": rbroker_message.model_dump_json()
        }
        message_id = await self._client.xadd(topic, message_payload)
        logging.info(f"Sent message {message_id} to topic '{topic}'")
        return message_id

    async def consumer(
        self,
        topic: str,
        callback: Callable[[RbrokerMessage], Coroutine[Any, Any, None]],
        group_id: str | None = None,
        count: int = 1,
        *args: Any,
        **kwargs: Any,
    ):
        """
        创建并启动消费者后台任务。
        """
        group_id = group_id or topic + "_group"

        try:
            await self._client.xgroup_create(topic, group_id, mkstream=True)
            logging.info(f"Consumer group '{group_id}' created for topic '{topic}'.")
        except ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

        for i in range(count):
            consumer_name = f"{group_id}-consumer-{i + 1}"
            task = asyncio.create_task(
                self._consume_worker(topic, group_id, consumer_name, callback)
            )
            self._consumer_tasks.append(task)
            logging.info(f"Started consumer task '{consumer_name}' on topic '{topic}'.")

    async def shutdown(self):
        logging.info("Shutting down consumer tasks...")

        for task in self._consumer_tasks:
            task.cancel()

        await asyncio.gather(*self._consumer_tasks, return_exceptions=True)
        logging.info("All consumer tasks have been shut down.")

```

## `/Users/askfiy/project/coding/taxonsk/core/shared/components/cacher.py`

```python
import json
from typing import Any

import redis.asyncio as redis


class RCacher:
    """
    基于 Redis 实现的 Simple 缓存系统
    """

    def __init__(self, redis_client: redis.Redis):
        self._client = redis_client

    async def has(self, key: str) -> bool:
        return await self._client.exists(key) > 0

    async def get(self, key: str, default: Any = None) -> Any:
        value = await self._client.get(key)

        if value is None:
            return default

        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        if not ttl and await self._client.exists(key):
            current_ttl = await self._client.ttl(key)
            if current_ttl == -1:
                raise ValueError(
                    f"Key '{key}' exists without TTL. Refusing to set without TTL."
                )

        if isinstance(value, (dict, list)):
            value = json.dumps(value)

        await self._client.set(key, value, ex=ttl)

    async def delete(self, key: str) -> int:
        return await self._client.delete(key)

    async def persist(self, key: str) -> bool:
        current_ttl = await self._client.ttl(key)

        if current_ttl == -1:
            raise ValueError(f"Key '{key}' has no TTL. Cannot persist.")

        return await self._client.persist(key)

```

## `/Users/askfiy/project/coding/taxonsk/core/shared/database/connection.py`

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from core.config import env_helper


engine = create_async_engine(
    env_helper.ASYNC_DB_URL,
    # echo=True,
)


AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession,  # 明确指定使用 AsyncSession
)

__all__ = ["engine", "AsyncSessionLocal"]

```

## `/Users/askfiy/project/coding/taxonsk/core/shared/database/redis.py`

```python
import redis.asyncio as redis

from core.config import env_helper


pool: redis.ConnectionPool = redis.ConnectionPool.from_url(  # pyright: ignore[reportUnknownMemberType]
    url=env_helper.ASYNC_REDIS_URL, decode_responses=True
)

client = redis.Redis(connection_pool=pool)

__all__ = ["pool", "client"]

```

## `/Users/askfiy/project/coding/taxonsk/core/shared/database/session.py`

```python
from typing import TypeAlias
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from .connection import engine, AsyncSessionLocal

AsyncTxSession: TypeAlias = AsyncSession


async def get_async_session():
    async with AsyncSessionLocal(bind=engine) as session:
        yield session


async def get_async_tx_session():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as exc:
            await session.rollback()
            raise exc


get_async_session_direct = asynccontextmanager(get_async_session)
get_async_tx_session_direct = asynccontextmanager(get_async_tx_session)

__all__ = [
    "get_async_session",
    "get_async_tx_session",
    "get_async_session_direct",
    "get_async_tx_session_direct",
    "AsyncSession",
    "AsyncTxSession",
]

```

## `/Users/askfiy/project/coding/taxonsk/core/shared/database/tables.py`

```python
from core.features.tasks.table import Tasks
from core.features.tasks_chat.table import TasksChat
from core.features.tasks_audit.table import TasksAudit
from core.features.tasks_history.table import TasksHistory
from core.features.tasks_metadata.table import TasksMetadata

__all__ = ["Tasks", "TasksChat", "TasksAudit", "TasksHistory", "TasksMetadata"]

```

## `/Users/askfiy/project/coding/taxonsk/core/shared/dependencies.py`

```python
from fastapi import Header

from core.shared.database.session import (
    get_async_session,
    get_async_tx_session,
    AsyncSession,
    AsyncTxSession,
)


async def global_headers(
    x_trace_id: str | None = Header(
        default=None,
        alias="X-Trace-Id",
        description="用于分布式追踪的唯一 ID. 若未提供. 则 Taxonsk 将自动生成一个 uuid.",
    ),
):
    pass


__all__ = [
    "get_async_session",
    "get_async_tx_session",
    "AsyncSession",
    "AsyncTxSession",
    "global_headers",
]

```

## `/Users/askfiy/project/coding/taxonsk/core/shared/enums.py`

```python
from enum import StrEnum


class TaskState(StrEnum):
    # 任务建立状态
    INITIAL = "initial"
    # 任务等待调度
    SCHEDULED = "scheduled"
    # 任务进入队列
    ENQUEUED = "enqueued"
    # 任务正在执行
    ACTIVATING = "activating"
    # 任务等待子任务
    PENDING = "pending"
    # 任务等待用户输入
    WAITING = "waiting"
    # 任务正在重试
    RETRYING = "retrying"
    # 任务已被取消
    CANCEL = "cancel"
    # 任务已经完成
    FINISH = "finish"
    # 任务已经失败
    FAILED = "failed"


class MessageRole(StrEnum):
    USER = "user"
    SYSTEM = "system"
    ASSISTANT = "assistant"


class TaskAuditSource(StrEnum):
    """
    触发任务状态变更的“来源”枚举
    """

    USER = "user"
    ADMIN = "admin"
    AGENT = "agent"
    SYSTEM = "system"

```

## `/Users/askfiy/project/coding/taxonsk/core/shared/exceptions.py`

```python
class ServiceException(Exception):
    """服务层异常"""
    pass


class ServiceNotFoundException(ServiceException):
    """未找到记录"""
    pass


class ServiceMissMessageException(ServiceException):
    """缺少信息"""
    pass

```

## `/Users/askfiy/project/coding/taxonsk/core/shared/globals.py`

```python
from core.shared.middleware.context import g
from core.shared.database.redis import client
from core.shared.components import RBroker, RCacher

broker = RBroker(client)
cacher = RCacher(client)

__all__ = ["g", "broker", "cacher"]

```

## `/Users/askfiy/project/coding/taxonsk/core/shared/middleware/__init__.py`

```python
from .context import GlobalContextMiddleware
from .monitor import GlobalMonitorMiddleware

__all__ = ["GlobalContextMiddleware", "GlobalMonitorMiddleware"]

```

## `/Users/askfiy/project/coding/taxonsk/core/shared/middleware/context.py`

```python
from typing import Any, override
from contextvars import ContextVar, copy_context
from dataclasses import dataclass

from starlette.types import ASGIApp, Receive, Scope, Send


class GlobalContextException(Exception):
    pass


@dataclass
class Globals:
    _context_data = ContextVar("context_data", default={})

    def clear(self) -> None:
        self._context_data.set({})

    def get(self, name: str, default: Any = None) -> Any:
        return self._context_data.get().get(name, default)

    def __getattr__(self, name: str) -> Any:
        try:
            return self._context_data.get()[name]
        except KeyError:
            raise GlobalContextException(f"'{name}' is not found from global context.")

    @override
    def __setattr__(self, name: str, value: Any) -> None:
        self._context_data.get()[name] = value


class GlobalContextMiddleware:
    """
    ASGI 层面的中间件. 旨在提供类似于 Flask 的 g 对象.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        g.clear()

        ctx = copy_context()
        await ctx.run(self.app, scope, receive, send)


g = Globals()

```

## `/Users/askfiy/project/coding/taxonsk/core/shared/middleware/monitor.py`

```python
import time
import json
import uuid
import logging
import typing
from typing import override

from starlette.requests import Request
from starlette.responses import Response
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
    _StreamingResponse,  # pyright: ignore[reportPrivateUsage]
)
from starlette.types import Message


logger = logging.getLogger("monitor-middleware")


class GlobalMonitorMiddleware(BaseHTTPMiddleware):
    FILTER_API_PATH = ["/docs", "/openapi.json"]
    ENABLED_CONTENT_TYPE_PREFIXES = ["application/json", "text/"]
    MAX_BODY_LOG_LENGTH = 500

    def get_request_info(self, request: Request) -> str:
        method = request.method
        path = request.url.path
        query = request.url.query
        http_version = request.scope.get("http_version", "unknown")
        full_path = f"{path}?{query}" if query else path
        return f"{method} {full_path} HTTP/{http_version}"

    def get_body_log(self, body: bytes) -> str:
        if not body:
            return ""

        try:
            parsed = json.loads(body)
            return f", JSON: {json.dumps(parsed, ensure_ascii=False)}"
        except json.JSONDecodeError:
            decoded = body.decode(errors="ignore")
            return f", (Non-JSON): {decoded[: self.MAX_BODY_LOG_LENGTH]}{'...' if len(decoded) > self.MAX_BODY_LOG_LENGTH else ''}"

    async def get_response_body(self, response: _StreamingResponse) -> bytes:
        response_body_chunks: list[bytes] = []
        async for chunk in response.body_iterator:
            response_body_chunks.append(typing.cast("bytes", chunk))
        return b"".join(response_body_chunks)

    @override
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.url.path in self.FILTER_API_PATH:
            return await call_next(request)

        request_id = str(uuid.uuid4())
        request.scope["request_id"] = request_id

        request_info = self.get_request_info(request)

        request_body = await request.body()

        async def receive() -> Message:
            return {"type": "http.request", "body": request_body, "more_body": False}

        request_log = self.get_body_log(request_body)
        logger.info(f"[{request_id}] Request: '{request_info}'{request_log}")

        # Create a safe-to-read request
        new_request = Request(request.scope, receive)

        start_time = time.perf_counter()
        response: _StreamingResponse = await call_next(new_request)
        duration = (time.perf_counter() - start_time) * 1000
        status_code = response.status_code

        content_type = response.headers.get("content-type", "")

        if any(content_type.startswith(t) for t in self.ENABLED_CONTENT_TYPE_PREFIXES):
            response_body = await self.get_response_body(response)
            response_log = self.get_body_log(response_body)

            logger.info(
                f"[{request_id}] Response: '{request_info} {status_code}' ({duration:.2f}ms){response_log}"
            )

            return Response(
                content=response_body,
                status_code=status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

        logger.info(
            f"[{request_id}] Response: '{request_info} {status_code}' ({duration:.2f}ms)"
        )
        return response

```

## `/Users/askfiy/project/coding/taxonsk/core/shared/models/__init__.py`

```python

```

## `/Users/askfiy/project/coding/taxonsk/core/shared/models/http.py`

```python
import re
from typing import Generic, Literal, Any, TypeAlias
from collections.abc import Sequence

import pydantic
from pydantic import Field, computed_field
from pydantic.alias_generators import to_snake

from core.shared.base.model import BaseModel, T


class BaseHttpResponseModel(BaseModel):
    """
    为 Taxonsk API 设计的、标准化的泛型响应模型。
    """

    code: int = Field(default=200, description="状态码")
    message: str = Field(default="Success", description="响应消息")
    is_failed: bool = Field(default=False, description="是否失败")


class ResponseModel(BaseHttpResponseModel, Generic[T]):
    result: T | None = Field(default=None, description="响应体负载")


PaginationSerializer: TypeAlias = BaseModel


class PaginationRequest(BaseModel):
    """
    分页请求对象
    """

    page: int = Field(default=1, ge=1, description="页码, 从 1 开始")
    size: int = Field(
        default=10, ge=1, le=100, description="单页数量, 最小 1, 最大 100"
    )
    order_by: str | None = Field(
        default=None,
        description="排序字段/方向, 默认按照 id 进行 DESC 排序.",
        examples=["id=asc,createAt=desc", "id"],
    )

    @computed_field
    @property
    def order_by_rule(self) -> list[tuple[str, Literal["asc", "desc"]]]:
        order_by = self.order_by or "id=desc"

        _order_by = [item.strip() for item in order_by.split(",") if item.strip()]
        _struct_order_by: list[tuple[str, Literal["asc", "desc"]]] = []

        for item in _order_by:
            match = re.match(r"([\w_]+)(=(asc|desc))?", item, re.IGNORECASE)
            if match:
                field_name = to_snake(match.group(1))
                order_direction = match.group(3)
                direction: Literal["asc", "desc"] = "desc"
                if order_direction and order_direction.lower() == "asc":
                    direction = "asc"
                _struct_order_by.append((field_name, direction))
            else:
                raise pydantic.ValidationError(f"Invalid order_by format: {item}")

        return _struct_order_by


class PaginationResponse(BaseHttpResponseModel):
    """
    分页响应对象
    """

    current_page: int = Field(default=0, description="当前页")
    current_size: int = Field(default=0, description="当前数")
    total_counts: int = Field(default=0, description="总记录数")
    result: list[Any] = Field(default_factory=list, description="所有记录对象")

    @computed_field
    @property
    def total_pages(self) -> int:
        if self.current_size == 0:
            return 0
        return (self.total_counts + self.current_size - 1) // self.current_size


class Paginator(
    BaseModel,
):
    """
    分页器对象
    """

    serializer_cls: type[PaginationSerializer]
    request: PaginationRequest
    response: PaginationResponse = Field(
        default_factory=PaginationResponse, description="分页响应对象"
    )

    def with_serializer_response(
        self, total_counts: int, orm_sequence: Sequence[Any]
    ) -> None:
        self.response.current_page = self.request.page
        self.response.current_size = self.request.size
        self.response.total_counts = total_counts

        self.response.result = [
            self.serializer_cls.model_validate(obj) for obj in orm_sequence
        ]

```

## `/Users/askfiy/project/coding/taxonsk/core/shared/util/func.py`

```python
from enum import StrEnum


def to_enum_values(enum_class: type[StrEnum]) -> list[str]:
    return [e.value for e in enum_class]

```

## `/Users/askfiy/project/coding/taxonsk/core/types.py`

```python
from typing import TypeVar, ParamSpec

P = ParamSpec("P")
R = TypeVar("R")

```

## `/Users/askfiy/project/coding/taxonsk/main.py`

```python
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
from core.shared.dependencies import global_headers
from core.shared.globals import g
from core.shared.middleware import GlobalContextMiddleware, GlobalMonitorMiddleware

logger = logging.getLogger("Taxonsk")


@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    setup_logging()
    yield


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

```

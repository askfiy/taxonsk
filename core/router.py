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

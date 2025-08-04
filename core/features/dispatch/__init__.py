import asyncio

from core.shared.globals import broker
from core.features.tasks.service import get_dispatch_tasks_id, get
from .agent import TaskAgentProxy


async def start_producer(topic: str):
    while True:
        tasks_id = await get_dispatch_tasks_id()
        for task_id in tasks_id:
            await broker.send(topic=topic, message={"task_id": task_id})

        await asyncio.sleep(60)


async def start_consumer(message: dict[str, int]):
    task_id: int = message["task_id"]
    task_obj = await get(task_id=task_id)

    agent = TaskAgentProxy(task_obj=task_obj)
    await agent.execute()


async def open_dispatch():
    topic = "readonly-tasks"
    asyncio.create_task(start_producer(topic=topic))
    await broker.consumer(topic=topic, callback=start_consumer, count=5)


async def stop_dispatch():
    await broker.shutdown()

# services/audit-service/app/main.py
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.consumer import run_consumer
from app.routers import health


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(run_consumer())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Audit Service", version="0.1.0", lifespan=lifespan)
app.include_router(health.router)

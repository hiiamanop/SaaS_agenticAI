from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.consumer import start_consumer, stop_consumer
from app.routers import health, metrics


@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_consumer()
    yield
    await stop_consumer()


app = FastAPI(title="Analytics Service", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3001"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(metrics.router)

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import get_settings
from app.repository import repository

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    repository.recover_interrupted_analyses()
    yield


app = FastAPI(
    lifespan=lifespan,
    title=settings.app_name,
    version="0.2.0",
    description="Reproducible zero-training microscopy inference API for OrganChip Insight.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "documentation": "/docs",
        "health": f"{settings.api_v1_prefix}/health",
    }

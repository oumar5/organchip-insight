from fastapi import APIRouter

from app.api.routes import experiments, health, inference

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(inference.router, prefix="/inference", tags=["inference"])
api_router.include_router(experiments.router, prefix="/experiments", tags=["experiments"])

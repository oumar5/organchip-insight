from fastapi import APIRouter

from app.api.routes import experiments, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(experiments.router, prefix="/experiments", tags=["experiments"])


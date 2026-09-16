from fastapi import APIRouter

from app.ml.runtime import list_inference_engines
from app.schemas import AnalysisEngine

router = APIRouter()


@router.get("/engines", response_model=list[AnalysisEngine])
def get_inference_engines() -> list[AnalysisEngine]:
    return list_inference_engines()

from typing import Annotated

from fastapi import APIRouter, Header

from app.config import get_settings
from app.i18n import localize_engine, resolve_locale
from app.ml.runtime import list_inference_engines
from app.schemas import AnalysisEngine

router = APIRouter()


@router.get("/upload-limits")
def get_upload_limits() -> dict[str, int]:
    settings = get_settings()
    return {
        "max_upload_bytes": settings.max_upload_bytes,
        "max_image_pixels": settings.max_image_pixels,
    }


@router.get("/engines", response_model=list[AnalysisEngine])
def get_inference_engines(
    accept_language: Annotated[str | None, Header()] = None,
) -> list[AnalysisEngine]:
    locale = resolve_locale(accept_language)
    return [localize_engine(engine, locale) for engine in list_inference_engines()]

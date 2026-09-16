from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str | bool]:
    return {
        "status": "ok",
        "service": "organchip-insight-api",
        "version": "0.2.0",
        "inference_ready": True,
    }

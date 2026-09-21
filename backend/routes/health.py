from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/", summary="Confirm that the API is running")
async def home():
    return {"message": "Investment app backend is running"}


@router.get("/health", summary="Deployment health check")
async def health():
    return {"status": "healthy"}

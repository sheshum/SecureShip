from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/")
def root():
    return {"message": "Welcome to my FastAPI application!"}


@router.get("/health")
def get_health():
    return {"status": "healthy"}

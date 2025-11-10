from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def read_root():
    return {"message": "Speech to Text API is running."}

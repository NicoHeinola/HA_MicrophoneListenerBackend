from fastapi import APIRouter, Response

router = APIRouter()


@router.get("/")
def read_root():
    return {"message": "Speech to Text API is running."}


@router.get("/favicon.ico")
def favicon():
    return Response(status_code=204)

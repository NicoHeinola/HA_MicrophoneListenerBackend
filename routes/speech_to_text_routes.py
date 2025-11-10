from fastapi import APIRouter, Response

router = APIRouter()


@router.post("/start-listening")
def start_listening():
    return Response(status_code=200)


@router.post("/stop-listening")
def stop_listening():
    return Response(status_code=200)

import logging
import os
from threading import Thread
from time import sleep
from dotenv import load_dotenv
from fastapi import FastAPI
import requests
import uvicorn

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s")

from routes.index import router as index_router
from routes.listener_routes import router as speech_to_text_router

app = FastAPI()

# Include routes
app.include_router(index_router)
app.include_router(speech_to_text_router, prefix="/listener")


def start_listening():
    sleep(1)  # Wait for server to start

    URL: str = f"http://{os.getenv('HOST', '')}:{os.getenv('PORT', '')}"
    requests.post(
        f"{URL}/listener/start-listening",
        headers={"Authorization": f"Bearer {os.getenv('API_TOKEN', '')}"},
        json={"duration_seconds": 0},
    )


if __name__ == "__main__":
    load_dotenv()

    HOST: str = os.getenv("HOST", "")
    PORT: int = int(os.getenv("PORT", ""))
    HOT_RELOADING: bool = os.getenv("HOT_RELOADING", "False").lower() in ("true", "1", "t")
    API_TOKEN: str = os.getenv("API_TOKEN", "")

    # Send a start listening request after 1 second delay to allow the server to start
    Thread(target=start_listening).start()

    if HOT_RELOADING:
        uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
    else:
        uvicorn.run(app=app, host=HOST, port=PORT)

import logging
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from windiq.routes import router

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

app = FastAPI(title="WindIQ")
app.include_router(router)
app.mount(
    "/",
    StaticFiles(directory=Path(__file__).resolve().parents[2] / "frontend", html=True),
    name="frontend",
)

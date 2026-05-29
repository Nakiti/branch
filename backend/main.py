from contextlib import asynccontextmanager
import os

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import chat, fork, tree, merge, threads


@asynccontextmanager
async def lifespan(app: FastAPI):
    # DB and API clients are initialized lazily on first request
    yield


app = FastAPI(title="Branch API", lifespan=lifespan)

# FRONTEND_URL can be a single URL or a comma-separated list for multiple deployments
_origins = ["http://localhost:3000"]
for _url in os.getenv("FRONTEND_URL", "").split(","):
    _url = _url.strip().rstrip("/")
    if _url and _url not in _origins:
        _origins.append(_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api")
app.include_router(fork.router, prefix="/api")
app.include_router(tree.router, prefix="/api")
app.include_router(merge.router, prefix="/api")
app.include_router(threads.router, prefix="/api")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}

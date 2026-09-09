from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.chat import router as chat_router
from app.routes.internal import router as internal_router
from app.routes.videos import router as videos_router


def create_app() -> FastAPI:
    app = FastAPI(title="Agentic Video Understanding", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Accept-Ranges", "Content-Range", "Content-Length"],
    )
    app.include_router(videos_router)
    app.include_router(chat_router)
    app.include_router(internal_router)
    return app


app = create_app()

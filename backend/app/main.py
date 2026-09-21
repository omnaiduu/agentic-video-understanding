from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.routes.chat import router as chat_router
from app.routes.internal import router as internal_router
from app.routes.videos import router as videos_router
from app.settings import get_settings
from app.ui_gateway import proxy_ui, wants_ui


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

    @app.middleware("http")
    async def ui_gateway(request: Request, call_next):
        origin = str(get_settings().ui_origin or "").strip()
        if wants_ui(request.method, request.url.path, request.headers.get("accept") or "", origin):
            return await proxy_ui(request)
        return await call_next(request)

    return app


app = create_app()

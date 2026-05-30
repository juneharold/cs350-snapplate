from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.http_errors import init_error_handlers
from app.config.lifespan import lifespan
from app.controllers.home import api as home_router
from app.controllers.home import misc as misc_router

# Frontend base path is /v1 (handlers.ts:46)
V1 = "/v1"


def init_routers(app: FastAPI) -> None:
    # /health lives at the root (liveness)
    app.include_router(home_router)
    app.include_router(misc_router, prefix=V1, tags=["Misc"])


def init_middleware(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:3001"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def create_app() -> FastAPI:
    app = FastAPI(
        title="SnapPlate Server API",
        version="1.0.0",
        lifespan=lifespan,
    )
    init_middleware(app)
    init_routers(app)
    init_error_handlers(app)
    return app


app = create_app()

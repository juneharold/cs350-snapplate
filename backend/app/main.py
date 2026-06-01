from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.auth_middleware import AuthMiddleware
from app.config.http_errors import init_error_handlers
from app.config.lifespan import lifespan
from app.controllers.auth import api as auth_router
from app.controllers.home import api as home_router
from app.controllers.home import misc as misc_router
from app.controllers.me import api as me_router
from app.controllers.restaurants import api as restaurants_router
from app.controllers.settings import api as settings_router

# Frontend base path is /v1 (handlers.ts:46)
V1 = "/v1"


def init_routers(app: FastAPI) -> None:
    # /health lives at the root (liveness)
    app.include_router(home_router)
    # Domain routers under /v1. auth_router carries /auth/*.
    app.include_router(auth_router, prefix=V1, tags=["Auth"])
    app.include_router(me_router, prefix=V1, tags=["Profile"])
    app.include_router(restaurants_router, prefix=V1, tags=["Restaurants"])
    app.include_router(settings_router, prefix=V1, tags=["Settings"])
    app.include_router(misc_router, prefix=V1, tags=["Misc"])


def init_middleware(app: FastAPI) -> None:
    # AuthMiddleware added before CORS so CORS runs OUTERMOST (Starlette applies
    # middleware in reverse order of registration).
    app.add_middleware(AuthMiddleware)
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

"""Run with one worker: uvicorn server.app:app --host 127.0.0.1 --no-access-log."""

from contextlib import asynccontextmanager
from pathlib import Path
import logging
from urllib.parse import urlparse
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from authlib.integrations.starlette_client import OAuth
from .settings import Settings
from .db import Database
from .common import APIError
from . import identity, channels, messages, documents, activity, instructions


class SecretPathFilter(logging.Filter):
    """Uvicorn access records must not retain invite secrets or OIDC codes."""

    def filter(self, record):
        if isinstance(record.args, tuple) and len(record.args) >= 3:
            args = list(record.args)
            path = str(args[2])
            if "/invites/" in path or "/i/" in path or "/auth/" in path:
                args[2] = "[private authentication URL]"
                record.args = tuple(args)
        return True


class BoundaryMiddleware:
    def __init__(self, app, owner):
        self.app, self.owner = app, owner

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        count = 0

        async def bounded_receive():
            nonlocal count
            message = await receive()
            if message["type"] == "http.request":
                count += len(message.get("body", b""))
                if count > 2 * 1024 * 1024:
                    raise APIError(413, "INVALID_ARGUMENT", "Request is too large")
            return message

        async def secured_send(message):
            if message["type"] == "http.response.start":
                message["headers"] = list(message["headers"]) + [
                    (b"cache-control", b"no-store"),
                    (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"no-referrer"),
                    (b"x-frame-options", b"DENY"),
                    (
                        b"content-security-policy",
                        b"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
                    ),
                ]
                if (
                    scope["method"] in ("POST", "PATCH", "DELETE")
                    and message["status"] < 400
                ):
                    for listener in tuple(self.owner.state.listeners):
                        listener.set()
            await send(message)

        await self.app(scope, bounded_receive, secured_send)


def create_app(settings: Settings | None = None):
    config = settings or Settings.from_env()

    def initialize(app):
        config.validate()
        app.state.db = Database(config.database_path)

    @asynccontextmanager
    async def lifespan(app):
        if not hasattr(app.state, "db"):
            initialize(app)
        yield

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = config
    app.state.polls = set()
    app.state.listeners = set()
    app.state.oauth = None
    if settings is not None:
        initialize(app)
    if config.oidc_metadata_url:
        oauth = OAuth()
        oauth.register(
            name="provider",
            server_metadata_url=config.oidc_metadata_url,
            client_id=config.oidc_client_id,
            client_secret=config.oidc_client_secret,
            client_kwargs={
                "scope": "openid email profile",
                "code_challenge_method": "S256",
            },
        )
        app.state.oauth = oauth
    app.add_middleware(
        SessionMiddleware,
        secret_key=config.secret_key,
        session_cookie="codifica_oidc",
        https_only=not config.dev_auth,
        same_site="lax",
        max_age=600,
    )
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[urlparse(config.origin).hostname or "localhost"],
    )
    app.add_middleware(BoundaryMiddleware, owner=app)
    logging.getLogger("uvicorn.access").addFilter(SecretPathFilter())

    @app.exception_handler(APIError)
    async def api_error(request: Request, error: APIError):
        return JSONResponse(
            error.payload,
            status_code=error.status,
            headers={"Retry-After": "1"} if error.status == 429 else None,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError):
        return JSONResponse(
            dict(
                code="INVALID_ARGUMENT", message="Invalid request fields or parameters"
            ),
            status_code=400,
        )

    for module in (identity, channels, messages, documents, activity, instructions):
        app.include_router(module.router, prefix="/api/v1")

    @app.get("/health")
    def health():
        with app.state.db.connect() as db:
            db.execute("SELECT 1")
        return {"status": "ok"}

    @app.get("/{path:path}")
    def frontend(path: str):
        if path.startswith("api/"):
            return JSONResponse(
                dict(code="NOT_FOUND", message="API endpoint not found"),
                status_code=404,
            )
        root = Path(__file__).resolve().parent.parent / "web" / "dist"
        candidate = (root / path).resolve()
        if candidate.is_relative_to(root) and candidate.is_file():
            return FileResponse(candidate)
        if (root / "index.html").is_file():
            return FileResponse(root / "index.html")
        return JSONResponse(
            dict(
                code="NOT_FOUND",
                message="Build the web client or use the Vite development server",
            ),
            status_code=404,
        )

    return app


app = create_app()

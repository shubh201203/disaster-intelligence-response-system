import os
from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.config import settings
from app.database import engine, Base
from app.core.websocket_manager import ws_manager

# Import routers
from app.routers import health, auth, users, incidents, shelters, volunteers, resources, alerts, analytics, ai, rag, recommendations, gis, simulation, recovery, recovery_optimization

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.on_event("startup")
def startup_event():
    if engine.dialect.name == "postgresql":
        try:
            with engine.begin() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        except Exception:
            pass  # PostGIS is provisioned by DBA; application operates with least privilege
    Base.metadata.create_all(bind=engine)

# Request Payload Size Limiter Middleware (Default 10MB, handles Content-Length and chunked streams)
@app.middleware("http")
async def request_size_limiter_middleware(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            cl = int(content_length)
            if cl > settings.MAX_REQUEST_BODY_BYTES:
                return JSONResponse(
                    status_code=413,
                    content={
                        "detail": f"Payload too large. Maximum permitted request body is {settings.MAX_REQUEST_BODY_BYTES} bytes."
                    }
                )
        except ValueError:
            pass

    # Safeguard against chunked or streaming uploads without Content-Length
    received_bytes = 0
    original_receive = request.receive

    async def counted_receive():
        nonlocal received_bytes
        message = await original_receive()
        if message["type"] == "http.request":
            body = message.get("body", b"")
            received_bytes += len(body)
            if received_bytes > settings.MAX_REQUEST_BODY_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"Payload too large. Streaming request exceeded {settings.MAX_REQUEST_BODY_BYTES} bytes."
                )
        return message

    request._receive = counted_receive
    return await call_next(request)

# HTTP Security Headers Middleware (Content Security Policy, frame options, MIME sniffing)
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    # Modern OWASP standard: disable legacy buggy X-XSS-Protection auditor in favor of modern CSP
    response.headers["X-XSS-Protection"] = "0"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(self), microphone=(), camera=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob: https://*.tile.openstreetmap.org; "
        "connect-src 'self' http://localhost:* http://127.0.0.1:* ws://localhost:* ws://127.0.0.1:* wss: https:; "
        "font-src 'self' data:; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "frame-ancestors 'none'"
    )
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# Hardened CORS configuration with explicit origins
allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://testserver",
]
env_origins = os.getenv("ALLOWED_ORIGINS")
if env_origins:
    for origin in env_origins.split(","):
        cleaned = origin.strip()
        if cleaned and cleaned not in allowed_origins:
            allowed_origins.append(cleaned)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Length", "X-Idempotency-Key", "Idempotency-Key", "X-Cache-Lookup"],
)

# Ensure upload directory exists
os.makedirs(settings.MEDIA_UPLOAD_DIR, exist_ok=True)
app.mount("/static/uploads", StaticFiles(directory=settings.MEDIA_UPLOAD_DIR), name="uploads")

# Include Routers
app.include_router(health.router, prefix=settings.API_V1_STR)
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(users.router, prefix=settings.API_V1_STR)
app.include_router(incidents.router, prefix=settings.API_V1_STR)
app.include_router(shelters.router, prefix=settings.API_V1_STR)
app.include_router(volunteers.router, prefix=settings.API_V1_STR)
app.include_router(resources.router, prefix=settings.API_V1_STR)
app.include_router(alerts.router, prefix=settings.API_V1_STR)
app.include_router(analytics.router, prefix=settings.API_V1_STR)
app.include_router(ai.router, prefix=settings.API_V1_STR)
app.include_router(rag.router, prefix=settings.API_V1_STR)
app.include_router(recommendations.router, prefix=settings.API_V1_STR)
app.include_router(gis.router, prefix=settings.API_V1_STR)
app.include_router(simulation.router, prefix=settings.API_V1_STR)
app.include_router(recovery.router, prefix=settings.API_V1_STR)
app.include_router(recovery_optimization.router, prefix=settings.API_V1_STR)

# Real-time WebSocket endpoint
@app.websocket("/ws/feed")
async def websocket_feed(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo or process incoming ping/heartbeat
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

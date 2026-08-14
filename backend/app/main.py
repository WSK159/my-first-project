from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import init_db
from .routers import auth, billing, delivery, keys, projects

init_db()

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(delivery.router, prefix="/api/delivery", tags=["delivery"])
app.include_router(billing.router, prefix="/api/billing", tags=["billing"])
app.include_router(keys.router, prefix="/api/keys", tags=["keys"])


@app.on_event("startup")
def startup_resume() -> None:
    """启动时自动恢复未完成项目（断点续跑）。"""
    from .workers.pipeline_runner import resume_projects

    resume_projects()


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}


@app.get("/api/health")
def api_health():
    return {"status": "ok", "app": settings.app_name}

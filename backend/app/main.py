from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings

app = FastAPI(
    title="CareAlign API",
    version=settings.app_version,
    description=(
        "Research prototype for source-linked care-instruction comparison and teach-back. "
        "Not medical advice."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-CI-Token"],
)

app.include_router(router, prefix="/api")

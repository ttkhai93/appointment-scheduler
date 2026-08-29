from fastapi import APIRouter

from app.dependencies import DbSession
from app.services.health import check_database

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(session: DbSession):
    return {
        "status": "ok",
        "database": "ok" if await check_database(session) else "unreachable",
    }

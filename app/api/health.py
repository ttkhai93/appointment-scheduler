from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db

router = APIRouter(tags=["health"])
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("/health")
async def health(db: DbSession):
    try:
        await db.execute(text("SELECT 1"))
        database = "ok"
    except SQLAlchemyError:
        database = "unreachable"
    return {"status": "ok", "database": database}

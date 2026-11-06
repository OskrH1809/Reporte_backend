from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db

router = APIRouter(prefix="/api", tags=["health"])


class HealthRead(BaseModel):
    status: Literal["ok"]


@router.get("/health", response_model=HealthRead)
def health(session: Annotated[Session, Depends(get_db)]) -> HealthRead:
    session.execute(text("SELECT 1"))
    return HealthRead(status="ok")

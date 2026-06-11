import os
import sqlite3
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from backend.app.config import settings

router = APIRouter(tags=["agent_suggestions"])


def get_db_path():
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    if not os.path.isabs(db_path):
        project_root = Path(__file__).parent.parent.parent.parent.parent
        db_path = str((project_root / db_path).resolve())
    return db_path


def init_tables():
    from core.schema import init_db as _core_init_db  # noqa: WPS433

    _core_init_db()


# Initialize tables when module loads
init_tables()


class FailedToolCallSchema(BaseModel):
    tool_name: str
    arguments: str
    error_message: str


class IntentionalPathSchema(BaseModel):
    agent_id: str
    intention: str
    missing_tools: str
    context: str


@router.post("/failed_tool_calls")
def log_failed_tool_call(call: FailedToolCallSchema):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO failed_tool_calls (timestamp, tool_name, arguments, error_message)
        VALUES (?, ?, ?, ?)
    """,
        (datetime.now().isoformat(), call.tool_name, call.arguments, call.error_message),
    )
    conn.commit()
    conn.close()
    return {"status": "success"}


@router.post("/intentional_paths")
def log_intentional_path(path: IntentionalPathSchema):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO intentional_paths (timestamp, agent_id, intention, missing_tools, context)
        VALUES (?, ?, ?, ?, ?)
    """,
        (datetime.now().isoformat(), path.agent_id, path.intention, path.missing_tools, path.context),
    )
    conn.commit()
    conn.close()
    return {"status": "success"}


@router.get("/intentional_paths", response_model=list[dict])
def get_intentional_paths():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM intentional_paths ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

"""Operations ledger API — views of real, timed operations, and cancel.

Operations are created by the services that perform them (render jobs,
broadcasts, workings); see core/operations.py. Live changes are pushed over
the WebSocket as ``{"type": "operation_update", "data": <operation>}``.
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from core import operations

router = APIRouter(prefix="/operations", tags=["operations"])


@router.get("")
async def list_operations(
    kind: str | None = None,
    status: str | None = None,
    working_id: str | None = None,
    limit: int = Query(50, ge=1, le=500),
) -> dict[str, Any]:
    if kind is not None and kind not in operations.KINDS:
        raise HTTPException(status_code=422, detail=f"unknown kind {kind!r}")
    if status is not None and status not in operations.STATUSES:
        raise HTTPException(status_code=422, detail=f"unknown status {status!r}")
    ops = operations.list_operations(kind=kind, status=status, working_id=working_id, limit=limit)
    return {"operations": ops, "count": len(ops)}


@router.get("/summary")
async def summarize_operations(since: str | None = None) -> dict[str, Any]:
    return operations.summarize_operations(since=since)


@router.get("/{op_id}")
async def get_operation(op_id: str) -> dict[str, Any]:
    op = operations.get_operation(op_id)
    if op is None:
        raise HTTPException(status_code=404, detail="operation not found")
    return op


@router.post("/{op_id}/cancel")
async def cancel_operation(op_id: str) -> dict[str, Any]:
    """Stop an active operation (spec contract W2-3).

    ``200 {"operation"}`` once it has ended (normally ``cancelled``, with the
    measured elapsed time); ``404`` for an unknown id; ``409`` when it is
    already finished or nothing in this process can stop its kind.
    """
    try:
        op = await operations.request_cancel(op_id)
    except operations.OperationNotFound:
        raise HTTPException(status_code=404, detail="operation not found") from None
    except operations.OperationNotCancellable as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    return {"operation": op}

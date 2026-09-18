"""Serving the portraits people uploaded for their own ducks (D44)."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.web.deps import PortraitsDep

router = APIRouter(prefix="/portraits")


@router.get("/{name}")
async def portrait(portraits: PortraitsDep, name: str) -> FileResponse:
    # Only names the store itself would make are looked up, so a request can never
    # reach a file outside the portraits folder.
    path = portraits.path(name)
    if path is None:
        raise HTTPException(status_code=404, detail="No such portrait.")
    # A name is never reused for different pixels, so the browser can keep it for good.
    return FileResponse(
        path,
        media_type="image/jpeg",
        headers={"cache-control": "private, max-age=31536000, immutable"},
    )

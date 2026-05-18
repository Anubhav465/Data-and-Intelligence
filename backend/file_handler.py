# backend/file_handler.py
"""
CSV upload validation and temporary file persistence.
"""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

# ── Constants ──────────────────────────────────────────────────────────────
MAX_FILE_SIZE_BYTES: int = 40 * 1024 * 1024          # 40 MB hard limit
TEMP_DIR: Path = Path(__file__).parent / "uploads_tmp"  # relative to backend/


def _generate_table_name() -> str:
    """Return a unique, PostgreSQL-safe table identifier."""
    return f"user_table_{uuid.uuid4().hex[:12]}"


async def save_csv_upload(file: UploadFile) -> tuple[str, str]:
    """
    Validate and persist an uploaded file to TEMP_DIR.

    Returns:
        (absolute_file_path, generated_table_name)

    Raises:
        HTTPException 400 – wrong extension or empty file
        HTTPException 413 – file exceeds MAX_FILE_SIZE_BYTES
    """
    filename = file.filename or ""
    ext = Path(filename).suffix.lower()
    if ext != ".csv":
        raise HTTPException(
            status_code=400,
            detail=f"Only .csv files are accepted. Received: '{ext or 'no extension'}'",
        )

    content: bytes = await file.read()

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if len(content) > MAX_FILE_SIZE_BYTES:
        mb_received = len(content) / (1024 * 1024)
        mb_limit = MAX_FILE_SIZE_BYTES / (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"File is {mb_received:.1f} MB; limit is {mb_limit:.0f} MB.",
        )

    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    table_name = _generate_table_name()
    dest = TEMP_DIR / f"{table_name}.csv"
    dest.write_bytes(content)

    return str(dest), table_name


def cleanup_temp_file(file_path: str) -> None:
    """Delete a temporary CSV file after it has been ingested."""
    try:
        Path(file_path).unlink(missing_ok=True)
    except OSError:
        pass  # best-effort cleanup

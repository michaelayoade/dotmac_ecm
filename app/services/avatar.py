import os
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import settings

JPEG_SIGNATURE = b"\xff\xd8\xff"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
GIF_SIGNATURE = b"GIF8"
WEBP_RIFF_SIGNATURE = b"RIFF"
WEBP_FORMAT_SIGNATURE = b"WEBP"


def get_allowed_types() -> set[str]:
    return set(settings.avatar_allowed_types.split(","))


def validate_avatar(file: UploadFile, file_header: bytes | None = None) -> None:
    allowed_types = get_allowed_types()
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(sorted(allowed_types))}",
        )

    if file_header is None:
        return

    detected_type = _detect_content_type_from_magic(file_header)
    if detected_type is None:
        raise HTTPException(
            status_code=415,
            detail="Invalid file signature for avatar upload.",
        )

    if detected_type not in allowed_types:
        raise HTTPException(
            status_code=415,
            detail=f"Invalid file signature. Allowed: {', '.join(sorted(allowed_types))}",
        )

    if detected_type != file.content_type:
        raise HTTPException(
            status_code=415,
            detail="File content does not match declared content type.",
        )


async def save_avatar(file: UploadFile, person_id: str) -> str:
    content = await file.read()
    validate_avatar(file, content[:512])

    if len(content) > settings.avatar_max_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {settings.avatar_max_size_bytes // 1024 // 1024}MB",
        )

    upload_dir = Path(settings.avatar_upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    ext = _get_extension(file.content_type)
    filename = f"{person_id}_{uuid.uuid4().hex[:8]}{ext}"
    file_path = upload_dir / filename

    with open(file_path, "wb") as f:
        f.write(content)

    return f"{settings.avatar_url_prefix}/{filename}"


def delete_avatar(avatar_url: str | None) -> None:
    if not avatar_url:
        return

    if avatar_url.startswith(settings.avatar_url_prefix):
        filename = avatar_url.replace(settings.avatar_url_prefix + "/", "")
        file_path = Path(settings.avatar_upload_dir) / filename
        if file_path.exists():
            os.remove(file_path)


def _get_extension(content_type: str) -> str:
    extensions = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
    }
    return extensions.get(content_type, ".jpg")


def _detect_content_type_from_magic(file_header: bytes) -> str | None:
    if file_header.startswith(JPEG_SIGNATURE):
        return "image/jpeg"
    if file_header.startswith(PNG_SIGNATURE):
        return "image/png"
    if file_header.startswith(GIF_SIGNATURE):
        return "image/gif"
    if (
        file_header.startswith(WEBP_RIFF_SIGNATURE)
        and len(file_header) >= 12
        and file_header[8:12] == WEBP_FORMAT_SIGNATURE
    ):
        return "image/webp"
    return None

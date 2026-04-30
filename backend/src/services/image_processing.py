from io import BytesIO

from PIL import Image, UnidentifiedImageError

from src.core.exceptions import UnsupportedImageFormat

SUPPORTED_FORMATS: dict[str, str] = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
}

# Receipt OCR doesn't benefit from resolution above this; keeping images small
# dramatically reduces VLM inference time and payload size.
MAX_SIDE_PX = 1536


def process_image(data: bytes) -> tuple[bytes, str, str]:
    """Validate, sniff format, strip EXIF/metadata, and downscale large images.

    Returns (re-encoded bytes, mime_type, pillow format name).
    Raises UnsupportedImageFormat if the bytes aren't a JPEG or PNG.
    """
    try:
        img = Image.open(BytesIO(data))
        img.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise UnsupportedImageFormat("not a recognizable image") from exc

    fmt = img.format or ""
    if fmt not in SUPPORTED_FORMATS:
        raise UnsupportedImageFormat(fmt)

    # Downscale if either dimension exceeds the cap (preserves aspect ratio).
    if max(img.size) > MAX_SIDE_PX:
        img.thumbnail((MAX_SIDE_PX, MAX_SIDE_PX), Image.LANCZOS)

    buf = BytesIO()
    if fmt == "JPEG":
        if img.mode != "RGB":
            img = img.convert("RGB")
        img.save(buf, format="JPEG", quality=85, optimize=True)
    else:
        img.save(buf, format="PNG", optimize=True)

    return buf.getvalue(), SUPPORTED_FORMATS[fmt], fmt

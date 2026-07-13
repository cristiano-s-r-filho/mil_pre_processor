import io
import logging
import os

import cv2
import numpy as np
from PIL import Image

from mil.config import get

logger = logging.getLogger(__name__)


def _thumbnail_from_array(arr: np.ndarray, size: int) -> tuple[np.ndarray, tuple[int, int]]:
    orig_h, orig_w = arr.shape[:2]
    scale = min(size / orig_w, size / orig_h)
    if scale < 1:
        new_w = int(orig_w * scale)
        new_h = int(orig_h * scale)
        arr = cv2.resize(arr, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return arr, (orig_w, orig_h)


def _decode_jpeg_tiff(path: str, size: int) -> tuple[np.ndarray, tuple[int, int]] | None:
    with open(path, "rb") as f:
        raw = f.read()
    if raw[:4] != b"\x49\x49\x2a\x00" or raw[4:8] != b"\x08\x00\x00\x00":
        return None
    jpeg_data = raw[8:]
    arr = cv2.imdecode(np.frombuffer(jpeg_data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if arr is not None:
        thumb, orig = _thumbnail_from_array(arr, size)
        return thumb, orig
    try:
        buf = io.BytesIO(jpeg_data)
        img = Image.open(buf)
        orig = img.size
        img.thumbnail((size, size), Image.LANCZOS)
        thumb = np.array(img.convert("RGB"))[:, :, ::-1]
        return thumb, orig
    except Exception:
        pass
    return None


def read_thumbnail(path: str, size: int | None = None) -> tuple[np.ndarray, tuple[int, int]] | None:
    if size is None:
        size = get("reader.thumbnail_size", 1024)

    max_pixels = get("reader.pil_max_image_pixels", 500_000_000)
    Image.MAX_IMAGE_PIXELS = max_pixels

    file_size = os.path.getsize(path)
    if file_size == 0:
        logger.warning("Arquivo vazio (0 bytes): %s", path)
        return None
    try:
        img = Image.open(path)
        orig = img.size
        img.thumbnail((size, size), Image.LANCZOS)
        thumb = np.array(img.convert("RGB"))[:, :, ::-1]
        return thumb, orig
    except Exception:
        pass
    result = _decode_jpeg_tiff(path, size)
    if result is not None:
        return result
    logger.warning("Formato de imagem nao reconhecido: %s", path)
    return None
